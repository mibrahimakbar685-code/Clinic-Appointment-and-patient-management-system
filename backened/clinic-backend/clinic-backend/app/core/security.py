from fastapi import Depends, HTTPException, Header, status
from supabase import create_client, Client
from app.core.config import settings

# Service-role client: bypasses RLS. Used ONLY inside server-side
# validation logic where we've already checked permissions ourselves.
supabase_admin: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def get_current_user(authorization: str = Header(...)) -> dict:
    """
    Expects: Authorization: Bearer <supabase_access_token>
    Validates the token with Supabase and returns the user's profile
    (id, role, full_name). Raises 401 if invalid.
    """
    token = authorization.replace("Bearer ", "").strip()
    try:
        user_resp = supabase_admin.auth.get_user(token)
        user = user_resp.user
        if not user:
            raise ValueError("no user")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    profile = (
        supabase_admin.table("profiles")
        .select("id, full_name, role")
        .eq("id", user.id)
        .single()
        .execute()
    )
    if not profile.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile.data


def require_role(*allowed_roles: str):
    """Dependency factory: use as Depends(require_role('admin'))"""

    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for your role")
        return user

    return checker
