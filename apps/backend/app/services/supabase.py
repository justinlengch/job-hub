from supabase import create_client, Client
from ..config import settings

def get_supabase_client() -> Client:
    """
    Create and return a Supabase client instance using credentials from settings.
    
    Uses the service role key to enable writing to the database without RLS restrictions.
    """
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY
    )
