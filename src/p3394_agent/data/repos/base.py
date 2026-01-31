"""
Base Repository

Abstract base class for all repositories.
Supports both Supabase and in-memory backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Repository(ABC, Generic[T]):
    """
    Abstract repository base class.

    Provides a consistent interface for data access across
    different storage backends (Supabase, in-memory, etc.)
    """

    def __init__(self, client: Any = None):
        """
        Initialize repository.

        Args:
            client: Database client (Supabase client or None for in-memory)
        """
        self.client = client
        self._in_memory_store: dict[UUID, T] = {}

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Get the database table name for this repository."""
        pass

    @property
    @abstractmethod
    def model_class(self) -> type[T]:
        """Get the Pydantic model class for this repository."""
        pass

    async def get(self, id: UUID) -> Optional[T]:
        """Get entity by ID."""
        if self.client:
            result = await self._db_get(id)
            return self.model_class(**result) if result else None
        return self._in_memory_store.get(id)

    async def create(self, entity: T) -> T:
        """Create a new entity."""
        if self.client:
            result = await self._db_create(entity)
            return self.model_class(**result)
        self._in_memory_store[entity.id] = entity
        return entity

    async def update(self, id: UUID, **updates) -> Optional[T]:
        """Update an entity."""
        if self.client:
            result = await self._db_update(id, updates)
            return self.model_class(**result) if result else None
        if id in self._in_memory_store:
            entity = self._in_memory_store[id]
            updated = entity.model_copy(update=updates)
            self._in_memory_store[id] = updated
            return updated
        return None

    async def delete(self, id: UUID) -> bool:
        """Delete an entity."""
        if self.client:
            return await self._db_delete(id)
        if id in self._in_memory_store:
            del self._in_memory_store[id]
            return True
        return False

    async def list(
        self,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[T]:
        """List entities with optional filters."""
        if self.client:
            results = await self._db_list(filters, limit, offset)
            return [self.model_class(**r) for r in results]

        # In-memory filtering
        entities = list(self._in_memory_store.values())
        if filters:
            entities = [
                e for e in entities
                if all(getattr(e, k, None) == v for k, v in filters.items())
            ]
        return entities[offset:offset + limit]

    # Database-specific implementations (for Supabase)
    async def _db_get(self, id: UUID) -> Optional[dict]:
        """Get from database."""
        response = self.client.table(self.table_name).select("*").eq("id", str(id)).single().execute()
        return response.data if response.data else None

    async def _db_create(self, entity: T) -> dict:
        """Create in database."""
        data = entity.model_dump(mode="json")
        response = self.client.table(self.table_name).insert(data).execute()
        return response.data[0]

    async def _db_update(self, id: UUID, updates: dict) -> Optional[dict]:
        """Update in database."""
        response = self.client.table(self.table_name).update(updates).eq("id", str(id)).execute()
        return response.data[0] if response.data else None

    async def _db_delete(self, id: UUID) -> bool:
        """Delete from database."""
        response = self.client.table(self.table_name).delete().eq("id", str(id)).execute()
        return len(response.data) > 0

    async def _db_list(
        self,
        filters: Optional[dict[str, Any]],
        limit: int,
        offset: int
    ) -> list[dict]:
        """List from database."""
        query = self.client.table(self.table_name).select("*")
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        query = query.range(offset, offset + limit - 1)
        response = query.execute()
        return response.data
