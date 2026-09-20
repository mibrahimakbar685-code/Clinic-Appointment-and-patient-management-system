-- =========================================================
-- Nowshera Family Clinic — Database Schema (Supabase/Postgres)
-- =========================================================
-- Run this in the Supabase SQL editor.
-- Uses Supabase Auth (auth.users) for login; this file adds
-- a profile table + all clinic-specific tables.

-- ---------------------------------------------------------
-- 1. PROFILES (extends Supabase auth.users with role + name)
-- ---------------------------------------------------------
create type user_role as enum ('patient', 'doctor', 'admin');

create table profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    full_name text not null,
    role user_role not null default 'patient',
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------
-- 2. DOCTORS
-- ---------------------------------------------------------
create table doctors (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references profiles(id) on delete cascade,
    specialization text,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    unique (user_id)
);

-- ---------------------------------------------------------
-- 3. DOCTOR WEEKLY HOURS
-- ---------------------------------------------------------
create table doctor_hours (
    id uuid primary key default gen_random_uuid(),
    doctor_id uuid not null references doctors(id) on delete cascade,
    day_of_week smallint not null check (day_of_week between 0 and 6), -- 0=Sunday
    start_time time not null,
    end_time time not null,
    created_at timestamptz not null default now(),
    constraint valid_range check (end_time > start_time)
);

-- Prevent overlapping hour-blocks for the same doctor on the same day.
-- (Postgres exclusion constraint using the btree_gist extension.)
create extension if not exists btree_gist;

alter table doctor_hours
add constraint no_overlapping_hours
exclude using gist (
    doctor_id with =,
    day_of_week with =,
    tsrange(
        ('2000-01-01 ' || start_time)::timestamp,
        ('2000-01-01 ' || end_time)::timestamp
    ) with &&
);

-- ---------------------------------------------------------
-- 4. DOCTOR LEAVE DAYS
-- ---------------------------------------------------------
create table doctor_leaves (
    id uuid primary key default gen_random_uuid(),
    doctor_id uuid not null references doctors(id) on delete cascade,
    leave_date date not null,
    created_at timestamptz not null default now(),
    unique (doctor_id, leave_date)
);

-- ---------------------------------------------------------
-- 5. APPOINTMENTS
-- ---------------------------------------------------------
create type appointment_status as enum (
    'Pending', 'Confirmed', 'Cancelled', 'Rejected', 'Completed', 'No-show'
);

create table appointments (
    id uuid primary key default gen_random_uuid(),
    patient_id uuid not null references profiles(id) on delete cascade,
    doctor_id uuid not null references doctors(id) on delete cascade,
    slot_start timestamptz not null,
    slot_end timestamptz not null,
    status appointment_status not null default 'Pending',
    note text,                       -- only patient + doctor can read (enforced by RLS)
    reminder_sent boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint valid_slot check (slot_end > slot_start)
);

-- No two active appointments can hold the SAME doctor slot.
create unique index one_appointment_per_doctor_slot
on appointments (doctor_id, slot_start)
where status in ('Pending', 'Confirmed');

-- A patient cannot hold two active appointments at the same slot_start
-- (even with different doctors).
create unique index one_appointment_per_patient_time
on appointments (patient_id, slot_start)
where status in ('Pending', 'Confirmed');

-- Auto-update updated_at on every change.
create or replace function set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger trg_appointments_updated_at
before update on appointments
for each row execute function set_updated_at();

-- ---------------------------------------------------------
-- 6. ROW LEVEL SECURITY
-- ---------------------------------------------------------
alter table profiles enable row level security;
alter table doctors enable row level security;
alter table doctor_hours enable row level security;
alter table doctor_leaves enable row level security;
alter table appointments enable row level security;

-- Helper: current user's role
create or replace function current_role_name()
returns user_role as $$
    select role from profiles where id = auth.uid();
$$ language sql stable;

-- profiles: everyone can read their own; admin can read all
create policy "profiles_self_read" on profiles
    for select using (id = auth.uid() or current_role_name() = 'admin');

-- doctors: readable by everyone (patients need to browse doctors)
create policy "doctors_public_read" on doctors
    for select using (true);
create policy "doctors_admin_write" on doctors
    for all using (current_role_name() = 'admin');

-- doctor_hours / doctor_leaves: public read (for slot calc), doctor manages own
create policy "hours_public_read" on doctor_hours for select using (true);
create policy "hours_doctor_write" on doctor_hours
    for all using (
        doctor_id in (select id from doctors where user_id = auth.uid())
    );

create policy "leaves_public_read" on doctor_leaves for select using (true);
create policy "leaves_doctor_write" on doctor_leaves
    for all using (
        doctor_id in (select id from doctors where user_id = auth.uid())
    );

-- appointments: patient sees own, doctor sees own, admin sees all
-- BUT note column must be hidden from admin — handled at API layer
-- (Postgres RLS is row-level, not column-level, so the FastAPI
--  service strips `note` before returning admin responses).
create policy "appt_patient_read" on appointments
    for select using (patient_id = auth.uid());

create policy "appt_doctor_read" on appointments
    for select using (
        doctor_id in (select id from doctors where user_id = auth.uid())
    );

create policy "appt_admin_read" on appointments
    for select using (current_role_name() = 'admin');

create policy "appt_patient_insert" on appointments
    for insert with check (patient_id = auth.uid());

create policy "appt_patient_update_own" on appointments
    for update using (patient_id = auth.uid());

create policy "appt_doctor_update_own" on appointments
    for update using (
        doctor_id in (select id from doctors where user_id = auth.uid())
    );
