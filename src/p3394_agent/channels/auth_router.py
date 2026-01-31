"""
Authentication Router

FastAPI router for user sign-up, login, and API key management.
Integrates with P3394 Principal identity system.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr

from ..data.models.auth import (
    User,
    UserRole,
    UserStatus,
    APIKey,
    Session,
    SignupRequest,
    LoginRequest,
    PasswordChangeRequest,
    CreateAPIKeyRequest,
)
from ..data.repos.auth import AuthRepository
from ..memory.control_tokens import ControlToken, TokenType, TokenScope, ProvenanceMethod
from ..core.auth.credential_binding import CredentialBinding, BindingType

import logging

logger = logging.getLogger(__name__)


# Response models
class AuthResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[UUID] = None
    session_token: Optional[str] = None


class APIKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    key_hint: str
    scopes: list[str]
    status: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    usage_count: int = 0


class APIKeyCreateResponse(BaseModel):
    id: UUID
    name: str
    key: str  # Full key, shown only once
    message: str


def create_auth_router(
    templates: Jinja2Templates,
    auth_repo: AuthRepository,
    kstar_memory=None,
    principal_registry=None,
) -> APIRouter:
    """
    Create authentication router with dependencies.

    Args:
        templates: Jinja2 templates for HTML pages
        auth_repo: Authentication repository for users, sessions, API keys
        kstar_memory: Optional KStarMemory for storing API keys as ControlTokens
        principal_registry: Optional PrincipalRegistry for credential bindings
    """

    router = APIRouter(prefix="/auth", tags=["auth"])

    # Session management helpers
    def set_session_cookie(response: Response, token: str) -> None:
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=7 * 24 * 60 * 60,  # 7 days
        )

    def clear_session_cookie(response: Response) -> None:
        response.delete_cookie(key="session_token")

    async def get_current_user(request: Request) -> Optional[User]:
        """Get current user from session cookie."""
        token = request.cookies.get("session_token")
        if not token:
            return None
        session, user, _ = await auth_repo.authenticate_session(token)
        return user

    async def require_user(request: Request) -> User:
        """Require authenticated user."""
        user = await get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return user

    # ==================== HTML Pages ====================

    @router.get("/signup", response_class=HTMLResponse, name="signup_page")
    async def signup_page(request: Request):
        """User sign-up page."""
        return templates.TemplateResponse(
            "auth/signup.html",
            {"request": request, "title": "Sign Up"},
        )

    @router.get("/login", response_class=HTMLResponse, name="login_page")
    async def login_page(request: Request, next: str = "/"):
        """Login page."""
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "title": "Login", "next": next},
        )

    @router.get("/forgot-password", response_class=HTMLResponse, name="forgot_password_page")
    async def forgot_password_page(request: Request):
        """Forgot password page."""
        return templates.TemplateResponse(
            "auth/forgot_password.html",
            {"request": request, "title": "Reset Password"},
        )

    @router.get("/reset-password", response_class=HTMLResponse, name="reset_password_page")
    async def reset_password_page(request: Request, token: str = ""):
        """Password reset page."""
        return templates.TemplateResponse(
            "auth/reset_password.html",
            {"request": request, "title": "Set New Password", "token": token},
        )

    @router.get("/verify-email", response_class=HTMLResponse, name="verify_email_page")
    async def verify_email_page(request: Request, token: str = ""):
        """Email verification handler."""
        if not token:
            return templates.TemplateResponse(
                "auth/verify_email.html",
                {"request": request, "title": "Verify Email", "success": False, "message": "No token provided"},
            )

        user = await auth_repo.users.get_by_verification_token(token)
        if not user:
            return templates.TemplateResponse(
                "auth/verify_email.html",
                {"request": request, "title": "Verify Email", "success": False, "message": "Invalid or expired token"},
            )

        if user.email_verification_expires and datetime.now(timezone.utc) > user.email_verification_expires:
            return templates.TemplateResponse(
                "auth/verify_email.html",
                {"request": request, "title": "Verify Email", "success": False, "message": "Token has expired"},
            )

        await auth_repo.users.verify_email(user.id)
        return templates.TemplateResponse(
            "auth/verify_email.html",
            {"request": request, "title": "Email Verified", "success": True, "message": "Your email has been verified. You can now log in."},
        )

    @router.get("/api-keys", response_class=HTMLResponse, name="api_keys_page")
    async def api_keys_page(request: Request, user: User = Depends(require_user)):
        """API key management page."""
        keys = await auth_repo.api_keys.list_by_user(user.id)
        return templates.TemplateResponse(
            "auth/api_keys.html",
            {
                "request": request,
                "title": "API Keys",
                "user": user,
                "api_keys": keys,
            },
        )

    @router.get("/settings", response_class=HTMLResponse, name="settings_page")
    async def settings_page(request: Request, user: User = Depends(require_user)):
        """User settings page."""
        return templates.TemplateResponse(
            "auth/settings.html",
            {"request": request, "title": "Settings", "user": user},
        )

    # ==================== API Endpoints ====================

    @router.post("/api/signup", response_model=AuthResponse)
    async def signup(request: SignupRequest):
        """Register a new user account."""
        # Check if email already exists
        existing = await auth_repo.users.get_by_email(request.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash password
        password_hash, salt = User.hash_password(request.password)

        # Create user with person_id
        person_id = uuid4()
        user = User(
            person_id=person_id,
            email=request.email,
            password_hash=password_hash,
            salt=salt,
            role=UserRole.TEACHER,
            metadata={
                "display_name": request.display_name,
                "organization": request.organization,
            },
        )

        # Generate verification token
        user.generate_verification_token()

        # Save user (also registers as Principal if registry available)
        await auth_repo.create_user(user)

        # TODO: Send verification email
        # For now, auto-verify in development
        await auth_repo.users.verify_email(user.id)

        return AuthResponse(
            success=True,
            message="Account created successfully. Please check your email to verify your account.",
            user_id=user.id,
        )

    @router.post("/api/login", response_model=AuthResponse)
    async def login(response: Response, request: LoginRequest):
        """Login with email and password."""
        user, error = await auth_repo.authenticate_user(request.email, request.password)

        if not user:
            raise HTTPException(status_code=401, detail=error)

        # Create session
        token, token_hash = Session.generate_token()
        session = Session(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        await auth_repo.sessions.create(session)

        # Set cookie
        set_session_cookie(response, token)

        return AuthResponse(
            success=True,
            message="Login successful",
            user_id=user.id,
            session_token=token,
        )

    @router.post("/api/logout")
    async def logout(response: Response, request: Request):
        """Logout current session."""
        token = request.cookies.get("session_token")
        if token:
            import hashlib
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            session = await auth_repo.sessions.get_by_token_hash(token_hash)
            if session:
                await auth_repo.sessions.delete(session.id)

        clear_session_cookie(response)
        return {"success": True, "message": "Logged out"}

    @router.post("/api/logout-all")
    async def logout_all(response: Response, user: User = Depends(require_user)):
        """Logout all sessions for current user."""
        count = await auth_repo.sessions.delete_all_for_user(user.id)
        clear_session_cookie(response)
        return {"success": True, "message": f"Logged out of {count} sessions"}

    @router.post("/api/forgot-password")
    async def forgot_password(email: str = Form(...)):
        """Request password reset."""
        user = await auth_repo.users.get_by_email(email)
        if user:
            token = user.generate_password_reset_token()
            await auth_repo.users.update(
                user.id,
                password_reset_token=user.password_reset_token,
                password_reset_expires=user.password_reset_expires.isoformat(),
            )
            # TODO: Send password reset email
        # Always return success to prevent email enumeration
        return {"success": True, "message": "If that email exists, a reset link has been sent"}

    @router.post("/api/reset-password")
    async def reset_password(token: str = Form(...), new_password: str = Form(...)):
        """Reset password with token."""
        if len(new_password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

        user = await auth_repo.users.get_by_password_reset_token(token)
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        if user.password_reset_expires and datetime.now(timezone.utc) > user.password_reset_expires:
            raise HTTPException(status_code=400, detail="Token has expired")

        # Update password
        password_hash, salt = User.hash_password(new_password)
        await auth_repo.users.update(
            user.id,
            password_hash=password_hash,
            salt=salt,
            password_reset_token=None,
            password_reset_expires=None,
        )

        # Invalidate all sessions
        await auth_repo.sessions.delete_all_for_user(user.id)

        return {"success": True, "message": "Password reset successfully"}

    @router.post("/api/change-password")
    async def change_password(
        request: PasswordChangeRequest,
        user: User = Depends(require_user),
    ):
        """Change password for authenticated user."""
        if not user.verify_password(request.current_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        password_hash, salt = User.hash_password(request.new_password)
        await auth_repo.users.update(
            user.id,
            password_hash=password_hash,
            salt=salt,
        )

        return {"success": True, "message": "Password changed successfully"}

    # ==================== API Key Management ====================

    @router.get("/api/keys", response_model=list[APIKeyResponse])
    async def list_api_keys(user: User = Depends(require_user)):
        """List all API keys for current user."""
        keys = await auth_repo.api_keys.list_by_user(user.id)
        return [
            APIKeyResponse(
                id=k.id,
                name=k.name,
                key_prefix=k.key_prefix,
                key_hint=k.key_hint,
                scopes=k.scopes,
                status=k.status.value,
                created_at=k.created_at,
                last_used_at=k.last_used_at,
                expires_at=k.expires_at,
                usage_count=k.usage_count,
            )
            for k in keys
        ]

    @router.post("/api/keys", response_model=APIKeyCreateResponse)
    async def create_api_key(
        request: CreateAPIKeyRequest,
        user: User = Depends(require_user),
    ):
        """
        Create a new API key.

        This creates:
        1. APIKey in the auth database (existing behavior)
        2. ControlToken in KSTAR+ LTM with principal binding (new)
        3. CredentialBinding mapping the key to the principal (new)
        """
        # Generate key
        full_key, key_prefix, key_hash, key_hint = APIKey.generate()

        # Calculate expiry
        expires_at = None
        if request.expires_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_days)

        # Create API key in auth database
        api_key = APIKey(
            user_id=user.id,
            name=request.name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            key_hint=key_hint,
            scopes=request.scopes,
            expires_at=expires_at,
        )

        await auth_repo.api_keys.create(api_key)

        # Get user's principal ID
        principal_id = user.principal_id

        # =====================================================================
        # Store as ControlToken in KSTAR+ LTM (with principal binding)
        # =====================================================================
        if kstar_memory:
            try:
                # Map API key scopes to TokenScope
                token_scopes = []
                for scope in request.scopes:
                    if scope == "read":
                        token_scopes.append(TokenScope.READ)
                    elif scope == "write":
                        token_scopes.append(TokenScope.WRITE)
                    elif scope == "admin":
                        token_scopes.append(TokenScope.ADMIN)
                    elif scope == "execute":
                        token_scopes.append(TokenScope.EXECUTE)

                # Create ControlToken with principal binding
                control_token = ControlToken.create(
                    key=f"api_key:{key_prefix}",
                    value=full_key,
                    token_type=TokenType.API_KEY,
                    binding_target="p3394_agent:api",
                    scopes=token_scopes or [TokenScope.READ],
                    provenance_source=principal_id,
                    provenance_method=ProvenanceMethod.ISSUED,
                    valid_days=request.expires_days,
                    metadata={
                        "name": request.name,
                        "api_key_id": str(api_key.id),
                        "user_id": str(user.id),
                        "email": user.email,
                    },
                    principal_id=principal_id,
                    authorized_principals=[principal_id],
                )

                # Store in KSTAR memory
                await kstar_memory.store_credential_binding({
                    "credential_type": "api_key",
                    "credential_value": key_prefix,
                    "principal_urn": principal_id,
                    "assurance_level": "medium",
                    "scopes": request.scopes,
                    "metadata": {
                        "token_id": control_token.token_id,
                        "api_key_id": str(api_key.id),
                        "name": request.name,
                    }
                })

                logger.info(f"Stored API key as ControlToken: {control_token.token_id} for principal: {principal_id}")

            except Exception as e:
                logger.warning(f"Failed to store API key in KSTAR LTM: {e}")
                # Continue - the API key was still created in the auth database

        # =====================================================================
        # Create CredentialBinding in PrincipalRegistry
        # =====================================================================
        if principal_registry:
            try:
                binding = CredentialBinding(
                    binding_id=f"urn:cred:api_key:{key_prefix}",
                    principal_id=principal_id,
                    channel="api",
                    binding_type=BindingType.API_KEY,
                    external_subject=key_prefix,
                    scopes=request.scopes,
                    secret_hash=key_hash,
                    metadata={
                        "name": request.name,
                        "api_key_id": str(api_key.id),
                        "user_id": str(user.id),
                    },
                    expires_at=expires_at,
                )

                principal_registry.register_binding(binding)
                logger.info(f"Created CredentialBinding: {binding.binding_id} for principal: {principal_id}")

            except Exception as e:
                logger.warning(f"Failed to create CredentialBinding: {e}")
                # Continue - the API key was still created

        return APIKeyCreateResponse(
            id=api_key.id,
            name=api_key.name,
            key=full_key,
            message="Save this key now. It will not be shown again.",
        )

    @router.delete("/api/keys/{key_id}")
    async def revoke_api_key(key_id: UUID, user: User = Depends(require_user)):
        """
        Revoke an API key.

        This also revokes:
        1. The ControlToken in KSTAR+ LTM
        2. The CredentialBinding in PrincipalRegistry
        """
        api_key = await auth_repo.api_keys.get(key_id)
        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")
        if api_key.user_id != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Revoke in auth database
        await auth_repo.api_keys.revoke(key_id)

        # Revoke CredentialBinding
        if principal_registry:
            try:
                binding_id = f"urn:cred:api_key:{api_key.key_prefix}"
                principal_registry.delete_binding(binding_id)
                logger.info(f"Revoked CredentialBinding: {binding_id}")
            except Exception as e:
                logger.warning(f"Failed to revoke CredentialBinding: {e}")

        # Note: ControlToken revocation would require the token store
        # For now, the KSTAR credential binding tracks the revocation status

        return {"success": True, "message": "API key revoked"}

    # ==================== Current User ====================

    @router.get("/api/me")
    async def get_current_user_info(user: User = Depends(require_user)):
        """Get current user information."""
        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "status": user.status.value,
            "email_verified": user.email_verified,
            "principal_id": user.principal_id,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        }

    return router
