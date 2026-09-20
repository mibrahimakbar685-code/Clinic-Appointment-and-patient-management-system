from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
from app.core.security import get_current_user, require_role, supabase_admin
from app.core.config import settings
from app.models.schemas import AppointmentCreate, AppointmentReschedule, AppointmentNote
from app.services.slots import is_slot_valid_and_free
from app.services.notify import (
    notify_appointment_confirmed,
    notify_appointment_cancelled,
    notify_appointment_rejected,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


def _get_appointment_or_404(appointment_id: str) -> dict:
    res = supabase_admin.table("appointments").select("*").eq("id", appointment_id).single().execute()
    if not res.data:
        raise HTTPException(404, "Appointment not found")
    return res.data


def _get_own_doctor_id(user_id: str) -> str | None:
    res = supabase_admin.table("doctors").select("id").eq("user_id", user_id).single().execute()
    return res.data["id"] if res.data else None


# ---------------------------------------------------------------
# PATIENT: book a slot
# ---------------------------------------------------------------
@router.post("")
def book_appointment(body: AppointmentCreate, user: dict = Depends(require_role("patient"))):
    slot_start = body.slot_start.replace(tzinfo=None)

    if slot_start <= datetime.utcnow():
        raise HTTPException(400, "Cannot book a slot in the past")

    doctor = supabase_admin.table("doctors").select("is_active").eq("id", body.doctor_id).single().execute()
    if not doctor.data or not doctor.data["is_active"]:
        raise HTTPException(400, "This doctor is not available for booking")

    # Server-side re-validation: never trust that the frontend's slot list is still accurate
    if not is_slot_valid_and_free(body.doctor_id, slot_start):
        raise HTTPException(409, "That slot is no longer available")

    slot_end = slot_start + timedelta(minutes=settings.SLOT_DURATION_MINUTES)

    try:
        # Unique DB indexes (doctor_id+slot_start, patient_id+slot_start)
        # are the real race-condition guard — this insert fails atomically
        # if someone else grabbed the slot a moment ago.
        res = (
            supabase_admin.table("appointments")
            .insert(
                {
                    "patient_id": user["id"],
                    "doctor_id": body.doctor_id,
                    "slot_start": slot_start.isoformat(),
                    "slot_end": slot_end.isoformat(),
                    "status": "Pending",
                }
            )
            .execute()
        )
    except Exception:
        raise HTTPException(409, "You already have an appointment at that time, or the slot was just taken")

    return res.data[0]


# ---------------------------------------------------------------
# DOCTOR: confirm / reject
# ---------------------------------------------------------------
@router.patch("/{appointment_id}/confirm")
def confirm_appointment(appointment_id: str, user: dict = Depends(require_role("doctor"))):
    appt = _get_appointment_or_404(appointment_id)
    own_doctor_id = _get_own_doctor_id(user["id"])
    if appt["doctor_id"] != own_doctor_id:
        raise HTTPException(403, "Not your appointment")
    if appt["status"] != "Pending":
        raise HTTPException(400, f"Cannot confirm an appointment that is {appt['status']}")

    supabase_admin.table("appointments").update({"status": "Confirmed"}).eq("id", appointment_id).execute()
    patient = supabase_admin.auth.admin.get_user_by_id(appt["patient_id"])
    notify_appointment_confirmed(appt, patient.user.email)
    return {"id": appointment_id, "status": "Confirmed"}


@router.patch("/{appointment_id}/reject")
def reject_appointment(appointment_id: str, user: dict = Depends(require_role("doctor"))):
    appt = _get_appointment_or_404(appointment_id)
    own_doctor_id = _get_own_doctor_id(user["id"])
    if appt["doctor_id"] != own_doctor_id:
        raise HTTPException(403, "Not your appointment")
    if appt["status"] != "Pending":
        raise HTTPException(400, f"Cannot reject an appointment that is {appt['status']}")

    supabase_admin.table("appointments").update({"status": "Rejected"}).eq("id", appointment_id).execute()
    patient = supabase_admin.auth.admin.get_user_by_id(appt["patient_id"])
    notify_appointment_rejected(appt, patient.user.email)
    return {"id": appointment_id, "status": "Rejected"}


# ---------------------------------------------------------------
# PATIENT: cancel / reschedule (>= 2 hours before slot_start)
# ---------------------------------------------------------------
def _check_cancel_window(appt: dict):
    slot_start = datetime.fromisoformat(appt["slot_start"])
    window = timedelta(hours=settings.RESCHEDULE_CANCEL_WINDOW_HOURS)
    if slot_start - datetime.utcnow() < window:
        raise HTTPException(
            400, f"Too late to change this appointment (must be {settings.RESCHEDULE_CANCEL_WINDOW_HOURS}+ hours before)"
        )


@router.patch("/{appointment_id}/cancel")
def cancel_appointment(appointment_id: str, user: dict = Depends(require_role("patient"))):
    appt = _get_appointment_or_404(appointment_id)
    if appt["patient_id"] != user["id"]:
        raise HTTPException(403, "Not your appointment")
    if appt["status"] not in ("Pending", "Confirmed"):
        raise HTTPException(400, f"Cannot cancel an appointment that is {appt['status']}")
    _check_cancel_window(appt)

    supabase_admin.table("appointments").update({"status": "Cancelled"}).eq("id", appointment_id).execute()
    return {"id": appointment_id, "status": "Cancelled"}


@router.patch("/{appointment_id}/reschedule")
def reschedule_appointment(
    appointment_id: str, body: AppointmentReschedule, user: dict = Depends(require_role("patient"))
):
    appt = _get_appointment_or_404(appointment_id)
    if appt["patient_id"] != user["id"]:
        raise HTTPException(403, "Not your appointment")
    if appt["status"] not in ("Pending", "Confirmed"):
        raise HTTPException(400, f"Cannot reschedule an appointment that is {appt['status']}")
    _check_cancel_window(appt)

    new_start = body.new_slot_start.replace(tzinfo=None)
    if new_start <= datetime.utcnow():
        raise HTTPException(400, "Cannot reschedule to a slot in the past")
    if not is_slot_valid_and_free(appt["doctor_id"], new_start):
        raise HTTPException(409, "That new slot is not available")

    new_end = new_start + timedelta(minutes=settings.SLOT_DURATION_MINUTES)
    try:
        supabase_admin.table("appointments").update(
            {
                "slot_start": new_start.isoformat(),
                "slot_end": new_end.isoformat(),
                "status": "Pending",  # goes back to Pending, needs re-confirmation
            }
        ).eq("id", appointment_id).execute()
    except Exception:
        raise HTTPException(409, "That slot was just taken by someone else")

    return {"id": appointment_id, "status": "Pending", "slot_start": new_start.isoformat()}


# ---------------------------------------------------------------
# DOCTOR: complete visit + add note
# ---------------------------------------------------------------
@router.patch("/{appointment_id}/complete")
def complete_appointment(appointment_id: str, user: dict = Depends(require_role("doctor"))):
    appt = _get_appointment_or_404(appointment_id)
    own_doctor_id = _get_own_doctor_id(user["id"])
    if appt["doctor_id"] != own_doctor_id:
        raise HTTPException(403, "Not your appointment")
    if appt["status"] != "Confirmed":
        raise HTTPException(400, "Only a Confirmed appointment can be completed")

    slot_start = datetime.fromisoformat(appt["slot_start"])
    if slot_start > datetime.utcnow():
        raise HTTPException(400, "Cannot complete a visit before its start time")

    supabase_admin.table("appointments").update({"status": "Completed"}).eq("id", appointment_id).execute()
    return {"id": appointment_id, "status": "Completed"}


@router.patch("/{appointment_id}/no-show")
def mark_no_show(appointment_id: str, user: dict = Depends(require_role("doctor"))):
    appt = _get_appointment_or_404(appointment_id)
    own_doctor_id = _get_own_doctor_id(user["id"])
    if appt["doctor_id"] != own_doctor_id:
        raise HTTPException(403, "Not your appointment")
    if appt["status"] != "Confirmed":
        raise HTTPException(400, "Only a Confirmed appointment can be marked No-show")

    supabase_admin.table("appointments").update({"status": "No-show"}).eq("id", appointment_id).execute()
    return {"id": appointment_id, "status": "No-show"}


@router.patch("/{appointment_id}/note")
def add_note(appointment_id: str, body: AppointmentNote, user: dict = Depends(require_role("doctor"))):
    appt = _get_appointment_or_404(appointment_id)
    own_doctor_id = _get_own_doctor_id(user["id"])
    if appt["doctor_id"] != own_doctor_id:
        raise HTTPException(403, "Not your appointment")

    supabase_admin.table("appointments").update({"note": body.note}).eq("id", appointment_id).execute()
    return {"id": appointment_id, "note_saved": True}


# ---------------------------------------------------------------
# Shared: patient's own history / doctor's own patient history
# ---------------------------------------------------------------
@router.get("/mine")
def my_appointments(user: dict = Depends(get_current_user)):
    if user["role"] == "patient":
        res = (
            supabase_admin.table("appointments")
            .select("*, doctors(specialization, profiles(full_name))")
            .eq("patient_id", user["id"])
            .order("slot_start", desc=True)
            .execute()
        )
        return res.data

    if user["role"] == "doctor":
        own_doctor_id = _get_own_doctor_id(user["id"])
        res = (
            supabase_admin.table("appointments")
            .select("*, profiles!appointments_patient_id_fkey(full_name)")
            .eq("doctor_id", own_doctor_id)
            .order("slot_start", desc=True)
            .execute()
        )
        return res.data

    raise HTTPException(403, "Admins should use /admin/dashboard")
