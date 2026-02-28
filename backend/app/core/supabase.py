from __future__ import annotations

from supabase import Client, create_client

from app.core.config import settings

# Anon client – used only for auth.sign_in_with_password
anon_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Service-role client – used for admin-level Supabase Auth API calls (e.g. list users)
service_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
