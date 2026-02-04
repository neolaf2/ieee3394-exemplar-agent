---
name: whatsapp-config
description: Configure WhatsApp channel for the IEEE 3394 agent. Admin-only skill for setting up Meta Business API credentials, webhook configuration, and service principal. Use when admin requests "configure whatsapp", "setup whatsapp channel", or "connect whatsapp".
---

# WhatsApp Channel Configuration

⚠️ **ADMIN-ONLY CAPABILITY** ⚠️

This skill requires administrator privileges. System users must `/login` with admin API key before proceeding.

**Required**:
- Assurance Level: HIGH (via `/login <api_key>`)
- Permissions: `["admin"]`
- Channel: CLI only (not accessible from WhatsApp)

---

## Overview

This skill guides admin users through configuring the WhatsApp channel for the IEEE 3394 agent. It handles Meta Business API setup, webhook configuration, credential validation, and service principal registration.

**Access Control**: This skill can ONLY be invoked by users with admin privileges (scope: `*` or `admin`). Verify the caller's principal has admin access before proceeding.

## When to Use This Skill

Use this skill when:
- Admin user requests to "configure whatsapp" or "setup whatsapp channel"
- Admin needs to update WhatsApp credentials or phone number
- Troubleshooting WhatsApp connection issues that require reconfiguration
- Initial agent setup requiring WhatsApp channel activation

## Configuration Workflow

### Step 1: Verify Admin Access

Before starting configuration, verify the user has admin privileges:

```python
if not session.has_permission("admin") and "*" not in session.granted_permissions:
    return "Error: WhatsApp configuration requires admin privileges. Current user does not have admin access."
```

### Step 2: Gather Required Information

Collect the following information from the admin:

1. **Meta App ID** (required)
   - Found in Meta Developer Dashboard → Your App → Settings → Basic
   - Format: numeric string (e.g., "123456789012345")

2. **Meta App Secret** (required)
   - Found in Meta Developer Dashboard → Your App → Settings → Basic
   - Format: alphanumeric string
   - WARNING: Keep this secret secure

3. **Phone Number ID** (required)
   - Found in Meta Developer Dashboard → WhatsApp → API Setup
   - Format: numeric string (e.g., "109876543210987")

4. **Business Account ID** (required)
   - Found in Meta Developer Dashboard → WhatsApp → API Setup
   - Format: numeric string

5. **Verify Token** (required)
   - Create a secure random string for webhook verification
   - Recommendation: Generate using: `openssl rand -hex 32`
   - This will be used when configuring the webhook in Meta dashboard

6. **Webhook URL** (optional, can be auto-detected)
   - The public URL where WhatsApp will send events
   - Format: `https://your-domain.com/api/whatsapp/webhook`
   - If running locally, use ngrok or similar tunneling service

**Prompt Template:**
```
I'll help you configure the WhatsApp channel. I need the following information from your Meta Business Account:

1. Meta App ID (from Developer Dashboard → Settings → Basic)
2. Meta App Secret (from Developer Dashboard → Settings → Basic)
3. Phone Number ID (from WhatsApp → API Setup)
4. Business Account ID (from WhatsApp → API Setup)
5. Verify Token (generate with: openssl rand -hex 32)
6. Webhook URL (optional, e.g., https://your-domain.com/api/whatsapp/webhook)

Please provide these values. I'll validate them before saving.
```

### Step 3: Validate Input

Before proceeding, validate all inputs:

```python
import re

def validate_credentials(app_id, app_secret, phone_id, business_id, verify_token):
    errors = []

    # App ID: numeric string
    if not re.match(r'^\d{15,20}$', app_id):
        errors.append("App ID must be a 15-20 digit number")

    # App Secret: alphanumeric, 32+ chars
    if not re.match(r'^[a-f0-9]{32,}$', app_secret):
        errors.append("App Secret must be a hexadecimal string (32+ chars)")

    # Phone Number ID: numeric string
    if not re.match(r'^\d{15,20}$', phone_id):
        errors.append("Phone Number ID must be a 15-20 digit number")

    # Business Account ID: numeric string
    if not re.match(r'^\d{15,20}$', business_id):
        errors.append("Business Account ID must be a 15-20 digit number")

    # Verify token: non-empty, 16+ chars
    if len(verify_token) < 16:
        errors.append("Verify token must be at least 16 characters")

    return errors
```

### Step 4: Test Credentials

Before saving, test the credentials with Meta's API:

Use the script: `scripts/validate_whatsapp_creds.py`

```bash
uv run python .claude/skills/whatsapp-config/scripts/validate_whatsapp_creds.py \
    --app-id <APP_ID> \
    --app-secret <APP_SECRET> \
    --phone-id <PHONE_ID> \
    --business-id <BUSINESS_ID>
```

This script will:
1. Request an access token from Meta Graph API
2. Verify the phone number ID is valid
3. Check that the business account has proper permissions
4. Return validation status

If validation fails, provide specific error messages to help the admin troubleshoot.

### Step 5: Configure Service Principal

Once credentials are validated, configure the service principal for WhatsApp channel:

Use the script: `scripts/configure_whatsapp.py`

```bash
uv run python .claude/skills/whatsapp-config/scripts/configure_whatsapp.py \
    --app-id <APP_ID> \
    --app-secret <APP_SECRET> \
    --phone-id <PHONE_ID> \
    --business-id <BUSINESS_ID> \
    --verify-token <VERIFY_TOKEN> \
    --webhook-url <WEBHOOK_URL>
```

This script will:
1. Encrypt credentials using Fernet symmetric encryption
2. Create/update service principal in `ServicePrincipalRegistry`
3. Store encrypted credentials in `.claude/principals/service_principals.json`
4. Update WhatsApp channel adapter configuration
5. Generate Meta webhook configuration instructions

### Step 6: Verify Configuration

After configuration, verify the setup:

1. Check that service principal was created:
   ```python
   from src.ieee3394_agent.core.auth.service_principal import ServicePrincipalRegistry

   registry = ServicePrincipalRegistry()
   sp = registry.get_service_principal("whatsapp")

   if sp:
       print(f"✓ Service principal created: {sp.principal_id}")
       print(f"✓ Channel: {sp.channel_id}")
       print(f"✓ Phone Number ID: {sp.metadata.get('phone_number_id')}")
   ```

2. Test webhook endpoint (if accessible):
   ```bash
   curl -X GET "https://your-domain.com/api/whatsapp/webhook?hub.mode=subscribe&hub.challenge=test&hub.verify_token=<VERIFY_TOKEN>"
   ```
   Expected response: `test` (the challenge value echoed back)

3. Attempt to send a test message (optional):
   ```python
   # This will be handled by the WhatsApp channel adapter
   # once it's fully configured
   ```

### Step 7: Display Next Steps

Once configuration is complete, display instructions for Meta webhook setup:

```
✓ WhatsApp channel configured successfully!

NEXT STEPS - Complete webhook setup in Meta Developer Dashboard:

1. Go to: https://developers.facebook.com/apps/<YOUR_APP_ID>/whatsapp-business/wa-settings/

2. Click "Edit" next to Webhook

3. Enter these values:
   - Callback URL: <WEBHOOK_URL>
   - Verify Token: <VERIFY_TOKEN>

4. Click "Verify and Save"

5. Subscribe to webhook fields:
   ✓ messages
   ✓ message_status (optional, for delivery receipts)

6. Test the webhook by sending a message to your WhatsApp number

Once webhook is active, the agent will start receiving WhatsApp messages!

To test: Send "hello" to your WhatsApp Business number.
```

## Error Handling

### Common Errors and Solutions

**Error: "Invalid access token"**
- Cause: App ID or App Secret is incorrect
- Solution: Verify credentials in Meta Developer Dashboard → Settings → Basic

**Error: "Phone number not found"**
- Cause: Phone Number ID doesn't exist or doesn't belong to the Business Account
- Solution: Check Phone Number ID in Meta Developer Dashboard → WhatsApp → API Setup

**Error: "Insufficient permissions"**
- Cause: Meta Business Account doesn't have proper permissions
- Solution: Ensure you're an admin of the WhatsApp Business Account

**Error: "Webhook verification failed"**
- Cause: Webhook URL is unreachable or verify token doesn't match
- Solution:
  - Ensure webhook URL is publicly accessible (use ngrok if testing locally)
  - Verify that verify token in Meta dashboard matches configuration

**Error: "Rate limit exceeded"**
- Cause: Too many API requests in a short time
- Solution: Wait a few minutes and try again

### Security Considerations

1. **Credential Storage**: All credentials are encrypted using Fernet symmetric encryption before storage. The encryption key is derived from the agent's master key.

2. **Admin-Only Access**: This skill MUST only be accessible to admin users. Always verify `session.has_permission("admin")` before proceeding.

3. **Secure Transmission**: When collecting credentials from admin, remind them to:
   - Never share credentials in public channels
   - Use secure connections (HTTPS/TLS)
   - Rotate credentials periodically

4. **Audit Logging**: All configuration changes are logged to KSTAR memory with the `whatsapp_configuration` tag.

## Resources

### Scripts

- **`scripts/configure_whatsapp.py`**: Main configuration script that handles credential encryption, service principal creation, and webhook setup
- **`scripts/validate_whatsapp_creds.py`**: Validates credentials with Meta Graph API before saving

### References

- **`references/meta_setup_guide.md`**: Step-by-step guide for setting up a Meta Business App and getting required credentials
- **`references/webhook_troubleshooting.md`**: Common webhook issues and solutions

### External Documentation

- Meta WhatsApp Business API: https://developers.facebook.com/docs/whatsapp/cloud-api
- Meta Graph API: https://developers.facebook.com/docs/graph-api
- Webhook Setup: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks

## Example Interaction

**Admin:** "I need to configure the WhatsApp channel"

**Agent:** "I'll help you configure the WhatsApp channel. First, let me verify you have admin access... ✓ Confirmed.

I need the following information from your Meta Business Account:

1. Meta App ID (from Developer Dashboard → Settings → Basic)
2. Meta App Secret (from Developer Dashboard → Settings → Basic)
3. Phone Number ID (from WhatsApp → API Setup)
4. Business Account ID (from WhatsApp → API Setup)
5. Verify Token (generate with: openssl rand -hex 32)
6. Webhook URL (optional, e.g., https://your-domain.com/api/whatsapp/webhook)

Please provide these values."

**Admin:** [Provides credentials]

**Agent:** "Thank you. Validating credentials with Meta API...

✓ Credentials validated successfully
✓ Phone number is active and accessible
✓ Business account permissions verified

Configuring service principal... ✓ Done

WhatsApp channel configured successfully!

NEXT STEPS - Complete webhook setup in Meta Developer Dashboard:
[Instructions displayed as in Step 7]"

## Notes

- Configuration can be run multiple times to update credentials
- Old credentials are backed up before being replaced
- If webhook configuration fails, channel will remain in "partial" state until webhook is active
- Admin can test the configuration by sending a message to the WhatsApp number
