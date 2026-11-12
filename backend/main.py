"""FastAPI backend for shipment route evaluation and map visualization."""
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

# Ensure the project root is importable regardless of launch directory and
# inherited by Uvicorn's --reload child process (SpawnProcess on Windows).
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

existing_pythonpath = os.environ.get("PYTHONPATH", "")
pythonpath_entries = [p for p in existing_pythonpath.split(os.pathsep) if p]
if str(ROOT_DIR) not in pythonpath_entries:
    os.environ["PYTHONPATH"] = os.pathsep.join([str(ROOT_DIR), *pythonpath_entries])

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.database import (
    init_db,
    seed_db_from_json,
    get_all_shipments,
    get_shipment_with_routes,
    log_optimization_run,
)
from backend.optimizer import evaluate_routes, generate_explanation


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure SQLite database tables exist and are seeded on server startup."""
    init_db()
    seed_db_from_json()
    yield


app = FastAPI(
    title="Shipment Route Optimizer API",
    description="Multi-criteria shipment route scoring and explanation API backed by SQLite.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for decoupled frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EvaluateRequest(BaseModel):
    shipment_id: str
    strategy: Optional[str] = "balanced"
    budget_usd: Optional[float] = None
    deadline_days: Optional[float] = None


@app.get("/api/shipments")
def get_shipments():
    """Returns list of shipment corridors from SQLite."""
    shipments = get_all_shipments()
    return [
        {
            "shipment_id": s["id"],
            "origin": s["origin"],
            "destination": s["destination"],
            "cargo_type": s["cargo_type"],
            "budget_usd": s["budget_usd"],
            "deadline_days": s["deadline_days"],
        }
        for s in shipments
    ]


@app.post("/api/evaluate")
def evaluate_shipment_endpoint(req: EvaluateRequest):
    """
    Evaluates candidate routes from SQLite under live budget and deadline overrides,
    and logs the decision into the optimization_history audit table.
    """
    shipment = get_shipment_with_routes(req.shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {req.shipment_id} not found")

    budget_used = float(req.budget_usd) if req.budget_usd is not None and req.budget_usd > 0 else shipment["budget_usd"]
    deadline_used = float(req.deadline_days) if req.deadline_days is not None and req.deadline_days > 0 else shipment["deadline_days"]

    shipment["budget_usd"] = budget_used
    shipment["deadline_days"] = deadline_used

    ranked_routes = evaluate_routes(shipment, strategy=req.strategy)
    explanation = generate_explanation(shipment, ranked_routes, strategy=req.strategy)

    # Preserve geographic waypoints from DB on each ranked route for map rendering
    route_waypoints = {r["route_id"]: r.get("waypoints", []) for r in shipment["routes"]}
    for rr in ranked_routes:
        rr["waypoints"] = route_waypoints.get(rr["route_id"], [])

    # Log decision to SQLite optimization_history table
    if ranked_routes:
        log_optimization_run(shipment, ranked_routes[0], req.strategy, budget_used, deadline_used)

    return {
        "shipment": shipment,
        "ranked_routes": ranked_routes,
        "explanation": explanation,
    }


# Serve the frontend directory if accessed directly via backend port
FRONTEND_DIR = ROOT_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(ROOT_DIR / "backend")],
    )
