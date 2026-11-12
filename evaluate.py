"""
Evaluation script for comparing the multi-criteria route optimizer against
single-metric baselines (lowest cost, fastest transit) across all 20 shipments.
"""
import copy
import json
from pathlib import Path

from backend.optimizer import STRATEGY_PRESETS, calculate_expected_time, evaluate_routes

DATA_PATH = Path(__file__).resolve().parent / "data" / "shipments_data.json"


def evaluate_policy(shipments: list, select_fn) -> dict:
    """Compute feasibility and average route metrics for a route-selection policy."""
    total = len(shipments)
    feasible = 0
    total_cost = 0.0
    total_exp_days = 0.0
    total_delay_prob = 0.0
    total_risk = 0.0
    winners = {}

    for s in shipments:
        chosen = select_fn(s)
        exp_days = chosen.get("expected_total_days", calculate_expected_time(chosen))
        within_budget = chosen["cost_usd"] <= s["budget_usd"]
        meets_deadline = exp_days <= s["deadline_days"]

        if within_budget and meets_deadline:
            feasible += 1

        total_cost += chosen["cost_usd"]
        total_exp_days += exp_days
        total_delay_prob += chosen["delay_probability"]
        total_risk += chosen["risk_score"]
        winners[s["shipment_id"]] = chosen["route_id"]

    return {
        "feasible": feasible,
        "total": total,
        "feasibility_pct": round((feasible / total) * 100, 1),
        "avg_cost": round(total_cost / total, 2),
        "avg_exp_days": round(total_exp_days / total, 2),
        "avg_delay_pct": round((total_delay_prob / total) * 100, 1),
        "avg_risk": round(total_risk / total, 2),
        "winners": winners,
    }


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        shipments = json.load(f)

    policies = [
        ("Baseline: Cheapest", lambda s: min(s["routes"], key=lambda r: r["cost_usd"])),
        ("Baseline: Fastest", lambda s: min(s["routes"], key=calculate_expected_time)),
    ]
    for strategy in STRATEGY_PRESETS:
        policies.append((f"Strategy: {strategy}", lambda s, st=strategy: evaluate_routes(s, strategy=st)[0]))

    print(f"Evaluating {len(shipments)} shipments ({sum(len(s['routes']) for s in shipments)} candidate routes)\n")
    print(f"{'Policy':<24} {'Feasible':<15} {'Avg Cost':<12} {'Avg Days':<10} {'Delay Prob':<12} {'Avg Risk'}")
    print("-" * 85)

    results = {}
    for name, fn in policies:
        stats = evaluate_policy(shipments, fn)
        results[name] = stats
        feas_str = f"{stats['feasible']}/{stats['total']} ({stats['feasibility_pct']}%)"
        delay_str = f"{stats['avg_delay_pct']:.1f}%"
        print(
            f"{name:<24} {feas_str:<15} ${stats['avg_cost']:<11,.2f} "
            f"{stats['avg_exp_days']:<10.2f} {delay_str:<12} {stats['avg_risk']:.2f}/10"
        )

    # Sensitivity: route changes when switching weight profiles away from balanced
    balanced_winners = results["Strategy: balanced"]["winners"]
    print("\nStrategy Sensitivity (vs. balanced):")
    for strategy in ("cost_first", "speed_first", "risk_averse"):
        alt_winners = results[f"Strategy: {strategy}"]["winners"]
        changed = sum(1 for sid, rid in balanced_winners.items() if alt_winners[sid] != rid)
        print(f"  - {strategy:<12}: {changed}/{len(shipments)} shipments switched recommended route")

    # Stress test: tighten both budget and deadline by 25%
    tight_shipments = copy.deepcopy(shipments)
    for s in tight_shipments:
        s["budget_usd"] = round(s["budget_usd"] * 0.75, 2)
        s["deadline_days"] = round(s["deadline_days"] * 0.75, 2)

    tight_stats = evaluate_policy(tight_shipments, lambda s: evaluate_routes(s, strategy="balanced")[0])
    print(
        f"\nConstraint Stress Test (-25% budget & deadline) under balanced:\n"
        f"  - Feasibility shifted from {results['Strategy: balanced']['feasibility_pct']}% "
        f"to {tight_stats['feasibility_pct']}% ({tight_stats['feasible']}/{tight_stats['total']} feasible)"
    )


if __name__ == "__main__":
    main()
