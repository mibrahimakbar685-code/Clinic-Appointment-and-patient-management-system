from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import doctors, appointments, admin, internal

app = FastAPI(title="Nowshera Family Clinic API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your frontend's domain before going live
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(doctors.router)
app.include_router(appointments.router)
app.include_router(admin.router)
app.include_router(internal.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "clinic-api"}
