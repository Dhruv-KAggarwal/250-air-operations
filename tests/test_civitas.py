from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app


def test_full_shockwave_workflow(tmp_path: Path) -> None:
    client = TestClient(create_app(str(tmp_path / "test.db")))
    baseline = client.get("/api/state").json()
    assert len(baseline["airports"]) == 8
    assert baseline["active_plan"]
    client.post("/api/closure", json={"airport_id": "GAU"})
    state = client.get("/api/state").json()
    assert state["affected_missions"]
    result = client.post("/api/optimize?mode=priority").json()
    assert result["plan"]["hard_constraints"] is True
    before = client.get("/api/state").json()["active_plan"]["id"]
    client.post("/api/approve")
    after = client.get("/api/state").json()["active_plan"]["id"]
    assert before != after
    assert any(row["event"] == "proposal_approved" for row in client.get("/api/ledger").json())


def test_rejection_does_not_change_active_plan(tmp_path: Path) -> None:
    client = TestClient(create_app(str(tmp_path / "test.db")))
    before = client.get("/api/state").json()["active_plan"]["id"]
    client.post("/api/closure", json={"airport_id": "BOM"})
    client.post("/api/optimize")
    client.post("/api/reject", json={"reason": "operator review"})
    state = client.get("/api/state").json()
    assert state["active_plan"]["id"] == before
