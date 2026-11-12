/**
 * Frontend controller for the Shipment Route Optimizer.
 * Evaluates candidate routes under budget, deadline, and priority weights,
 * and visualizes the selected corridor on an OpenStreetMap Leaflet map.
 */

const API_BASE_URL = window.location.port === "8000" ? "" : "http://localhost:8000";

const STRATEGY_WEIGHT_LABELS = {
    balanced: "Active weights: 40% Cost · 35% Expected Time · 25% Risk",
    cost_first: "Active weights: 70% Cost · 15% Expected Time · 15% Risk",
    speed_first: "Active weights: 15% Cost · 70% Expected Time · 15% Risk",
    risk_averse: "Active weights: 20% Cost · 20% Expected Time · 60% Risk",
};

let availableShipments = [];
let activeStrategy = "balanced";
let lastEvaluation = null;
let previewedRouteId = null;

let mapInstance = null;
let currentRoutePolyline = null;
let mapMarkers = [];

document.addEventListener("DOMContentLoaded", async () => {
    await loadShipmentDropdown();
    initMap();
});

async function loadShipmentDropdown() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/shipments`);
        if (!response.ok) throw new Error("Failed to fetch shipments");
        availableShipments = await response.json();

        const select = document.getElementById("corridorSelect");
        select.innerHTML = "";

        const grouped = new Map();
        availableShipments.forEach(s => {
            const lane = `${s.origin} -> ${s.destination}`;
            if (!grouped.has(lane)) grouped.set(lane, []);
            grouped.get(lane).push(s);
        });

        grouped.forEach((items, laneLabel) => {
            const groupEl = document.createElement("optgroup");
            groupEl.label = laneLabel;
            items.forEach(s => {
                const originCity = s.origin.split(",")[0].split(" (")[0];
                const destCity = s.destination.split(",")[0].split(" (")[0];
                const opt = document.createElement("option");
                opt.value = s.shipment_id;
                opt.textContent = `${s.shipment_id} · ${originCity} -> ${destCity} ($${Number(s.budget_usd).toLocaleString()} / ${s.deadline_days}d)`;
                groupEl.appendChild(opt);
            });
            select.appendChild(groupEl);
        });

        if (availableShipments.length > 0) {
            updateInputDefaults(availableShipments[0]);
        }
    } catch (err) {
        console.error("Failed to load shipments:", err);
        document.getElementById("decisionText").textContent =
            "Unable to reach the backend API on port 8000. Start the server and refresh.";
    }
}

function updateInputDefaults(shipment) {
    document.getElementById("budgetInput").value = shipment.budget_usd;
    document.getElementById("deadlineInput").value = shipment.deadline_days;
}

function onCorridorChange() {
    const selectedId = document.getElementById("corridorSelect").value;
    const matched = availableShipments.find(s => s.shipment_id === selectedId);
    if (matched) {
        updateInputDefaults(matched);
        runOptimization();
    }
}

function selectStrategy(strategyKey) {
    activeStrategy = strategyKey;
    document.querySelectorAll(".strat-btn").forEach(btn => {
        btn.classList.toggle("active", btn.getAttribute("data-strategy") === strategyKey);
    });
    document.getElementById("activeWeightsText").textContent =
        STRATEGY_WEIGHT_LABELS[strategyKey] || STRATEGY_WEIGHT_LABELS.balanced;
    runOptimization();
}

function initMap() {
    mapInstance = L.map("trackingMap", {
        zoomControl: false,
        attributionControl: false,
        worldCopyJump: true
    }).setView([20.0, 50.0], 3);

    L.control.zoom({ position: "bottomright" }).addTo(mapInstance);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "OpenStreetMap"
    }).addTo(mapInstance);

    if (availableShipments.length > 0) {
        runOptimization();
    }
}

async function runOptimization() {
    const shipmentId = document.getElementById("corridorSelect").value;
    if (!shipmentId) return;

    const userBudget = parseFloat(document.getElementById("budgetInput").value) || 5000;
    const userDeadline = parseFloat(document.getElementById("deadlineInput").value) || 35;

    const btn = document.getElementById("optimizeBtn");
    btn.textContent = "Evaluating...";

    try {
        const response = await fetch(`${API_BASE_URL}/api/evaluate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                shipment_id: shipmentId,
                strategy: activeStrategy,
                budget_usd: userBudget,
                deadline_days: userDeadline,
            }),
        });

        if (!response.ok) throw new Error("Evaluation request failed");
        const data = await response.json();
        lastEvaluation = data;
        previewedRouteId = data.ranked_routes[0]?.route_id || null;
        renderResults(data);
    } catch (err) {
        console.error("Evaluation error:", err);
        document.getElementById("decisionText").textContent =
            "Error evaluating routes. Check that the backend server is running on port 8000.";
    } finally {
        btn.textContent = "Evaluate Routes";
    }
}

function previewRoute(routeId) {
    if (!lastEvaluation) return;
    const target = lastEvaluation.ranked_routes.find(r => r.route_id === routeId);
    if (!target) return;

    previewedRouteId = routeId;
    renderRouteOverlay(lastEvaluation.shipment, target, target.rank === 1);
    renderComparisonTable(lastEvaluation.ranked_routes);
    if (mapInstance) {
        drawRoutePath(target);
    }
}

function renderResults(data) {
    const shipment = data.shipment;
    const ranked = data.ranked_routes;
    const explanation = data.explanation;
    if (!ranked || ranked.length === 0) return;

    const best = ranked[0];
    renderRouteOverlay(shipment, best, true);

    document.getElementById("decisionText").textContent = explanation.executive_summary || "";
    document.getElementById("tradeoffCheapest").textContent = explanation.comparison_vs_cheapest || "";
    document.getElementById("tradeoffFastest").textContent = explanation.comparison_vs_fastest || "";

    renderComparisonTable(ranked);

    if (mapInstance) {
        drawRoutePath(best);
    }
}

function renderRouteOverlay(shipment, route, isWinner) {
    document.getElementById("overlayModeTag").textContent = isWinner
        ? "RECOMMENDED ROUTE (RANK #1)"
        : `ROUTE PREVIEW (RANK #${route.rank})`;
    document.getElementById("mapVesselName").textContent = `${route.carrier} — ${route.route_id}`;
    document.getElementById("mapCorridorText").textContent = `${shipment.origin} -> ${shipment.destination} (via ${route.via})`;

    const bBadge = document.getElementById("mapBudgetBadge");
    bBadge.textContent = route.within_budget ? "Within Budget" : "Over Budget";
    bBadge.className = route.within_budget ? "badge-safe" : "badge-danger";

    const dBadge = document.getElementById("mapDeadlineBadge");
    dBadge.textContent = route.meets_deadline ? "Meets Deadline" : "Misses Deadline";
    dBadge.className = route.meets_deadline ? "badge-safe" : "badge-danger";
}

function formatConstraintStatus(route) {
    if (route.is_feasible) {
        return '<span class="status-feasible">Feasible</span>';
    }
    if (!route.within_budget && !route.meets_deadline) {
        return '<span class="status-breached">Over Budget &amp; Late</span>';
    }
    if (!route.within_budget) {
        return '<span class="status-breached">Over Budget</span>';
    }
    return '<span class="status-breached">Misses Deadline</span>';
}

function renderComparisonTable(ranked) {
    const tbody = document.getElementById("trackerTableBody");
    tbody.innerHTML = ranked.map(r => {
        const classes = [];
        if (r.rank === 1) classes.push("winner-row");
        if (r.route_id === previewedRouteId) classes.push("previewed-row");
        const congRisk = r.congestion_risk !== undefined ? r.congestion_risk : r.risk_score;
        const geoRisk = r.geopolitical_risk !== undefined ? r.geopolitical_risk : r.risk_score;
        const routeLabel = r.route_id.split("-").pop();

        return `
            <tr class="${classes.join(" ")}" onclick="previewRoute('${r.route_id}')">
                <td><strong>#${r.rank}</strong></td>
                <td><strong>${routeLabel}</strong> <span class="sub-cell">· ${r.carrier}</span></td>
                <td>${r.via}</td>
                <td>$${Number(r.cost_usd).toLocaleString()}</td>
                <td><strong>${r.expected_total_days}d</strong> <span class="sub-cell">(base ${r.transit_time_days}d)</span></td>
                <td>${(r.delay_probability * 100).toFixed(0)}%</td>
                <td><strong>${r.risk_score}/10</strong> <span class="sub-cell">(${congRisk} / ${geoRisk})</span></td>
                <td>${r.score.toFixed(2)}</td>
                <td>${formatConstraintStatus(r)}</td>
            </tr>
        `;
    }).join("");
}

function unwrapWaypoints(rawWaypoints) {
    if (!rawWaypoints || rawWaypoints.length === 0) return [];
    const unwrapped = [[rawWaypoints[0][0], rawWaypoints[0][1]]];
    for (let i = 1; i < rawWaypoints.length; i++) {
        const lat = rawWaypoints[i][0];
        let lng = rawWaypoints[i][1];
        const prevLng = unwrapped[i - 1][1];
        // Unwrap longitudes across the 180-degree line so Pacific routes do not wrap via 0 deg
        while (lng - prevLng > 180) lng -= 360;
        while (lng - prevLng < -180) lng += 360;
        unwrapped.push([lat, lng]);
    }
    return unwrapped;
}

function makePinIcon(label, bgColor) {
    return L.divIcon({
        className: "custom-port-icon",
        html: `<div style="background:${bgColor}; color:#fff; width:26px; height:26px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; box-shadow:0 2px 6px rgba(15,23,42,0.28); border:2px solid #fff;">${label}</div>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13]
    });
}

function drawRoutePath(route) {
    if (currentRoutePolyline) {
        mapInstance.removeLayer(currentRoutePolyline);
    }
    mapMarkers.forEach(m => mapInstance.removeLayer(m));
    mapMarkers = [];

    const rawWaypoints = route.waypoints && route.waypoints.length > 0
        ? route.waypoints
        : [[31.23, 121.47], [1.25, 103.8], [12.5, 43.5], [29.97, 32.55], [35.95, -5.6], [51.95, 4.14]];
    const waypoints = unwrapWaypoints(rawWaypoints);
    const routeColor = route.is_feasible ? "#2563eb" : "#dc2626";

    currentRoutePolyline = L.polyline(waypoints, {
        color: routeColor,
        weight: 4,
        dashArray: "10, 8",
        opacity: 0.92
    }).addTo(mapInstance);

    mapMarkers.push(
        L.marker(waypoints[0], { icon: makePinIcon("O", "#059669") })
            .bindPopup(`<b>Origin Port</b><br>${rawWaypoints[0][0]}, ${rawWaypoints[0][1]}`)
            .addTo(mapInstance)
    );

    const lastIdx = rawWaypoints.length - 1;
    mapMarkers.push(
        L.marker(waypoints[lastIdx], { icon: makePinIcon("D", "#dc2626") })
            .bindPopup(`<b>Destination Port</b><br>${rawWaypoints[lastIdx][0]}, ${rawWaypoints[lastIdx][1]}`)
            .addTo(mapInstance)
    );

    const midIdx = Math.floor(waypoints.length / 2);
    const congRisk = route.congestion_risk !== undefined ? route.congestion_risk : route.risk_score;
    const geoRisk = route.geopolitical_risk !== undefined ? route.geopolitical_risk : route.risk_score;
    const hubMarker = L.circleMarker(waypoints[midIdx], {
        radius: 7,
        color: "#ffffff",
        weight: 2,
        fillColor: routeColor,
        fillOpacity: 1
    })
        .bindPopup(
            `<b>${route.route_id}</b><br>Carrier: ${route.carrier}<br>Via: ${route.via || "Direct"}` +
            `<br>Congestion Risk: ${congRisk}/10 | Geopolitical Risk: ${geoRisk}/10`
        )
        .addTo(mapInstance);
    mapMarkers.push(hubMarker);

    mapInstance.fitBounds(currentRoutePolyline.getBounds(), {
        paddingTopLeft: [40, 115],
        paddingBottomRight: [40, 40]
    });
}
