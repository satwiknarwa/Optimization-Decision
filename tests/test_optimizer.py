"""
Unit tests for the shipment route optimizer.
Verifies budget constraints, deadline constraints, normalization, and explainability.
"""
import unittest
from backend.optimizer import (
    calculate_expected_time,
    min_max_normalize,
    evaluate_routes,
    generate_explanation,
)


class TestOptimizer(unittest.TestCase):

    def setUp(self):
        self.sample_shipment = {
            "shipment_id": "TEST-001",
            "origin": "Shanghai",
            "destination": "Rotterdam",
            "cargo_type": "Electronics",
            "budget_usd": 5000.0,
            "deadline_days": 35.0,
            "routes": [
                {
                    "route_id": "Route A (Balanced)",
                    "carrier": "Maersk Line",
                    "mode": "Direct Ocean",
                    "cost_usd": 3800.0,
                    "transit_time_days": 28.0,
                    "delay_probability": 0.18,
                    "expected_delay_days": 3.0,
                    "risk_score": 3.5,
                },
                {
                    "route_id": "Route B (Late)",
                    "carrier": "Hapag-Lloyd",
                    "mode": "Cape Diversion",
                    "cost_usd": 4400.0,
                    "transit_time_days": 38.0,  # Misses 35d deadline!
                    "delay_probability": 0.08,
                    "expected_delay_days": 2.0,
                    "risk_score": 1.5,
                },
                {
                    "route_id": "Route C (Risky)",
                    "carrier": "CMA CGM",
                    "mode": "Transshipment",
                    "cost_usd": 3500.0,         # Cheapest, but 35% delay prob
                    "transit_time_days": 32.0,
                    "delay_probability": 0.35,
                    "expected_delay_days": 6.0,
                    "risk_score": 7.5,
                },
                {
                    "route_id": "Route D (Expensive)",
                    "carrier": "DHL Express",
                    "mode": "Air-Sea",
                    "cost_usd": 5400.0,         # Exceeds $5,000 budget!
                    "transit_time_days": 24.0,
                    "delay_probability": 0.07,
                    "expected_delay_days": 1.0,
                    "risk_score": 1.0,
                },
            ],
        }

    def test_expected_time_calculation(self):
        route = {"transit_time_days": 28.0, "delay_probability": 0.18, "expected_delay_days": 3.0}
        # 28.0 + (0.18 * 3.0) = 28.54
        self.assertAlmostEqual(calculate_expected_time(route), 28.54, places=2)

    def test_min_max_normalize(self):
        raw = [100, 200, 300]
        norm = min_max_normalize(raw)
        self.assertEqual(norm[0], 0.0)
        self.assertEqual(norm[1], 0.5)
        self.assertEqual(norm[2], 1.0)

    def test_budget_constraint(self):
        ranked = evaluate_routes(self.sample_shipment, strategy="balanced")
        route_d = next(r for r in ranked if r["route_id"] == "Route D (Expensive)")
        # Route D costs $5,400 > $5,000 budget
        self.assertFalse(route_d["within_budget"])

    def test_deadline_constraint(self):
        ranked = evaluate_routes(self.sample_shipment, strategy="balanced")
        route_b = next(r for r in ranked if r["route_id"] == "Route B (Late)")
        # Route B takes ~38.16 days > 35-day deadline
        self.assertFalse(route_b["meets_deadline"])

    def test_optimal_recommendation_selected(self):
        ranked = evaluate_routes(self.sample_shipment, strategy="balanced")
        # Route A meets both budget and deadline and has the best balanced score
        best = ranked[0]
        self.assertEqual(best["route_id"], "Route A (Balanced)")
        self.assertTrue(best["within_budget"])
        self.assertTrue(best["meets_deadline"])

    def test_generate_explanation(self):
        ranked = evaluate_routes(self.sample_shipment, strategy="balanced")
        explanation = generate_explanation(self.sample_shipment, ranked, strategy="balanced")
        self.assertIn("Route A (Balanced)", explanation["executive_summary"])
        self.assertIn("within budget and meets delivery deadline", explanation["executive_summary"])
        self.assertIn("exceeds the $5,000.00 shipment budget", explanation["comparison_vs_fastest"])

    def test_infeasible_explanation_grammar(self):
        tight_shipment = dict(self.sample_shipment)
        tight_shipment["budget_usd"] = 1000.0
        tight_shipment["deadline_days"] = 5.0
        ranked = evaluate_routes(tight_shipment, strategy="balanced")
        self.assertFalse(ranked[0]["is_feasible"])
        explanation = generate_explanation(tight_shipment, ranked, strategy="balanced")
        self.assertIn("exceeds both budget and delivery deadline constraints", explanation["executive_summary"])

    def test_strategy_changes_ranking(self):
        # Local fixture where balanced (Route A), risk_averse (Route B), and cost_first (Route C) diverge
        shipment = {
            "shipment_id": "TEST-STRAT",
            "budget_usd": 5000.0,
            "deadline_days": 40.0,
            "routes": [
                {**self.sample_shipment["routes"][0], "risk_score": 4.5},
                self.sample_shipment["routes"][1],
                {**self.sample_shipment["routes"][2], "cost_usd": 2950.0, "transit_time_days": 31.0, "expected_delay_days": 5.5},
                self.sample_shipment["routes"][3],
            ],
        }
        balanced_best = evaluate_routes(shipment, strategy="balanced")[0]["route_id"]
        risk_best = evaluate_routes(shipment, strategy="risk_averse")[0]["route_id"]
        cost_best = evaluate_routes(shipment, strategy="cost_first")[0]["route_id"]
        self.assertEqual(balanced_best, "Route A (Balanced)")
        self.assertEqual(risk_best, "Route B (Late)")
        self.assertEqual(cost_best, "Route C (Risky)")


if __name__ == "__main__":
    unittest.main()
