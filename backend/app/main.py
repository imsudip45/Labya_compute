from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import init_db
from app.routers.auth import router as auth_router
from app.routers.gpus import router as gpus_router
from app.routers.wallets import router as wallets_router
from app.routers.sessions import router as sessions_router
from app.routers.dashboard import router as dashboard_router

app = FastAPI(
    title="Labhya Compute API",
    description="FastAPI rewrite of the Labhya Compute GPU rental and hosting platform",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router)
app.include_router(gpus_router)
app.include_router(wallets_router)
app.include_router(sessions_router)
app.include_router(dashboard_router)

@app.on_event("startup")
def on_startup():
    # Automatically initialize tables in Postgres if not exists
    init_db()

@app.get("/")
def read_root():
    return {"message": "Welcome to Labhya Compute API (FastAPI)"}
