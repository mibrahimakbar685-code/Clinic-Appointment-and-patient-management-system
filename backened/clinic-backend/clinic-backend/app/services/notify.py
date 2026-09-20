import httpx
from app.core.config import settings


def _fire(event: str, payload: dict) -> None:
    """
    Fire-and-forget POST to an n8n webhook. n8n owns the actual email
    sending (SMTP / Gmail node) — the backend just reports what happened.
    Each `event` maps to its own n8n webhook workflow, e.g.:
      /webhook/appointment-confirmed
      /webhook/appointment-cancelled
      /webhook/appointment-reminder
      /webhook/doctor-invited
    """
    url = f"{settings.N8N_WEBHOOK_BASE}/{event}"
    try:
        httpx.post(url, json=payload, timeout=5)
    except httpx.HTTPError:
        # Don't let a notification failure break the main request.
        # In production: log this to a retry queue / dead-letter table.
        pass


def notify_appointment_confirmed(appointment: dict, patient_email: str):
    _fire("appointment-confirmed", {"appointment": appointment, "to": patient_email})


def notify_appointment_cancelled(appointment: dict, patient_email: str, reason: str):
    _fire("appointment-cancelled", {"appointment": appointment, "to": patient_email, "reason": reason})


def notify_appointment_rejected(appointment: dict, patient_email: str):
    _fire("appointment-rejected", {"appointment": appointment, "to": patient_email})


def notify_appointment_reminder(appointment: dict, patient_email: str):
    _fire("appointment-reminder", {"appointment": appointment, "to": patient_email})


def notify_doctor_invited(doctor_email: str, full_name: str, set_password_link: str):
    _fire("doctor-invited", {"to": doctor_email, "full_name": full_name, "link": set_password_link})
