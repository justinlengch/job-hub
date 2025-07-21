from supabase import acreate_client, AsyncClient
from typing import Optional

from .base_service import BaseService, ServiceInitializationError
from ..core.config import settings


class SupabaseService(BaseService):
    """Service for managing Supabase database connections and operations."""
    
    def __init__(self):
        self._client: Optional[AsyncClient] = None
        super().__init__()
    
    def _initialize(self) -> None:
        """Initialize Supabase service configuration."""
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise ServiceInitializationError("Supabase URL and service role key are required")
        self._log_operation("Supabase service initialized")
    
    async def get_client(self) -> AsyncClient:
        """Get the Supabase client, creating it if it doesn't exist."""
        if self._client is None:
            try:
                self._client = await acreate_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_SERVICE_ROLE_KEY
                )
                self._log_operation("Supabase client created")
            except Exception as e:
                self._log_error("creating Supabase client", e)
                raise ServiceInitializationError(f"Failed to create Supabase client: {str(e)}")
        
        return self._client

supabase_service = SupabaseService()


