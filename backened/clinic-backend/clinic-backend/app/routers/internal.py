from fastapi import APIRouter, Header, HTTPException
from datetime import datetime, timedelta
from app.core.config import settings
from app.core.security import supabase_admin
from app.services.notify import notify_appointment_cancelled, notify_appointment_reminder

router = APIRouter(prefix="/internal", tags=["internal (n8n only)"])

# Simple shared-secret so only n8n can call these — not for browser/user traffic.
INTERNAL_SECRET = "change-this-shared-secret"


def _check_secret(x_internal_secret: str = Header(...)):
    if x_internal_secret != INTERNAL_SECRET:
        raise HTTPException(401, "Invalid internal secret")


@router.post("/expire-pending")
def expire_pending_appointments(x_internal_secret: str = Header(...)):
    """
    Called by an n8n Cron node every few minutes.
    Any 'Pending' appointment whose slot_start has already passed
    gets auto-cancelled, and the patient is emailed.
    """
    _check_secret(x_internal_secret)

    now = datetime.utcnow().isoformat()
    expired = (
        supabase_admin.table("appointments")
        .select("*")
        .eq("status", "Pending")
        .lt("slot_start", now)
        .execute()
    )

    for appt in expired.data:
        supabase_admin.table("appointments").update({"status": "Cancelled"}).eq("id", appt["id"]).execute()
        patient = supabase_admin.auth.admin.get_user_by_id(appt["patient_id"])
        notify_appointment_cancelled(appt, patient.user.email, reason="Not confirmed in time")

    return {"expired_count": len(expired.data)}


@router.post("/send-reminders")
def send_reminders(x_internal_secret: str = Header(...)):
    """
    Called by an n8n Cron node once a day.
    Sends a reminder for every Confirmed appointment happening tomorrow
    that hasn't already had a reminder sent.
    """
    _check_secret(x_internal_secret)

    tomorrow_start = (datetime.utcnow() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_end = tomorrow_start + timedelta(days=1)

    due = (
        supabase_admin.table("appointments")
        .select("*")
        .eq("status", "Confirmed")
        .eq("reminder_sent", False)
        .gte("slot_start", tomorrow_start.isoformat())
        .lt("slot_start", tomorrow_end.isoformat())
        .execute()
    )

    for appt in due.data:
        patient = supabase_admin.auth.admin.get_user_by_id(appt["patient_id"])
        notify_appointment_reminder(appt, patient.user.email)
        supabase_admin.table("appointments").update({"reminder_sent": True}).eq("id", appt["id"]).execute()

    return {"reminders_sent": len(due.data)}
