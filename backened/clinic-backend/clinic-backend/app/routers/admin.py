from fastapi import APIRouter, Depends, HTTPException
from datetime import date, datetime, time
from app.core.security import require_role, supabase_admin
from app.models.schemas import DoctorCreate
from app.services.notify import notify_doctor_invited

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/doctors")
def add_doctor(body: DoctorCreate, user: dict = Depends(require_role("admin"))):
    # Create the auth user via Supabase Admin API + trigger a recovery/set-password link.
    created = supabase_admin.auth.admin.create_user(
        {"email": body.email, "email_confirm": True, "user_metadata": {"full_name": body.full_name}}
    )
    new_user_id = created.user.id

    supabase_admin.table("profiles").insert(
        {"id": new_user_id, "full_name": body.full_name, "role": "doctor"}
    ).execute()

    doctor = (
        supabase_admin.table("doctors")
        .insert({"user_id": new_user_id, "specialization": body.specialization, "is_active": True})
        .execute()
    )

    link_res = supabase_admin.auth.admin.generate_link(
        {"type": "recovery", "email": body.email}
    )
    notify_doctor_invited(body.email, body.full_name, link_res.properties.action_link)

    return doctor.data[0]


@router.patch("/doctors/{doctor_id}/deactivate")
def deactivate_doctor(doctor_id: str, user: dict = Depends(require_role("admin"))):
    res = supabase_admin.table("doctors").update({"is_active": False}).eq("id", doctor_id).execute()
    if not res.data:
        raise HTTPException(404, "Doctor not found")
    return {"id": doctor_id, "is_active": False}


@router.patch("/doctors/{doctor_id}/activate")
def activate_doctor(doctor_id: str, user: dict = Depends(require_role("admin"))):
    res = supabase_admin.table("doctors").update({"is_active": True}).eq("id", doctor_id).execute()
    if not res.data:
        raise HTTPException(404, "Doctor not found")
    return {"id": doctor_id, "is_active": True}


@router.get("/dashboard")
def dashboard(user: dict = Depends(require_role("admin"))):
    today = date.today()
    start = datetime.combine(today, time.min).isoformat()
    end = datetime.combine(today, time.max).isoformat()

    todays_appointments = (
        supabase_admin.table("appointments")
        .select("id, slot_start, status, doctors(profiles(full_name)), profiles!appointments_patient_id_fkey(full_name)")
        .gte("slot_start", start)
        .lte("slot_start", end)
        .execute()
    )

    doctors = supabase_admin.table("doctors").select("id, profiles(full_name)").execute()
    per_doctor_counts = []
    for doc in doctors.data:
        counts_res = (
            supabase_admin.table("appointments").select("status").eq("doctor_id", doc["id"]).execute()
        )
        tally = {"Pending": 0, "Confirmed": 0, "Completed": 0, "No-show": 0, "Cancelled": 0, "Rejected": 0}
        for row in counts_res.data:
            tally[row["status"]] = tally.get(row["status"], 0) + 1
        per_doctor_counts.append({"doctor_id": doc["id"], "doctor_name": doc["profiles"]["full_name"], "counts": tally})

    # NOTE: `note` field intentionally excluded from every query above — admin never sees visit notes.
    return {
        "today": today.isoformat(),
        "todays_appointments": todays_appointments.data,
        "per_doctor_counts": per_doctor_counts,
    }
