# n8n Workflows — Nowshera Family Clinic

7 ready-to-import workflow files. Each one is a `.json` file exported
in n8n's native format.

## How to import

1. Open n8n → click **"+ Add workflow"** → menu (⋯) → **Import from File**.
2. Pick one of these `.json` files. Repeat for all 7.
3. For every **webhook** workflow, open the "Send ... Email" node and
   set your own **SMTP credential** (or swap the node for Gmail /
   SendGrid if you prefer — same fields: to, subject, body).
4. For the 2 **cron** workflows, open the HTTP Request node and:
   - Update the `url` if your backend isn't on `localhost:8000`.
   - Update the `x-internal-secret` header value to match
     `INTERNAL_SECRET` in `app/routers/internal.py`.
5. Click **Activate** (top-right toggle) on all 7 workflows.
6. Copy each webhook's **Production URL** (click the Webhook node →
   copy URL) and confirm it matches `N8N_WEBHOOK_BASE` + the event
   name in your backend's `.env`, e.g.
   `http://localhost:5678/webhook/appointment-confirmed`.

## The 7 workflows

| # | File | Type | Fires when |
|---|---|---|---|
| 1 | `1-cron-expire-pending.json` | Cron (every 5 min) | Calls backend to auto-cancel overdue Pending appointments |
| 2 | `2-cron-daily-reminders.json` | Cron (daily 8am) | Calls backend to send tomorrow's reminders |
| 3 | `3-webhook-appointment-confirmed.json` | Webhook | Doctor confirms an appointment |
| 4 | `4-webhook-appointment-cancelled.json` | Webhook | Appointment cancelled (leave day or expired) |
| 5 | `5-webhook-appointment-rejected.json` | Webhook | Doctor rejects a request |
| 6 | `6-webhook-appointment-reminder.json` | Webhook | Day-before reminder |
| 7 | `7-webhook-doctor-invited.json` | Webhook | Admin adds a new doctor |

## How the pieces connect

```
Backend (FastAPI)  --POST-->  n8n Webhook  -->  Email node  -->  patient/doctor inbox
n8n Cron  --POST-->  Backend /internal/*  --(internally calls the webhooks above)-->  emails sent
```

You never call an email node directly from the backend — the backend
only decides *when* to notify; n8n owns *how* the email looks and is sent.
This means you can change email wording/branding anytime in n8n without
touching backend code.

## Testing (matches the brief's test case #10)

1. Activate all workflows.
2. Confirm an appointment for tomorrow → check webhook #3 fires, then
   #6 fires the next day (or trigger #2's cron manually to test now).
3. Leave a Pending appointment unconfirmed past its start time → run
   workflow #1 manually ("Execute Workflow" button) → check #4 fires.
4. Add a doctor from the admin panel → check #7 fires with the
   correct set-password link.
