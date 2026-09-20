# Nowshera Family Clinic — Backend

FastAPI + Supabase (Postgres + Auth) backend. Emails/reminders are
sent by **n8n**, triggered either directly by this API (webhooks) or
by n8n's own Cron nodes calling the `/internal/*` endpoints.

## 1. Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # fill in your Supabase project keys
```

## 2. Database

1. Create a Supabase project.
2. Open the SQL editor and run `database/schema.sql` — this creates
   all tables, constraints, and Row Level Security policies.
3. Copy your Project URL, `service_role` key, and `anon` key into `.env`.

## 3. Run

```bash
uvicorn app.main:app --reload --port 8000
```

API docs (auto-generated): http://localhost:8000/docs

## 4. n8n workflows to build

| Workflow | Trigger | What it does |
|---|---|---|
| Expire pending | Cron, every 5 min | POST `/internal/expire-pending` (header `x-internal-secret`) → for each returned cancelled appointment, send cancellation email |
| Daily reminders | Cron, once/day (e.g. 8am) | POST `/internal/send-reminders` → send reminder email per appointment returned |
| Appointment confirmed | Webhook `appointment-confirmed` | Backend calls this on confirm → send confirmation email |
| Appointment cancelled/rejected | Webhook `appointment-cancelled` / `appointment-rejected` | Backend calls this → send email with reason |
| Doctor invited | Webhook `doctor-invited` | Backend calls this when admin adds a doctor → send set-password email with the link |

Set `N8N_WEBHOOK_BASE` in `.env` to your n8n instance's webhook base URL,
e.g. `http://localhost:5678/webhook`.

⚠️ Before going live, change `INTERNAL_SECRET` in
`app/routers/internal.py` to a real secret (move it to `.env` too),
and lock down CORS `allow_origins` in `app/main.py` to your frontend's
actual domain.

## 5. Key design decisions (map back to the brief)

- **No double booking**: enforced by a real Postgres unique index
  (`one_appointment_per_doctor_slot`), not just application code — so
  it holds even under concurrent requests.
- **No double-booking a patient across doctors**: a second unique
  index on `(patient_id, slot_start)`.
- **Server re-validates every slot** (`services/slots.py`) before
  booking/rescheduling — the frontend's slot list is a convenience,
  never trusted blindly.
- **Visit notes privacy**: the `note` column is simply never selected
  in any admin-facing query, and RLS policies restrict row-level read
  access to the owning patient/doctor.
- **Role checks**: every mutating endpoint uses
  `Depends(require_role(...))` plus an explicit ownership check
  (e.g. doctor can only confirm their own appointments).

## 6. Folder structure

```
app/
  core/        # config + auth/role dependencies
  models/      # Pydantic request/response schemas
  routers/     # doctors, appointments, admin, internal (n8n)
  services/    # slot calculation, notification triggers
  main.py
database/
  schema.sql   # run this in Supabase SQL editor
```
