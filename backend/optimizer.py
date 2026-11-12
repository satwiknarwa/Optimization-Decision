"""Multi-criteria route scoring, constraint validation, and explanation builder."""

STRATEGY_PRESETS = {
    "balanced": {"cost": 0.40, "time": 0.35, "risk": 0.25},
    "cost_first": {"cost": 0.70, "time": 0.15, "risk": 0.15},
    "speed_first": {"cost": 0.15, "time": 0.70, "risk": 0.15},
    "risk_averse": {"cost": 0.20, "time": 0.20, "risk": 0.60},
}


def calculate_expected_time(route: dict) -> float:
    """
    Computes total expected transit time including delay probability.
    Expected Time = Base Transit Days + (Delay Probability * Expected Delay Days)
    """
    base_time = route["transit_time_days"]
    prob = route["delay_probability"]
    delay_days = route["expected_delay_days"]
    return round(base_time + (prob * delay_days), 2)


def min_max_normalize(values: list) -> list:
    """
    Scales a list of numbers between 0.0 (lowest/best) and 1.0 (highest/worst).
    Formula: (x - min) / (max - min)
    """
    min_val = min(values)
    max_val = max(values)
    if max_val == min_val:
        return [0.5 for _ in values]
    return [round((v - min_val) / (max_val - min_val), 4) for v in values]


def evaluate_routes(shipment: dict, strategy: str = "balanced") -> list:
    """
    Score candidate routes under budget and deadline constraints using
    Min-Max normalization across cost, expected transit time, and risk.
    """
    routes = shipment["routes"]
    if not routes:
        return []

    weights = STRATEGY_PRESETS.get(strategy, STRATEGY_PRESETS["balanced"])
    budget_limit = shipment.get("budget_usd", float("inf"))
    deadline_limit = shipment.get("deadline_days", float("inf"))

    costs = [r["cost_usd"] for r in routes]
    expected_times = [calculate_expected_time(r) for r in routes]
    risks = [r["risk_score"] for r in routes]

    norm_costs = min_max_normalize(costs)
    norm_times = min_max_normalize(expected_times)
    norm_risks = min_max_normalize(risks)

    scored_routes = []
    for i, r in enumerate(routes):
        cost = r["cost_usd"]
        exp_time = expected_times[i]

        is_within_budget = cost <= budget_limit
        meets_deadline = exp_time <= deadline_limit

        # Weighted penalty score where 0.0 is best
        base_score = (
            weights["cost"] * norm_costs[i]
            + weights["time"] * norm_times[i]
            + weights["risk"] * norm_risks[i]
        )

        # Penalize constraint violations so feasible routes always rank ahead
        budget_penalty = 0.50 if not is_within_budget else 0.0
        deadline_penalty = 0.50 if not meets_deadline else 0.0

        final_score = round(base_score + budget_penalty + deadline_penalty, 4)

        scored_routes.append({
            "route_id": r["route_id"],
            "carrier": r["carrier"],
            "mode": r["mode"],
            "via": r.get("via", "Direct"),
            "cost_usd": cost,
            "transit_time_days": r["transit_time_days"],
            "expected_total_days": exp_time,
            "delay_probability": r["delay_probability"],
            "expected_delay_days": r["expected_delay_days"],
            "congestion_risk": r.get("congestion_risk", r["risk_score"]),
            "geopolitical_risk": r.get("geopolitical_risk", r["risk_score"]),
            "risk_score": r["risk_score"],
            "within_budget": is_within_budget,
            "meets_deadline": meets_deadline,
            "is_feasible": is_within_budget and meets_deadline,
            "score": final_score,
        })

    scored_routes.sort(key=lambda x: x["score"])

    for rank, route in enumerate(scored_routes, start=1):
        route["rank"] = rank

    return scored_routes


def generate_explanation(shipment: dict, ranked_routes: list, strategy: str = "balanced") -> dict:
    """
    Build a plain-English summary comparing the selected route against
    the cheapest and fastest alternatives.
    """
    if not ranked_routes:
        return {}

    best = ranked_routes[0]
    cheapest = min(ranked_routes, key=lambda x: x["cost_usd"])
    fastest = min(ranked_routes, key=lambda x: x["expected_total_days"])

    budget = shipment.get("budget_usd", 0)
    deadline = shipment.get("deadline_days", 0)

    if best["within_budget"] and best["meets_deadline"]:
        status_text = "is within budget and meets delivery deadline"
    elif best["within_budget"]:
        status_text = "is within budget but exceeds the delivery deadline"
    elif best["meets_deadline"]:
        status_text = "meets the delivery deadline but exceeds the budget"
    else:
        status_text = "exceeds both budget and delivery deadline constraints"

    executive_summary = (
        f"Selected {best['route_id']} ({best['carrier']}, {best['mode']}) using the "
        f"{strategy.replace('_', ' ')} profile. It {status_text}, with expected transit "
        f"of {best['expected_total_days']} days at ${best['cost_usd']:,.2f}."
    )

    if best["route_id"] == cheapest["route_id"]:
        vs_cheapest = "Selected route is also the lowest-cost option."
    else:
        if not cheapest["meets_deadline"]:
            vs_cheapest = (
                f"Cheaper option {cheapest['route_id']} (${cheapest['cost_usd']:,.2f}) was skipped because "
                f"its expected arrival ({cheapest['expected_total_days']} days) misses the {deadline}-day deadline."
            )
        elif cheapest["delay_probability"] >= 0.30:
            vs_cheapest = (
                f"Cheaper option {cheapest['route_id']} saves ${best['cost_usd'] - cheapest['cost_usd']:,.2f} "
                f"but carries a {cheapest['delay_probability'] * 100:.0f}% delay probability "
                f"(congestion {cheapest['congestion_risk']}/10, geopolitical {cheapest['geopolitical_risk']}/10)."
            )
        else:
            cost_diff = best["cost_usd"] - cheapest["cost_usd"]
            vs_cheapest = (
                f"Costs ${cost_diff:,.2f} more than {cheapest['route_id']}, saving "
                f"{cheapest['expected_total_days'] - best['expected_total_days']:.1f} days and reducing delay risk by "
                f"{(cheapest['delay_probability'] - best['delay_probability']) * 100:.0f}%."
            )

    if best["route_id"] == fastest["route_id"]:
        vs_fastest = "Selected route is also the fastest option."
    else:
        if not fastest["within_budget"]:
            vs_fastest = (
                f"Fastest option {fastest['route_id']} ({fastest['expected_total_days']} days) costs "
                f"${fastest['cost_usd']:,.2f}, which exceeds the ${budget:,.2f} shipment budget."
            )
        else:
            savings = fastest["cost_usd"] - best["cost_usd"]
            if best["meets_deadline"]:
                vs_fastest = (
                    f"Saves ${savings:,.2f} compared to {fastest['route_id']} while still arriving "
                    f"within the {deadline}-day deadline."
                )
            else:
                vs_fastest = (
                    f"Saves ${savings:,.2f} compared to {fastest['route_id']} "
                    f"({fastest['expected_total_days']} expected days)."
                )

    advantages = [
        f"Budget: ${best['cost_usd']:,.2f} vs ${budget:,.2f} limit." if best["within_budget"] else f"Exceeds budget of ${budget:,.2f}.",
        f"Deadline: {best['expected_total_days']} days vs {deadline}-day limit." if best["meets_deadline"] else f"Exceeds deadline of {deadline} days.",
        (
            f"Composite risk {best['risk_score']}/10 (congestion {best['congestion_risk']}/10, "
            f"geopolitical {best['geopolitical_risk']}/10) with {best['delay_probability'] * 100:.0f}% delay probability."
        ),
    ]

    return {
        "recommended_route_id": best["route_id"],
        "strategy_used": strategy,
        "executive_summary": executive_summary,
        "comparison_vs_cheapest": vs_cheapest,
        "comparison_vs_fastest": vs_fastest,
        "key_advantages": advantages,
    }
