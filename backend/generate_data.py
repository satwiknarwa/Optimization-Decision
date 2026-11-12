"""
Synthetic Dataset Generator for Shipment Route Optimization.
Generates realistic global freight corridors with explicit budgets,
delivery deadlines, candidate routes, and authentic maritime ocean waypoints.
"""
import json
from pathlib import Path

CORRIDORS = [
    {
        "origin": "Shanghai, China (CNSHA)",
        "destination": "Rotterdam, Netherlands (NLRTM)",
        "cargo": "Consumer Electronics",
        "budget": 5000.0,
        "deadline_days": 35.0,
        "routes": [
            {
                "route_id": "Route A (Suez Canal)",
                "carrier": "Maersk Line",
                "mode": "Direct Ocean Line",
                "via": "Suez Canal Corridor",
                "cost_usd": 3800.0,
                "transit_time_days": 28.0,
                "delay_probability": 0.18,
                "expected_delay_days": 3.0,
                "congestion_risk": 4.0,
                "geopolitical_risk": 5.0,
                "risk_score": 4.5,
                "waypoints": [
                    [31.23, 121.47],  # Shanghai Port
                    [25.00, 121.50],  # Taiwan Strait
                    [14.00, 113.00],  # South China Sea
                    [1.25, 103.80],   # Singapore Strait
                    [4.50, 99.00],    # Malacca Strait
                    [5.50, 80.50],    # South of Sri Lanka (Indian Ocean)
                    [11.00, 60.00],   # Arabian Sea
                    [12.50, 43.50],   # Bab-el-Mandeb
                    [20.00, 38.50],   # Red Sea
                    [29.97, 32.55],   # Suez Canal
                    [34.50, 24.00],   # Mediterranean (South of Crete)
                    [36.50, 14.50],   # Mediterranean (South of Sicily)
                    [35.95, -5.60],   # Strait of Gibraltar
                    [43.50, -9.50],   # Cape Finisterre (Atlantic)
                    [49.50, -3.50],   # English Channel
                    [51.95, 4.14],    # Port of Rotterdam
                ],
            },
            {
                "route_id": "Route B (Cape of Good Hope)",
                "carrier": "Hapag-Lloyd",
                "mode": "Ocean Diversion",
                "via": "Cape of Good Hope",
                "cost_usd": 4300.0,
                "transit_time_days": 33.5,
                "delay_probability": 0.07,
                "expected_delay_days": 1.5,
                "congestion_risk": 1.5,
                "geopolitical_risk": 1.0,
                "risk_score": 1.3,
                "waypoints": [
                    [31.23, 121.47],  # Shanghai Port
                    [14.00, 113.00],  # South China Sea
                    [1.25, 103.80],   # Singapore
                    [-8.00, 90.00],   # Sunda Strait / South Indian Ocean
                    [-25.00, 55.00],  # South Indian Ocean
                    [-34.80, 19.50],  # Cape of Good Hope (South Africa)
                    [-15.00, 0.00],   # South Atlantic
                    [10.00, -20.00],  # West Africa (Dakar offshore)
                    [28.00, -16.00],  # Canary Islands
                    [44.00, -9.00],   # Bay of Biscay
                    [49.50, -3.50],   # English Channel
                    [51.95, 4.14],    # Port of Rotterdam
                ],
            },
            {
                "route_id": "Route C (Transshipment Economy)",
                "carrier": "CMA CGM",
                "mode": "Feeder Transshipment",
                "via": "Malacca & Red Sea Hubs",
                "cost_usd": 2950.0,         # Cheapest feasible option, high delay risk
                "transit_time_days": 31.0,
                "delay_probability": 0.35,
                "expected_delay_days": 5.5,
                "congestion_risk": 8.0,
                "geopolitical_risk": 5.0,
                "risk_score": 6.5,
                "waypoints": [
                    [31.23, 121.47],  # Shanghai
                    [22.31, 114.17],  # Hong Kong Port
                    [6.92, 79.86],    # Colombo Hub
                    [12.50, 43.50],   # Bab-el-Mandeb
                    [31.26, 32.30],   # Port Said
                    [36.00, 14.00],   # Malta Hub
                    [35.95, -5.60],   # Gibraltar
                    [51.95, 4.14],    # Rotterdam
                ],
            },
            {
                "route_id": "Route D (Premium Express)",
                "carrier": "DHL Global Forwarding",
                "mode": "Air-Sea Multimodal",
                "via": "Dubai Intermodal Hub",
                "cost_usd": 5400.0,         # Exceeds $5,000 budget!
                "transit_time_days": 24.0,
                "delay_probability": 0.07,
                "expected_delay_days": 1.0,
                "congestion_risk": 1.5,
                "geopolitical_risk": 1.0,
                "risk_score": 1.3,
                "waypoints": [
                    [31.23, 121.47],  # Shanghai
                    [25.20, 55.27],   # Dubai Airport Hub
                    [48.11, 16.57],   # European Cargo Hub
                    [51.95, 4.14],    # Rotterdam
                ],
            },
        ],
    },
    {
        "origin": "Shenzhen, China (CNSZX)",
        "destination": "Los Angeles, USA (USLAX)",
        "cargo": "Medical Devices",
        "budget": 4500.0,
        "deadline_days": 22.0,
        "routes": [
            {
                "route_id": "Route A (Pacific Direct)",
                "carrier": "ONE",
                "mode": "Direct Transpacific",
                "via": "Direct Service",
                "cost_usd": 3200.0,
                "transit_time_days": 16.0,
                "delay_probability": 0.14,
                "expected_delay_days": 2.5,
                "congestion_risk": 3.0,
                "geopolitical_risk": 2.0,
                "risk_score": 2.5,
                "waypoints": [
                    [22.54, 114.05],  # Shenzhen
                    [21.00, 123.00],  # Luzon Strait
                    [30.00, 140.00],  # South of Japan
                    [38.00, 175.00],  # Mid North Pacific
                    [36.00, -145.00], # Eastern Pacific
                    [33.74, -118.26], # Port of Los Angeles
                ],
            },
            {
                "route_id": "Route B (Budget Transshipment)",
                "carrier": "Evergreen Line",
                "mode": "Transshipment Ocean",
                "via": "Busan Hub",
                "cost_usd": 2400.0,
                "transit_time_days": 23.0,  # Exceeds 22-day deadline!
                "delay_probability": 0.40,
                "expected_delay_days": 5.0,
                "congestion_risk": 8.0,
                "geopolitical_risk": 4.0,
                "risk_score": 6.0,
                "waypoints": [
                    [22.54, 114.05],  # Shenzhen
                    [35.10, 129.04],  # Port of Busan (Korea)
                    [42.00, 155.00],  # North Pacific Circle
                    [38.00, -140.00],
                    [33.74, -118.26], # Los Angeles
                ],
            },
            {
                "route_id": "Route C (Expedited Express)",
                "carrier": "MSC",
                "mode": "Fast-Track Ocean",
                "via": "Oakland Bypass",
                "cost_usd": 4200.0,
                "transit_time_days": 14.0,
                "delay_probability": 0.09,
                "expected_delay_days": 1.5,
                "congestion_risk": 2.5,
                "geopolitical_risk": 1.5,
                "risk_score": 2.0,
                "waypoints": [
                    [22.54, 114.05],
                    [25.00, 145.00],
                    [34.00, -135.00],
                    [33.74, -118.26],
                ],
            },
            {
                "route_id": "Route D (Air-Sea Charter)",
                "carrier": "FedEx Logistics",
                "mode": "Air-Sea Hybrid",
                "via": "Incheon Air Cargo",
                "cost_usd": 6200.0,         # Exceeds $4,500 budget!
                "transit_time_days": 10.0,
                "delay_probability": 0.05,
                "expected_delay_days": 1.0,
                "congestion_risk": 1.5,
                "geopolitical_risk": 1.0,
                "risk_score": 1.3,
                "waypoints": [
                    [22.54, 114.05],
                    [37.46, 126.44],  # Incheon Airport Hub
                    [33.74, -118.26], # Los Angeles
                ],
            },
        ],
    },
    {
        "origin": "Singapore (SGSIN)",
        "destination": "Hamburg, Germany (DEHAM)",
        "cargo": "Automotive Sensors",
        "budget": 4800.0,
        "deadline_days": 32.0,
        "routes": [
            {
                "route_id": "Route A (Direct Ocean Express)",
                "carrier": "Maersk Line",
                "mode": "Deepsea Direct",
                "via": "Suez Corridor",
                "cost_usd": 3600.0,
                "transit_time_days": 25.0,
                "delay_probability": 0.15,
                "expected_delay_days": 2.5,
                "congestion_risk": 3.5,
                "geopolitical_risk": 4.5,
                "risk_score": 4.0,
                "waypoints": [
                    [1.25, 103.80],   # Singapore
                    [4.50, 99.00],    # Malacca
                    [5.50, 80.50],    # Indian Ocean
                    [12.50, 43.50],   # Bab-el-Mandeb
                    [29.97, 32.55],   # Suez
                    [36.50, 14.50],   # Mediterranean
                    [35.95, -5.60],   # Gibraltar
                    [49.50, -3.50],   # English Channel
                    [53.55, 9.99],    # Port of Hamburg
                ],
            },
            {
                "route_id": "Route B (Cape Bypass)",
                "carrier": "Hapag-Lloyd",
                "mode": "Cape Diversion",
                "via": "South Atlantic",
                "cost_usd": 4100.0,
                "transit_time_days": 30.5,
                "delay_probability": 0.08,
                "expected_delay_days": 1.5,
                "congestion_risk": 1.5,
                "geopolitical_risk": 1.0,
                "risk_score": 1.3,
                "waypoints": [
                    [1.25, 103.80],
                    [-25.00, 55.00],
                    [-34.80, 19.50],  # Cape
                    [10.00, -20.00],
                    [53.55, 9.99],
                ],
            },
            {
                "route_id": "Route C (Economy Linehaul)",
                "carrier": "COSCO Shipping",
                "mode": "Multi-Port Feeder",
                "via": "Colombo & Port Said",
                "cost_usd": 2700.0,
                "transit_time_days": 28.5,
                "delay_probability": 0.40,
                "expected_delay_days": 5.0,
                "congestion_risk": 8.5,
                "geopolitical_risk": 5.5,
                "risk_score": 7.0,
                "waypoints": [
                    [1.25, 103.80],
                    [6.92, 79.86],    # Colombo
                    [29.97, 32.55],   # Suez
                    [53.55, 9.99],
                ],
            },
            {
                "route_id": "Route D (Intermodal Rail/Sea)",
                "carrier": "DHL Forwarding",
                "mode": "Rail-Sea Multimodal",
                "via": "Central Asia Corridor",
                "cost_usd": 5300.0,
                "transit_time_days": 18.0,
                "delay_probability": 0.08,
                "expected_delay_days": 1.5,
                "congestion_risk": 2.0,
                "geopolitical_risk": 3.0,
                "risk_score": 2.5,
                "waypoints": [
                    [1.25, 103.80],
                    [25.20, 55.27],   # Dubai Hub
                    [53.55, 9.99],
                ],
            },
        ],
    },
    {
        "origin": "Mumbai, India (INBOM)",
        "destination": "Antwerp, Belgium (BEANR)",
        "cargo": "Pharmaceutical Chemicals",
        "budget": 3500.0,
        "deadline_days": 26.0,
        "routes": [
            {
                "route_id": "Route A (Direct Red Sea)",
                "carrier": "MSC",
                "mode": "Direct Linehaul",
                "via": "Bab-el-Mandeb & Suez",
                "cost_usd": 2700.0,
                "transit_time_days": 21.0,
                "delay_probability": 0.16,
                "expected_delay_days": 2.5,
                "congestion_risk": 4.0,
                "geopolitical_risk": 5.0,
                "risk_score": 4.5,
                "waypoints": [
                    [18.95, 72.82],   # Mumbai
                    [14.00, 60.00],   # Arabian Sea
                    [12.50, 43.50],   # Bab-el-Mandeb
                    [29.97, 32.55],   # Suez
                    [35.95, -5.60],   # Gibraltar
                    [49.50, -3.50],   # English Channel
                    [51.22, 4.40],    # Antwerp
                ],
            },
            {
                "route_id": "Route B (West Africa Bypass)",
                "carrier": "CMA CGM",
                "mode": "Diversion Route",
                "via": "Cape / Gibraltar",
                "cost_usd": 3200.0,
                "transit_time_days": 28.0,  # Exceeds 26-day deadline!
                "delay_probability": 0.10,
                "expected_delay_days": 2.0,
                "congestion_risk": 2.0,
                "geopolitical_risk": 1.5,
                "risk_score": 1.8,
                "waypoints": [
                    [18.95, 72.82],
                    [-10.00, 55.00],
                    [-34.80, 19.50],  # Cape
                    [15.00, -20.00],
                    [51.22, 4.40],
                ],
            },
            {
                "route_id": "Route C (Budget Feeder)",
                "carrier": "Evergreen Line",
                "mode": "Feeder Transshipment",
                "via": "Salalah & Piraeus",
                "cost_usd": 2200.0,
                "transit_time_days": 24.0,
                "delay_probability": 0.42,
                "expected_delay_days": 5.0,
                "congestion_risk": 7.5,
                "geopolitical_risk": 5.5,
                "risk_score": 6.5,
                "waypoints": [
                    [18.95, 72.82],
                    [17.01, 54.09],   # Salalah Hub (Oman)
                    [29.97, 32.55],   # Suez
                    [37.94, 23.63],   # Piraeus Hub (Greece)
                    [51.22, 4.40],    # Antwerp
                ],
            },
            {
                "route_id": "Route D (Air-Sea Hybrid)",
                "carrier": "Kuehne+Nagel",
                "mode": "Air-Sea Multimodal",
                "via": "Dubai Relay",
                "cost_usd": 4200.0,
                "transit_time_days": 12.0,
                "delay_probability": 0.06,
                "expected_delay_days": 1.0,
                "congestion_risk": 1.5,
                "geopolitical_risk": 1.5,
                "risk_score": 1.5,
                "waypoints": [
                    [18.95, 72.82],
                    [25.20, 55.27],   # Dubai
                    [51.22, 4.40],    # Antwerp
                ],
            },
        ],
    },
]


def generate_shipments(count=20):
    shipments = []
    for idx in range(1, count + 1):
        c = CORRIDORS[(idx - 1) % len(CORRIDORS)]
        shipment_id = f"SHP-{idx:03d}"
        cost_jitter = 1.0 + (0.02 * ((idx - 1) // len(CORRIDORS)))
        
        routes = []
        for r in c["routes"]:
            r_copy = dict(r)
            r_name = r["route_id"].split(" ")[0] + " " + r["route_id"].split(" ")[1]
            r_copy["route_id"] = f"{shipment_id}-{r_name}"
            r_copy["cost_usd"] = round(r["cost_usd"] * cost_jitter, 2)
            routes.append(r_copy)

        shipments.append({
            "shipment_id": shipment_id,
            "origin": c["origin"],
            "destination": c["destination"],
            "cargo_type": c["cargo"],
            "budget_usd": round(c["budget"] * cost_jitter, 2),
            "deadline_days": c["deadline_days"],
            "routes": routes,
        })
    return shipments


def save_dataset(output_path="data/shipments_data.json"):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = generate_shipments(count=20)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Generated {len(data)} shipments with refined maritime waypoints to {output_path}")


if __name__ == "__main__":
    save_dataset()
