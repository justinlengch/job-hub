from supabase import acreate_client, AsyncClient
from app.core.config import settings

_supabase_client: AsyncClient | None = None

async def get_supabase_client() -> AsyncClient:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = await acreate_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
    return _supabase_client
