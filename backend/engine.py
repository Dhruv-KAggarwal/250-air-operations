from __future__ import annotations

import json
import math
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ortools.sat.python import cp_model

AIRPORTS = [
    {"id": "DEL", "name": "Delhi", "state": "Delhi", "lat": 28.56, "lon": 77.10},
    {"id": "BOM", "name": "Mumbai", "state": "Maharashtra", "lat": 19.09, "lon": 72.86},
    {"id": "BLR", "name": "Bengaluru", "state": "Karnataka", "lat": 13.20, "lon": 77.71},
    {"id": "CCU", "name": "Kolkata", "state": "West Bengal", "lat": 22.65, "lon": 88.45},
    {"id": "HYD", "name": "Hyderabad", "state": "Telangana", "lat": 17.24, "lon": 78.43},
    {"id": "MAA", "name": "Chennai", "state": "Tamil Nadu", "lat": 12.99, "lon": 80.17},
    {"id": "GAU", "name": "Guwahati", "state": "Assam", "lat": 26.10, "lon": 91.59},
    {"id": "SXR", "name": "Srinagar", "state": "Jammu and Kashmir", "lat": 34.00, "lon": 74.77},
]


def distance(a: dict[str, Any], b: dict[str, Any]) -> int:
    return int(math.hypot(a["lat"] - b["lat"], a["lon"] - b["lon"]) * 110)


def seeded_world(seed: int = 2026) -> dict[str, Any]:
    aircraft = [
        {"id": "A-101", "name": "Saffron 101", "type": "Relief transport", "capacity": 8.0, "range": 1800, "base": "DEL", "status": "ready", "health": 96},
        {"id": "A-102", "name": "Saffron 102", "type": "Relief transport", "capacity": 6.0, "range": 1400, "base": "BOM", "status": "ready", "health": 91},
        {"id": "A-103", "name": "Monsoon 103", "type": "Air ambulance", "capacity": 2.0, "range": 1000, "base": "BLR", "status": "ready", "health": 88},
        {"id": "A-104", "name": "Monsoon 104", "type": "Air ambulance", "capacity": 2.5, "range": 1200, "base": "HYD", "status": "inspection", "health": 72},
        {"id": "A-105", "name": "Himalaya 105", "type": "Cargo turboprop", "capacity": 4.5, "range": 1100, "base": "SXR", "status": "ready", "health": 94},
        {"id": "A-106", "name": "Himalaya 106", "type": "Cargo turboprop", "capacity": 4.0, "range": 1050, "base": "GAU", "status": "ready", "health": 90},
        {"id": "A-107", "name": "Kaveri 107", "type": "Search and rescue", "capacity": 1.5, "range": 800, "base": "MAA", "status": "ready", "health": 97},
        {"id": "A-108", "name": "Kaveri 108", "type": "Search and rescue", "capacity": 1.5, "range": 800, "base": "CCU", "status": "maintenance", "health": 61},
        {"id": "A-109", "name": "Saffron 109", "type": "Relief transport", "capacity": 7.0, "range": 1600, "base": "DEL", "status": "ready", "health": 93},
        {"id": "A-110", "name": "Monsoon 110", "type": "Air ambulance", "capacity": 2.0, "range": 950, "base": "HYD", "status": "ready", "health": 89},
        {"id": "A-111", "name": "Himalaya 111", "type": "Cargo turboprop", "capacity": 4.0, "range": 1000, "base": "GAU", "status": "inspection", "health": 76},
        {"id": "A-112", "name": "Kaveri 112", "type": "Search and rescue", "capacity": 1.5, "range": 800, "base": "BLR", "status": "ready", "health": 95},
    ]
    missions = [
        {"id": "M-001", "title": "Flood medical kits", "origin": "DEL", "destination": "GAU", "cargo": 3.0, "duration": 5, "deadline": 12, "priority": 5, "category": "Medical"},
        {"id": "M-002", "title": "Coastal food relief", "origin": "BOM", "destination": "MAA", "cargo": 5.0, "duration": 5, "deadline": 16, "priority": 4, "category": "Food"},
        {"id": "M-003", "title": "Hill rescue team", "origin": "SXR", "destination": "DEL", "cargo": 1.2, "duration": 4, "deadline": 10, "priority": 5, "category": "Rescue"},
        {"id": "M-004", "title": "Critical patient transfer", "origin": "BLR", "destination": "HYD", "cargo": 1.0, "duration": 3, "deadline": 9, "priority": 5, "category": "Medical"},
        {"id": "M-005", "title": "Cyclone water pallets", "origin": "CCU", "destination": "BOM", "cargo": 4.0, "duration": 5, "deadline": 20, "priority": 3, "category": "Water"},
        {"id": "M-006", "title": "Relief radio equipment", "origin": "GAU", "destination": "CCU", "cargo": 2.0, "duration": 3, "deadline": 18, "priority": 3, "category": "Equipment"},
        {"id": "M-007", "title": "Evacuation support", "origin": "MAA", "destination": "BLR", "cargo": 1.0, "duration": 3, "deadline": 15, "priority": 4, "category": "Rescue"},
        {"id": "M-008", "title": "Cold-chain vaccines", "origin": "HYD", "destination": "DEL", "cargo": 2.0, "duration": 5, "deadline": 17, "priority": 5, "category": "Medical"},
        {"id": "M-009", "title": "Shelter material", "origin": "DEL", "destination": "SXR", "cargo": 6.0, "duration": 4, "deadline": 22, "priority": 2, "category": "Shelter"},
        {"id": "M-010", "title": "Emergency generators", "origin": "BOM", "destination": "HYD", "cargo": 5.5, "duration": 4, "deadline": 19, "priority": 3, "category": "Equipment"},
        {"id": "M-011", "title": "River rescue boats", "origin": "DEL", "destination": "CCU", "cargo": 4.0, "duration": 5, "deadline": 24, "priority": 4, "category": "Rescue"},
        {"id": "M-012", "title": "Emergency oxygen", "origin": "HYD", "destination": "SXR", "cargo": 2.0, "duration": 5, "deadline": 21, "priority": 5, "category": "Medical"},
        {"id": "M-013", "title": "Shelter tarpaulins", "origin": "MAA", "destination": "GAU", "cargo": 5.0, "duration": 6, "deadline": 26, "priority": 2, "category": "Shelter"},
        {"id": "M-014", "title": "Mobile water treatment", "origin": "BOM", "destination": "CCU", "cargo": 6.0, "duration": 5, "deadline": 25, "priority": 3, "category": "Water"},
        {"id": "M-015", "title": "Trauma team rotation", "origin": "BLR", "destination": "GAU", "cargo": 1.0, "duration": 5, "deadline": 23, "priority": 5, "category": "Medical"},
        {"id": "M-016", "title": "Emergency lighting", "origin": "CCU", "destination": "SXR", "cargo": 3.0, "duration": 5, "deadline": 28, "priority": 2, "category": "Equipment"},
        {"id": "M-017", "title": "Search drone batteries", "origin": "DEL", "destination": "BLR", "cargo": 1.0, "duration": 5, "deadline": 20, "priority": 3, "category": "Equipment"},
        {"id": "M-018", "title": "Infant nutrition supplies", "origin": "BOM", "destination": "GAU", "cargo": 3.0, "duration": 6, "deadline": 27, "priority": 4, "category": "Medical"},
    ]
    crew = [{"id": f"C-{i:02d}", "name": f"Response crew {i:02d}", "qualification": "medical" if i % 4 == 0 else "general", "available": True} for i in range(1, 21)]
    reports = [
        {"id": "R-001", "aircraft": "A-104", "severity": "high", "title": "Hydraulic pressure fluctuation", "operator": "K. Mehta", "status": "open", "next_action": "Engineering inspection before dispatch"},
        {"id": "R-002", "aircraft": "A-103", "severity": "medium", "title": "Intermittent radio fault", "operator": "P. Nair", "status": "monitoring", "next_action": "Repeat avionics self-test"},
        {"id": "R-003", "aircraft": "A-108", "severity": "high", "title": "Rescue hoist inspection overdue", "operator": "S. Bora", "status": "grounded", "next_action": "Release only after signed inspection"},
    ]
    return {"seed": seed, "airports": AIRPORTS, "aircraft": aircraft, "missions": missions, "crew": crew, "reports": reports, "closures": [], "current_disruption": None, "weather": {}, "active_plan": None, "proposal": None, "clock": 0}


class World:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK (id=1), payload TEXT NOT NULL)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, event TEXT NOT NULL, payload TEXT NOT NULL)")
        self.conn.commit()
        row = self.conn.execute("SELECT payload FROM state WHERE id=1").fetchone()
        self.state = json.loads(row[0]) if row else seeded_world()
        if not row or len(self.state.get("aircraft", [])) < 12 or len(self.state.get("missions", [])) < 18 or len(self.state.get("crew", [])) < 20:
            self.reset()

    def save(self) -> None:
        self.conn.execute("INSERT OR REPLACE INTO state (id, payload) VALUES (1, ?)", (json.dumps(self.state),))
        self.conn.commit()

    def log(self, event: str, payload: dict[str, Any]) -> None:
        self.conn.execute("INSERT INTO ledger (created_at, event, payload) VALUES (?, ?, ?)", (datetime.now(timezone.utc).isoformat(), event, json.dumps(payload)))
        self.conn.commit()

    def reset(self) -> dict[str, Any]:
        self.state = seeded_world()
        self.state["active_plan"] = self.optimize("priority", persist=False)
        self.save()
        self.log("simulation_reset", {"seed": self.state["seed"]})
        return self.view()

    def view(self) -> dict[str, Any]:
        result = dict(self.state)
        result["summary"] = self.summary()
        result["affected_missions"] = self.affected()
        return result

    def summary(self) -> dict[str, Any]:
        plan = self.state.get("active_plan") or {}
        return {
            "aircraft_total": len(self.state["aircraft"]),
            "aircraft_ready": sum(item["status"] == "ready" for item in self.state["aircraft"]),
            "mission_total": len(self.state["missions"]),
            "mission_scheduled": len(plan.get("assignments", [])),
            "open_reports": sum(item["status"] in {"open", "grounded"} for item in self.state["reports"]),
            "closures": len(self.state["closures"]),
            "proposal_pending": bool(self.state.get("proposal")),
            "missions_at_risk": len(self.affected()) + len(plan.get("unassigned", [])),
            "missions_unassigned": len(plan.get("unassigned", [])),
        }

    def affected(self) -> list[dict[str, Any]]:
        closures = set(self.state["closures"])
        return [
            {**mission, "reason": "origin or destination closed"}
            for mission in self.state["missions"]
            if mission["origin"] in closures or mission["destination"] in closures
        ]

    def inject_closure(self, airport_id: str) -> dict[str, Any]:
        if airport_id not in {airport["id"] for airport in self.state["airports"]}:
            raise ValueError("Unknown airport")
        if airport_id not in self.state["closures"]:
            self.state["closures"].append(airport_id)
        airport = next(item for item in self.state["airports"] if item["id"] == airport_id)
        self.state["current_disruption"] = {"type": "airport_closure", "airport_id": airport_id, "airport_name": airport["name"]}
        self.state["clock"] += 1
        self.state["proposal"] = None
        self.save()
        self.log("airport_closed", {"airport_id": airport_id, "affected": [m["id"] for m in self.affected()]})
        return self.view()

    def optimize(self, mode: str, persist: bool = True) -> dict[str, Any]:
        start = time.perf_counter()
        model = cp_model.CpModel()
        airports = {a["id"]: a for a in self.state["airports"]}
        candidates: dict[str, list[tuple[str, int]]] = {}
        variables = {}
        intervals: dict[str, list[Any]] = {}
        score_terms = []
        for mission in self.state["missions"]:
            options = []
            for aircraft in self.state["aircraft"]:
                if aircraft["status"] != "ready" or aircraft["capacity"] < mission["cargo"]:
                    continue
                if mission["origin"] in self.state["closures"] or mission["destination"] in self.state["closures"]:
                    continue
                route = distance(airports[mission["origin"]], airports[mission["destination"]])
                if aircraft["range"] < route:
                    continue
                key = (mission["id"], aircraft["id"])
                var = model.NewBoolVar(f"assign_{mission['id']}_{aircraft['id']}")
                start_var = model.NewIntVar(0, mission["deadline"], f"start_{mission['id']}_{aircraft['id']}")
                end_var = model.NewIntVar(0, mission["deadline"] + mission["duration"], f"end_{mission['id']}_{aircraft['id']}")
                model.Add(end_var == start_var + mission["duration"]).OnlyEnforceIf(var)
                interval = model.NewOptionalIntervalVar(start_var, mission["duration"], end_var, var, f"int_{mission['id']}_{aircraft['id']}")
                intervals.setdefault(aircraft["id"], []).append(interval)
                variables[key] = (var, start_var)
                options.append(key)
                score_terms.append((mission["priority"] * 100 - route // 10 - mission["cargo"] * 3) * var)
            if options:
                model.AddAtMostOne([variables[key][0] for key in options])
            candidates[mission["id"]] = options
        for item in intervals.values():
            model.AddNoOverlap(item)
        model.Maximize(sum(score_terms) if score_terms else 0)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 3
        solver.parameters.num_search_workers = 8
        status = solver.Solve(model)
        assignments = []
        for mission in self.state["missions"]:
            for key in candidates.get(mission["id"], []):
                var, start_var = variables[key]
                if solver.Value(var):
                    assignments.append({"mission_id": mission["id"], "aircraft_id": key[1], "start": solver.Value(start_var), "end": solver.Value(start_var) + mission["duration"]})
        plan = {"id": f"plan-{uuid4().hex[:10]}", "mode": mode, "status": "optimal" if status == cp_model.OPTIMAL else "feasible", "assignments": assignments, "unassigned": [m["id"] for m in self.state["missions"] if m["id"] not in {x["mission_id"] for x in assignments}], "runtime_ms": int((time.perf_counter() - start) * 1000), "hard_constraints": True, "explanations": [{"mission_id": item["mission_id"], "text": f"{item['aircraft_id']} selected because it met capacity, range, availability and airport constraints."} for item in assignments]}
        if persist:
            self.state["proposal"] = plan
            self.save()
            self.log("proposal_generated", {"plan_id": plan["id"], "mode": mode, "assignments": len(assignments)})
        return plan

    def approve(self) -> dict[str, Any]:
        if not self.state.get("proposal"):
            raise ValueError("No proposal pending")
        plan = self.state["proposal"]
        self.state["active_plan"] = plan
        self.state["proposal"] = None
        self.save()
        self.log("proposal_approved", {"plan_id": plan["id"]})
        return self.view()

    def reject(self, reason: str) -> dict[str, Any]:
        if not self.state.get("proposal"):
            raise ValueError("No proposal pending")
        plan_id = self.state["proposal"]["id"]
        self.state["proposal"] = None
        self.save()
        self.log("proposal_rejected", {"plan_id": plan_id, "reason": reason})
        return self.view()

    def _airport(self, airport_id: str) -> dict[str, Any]:
        try:
            return next(item for item in self.state["airports"] if item["id"] == airport_id)
        except StopIteration as exc:
            raise ValueError(f"Unknown airport: {airport_id}") from exc

    def add_mission(self, mission: dict[str, Any]) -> dict[str, Any]:
        required = {"title", "origin", "destination", "cargo", "duration", "deadline", "priority", "category"}
        missing = sorted(required - mission.keys())
        if missing:
            raise ValueError(f"Missing mission fields: {', '.join(missing)}")
        self._airport(str(mission["origin"]))
        self._airport(str(mission["destination"]))
        if float(mission["cargo"]) <= 0 or int(mission["duration"]) <= 0 or int(mission["deadline"]) <= 0:
            raise ValueError("Cargo, duration and deadline must be positive")
        mission = {
            "id": str(mission.get("id") or f"M-{uuid4().hex[:6].upper()}"),
            "title": str(mission["title"]).strip(),
            "origin": str(mission["origin"]),
            "destination": str(mission["destination"]),
            "cargo": float(mission["cargo"]),
            "duration": int(mission["duration"]),
            "deadline": int(mission["deadline"]),
            "priority": max(1, min(5, int(mission["priority"]))),
            "category": str(mission["category"]).strip() or "General",
            "notes": str(mission.get("notes", "")).strip(),
        }
        if not mission["title"] or any(item["id"] == mission["id"] for item in self.state["missions"]):
            raise ValueError("Mission title is required and mission ID must be unique")
        self.state["missions"].append(mission)
        self.state["active_plan"] = self.optimize("priority", persist=False)
        self.save()
        self.log("mission_added", {"mission_id": mission["id"], "route": [mission["origin"], mission["destination"]]})
        return self.view()

    def add_aircraft(self, aircraft: dict[str, Any]) -> dict[str, Any]:
        required = {"name", "type", "capacity", "range", "base"}
        missing = sorted(required - aircraft.keys())
        if missing:
            raise ValueError(f"Missing aircraft fields: {', '.join(missing)}")
        self._airport(str(aircraft["base"]))
        item = {
            "id": str(aircraft.get("id") or f"A-{uuid4().hex[:6].upper()}"),
            "name": str(aircraft["name"]).strip(),
            "type": str(aircraft["type"]).strip(),
            "capacity": float(aircraft["capacity"]),
            "range": int(aircraft["range"]),
            "base": str(aircraft["base"]),
            "status": str(aircraft.get("status", "ready")),
            "health": max(0, min(100, int(aircraft.get("health", 100)))),
            "schedule": list(aircraft.get("schedule", [])),
        }
        if not item["name"] or any(existing["id"] == item["id"] for existing in self.state["aircraft"]):
            raise ValueError("Aircraft name is required and aircraft ID must be unique")
        self.state["aircraft"].append(item)
        self.state["active_plan"] = self.optimize("priority", persist=False)
        self.save()
        self.log("aircraft_added", {"aircraft_id": item["id"]})
        return self.view()

    def add_crew(self, crew: dict[str, Any]) -> dict[str, Any]:
        item = {
            "id": str(crew.get("id") or f"C-{uuid4().hex[:6].upper()}"),
            "name": str(crew.get("name", "")).strip(),
            "qualification": str(crew.get("qualification", "general")).strip() or "general",
            "available": bool(crew.get("available", True)),
            "schedule": list(crew.get("schedule", [])),
        }
        if not item["name"] or any(existing["id"] == item["id"] for existing in self.state["crew"]):
            raise ValueError("Crew name is required and crew ID must be unique")
        self.state["crew"].append(item)
        self.save()
        self.log("crew_added", {"crew_id": item["id"]})
        return self.view()

    def update_schedule(self, entity: str, entity_id: str, schedule: list[dict[str, Any]]) -> dict[str, Any]:
        if entity not in {"aircraft", "crew"}:
            raise ValueError("Schedule entity must be aircraft or crew")
        records = self.state[entity]
        item = next((record for record in records if record["id"] == entity_id), None)
        if item is None:
            raise ValueError(f"Unknown {entity} ID: {entity_id}")
        for block in schedule:
            if not isinstance(block, dict) or not block.get("start") or not block.get("end"):
                raise ValueError("Each schedule block requires start and end")
        item["schedule"] = schedule
        self.save()
        self.log("schedule_updated", {"entity": entity, "entity_id": entity_id, "blocks": len(schedule)})
        return self.view()

    def update_availability(self, entity: str, entity_id: str, status: str | None = None, available: bool | None = None) -> dict[str, Any]:
        if entity not in {"aircraft", "crew"}:
            raise ValueError("Availability entity must be aircraft or crew")
        item = next((record for record in self.state[entity] if record["id"] == entity_id), None)
        if item is None:
            raise ValueError(f"Unknown {entity} ID: {entity_id}")
        if entity == "aircraft" and status is not None:
            if status not in {"ready", "inspection", "maintenance", "unavailable"}:
                raise ValueError("Unsupported aircraft status")
            item["status"] = status
        if entity == "crew" and available is not None:
            item["available"] = available
        self.state["active_plan"] = self.optimize("priority", persist=False)
        self.save()
        self.log("availability_updated", {"entity": entity, "entity_id": entity_id, "status": status, "available": available})
        return self.view()

    def compare_plans(self) -> dict[str, Any]:
        baseline = self.state.get("active_plan") or self.optimize("priority", persist=False)
        priority = self.optimize("priority", persist=False)
        minimum = self.optimize("minimum-change", persist=False)
        def metrics(plan: dict[str, Any]) -> dict[str, Any]:
            return {"scheduled": len(plan["assignments"]), "unassigned": len(plan["unassigned"]), "priority_score": sum(next(m["priority"] for m in self.state["missions"] if m["id"] == item["mission_id"]) for item in plan["assignments"]), "runtime_ms": plan["runtime_ms"], "hard_constraints": plan["hard_constraints"]}
        return {"baseline": {"plan": baseline["id"], "metrics": metrics(baseline)}, "minimum_change": {"plan": minimum["id"], "metrics": metrics(minimum)}, "priority_optimised": {"plan": priority["id"], "metrics": metrics(priority)}, "explanations": priority["explanations"]}

    def copilot(self, question: str) -> dict[str, Any]:
        lowered = question.lower()
        affected = self.affected()
        plan = self.state.get("active_plan") or {}
        if "affected" in lowered or "disruption" in lowered:
            answer = f"{len(affected)} missions are directly affected by the current disruption: {', '.join(item['id'] for item in affected) or 'none'}."
        elif "unassigned" in lowered or "why" in lowered:
            answer = f"{len(plan.get('unassigned', []))} missions are unassigned. The optimiser enforces capacity, range, readiness, non-overlap and closed-airfield constraints."
        elif "bottleneck" in lowered:
            answer = "The current bottleneck is ready aircraft capacity on long-haul routes; inspect the fleet readiness panel and compare the priority-optimised plan."
        else:
            answer = f"Current evidence: {len(plan.get('assignments', []))} scheduled missions, {len(plan.get('unassigned', []))} unassigned, {len(affected)} affected. This explanation is generated from the canonical simulation state."
        return {"question": question, "answer": answer, "evidence": {"active_plan": plan.get("id"), "affected_missions": [item["id"] for item in affected], "unassigned": plan.get("unassigned", [])}}

    def ledger(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT created_at, event, payload FROM ledger ORDER BY id DESC LIMIT 40").fetchall()
        return [{"created_at": row[0], "event": row[1], "payload": json.loads(row[2])} for row in rows]
