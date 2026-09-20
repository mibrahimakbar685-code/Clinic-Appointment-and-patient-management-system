import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    N8N_WEBHOOK_BASE: str = os.getenv("N8N_WEBHOOK_BASE", "http://localhost:5678/webhook")
    RESCHEDULE_CANCEL_WINDOW_HOURS: int = int(os.getenv("RESCHEDULE_CANCEL_WINDOW_HOURS", 2))
    SLOT_DURATION_MINUTES: int = int(os.getenv("SLOT_DURATION_MINUTES", 30))


settings = Settings()
