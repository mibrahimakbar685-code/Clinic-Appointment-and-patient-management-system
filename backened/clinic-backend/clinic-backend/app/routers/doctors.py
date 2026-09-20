from fastapi import APIRouter, Depends, HTTPException
from datetime import date
from app.core.security import get_current_user, require_role, supabase_admin
from app.models.schemas import DoctorHoursCreate, DoctorLeaveCreate
from app.services.slots import get_free_slots
from app.services.notify import notify_appointment_cancelled

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.get("")
def list_doctors():
    """Public: patients browse active doctors."""
    res = (
        supabase_admin.table("doctors")
        .select("id, specialization, profiles(full_name)")
        .eq("is_active", True)
        .execute()
    )
    return res.data


@router.get("/{doctor_id}/slots")
def doctor_slots(doctor_id: str, target_date: date):
    doc = supabase_admin.table("doctors").select("is_active").eq("id", doctor_id).single().execute()
    if not doc.data or not doc.data["is_active"]:
        raise HTTPException(404, "Doctor not found or inactive")
    return {"date": target_date.isoformat(), "slots": get_free_slots(doctor_id, target_date)}


def _get_own_doctor_id(user: dict) -> str:
    res = supabase_admin.table("doctors").select("id").eq("user_id", user["id"]).single().execute()
    if not res.data:
        raise HTTPException(403, "Not registered as a doctor")
    return res.data["id"]


@router.post("/me/hours")
def add_hours(body: DoctorHoursCreate, user: dict = Depends(require_role("doctor"))):
    doctor_id = _get_own_doctor_id(user)
    if body.end_time <= body.start_time:
        raise HTTPException(400, "End time must be after start time")

    # Overlap check happens at DB level (exclusion constraint) too,
    # but we check here first for a clean error message.
    existing = (
        supabase_admin.table("doctor_hours")
        .select("start_time, end_time")
        .eq("doctor_id", doctor_id)
        .eq("day_of_week", body.day_of_week)
        .execute()
    )
    for h in existing.data:
        if body.start_time < h["end_time"] and h["start_time"] < body.end_time:
            raise HTTPException(400, "These hours overlap an existing block for that day")

    try:
        res = (
            supabase_admin.table("doctor_hours")
            .insert(
                {
                    "doctor_id": doctor_id,
                    "day_of_week": body.day_of_week,
                    "start_time": body.start_time.isoformat(),
                    "end_time": body.end_time.isoformat(),
                }
            )
            .execute()
        )
    except Exception as e:
        raise HTTPException(400, f"Could not save hours: {e}")
    return res.data[0]


@router.post("/me/leaves")
def add_leave(body: DoctorLeaveCreate, user: dict = Depends(require_role("doctor"))):
    doctor_id = _get_own_doctor_id(user)
    if body.leave_date < date.today():
        raise HTTPException(400, "Cannot add a leave day in the past")

    try:
        supabase_admin.table("doctor_leaves").insert(
            {"doctor_id": doctor_id, "leave_date": body.leave_date.isoformat()}
        ).execute()
    except Exception as e:
        raise HTTPException(400, f"Could not save leave day: {e}")

    # Cancel any Pending/Confirmed appointments on that day + email patients
    affected = (
        supabase_admin.table("appointments")
        .select("id, patient_id, slot_start, profiles(full_name)")
        .eq("doctor_id", doctor_id)
        .gte("slot_start", f"{body.leave_date}T00:00:00")
        .lte("slot_start", f"{body.leave_date}T23:59:59")
        .in_("status", ["Pending", "Confirmed"])
        .execute()
    )
    for appt in affected.data:
        supabase_admin.table("appointments").update({"status": "Cancelled"}).eq("id", appt["id"]).execute()
        patient = supabase_admin.auth.admin.get_user_by_id(appt["patient_id"])
        notify_appointment_cancelled(appt, patient.user.email, reason="Doctor is on leave that day")

    return {"leave_date": body.leave_date.isoformat(), "cancelled_appointments": len(affected.data)}
