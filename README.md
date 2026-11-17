# Smart E-Mobility Hub — Backend

Backend prototype for an electric vehicle booking and charging scheduling system for students.

## 🚀 Modules & Features
- **Search & Reservation**: Find available vehicles and create bookings.
- **Pickup & Return**: Manage vehicle lifecycle and rental sessions (`AVAILABLE` ↔ `IN_USE`).
- **Charging Management**: Handle charging slots and strict vehicle charging states (`CHARGING`).
- **Dashboard (UC-09)**: Real-time metrics and system monitoring.
- **What-If Analysis (UC-12)**: Simulate operational scenarios (e.g., adding stations, changing pricing).
- **Event Processing (UC-14)**: Webhook API for IoT telemetry and manual operational events with idempotency logic.
- **Live Simulator**: A background task simulating real-time vehicle movement (GPS tracking) and battery consumption.

## 🛠 Tech Stack
- **Framework**: FastAPI + Pydantic
- **Database**: In-memory store (Thread-safe via `threading.RLock`, no external DB required)
- **Language**: Python 3.11+
- **Testing**: Pytest with HTTPX

## ⚙️ Setup & Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration:**
   Copy the provided example environment file to create your own configuration:
   ```bash
   cp .env.example .env
   ```
   *Note on Simulation:* By default, `SIM_ENABLED` is set to `False` to keep data static for testing. To see vehicles move and batteries drain in real-time, edit `.env` and set `SIM_ENABLED=True`.

## ▶️ Running the Server

Start the FastAPI server using the provided startup scripts:

- **Windows:** 
  ```cmd
  run.bat
  ```
- **Mac/Linux:** 
  ```bash
  ./run.sh
  ```

*(Alternatively, run manually: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --workers 1`)*

Once the server is running, you can access the system at:
- **API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Re-Doc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 🧪 Testing

The project includes a comprehensive test suite (Service and API levels) ensuring strict state transitions (NIF-05) and event idempotency (NIF-01).

To run all tests:
```bash
pytest -v
```