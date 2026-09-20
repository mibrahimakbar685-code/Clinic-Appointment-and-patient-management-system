from pydantic import BaseModel, EmailStr
from datetime import date, time, datetime
from typing import Optional
from enum import Enum


class AppointmentStatus(str, Enum):
    pending = "Pending"
    confirmed = "Confirmed"
    cancelled = "Cancelled"
    rejected = "Rejected"
    completed = "Completed"
    no_show = "No-show"


class DoctorCreate(BaseModel):
    full_name: str
    email: EmailStr
    specialization: Optional[str] = None


class DoctorHoursCreate(BaseModel):
    day_of_week: int  # 0=Sunday ... 6=Saturday
    start_time: time
    end_time: time


class DoctorLeaveCreate(BaseModel):
    leave_date: date


class AppointmentCreate(BaseModel):
    doctor_id: str
    slot_start: datetime  # must exactly match a generated 30-min slot


class AppointmentReschedule(BaseModel):
    new_slot_start: datetime


class AppointmentNote(BaseModel):
    note: str


class AppointmentActionResult(BaseModel):
    id: str
    status: AppointmentStatus
    message: str
