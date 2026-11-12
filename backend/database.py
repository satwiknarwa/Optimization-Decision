"""SQLite persistence layer for shipments, routes, and optimization run history."""
import sqlite3
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "data" / "routeiq.db"


def get_db_connection():
    """Returns a SQLite connection with dict-like row access."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates the 3 SQL tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Shipments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shipments (
        id TEXT PRIMARY KEY,
        origin TEXT NOT NULL,
        destination TEXT NOT NULL,
        cargo_type TEXT NOT NULL,
        budget_usd REAL NOT NULL,
        deadline_days REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Routes Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS routes (
        id TEXT PRIMARY KEY,
        shipment_id TEXT NOT NULL,
        route_name TEXT NOT NULL,
        carrier TEXT NOT NULL,
        mode TEXT NOT NULL,
        via_hub TEXT NOT NULL,
        cost_usd REAL NOT NULL,
        transit_time_days REAL NOT NULL,
        delay_probability REAL NOT NULL,
        expected_delay_days REAL NOT NULL,
        congestion_risk REAL NOT NULL DEFAULT 0.0,
        geopolitical_risk REAL NOT NULL DEFAULT 0.0,
        risk_score REAL NOT NULL,
        waypoints_json TEXT NOT NULL,
        FOREIGN KEY (shipment_id) REFERENCES shipments(id)
    );
    """)

    # Add risk breakdown columns if upgrading an existing database
    cursor.execute("PRAGMA table_info(routes)")
    existing_cols = {row["name"] for row in cursor.fetchall()}
    if "congestion_risk" not in existing_cols:
        cursor.execute("ALTER TABLE routes ADD COLUMN congestion_risk REAL NOT NULL DEFAULT 0.0")
    if "geopolitical_risk" not in existing_cols:
        cursor.execute("ALTER TABLE routes ADD COLUMN geopolitical_risk REAL NOT NULL DEFAULT 0.0")

    # 3. Optimization History Table (Live Audit Trail)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS optimization_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shipment_id TEXT NOT NULL,
        corridor TEXT NOT NULL,
        strategy TEXT NOT NULL,
        budget_used REAL NOT NULL,
        deadline_used REAL NOT NULL,
        recommended_route_id TEXT NOT NULL,
        carrier TEXT NOT NULL,
        cost_usd REAL NOT NULL,
        expected_days REAL NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()
    print("Database tables initialized successfully in data/routeiq.db")


def seed_db_from_json(json_path=None):
    """Seeds or syncs shipments and candidate routes from JSON while preserving history."""
    conn = get_db_connection()
    cursor = conn.cursor()

    path = Path(json_path) if json_path else (ROOT_DIR / "data" / "shipments_data.json")
    if not path.is_absolute() and not path.exists():
        path = ROOT_DIR / path
    if not path.exists():
        from backend.generate_data import save_dataset
        save_dataset(output_path=str(path))

    with open(path, "r", encoding="utf-8") as f:
        shipments = json.load(f)

    for s in shipments:
        cursor.execute("""
            INSERT OR REPLACE INTO shipments (id, origin, destination, cargo_type, budget_usd, deadline_days)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (s["shipment_id"], s["origin"], s["destination"], s["cargo_type"], s["budget_usd"], s["deadline_days"]))

        for r in s["routes"]:
            cursor.execute("""
                INSERT OR REPLACE INTO routes (
                    id, shipment_id, route_name, carrier, mode, via_hub,
                    cost_usd, transit_time_days, delay_probability, expected_delay_days,
                    congestion_risk, geopolitical_risk, risk_score, waypoints_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r["route_id"], s["shipment_id"], r["route_id"].split("-")[-1], r["carrier"], r["mode"],
                r.get("via", "Direct"), r["cost_usd"], r["transit_time_days"], r["delay_probability"],
                r["expected_delay_days"], r.get("congestion_risk", r["risk_score"]),
                r.get("geopolitical_risk", r["risk_score"]), r["risk_score"],
                json.dumps(r.get("waypoints", []))
            ))

    conn.commit()
    conn.close()
    print("Database seeded with sample shipment and route records.")


def get_all_shipments():
    """Queries all shipments from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shipments ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_shipment_with_routes(shipment_id: str):
    """Joins a shipment with all its candidate routes."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,))
    shipment_row = cursor.fetchone()
    if not shipment_row:
        conn.close()
        return None

    shipment = dict(shipment_row)
    shipment["shipment_id"] = shipment["id"]

    cursor.execute("SELECT * FROM routes WHERE shipment_id = ?", (shipment_id,))
    route_rows = cursor.fetchall()
    conn.close()

    routes = []
    for r in route_rows:
        rd = dict(r)
        rd["route_id"] = rd["id"]
        rd["via"] = rd["via_hub"]
        rd["waypoints"] = json.loads(rd["waypoints_json"]) if rd["waypoints_json"] else []
        routes.append(rd)

    shipment["routes"] = routes
    return shipment


def log_optimization_run(shipment, best_route, strategy, budget_used, deadline_used):
    """Inserts a new decision record into the optimization_history table."""
    conn = get_db_connection()
    cursor = conn.cursor()

    corridor = f"{shipment['origin'].split(',')[0]} → {shipment['destination'].split(',')[0]}"
    status = "Optimized" if best_route["is_feasible"] else "Infeasible"

    cursor.execute("""
        INSERT INTO optimization_history (
            shipment_id, corridor, strategy, budget_used, deadline_used,
            recommended_route_id, carrier, cost_usd, expected_days, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        shipment["id"], corridor, strategy, budget_used, deadline_used,
        best_route["route_id"], best_route["carrier"], best_route["cost_usd"],
        best_route["expected_total_days"], status
    ))

    conn.commit()
    conn.close()
