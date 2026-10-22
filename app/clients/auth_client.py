
from supabase import create_client, Client

from app.core.config import settings


auth_client: Client = create_client(
    settings.supabase_url,
    settings.supabase_publishable_key,
)
