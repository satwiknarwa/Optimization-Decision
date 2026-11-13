# Shipment Route Optimizer & Decision Support System

A multi-criteria freight route evaluation and ranking engine built with **FastAPI**, **SQLite**, and **Vanilla JavaScript + Leaflet.js**. It optimizes shipping corridors across cost, transit duration, and operational risk under strict budget and delivery deadline constraints.

---

## 1. Architecture & Tech Stack

```
┌────────────────────────────────────────────────────────┐
│                   Browser Client                       │
│  - Vanilla ES6+ JavaScript (Asynchronous fetch)        │
│  - Leaflet.js (OpenStreetMap corridor visualization)   │
│  - Responsive CSS3 UI (No Node.js/build step needed)   │
└───────────────────────────┬────────────────────────────┘
                            │
               HTTP / JSON  │  (Port 8000 or Port 3000)
                            ▼
┌────────────────────────────────────────────────────────┐
│                   FastAPI Backend                      │
│  - Port 8000: REST API & Static Asset Mounting         │
│  - Multi-Criteria Optimization Engine (optimizer.py)   │
│  - SQLite Database with auto-migration (database.py)   │
└────────────────────────────────────────────────────────┘
```

* **Backend**: Python 3.10+, FastAPI, Uvicorn, SQLite3, Pydantic.
* **Frontend**: Vanilla HTML5, CSS3, ES6+ JavaScript, Leaflet.js (CDN). Zero build tooling, zero external Node dependencies.
* **Storage**: SQLite (`data/routeiq.db`) with automatic table creation, JSON seed loading, and evaluation audit logging.

---

## 2. Project Structure

```text
.
├── backend/
│   ├── main.py            # FastAPI application, CORS configuration, and static file mount
│   ├── optimizer.py       # Core scoring algorithm, min-max normalization, constraint checks
│   ├── database.py        # SQLite schema initialization, data seeding, and audit logging
│   ├── generate_data.py   # Deterministic synthetic shipment generator (20 shipments / 80 routes)
│   └── __init__.py
├── frontend/
│   ├── index.html         # Single-page interface (corridor selection, priority weights, map)
│   ├── app.js             # Client controller, API client, and Leaflet map renderer
│   └── style.css          # Design system, responsive split-view, and card layouts
├── data/
│   ├── routeiq.db         # Persistent SQLite database (auto-seeded on first run)
│   └── shipments_data.json# Canonical dataset fixture
├── tests/
│   └── test_optimizer.py  # Unit tests for scoring logic, constraints, and explanations
├── evaluate.py            # Comprehensive benchmark and sensitivity analysis across all lanes
├── requirements.txt       # Pinned production dependencies
└── README.md
```

---

## 3. Quickstart & Execution Commands

### Prerequisites
* Python 3.10 or higher installed.

```bash
# Clone the repository and navigate into the root directory
cd assignment

# Install Python dependencies
pip install -r requirements.txt
```

---

### Option A: Single-Command Full-Stack (Recommended)

FastAPI serves both the REST API endpoints and mounts the static `frontend/` directory on the same port:

```bash
python backend/main.py
```

* **Web Dashboard**: [http://localhost:8000](http://localhost:8000)
* **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

> **Why this works**: `backend/main.py` mounts `frontend/` at `/`. A recruiter or evaluator can run the entire system with one single command—no separate terminal or Node runtime required.

---

### Option B: Decoupled Development Mode (Two Terminals)

If you prefer running the frontend and backend in isolated processes during frontend development:

**Terminal 1 — Backend API (Port 8000):**
```bash
python backend/main.py
```

**Terminal 2 — Frontend Static Server (Port 3000):**
```bash
python -m http.server 3000 --directory frontend
```
* **Web Dashboard**: [http://localhost:3000](http://localhost:3000)

> **What `python -m http.server 3000 --directory frontend` does**:
> Uses Python's built-in standard library static file server module to serve the `frontend/` folder on port `3000`. `app.js` automatically detects port `3000` and communicates with the FastAPI backend on port `8000` via CORS.

---

## 4. REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/shipments` | Returns all available shipment corridors and metadata. |
| `GET` | `/api/shipments/{id}` | Returns a specific shipment with its candidate route options. |
| `POST` | `/api/evaluate` | Evaluates, ranks, and returns explanations for routes under budget, deadline, and priority weights. |
| `GET` | `/docs` | Interactive OpenAPI / Swagger UI documentation. |

---

## 5. Optimization Methodology

1. **Expected Transit Time**: Raw transit days ignore disruption risks. Routes are compared using expected delivery duration:
   $$\text{expected\_total\_days} = \text{transit\_time\_days} + (\text{delay\_probability} \times \text{expected\_delay\_days})$$
2. **Min-Max Normalization**: Cost (\$), transit time (days), and risk score (`0–10`) operate on different units. Each metric is normalized to $[0.0, 1.0]$ across candidate routes for that shipment ($0.0 = \text{best}$, $1.0 = \text{worst}$).
3. **Priority Profiles**:
   * `balanced`: 40% Cost, 35% Expected Time, 25% Risk
   * `cost_first`: 70% Cost, 15% Expected Time, 15% Risk
   * `speed_first`: 15% Cost, 70% Expected Time, 15% Risk
   * `risk_averse`: 20% Cost, 20% Expected Time, 60% Risk
4. **Hard Constraint Enforcement**: Routes exceeding budget or deadline receive a `+0.50` penalty per breached constraint, ensuring feasible routes always rank ahead of infeasible ones while maintaining visibility when all options exceed limits.
5. **Trade-off Explanations**: Generates deterministic natural-language explanations comparing the recommended route against the cheapest and fastest alternatives with concrete dollar and day differentials.

---

## 6. Testing & Evaluation Benchmark

### Run Unit Tests
```bash
python -m unittest tests/test_optimizer.py
```

### Run Evaluation & Sensitivity Benchmark
Evaluates all 20 shipments (80 total routes) across all policies and stress tests:
```bash
python evaluate.py
```

#### Benchmark Results (20 Shipments / 80 Routes)

| Policy | Feasible | Avg Cost | Avg Exp. Days | Avg Delay Prob | Avg Risk |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Baseline: Cheapest** | 10/20 (50.0%) | \$2,665.00 | 28.63 | 39.2% | 6.50/10 |
| **Baseline: Fastest** | 0/20 (0.0%) | \$5,486.00 | 16.07 | 6.5% | 1.65/10 |
| **Strategy: `balanced`** | 20/20 (100.0%) | \$3,458.00 | 22.92 | 15.8% | 3.88/10 |
| **Strategy: `cost_first`** | 20/20 (100.0%) | \$3,003.00 | 25.29 | 26.3% | 5.12/10 |
| **Strategy: `speed_first`** | 20/20 (100.0%) | \$3,718.00 | 22.36 | 14.5% | 3.75/10 |
| **Strategy: `risk_averse`** | 20/20 (100.0%) | \$3,978.00 | 24.94 | 10.0% | 2.27/10 |

* **Strategy Sensitivity**: Compared to `balanced`, switching to `cost_first` shifts 10/20 recommendations, `speed_first` shifts 5/20, and `risk_averse` shifts 15/20.
* **Constraint Stress Test**: Tightening budget and deadline by 25% reduces feasible coverage under `balanced` from 100.0% to 25.0%.
