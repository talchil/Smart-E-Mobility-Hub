# Smart E-Mobility Hub — Backend

Backend prototype for an electric vehicle booking and charging scheduling system for students.

## 🚀 Modules & Features

* **Search & Reservation**: Find available vehicles and create bookings.

* **Pickup & Return**: Manage vehicle lifecycle and rental sessions (`AVAILABLE` ↔ `IN_USE`).

* **Charging Management**: Handle charging slots and strict vehicle charging states (`CHARGING`).

* **Dashboard (UC-09)**: Real-time metrics and system monitoring.

* **What-If Analysis (UC-12)**: Simulate operational scenarios (e.g., adding stations, changing pricing).

* **Event Processing (UC-14)**: Webhook API for IoT telemetry and manual operational events with idempotency logic.

* **Live Simulator**: A background task simulating real-time vehicle movement (GPS tracking) and battery consumption.

## 🛠 Tech Stack

* **Framework**: FastAPI + Pydantic

* **Database**: In-memory store (Thread-safe via `threading.RLock`, no external DB required)

* **Language**: Python 3.11+

* **Testing**: Pytest with HTTPX

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
   *Note:* By default, `SIM_ENABLED` is set to `False` in `.env` to keep data static for stable testing.

## ▶️ Running the Server

### Windows
Start the server using the provided batch script:
```cmd
run.bat
```
*When you run this file, an interactive startup menu will appear allowing you to choose:*
- **[1] Standard Mode (SIM_ENABLED=False):** Static data, perfect for API testing and development.
- **[2] Live Mode (SIM_ENABLED=True):** Simulator activates. Vehicles currently `IN_USE` will dynamically update their GPS coordinates and drain battery every 5 seconds.

### Mac/Linux
Run the shell script for standard mode:
```bash
./run.sh
```
To run with the Live Simulator enabled, pass the environment variable inline:
```bash
SIM_ENABLED=True ./run.sh
```

*(Alternatively, run manually: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`)*
*(To run manually with simulator: `SIM_ENABLED=True uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`)*

---

Once the server is running, you can access the system at:

* **API Documentation (Swagger UI)**: <http://localhost:8000/docs>
* **Health Check**: <http://localhost:8000/health>
* **Re-Doc**: <http://localhost:8000/redoc>

## 🧪 Testing

The project includes a comprehensive test suite (Service and API levels) ensuring strict state transitions (NIF-05) and event idempotency (NIF-01).

To run all tests:

```bash
pytest -v
```