# Clinic Appointment & Patient Management System

A website where patients request appointments with doctors, doctors manage their schedule and visits, and the clinic manages everything in one place.

## The problem
Nowshera Family Clinic has several doctors and sees more patients every month. Appointments are still booked by phone calls and WhatsApp messages and written in a register. This is causing problems:
- **Bookings are scattered** Appointments come in by phone and WhatsApp and are written in a register. There is no single, reliable place to see them.
- **Double bookings** Two patients sometimes get the same doctor at the same time, and one of them has to wait or go home.
- **Doctors' schedules aren't clear** Patients and the clinic don't know which days and hours each doctor is free.
- **Plans change, but the register doesn't** When a patient cancels or wants a different time, the change is often not written down, so slots stay blocked or get double-booked.
- **Doctors' days off aren't planned for** When a doctor takes a day off, patients who already booked that day aren't told and come to the clinic for nothing.
- **Patients forget appointments** Nobody confirms or reminds them, so patients miss visits and the time is wasted.
- **Visit history is hard to find** A doctor can't quickly see a patient's past visits or what happened at them.
- **No clear view of the clinic** The clinic can't easily see today's appointments, or how busy each doctor is.

The client needs one dependable website for patients, doctors, and the clinic admin, instead of phone calls, WhatsApp, and a paper register.

## Your approach
You'll build a clinic appointment website with three sides: one for patients, one for doctors, and one for the admin (clinic manager). Emails are sent automatically.
- **One place for all appointments** Patients create an account, choose a doctor, and request an appointment on the website. No more phone calls, WhatsApp messages, or paper register.
- **No double bookings** Each time slot with a doctor can only be held by one appointment. A slot is taken as soon as it is requested, so nobody else can book it while it waits for the doctor. A patient can't have two appointments at the same time, even with different doctors.
- **Clear doctor availability** Each doctor sets the days and hours they work. Their hours are split into 30-minute slots, and patients only see slots that are free.
- **Doctor leave days** Doctors mark the dates they are on leave, and no slots are shown on those days. Any Pending or Confirmed appointments on a leave day are cancelled automatically, and the patients are emailed.
- **Easy cancel and reschedule** Patients can cancel an appointment, or move it to another free slot, up to 2 hours before it starts. The old slot becomes free straight away for someone else.
- **Confirmation and reminders** The doctor confirms or rejects each appointment request. If a Pending appointment still isn't confirmed when its start time comes, it is cancelled automatically. The patient is emailed automatically when an appointment is confirmed, when it is cancelled or rejected, and the day before it.
- **Visit history and notes** Doctors see each patient's past appointments with them. Once the visit time has started, the doctor marks it Completed or No-show and can add a short note.
- **A dashboard for the clinic** Admins see today's appointments. For each doctor, they see how many appointments are Pending, Confirmed, Completed, No-show, and Cancelled.
- **Safe and private** Patients only see their own appointments and notes. Doctors only see their own appointments and patients. Only the patient and the doctor who saw them can read visit notes; the admin can't. The server must check all of this, not just hide buttons on the screen.
- **Built as a full-stack project** A frontend: the pages each person sees and uses. A backend (API): where every rule is checked and data is saved. A database with secure sign-in, so each person's data stays safe. Automation that sends the emails and reminders by itself. You choose the tools. For example: React for the frontend, Python for the backend, Supabase or MongoDB for the database, and n8n for automation. Research what fits your project.

### Not included
- Online payments
- Video consultations
- Prescriptions or pharmacy
- Lab reports
- Insurance or billing
- Real SMS or WhatsApp messages
- Mobile app (Android/iOS)
- Multiple clinic branches

## Test cases
1. **Book an appointment** — Sign in as a patient. Choose a doctor, pick a free slot, and request it. Then sign in as that doctor and confirm it. Expected: It is saved as Pending, then becomes Confirmed. The patient receives a confirmation email.
2. **Add a doctor and check the dashboard** — As admin, add a doctor. Use the email they receive to set their password and sign in. As that doctor, add hours for Monday 9:00–11:00. As a patient, open that doctor and request one slot. As admin, open the dashboard and refresh the page. Expected: The doctor gets a set-password email. Patients see four 30-minute slots on Monday from 9:00 to 11:00. The dashboard shows 1 Pending appointment for that doctor, and it stays the same after refresh.
3. **Same slot or same time twice** — Patient A requests a slot. Patient B tries to book the same slot with the same doctor. Then Patient A tries to book a different doctor at the same time. Expected: Both are blocked with a clear message. The slot still has only one appointment, and Patient A still has only one appointment at that time.
4. **Outside hours or fully booked** — Try to book a time outside the doctor's hours (for example, by sending the request directly with Postman). Then book every slot in one day and check that day again. Expected: The outside-hours booking is blocked. The fully booked day shows no free slots.
5. **Past slot, early completion, or leave day** — Try to book a slot whose time has passed. As admin, deactivate a doctor, then try to book them. As a doctor, try to mark tomorrow's appointment Completed. Then add a leave day on a date where a patient has a Confirmed appointment. Expected: The first three are blocked with a clear message. On the leave day, no slots are shown, the existing appointment becomes Cancelled, and that patient receives an email.
6. **Cancel and reschedule** — Cancel a Confirmed appointment that is more than 2 hours away, and book the same slot with another patient. Reschedule a different appointment to a new slot. Then try to cancel an appointment that starts in less than 2 hours. Expected: The cancelled slot is free, the new booking works, and a cancellation email is sent. After rescheduling, the old slot is free and the appointment is Pending at the new time. The last cancellation is blocked.
7. **Wrong hours or leave day** — As a doctor, add hours where the end time is before the start time (like 13:00–9:00), hours that overlap hours you already added, and a leave day in the past. Expected: None of them are saved, and a clear message explains why.
8. **Wrong role** — Sign in as a patient and try to confirm an appointment or add a doctor by sending the request directly (for example, with Postman). Sign in as Doctor A and try to confirm Doctor B's appointment. Expected: All are blocked by the server. Nothing changes.
9. **Private records** — Sign in as Patient A and try to open Patient B's appointment. Sign in as Doctor A and try to open Doctor B's patient history. Sign in as admin and try to open a visit note. Expected: Access is denied every time, and no private details or notes are shown.
10. **Automatic emails and mobile view** — Confirm an appointment for tomorrow. Leave another appointment Pending until its start time has passed. Run your automations, then refresh. Check the site in mobile view (F12, then Ctrl+Shift+M). Expected: The confirmed patient receives one reminder email. The unconfirmed appointment becomes Cancelled and that patient receives one email. Nothing changes after refresh, and the site is usable in mobile view.

## Definition of done
Your project is done when your website runs on your computer, everything below works, and all 10 test cases above pass. If any test fails, fix it before you submit.
- Your website, backend, database, and automations run on your computer without errors.
- Patients can sign up, choose a doctor, and request a free slot.
- Doctors can set their hours, confirm or reject requests, and complete visits with notes.
- No slot can be booked twice, in the past, or outside the doctor's hours, and no patient has two appointments at the same time.
- Pending appointments that aren't confirmed by their start time are cancelled automatically.
- Doctors can mark leave days, and appointments on those days are cancelled with an email.
- Patients can cancel and reschedule up to 2 hours before, and the old slot becomes free.
- Confirmation, cancellation, and reminder emails are sent automatically.
- Admins can manage doctors and see correct appointments and totals.
- Each person can only see and do what their role allows, and visit notes stay private.
- The website works in mobile view and on a normal screen, and nothing is lost after refresh.
- All 10 test cases pass.