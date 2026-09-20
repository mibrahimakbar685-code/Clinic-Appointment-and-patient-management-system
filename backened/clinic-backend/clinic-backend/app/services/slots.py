from datetime import datetime, date, time, timedelta
from app.core.config import settings
from app.core.security import supabase_admin


def get_free_slots(doctor_id: str, target_date: date) -> list[datetime]:
    """
    Returns a list of free 30-min slot start-times for a doctor on a given date.
    Logic:
      1. If the date is a leave day -> return [].
      2. Get the doctor's working hours for that day_of_week.
      3. Split each hour-block into SLOT_DURATION_MINUTES chunks.
      4. Remove slots that are already Pending/Confirmed.
      5. Remove slots that are in the past (if target_date is today).
    """
    # 1. Leave day check
    leave = (
        supabase_admin.table("doctor_leaves")
        .select("id")
        .eq("doctor_id", doctor_id)
        .eq("leave_date", target_date.isoformat())
        .execute()
    )
    if leave.data:
        return []

    # 2. Working hours for this weekday (Python: Monday=0 -> convert to Sun=0 convention)
    day_of_week = (target_date.weekday() + 1) % 7  # Python Mon=0 -> our Sun=0
    hours = (
        supabase_admin.table("doctor_hours")
        .select("start_time, end_time")
        .eq("doctor_id", doctor_id)
        .eq("day_of_week", day_of_week)
        .execute()
    )
    if not hours.data:
        return []

    slot_len = timedelta(minutes=settings.SLOT_DURATION_MINUTES)
    all_slots: list[datetime] = []
    for block in hours.data:
        start = datetime.combine(target_date, time.fromisoformat(block["start_time"]))
        end = datetime.combine(target_date, time.fromisoformat(block["end_time"]))
        cursor = start
        while cursor + slot_len <= end:
            all_slots.append(cursor)
            cursor += slot_len

    # 3. Remove already-booked slots (Pending or Confirmed)
    booked = (
        supabase_admin.table("appointments")
        .select("slot_start")
        .eq("doctor_id", doctor_id)
        .in_("status", ["Pending", "Confirmed"])
        .gte("slot_start", datetime.combine(target_date, time.min).isoformat())
        .lte("slot_start", datetime.combine(target_date, time.max).isoformat())
        .execute()
    )
    booked_times = {datetime.fromisoformat(b["slot_start"]).replace(tzinfo=None) for b in booked.data}

    # 4. Remove past slots
    now = datetime.utcnow()
    free = [s for s in all_slots if s not in booked_times and s > now]
    return free


def is_slot_valid_and_free(doctor_id: str, slot_start: datetime) -> bool:
    """Server-side re-check before booking — never trust the frontend's slot list."""
    free_slots = get_free_slots(doctor_id, slot_start.date())
    return any(s == slot_start.replace(tzinfo=None) for s in free_slots)
