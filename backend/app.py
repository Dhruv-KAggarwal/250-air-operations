from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .engine import World


class Closure(BaseModel):
    airport_id: str


class Rejection(BaseModel):
    reason: str


class MissionPayload(BaseModel):
    title: str
    origin: str
    destination: str
    cargo: float
    duration: int
    deadline: int
    priority: int
    category: str
    notes: str = ""


class AircraftPayload(BaseModel):
    name: str
    type: str
    capacity: float
    range: int
    base: str
    status: str = "ready"
    health: int = 100


class CrewPayload(BaseModel):
    name: str
    qualification: str = "general"
    available: bool = True


class SchedulePayload(BaseModel):
    entity: str
    entity_id: str
    schedule: list[dict[str, Any]]


class AvailabilityPayload(BaseModel):
    entity: str
    entity_id: str
    status: str | None = None
    available: bool | None = None


class CopilotPayload(BaseModel):
    question: str


def create_app(db_path: str | None = None) -> FastAPI:
    root = Path(__file__).resolve().parent.parent
    world = World(db_path or os.getenv("CIVITAS_DB", str(root / "civitas.db")))
    clients: set[WebSocket] = set()
    app = FastAPI(title="Civitas AirOps", version="2.0")
    app.state.world = world

    async def broadcast(message: dict[str, Any]) -> None:
        text = json.dumps(message)
        stale = []
        for client in clients:
            try:
                await client.send_text(text)
            except Exception:
                stale.append(client)
        for client in stale:
            clients.discard(client)

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(root / "index.html")

    @app.get("/styles.css")
    def styles() -> FileResponse:
        return FileResponse(root / "styles.css")

    @app.get("/app.js")
    def script() -> FileResponse:
        return FileResponse(root / "app.js")

    @app.get("/api/state")
    def state() -> dict[str, Any]:
        return world.view()

    @app.get("/api/ledger")
    def ledger(search: str = "") -> list[dict[str, Any]]:
        rows = world.ledger()
        if not search:
            return rows
        query = search.lower()
        return [row for row in rows if query in row["event"].lower() or query in json.dumps(row["payload"]).lower()]

    @app.post("/api/reset")
    async def reset() -> dict[str, Any]:
        value = world.reset()
        await broadcast({"type": "state", "state": value})
        return value

    @app.post("/api/availability")
    async def update_availability(payload: AvailabilityPayload) -> dict[str, Any]:
        try:
            value = world.update_availability(payload.entity, payload.entity_id, payload.status, payload.available)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        await broadcast({"type": "state", "state": value})
        return value

    @app.get("/api/plan-comparison")
    def plan_comparison() -> dict[str, Any]:
        return world.compare_plans()

    @app.post("/api/copilot")
    def copilot(payload: CopilotPayload) -> dict[str, Any]:
        return world.copilot(payload.question)

    @app.post("/api/closure")
    async def close_airport(payload: Closure) -> dict[str, Any]:
        try:
            value = world.inject_closure(payload.airport_id)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        await broadcast({"type": "state", "state": value})
        return value

    @app.post("/api/optimize")
    async def optimize(mode: str = "priority") -> dict[str, Any]:
        plan = world.optimize(mode)
        value = world.view()
        await broadcast({"type": "proposal", "plan": plan, "state": value})
        return {"plan": plan, "state": value}

    @app.post("/api/approve")
    async def approve() -> dict[str, Any]:
        try:
            value = world.approve()
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        await broadcast({"type": "state", "state": value})
        return value

    @app.post("/api/reject")
    async def reject(payload: Rejection) -> dict[str, Any]:
        try:
            value = world.reject(payload.reason)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        await broadcast({"type": "state", "state": value})
        return value

    @app.post("/api/missions")
    async def add_mission(payload: MissionPayload) -> dict[str, Any]:
        try:
            value = world.add_mission(payload.model_dump())
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        await broadcast({"type": "state", "state": value})
        return value

    @app.post("/api/aircraft")
    async def add_aircraft(payload: AircraftPayload) -> dict[str, Any]:
        try:
            value = world.add_aircraft(payload.model_dump())
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        await broadcast({"type": "state", "state": value})
        return value

    @app.post("/api/crew")
    async def add_crew(payload: CrewPayload) -> dict[str, Any]:
        try:
            value = world.add_crew(payload.model_dump())
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        await broadcast({"type": "state", "state": value})
        return value

    @app.post("/api/schedules")
    async def update_schedule(payload: SchedulePayload) -> dict[str, Any]:
        try:
            value = world.update_schedule(payload.entity, payload.entity_id, payload.schedule)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        await broadcast({"type": "state", "state": value})
        return value

    @app.get("/api/weather")
    def weather(lat: float = 20.59, lon: float = 78.96) -> dict[str, Any]:
        query = urlencode({"latitude": lat, "longitude": lon, "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,visibility", "timezone": "Asia/Kolkata"})
        try:
            with urlopen(f"https://api.open-meteo.com/v1/forecast?{query}", timeout=4) as response:
                value = json.loads(response.read().decode())
            value["source"] = "Open-Meteo public feed"
            value["is_fallback"] = False
            return value
        except Exception:
            return {"source": "Local safety fallback", "is_fallback": True, "current": {"temperature_2m": 27, "relative_humidity_2m": 61, "precipitation": 0, "wind_speed_10m": 12, "visibility": 10000}}

    @app.get("/api/route-weather")
    def route_weather(origin: str, destination: str) -> dict[str, Any]:
        try:
            start = world._airport(origin)
            end = world._airport(destination)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        points = [
            {"name": start["name"], "lat": start["lat"], "lon": start["lon"]},
            {"name": "Route midpoint", "lat": (start["lat"] + end["lat"]) / 2, "lon": (start["lon"] + end["lon"]) / 2},
            {"name": end["name"], "lat": end["lat"], "lon": end["lon"]},
        ]
        conditions = []
        for point in points:
            query = urlencode({"latitude": point["lat"], "longitude": point["lon"], "current": "temperature_2m,precipitation,wind_speed_10m,visibility", "timezone": "Asia/Kolkata"})
            try:
                with urlopen(f"https://api.open-meteo.com/v1/forecast?{query}", timeout=4) as response:
                    current = json.loads(response.read().decode()).get("current", {})
                source = "live public feed"
            except Exception:
                current = {"temperature_2m": 27, "precipitation": 0, "wind_speed_10m": 12, "visibility": 10000}
                source = "local safety fallback"
            risk_reasons = []
            if float(current.get("wind_speed_10m", 0)) > 35:
                risk_reasons.append("high wind")
            if float(current.get("visibility", 10000)) < 5000:
                risk_reasons.append("low visibility")
            if float(current.get("precipitation", 0)) > 5:
                risk_reasons.append("heavy precipitation")
            conditions.append({**point, "current": current, "source": source, "risk": bool(risk_reasons), "reasons": risk_reasons})
        risks = [item for item in conditions if item["risk"]]
        return {"origin": origin, "destination": destination, "distance_km": int(math.hypot(start["lat"] - end["lat"], start["lon"] - end["lon"]) * 110), "recommendation": "Avoid or review route" if risks else "Preferred route", "route_status": "restricted" if risks else "operational", "conditions": conditions, "avoid": [item["name"] for item in risks], "source": "Open-Meteo sampled route corridor"}

    @app.websocket("/ws")
    async def websocket(ws: WebSocket) -> None:
        await ws.accept()
        clients.add(ws)
        await ws.send_text(json.dumps({"type": "state", "state": world.view()}))
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            clients.discard(ws)

    return app


app = create_app()
