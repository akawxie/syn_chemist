"""HTTP-level smoke tests via FastAPI TestClient."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "judge_provider" in body


def test_normalize_endpoint_runs_without_llm():
    client = TestClient(app)
    r = client.post("/api/molecule/normalize", json={"input": "CCO"})
    assert r.status_code == 200
    body = r.json()
    assert body["canonical_smiles"]  # populated by RDKit
    # Stub naming provider returns no IUPAC, but partial score should be > 0.
    assert body["round_trip_score"] >= 0.5


def test_normalize_endpoint_bad_input():
    client = TestClient(app)
    r = client.post("/api/molecule/normalize", json={"input": "xxx"})
    assert r.status_code == 200
    body = r.json()
    assert body["canonical_smiles"] == ""
    assert body["round_trip_score"] == 0.0
