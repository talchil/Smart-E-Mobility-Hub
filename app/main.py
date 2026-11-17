from contextlib import asynccontextmanager
from fastapi import FastAPI
from app import store
from app.seed_data import load_seed
from app.routers import search, reservation, pickup_return, charging, dashboard, whatif, events
from app import simulator

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: seed the store on startup."""
    load_seed()
    print(
        f"[startup] seeded {len(store.vehicles)} vehicles, "
        f"{len(store.stations)} stations"
    )
    
    # Khởi động simulator (sẽ tự chặn lại nếu SIM_ENABLED != True)
    simulator.start_simulator()
    
    yield

app = FastAPI(
    title="Smart E-Mobility Hub",
    description=(
        "Prototype backend: search, reserve, pickup/return, "
        "charging, dashboard, what-if"
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(search.router)
app.include_router(reservation.router)
app.include_router(pickup_return.router)
app.include_router(charging.router)
app.include_router(dashboard.router)
app.include_router(whatif.router)
app.include_router(events.router)

@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}