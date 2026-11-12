# Shipment Route Optimizer

Multi-criteria shipment route evaluation and explanation system built for optimizing freight lanes across cost, transit time, and operational risk under budget and deadline constraints.

---

## 1. Problem Formulation

Selecting a shipping route involves balancing conflicting objectives rather than picking the cheapest or fastest option alone:

- **Expected Transit Time**: Raw transit days ignore disruption uncertainty, so routes are compared using expected delivery time:
  `expected_total_days = transit_time_days + (delay_probability * expected_delay_days)`
- **Min-Max Normalization**: Because freight cost (USD), transit duration (days), and risk score (`0–10`) have different scales, each metric is normalized to `[0.0, 1.0]` across the shipment's candidate routes (`0.0` = best, `1.0` = worst).
- **Weighted Priority Profiles**:
  - `balanced`: 40% cost, 35% expected time, 25% risk
  - `cost_first`: 70% cost, 15% expected time, 15% risk
  - `speed_first`: 15% cost, 70% expected time, 15% risk
  - `risk_averse`: 20% cost, 20% expected time, 60% risk
- **Hard Constraint Checks**: Routes exceeding `budget_usd` or `deadline_days` receive a `0.50` penalty per breached constraint so feasible routes rank ahead of infeasible alternatives while still allowing operators to inspect the nearest option when all routes breach tight limits.
- **Plain-English Explanations**: `generate_explanation()` compares the selected route against both the lowest-cost and fastest alternatives, reporting exact dollar, day, and delay-probability trade-offs.

---

## 2. Synthetic Dataset Construction

`backend/generate_data.py` builds 20 shipments (`80` candidate routes total) across 4 global maritime corridors (`Shanghai -> Rotterdam`, `Shenzhen -> Los Angeles`, `Singapore -> Hamburg`, `Mumbai -> Antwerp`) with slight cost variation per shipment.

Each shipment intentionally includes 4 contrasting route options so no single metric dominates trivially:
1. **Direct Ocean**: Moderate cost and risk, meets both budget and deadline.
2. **Diversion Route** (e.g., Cape of Good Hope): Lower geopolitical/delay risk, higher cost or misses the delivery deadline.
3. **Economy Transshipment**: Lowest freight cost, but high delay probability (`35–42%`) and longer expected delay.
4. **Premium Multimodal (Air-Sea / Rail-Sea)**: Fastest transit time and lowest risk, but priced above the shipment budget.

Shipments, candidate routes, and evaluation logs are persisted in SQLite (`data/routeiq.db`) on server startup.

---

## 3. Project Structure

```text
.
├── backend/
│   ├── __init__.py
│   ├── main.py           # FastAPI app (GET /api/shipments, POST /api/evaluate)
│   ├── database.py       # SQLite initialization, seeding, and optimization logs
│   ├── optimizer.py      # Min-Max scoring, constraint checks, and explanations
│   └── generate_data.py  # Generates data/shipments_data.json (20 shipments)
├── frontend/
│   ├── index.html        # Single-page light-mode route planner & map UI
│   ├── style.css         # Light-mode styles
│   └── app.js            # Fetches API results and renders Leaflet routes
├── data/
│   ├── shipments_data.json
│   └── routeiq.db        # Auto-created SQLite database on first startup
├── tests/
│   └── test_optimizer.py # Unit tests for constraints, normalization, explanations
├── evaluate.py           # Benchmark and sensitivity analysis across all 20 shipments
├── requirements.txt
└── README.md
```

---

## 4. Setup & Running Locally

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Start the Backend API (Port 8000)
```bash
python backend/main.py
```
- API Docs (Swagger UI): `http://127.0.0.1:8000/docs`

### Start the Frontend (Port 3000)
In a second terminal:
```bash
python -m http.server 3000 --directory frontend
```
Open `http://localhost:3000` in your browser. (You can also open `http://127.0.0.1:8000` directly since FastAPI mounts `frontend/` as a fallback.)

---

## 5. Evaluation & Testing

Run the unit tests:
```bash
python -m unittest tests/test_optimizer.py
```

Run the dataset benchmark and sensitivity check across all 20 shipments:
```bash
python evaluate.py
```

Measured output across the 20 synthetic shipments (80 routes):

| Policy | Feasible | Avg Cost | Avg Exp. Days | Avg Delay Prob | Avg Risk |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Baseline: Cheapest | 10/20 (50.0%) | \$2,665.00 | 28.63 | 39.2% | 6.50/10 |
| Baseline: Fastest | 0/20 (0.0%) | \$5,486.00 | 16.07 | 6.5% | 1.65/10 |
| Strategy: `balanced` | 20/20 (100.0%) | \$3,458.00 | 22.92 | 15.8% | 3.88/10 |
| Strategy: `cost_first` | 20/20 (100.0%) | \$3,003.00 | 25.29 | 26.3% | 5.12/10 |
| Strategy: `speed_first` | 20/20 (100.0%) | \$3,718.00 | 22.36 | 14.5% | 3.75/10 |
| Strategy: `risk_averse` | 20/20 (100.0%) | \$3,978.00 | 24.94 | 10.0% | 2.27/10 |

- **Strategy Sensitivity**: Compared to `balanced`, switching to `cost_first` changes 10/20 recommendations, `speed_first` changes 5/20, and `risk_averse` changes 15/20.
- **Constraint Stress Test**: Tightening both budget and deadline by 25% reduces feasible shipment coverage under `balanced` from 100.0% (20/20) to 25.0% (5/20).

---

## 6. Assumptions & Limitations

- Expected transit time models delay linearly (`transit_time_days + delay_probability * expected_delay_days`) rather than simulating tail-risk distributions via Monte Carlo.
- Min-Max normalization scales values relative to the candidate set of each individual shipment, so scores should be compared across routes for the same shipment rather than across different corridors.
- Waypoint coordinates are representative maritime corridor points for visualization rather than real-time AIS vessel telemetry.
