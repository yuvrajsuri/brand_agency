"""
PocketBase Client
Generic CRUD wrapper for PocketBase REST API.
Replaces n8n workflow 01_util_pocketbase_crud.
"""

import logging
from typing import Any, Optional
import httpx

from config import settings

logger = logging.getLogger(__name__)


class PocketBaseClient:
    """Async client for PocketBase REST API"""

    def __init__(self):
        self.base_url = settings.POCKETBASE_URL
        self._token: Optional[str] = None

    async def _get_token(self) -> str:
        """Authenticate with PocketBase and cache token"""
        if self._token:
            return self._token

        # PocketBase admin auth — only used for privileged ops
        # For collection access, rely on API rules
        return ""

    async def get_record(self, collection: str, record_id: str) -> Optional[dict]:
        """Get a single record by ID"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/collections/{collection}/records/{record_id}"
                )
                if response.status_code == 200:
                    return response.json()
                logger.warning(f"PocketBase: record not found {collection}/{record_id}")
                return None
        except Exception as e:
            logger.error(f"PocketBase get_record error: {e}")
            return None

    async def list_records(
        self,
        collection: str,
        filter: str = "",
        sort: str = "-created",
        page: int = 1,
        per_page: int = 50
    ) -> list[dict]:
        """List records from a collection"""
        try:
            params = {"page": page, "perPage": per_page, "sort": sort}
            if filter:
                params["filter"] = filter

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/collections/{collection}/records",
                    params=params
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("items", [])
                return []
        except Exception as e:
            logger.error(f"PocketBase list_records error: {e}")
            return []

    async def create_record(self, collection: str, data: dict) -> Optional[dict]:
        """Create a new record"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/collections/{collection}/records",
                    json=data
                )
                if response.status_code in (200, 201):
                    return response.json()
                logger.error(f"PocketBase create error: {response.status_code} — {response.text}")
                return None
        except Exception as e:
            logger.error(f"PocketBase create_record error: {e}")
            return None

    async def update_record(self, collection: str, record_id: str, data: dict) -> Optional[dict]:
        """Update an existing record"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.patch(
                    f"{self.base_url}/api/collections/{collection}/records/{record_id}",
                    json=data
                )
                if response.status_code == 200:
                    return response.json()
                logger.error(f"PocketBase update error: {response.status_code} — {response.text}")
                return None
        except Exception as e:
            logger.error(f"PocketBase update_record error: {e}")
            return None

    async def delete_record(self, collection: str, record_id: str) -> bool:
        """Delete a record"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(
                    f"{self.base_url}/api/collections/{collection}/records/{record_id}"
                )
                return response.status_code == 204
        except Exception as e:
            logger.error(f"PocketBase delete_record error: {e}")
            return False

    async def get_client_by_phone(self, phone: str) -> Optional[dict]:
        """Look up a client record by phone number"""
        records = await self.list_records(
            collection="clients",
            filter=f'phone="{phone}"',
            per_page=1
        )
        return records[0] if records else None
