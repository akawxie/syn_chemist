"""P2 — POST /api/molecule/from_image with mocked OCR."""
from __future__ import annotations

import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.api import molecule_image as molecule_image_api
from app.llm.gemini_vision import NotAMoleculeError, OCRResult


def _make_png(size: tuple[int, int] = (400, 400), color=(255, 255, 255)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg(size: tuple[int, int] = (400, 400)) -> bytes:
    img = Image.new("RGB", size, color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class FakeOCR:
    """Stand-in for GeminiVisionOCR."""

    def __init__(self, behavior: str = "ok") -> None:
        self.behavior = behavior

    async def smiles_from_image(self, raw: bytes, mime: str) -> OCRResult:
        if self.behavior == "not_molecule":
            raise NotAMoleculeError("nope")
        if self.behavior == "uncertain":
            return OCRResult(smiles="", raw="UNCERTAIN", warning="OCR uncertain")
        if self.behavior == "bad_smiles":
            return OCRResult(smiles="", raw="abc", warning="OCR returned invalid SMILES: abc")
        return OCRResult(smiles="CCO", raw="CCO")


class FakeValidator:
    """Stand-in for RoundTripValidator."""

    def __init__(self, ok: bool = True) -> None:
        self.ok = ok

    async def normalize(self, raw: str):
        from app.pipeline.naming import NormalizedMolecule

        if self.ok:
            return NormalizedMolecule(
                input_raw=raw,
                canonical_smiles="CCO",
                iupac="ethanol",
                round_trip_ok=True,
                round_trip_score=1.0,
                notes=[],
            )
        return NormalizedMolecule(
            input_raw=raw,
            canonical_smiles="CCO",
            iupac=None,
            round_trip_ok=False,
            round_trip_score=0.4,
            notes=["round-trip failed"],
        )


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(molecule_image_api.router)
    return app


def _build_client_with(monkeypatch, ocr_behavior="ok", validator_ok=True):
    app = FastAPI()
    app.include_router(molecule_image_api.router)
    monkeypatch.setattr(
        molecule_image_api, "GeminiVisionOCR", lambda: FakeOCR(ocr_behavior)
    )
    monkeypatch.setattr(
        molecule_image_api, "RoundTripValidator", lambda: FakeValidator(validator_ok)
    )
    return TestClient(app)


def test_upload_png_ok(monkeypatch):
    c = _build_client_with(monkeypatch, ocr_behavior="ok", validator_ok=True)
    files = {"file": ("aspirin.png", _make_png(), "image/png")}
    r = c.post("/api/molecule/from_image", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["smiles"] == "CCO"
    assert body["canonical_smiles"] == "CCO"
    assert body["round_trip_ok"] is True


def test_upload_jpeg_ok(monkeypatch):
    c = _build_client_with(monkeypatch, ocr_behavior="ok", validator_ok=True)
    files = {"file": ("aspirin.jpg", _make_jpeg(), "image/jpeg")}
    r = c.post("/api/molecule/from_image", files=files)
    assert r.status_code == 200


def test_upload_oversize_blocked(monkeypatch):
    c = _build_client_with(monkeypatch)
    # 6MB of zeros — not a valid image, but size check triggers first
    files = {"file": ("big.png", b"\x00" * (6 * 1024 * 1024), "image/png")}
    r = c.post("/api/molecule/from_image", files=files)
    assert r.status_code == 413


def test_upload_pdf_rejected(monkeypatch):
    """Even with image/png Content-Type header, content-sniffing should reject."""
    c = _build_client_with(monkeypatch)
    fake_pdf = b"%PDF-1.4\n%fake\n"
    files = {"file": ("evil.png", fake_pdf, "image/png")}
    r = c.post("/api/molecule/from_image", files=files)
    assert r.status_code in (415, 422)


def test_upload_too_small(monkeypatch):
    c = _build_client_with(monkeypatch)
    files = {"file": ("tiny.png", _make_png((50, 50)), "image/png")}
    r = c.post("/api/molecule/from_image", files=files)
    assert r.status_code == 400
    assert "too small" in r.json()["detail"].lower()


def test_upload_round_trip_fails(monkeypatch):
    """OCR returns valid SMILES but round-trip can't verify → warning, but 200."""
    c = _build_client_with(monkeypatch, ocr_behavior="ok", validator_ok=False)
    files = {"file": ("img.png", _make_png(), "image/png")}
    r = c.post("/api/molecule/from_image", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["round_trip_ok"] is False
    assert "not verified" in (body.get("warning") or "").lower()


def test_upload_not_a_molecule(monkeypatch):
    c = _build_client_with(monkeypatch, ocr_behavior="not_molecule")
    files = {"file": ("cat.png", _make_png(), "image/png")}
    r = c.post("/api/molecule/from_image", files=files)
    assert r.status_code == 422


def test_upload_ocr_uncertain(monkeypatch):
    c = _build_client_with(monkeypatch, ocr_behavior="uncertain")
    files = {"file": ("blurry.png", _make_png(), "image/png")}
    r = c.post("/api/molecule/from_image", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["smiles"] == ""
    assert "uncertain" in (body.get("warning") or "").lower()


def test_upload_empty(monkeypatch):
    c = _build_client_with(monkeypatch)
    files = {"file": ("empty.png", b"", "image/png")}
    r = c.post("/api/molecule/from_image", files=files)
    assert r.status_code == 422


def test_oversize_image_dimension_downscaled(monkeypatch):
    """5000x5000 png should be accepted (after downscale) — verify endpoint succeeds."""
    c = _build_client_with(monkeypatch, ocr_behavior="ok")
    files = {"file": ("huge.png", _make_png((5000, 5000)), "image/png")}
    r = c.post("/api/molecule/from_image", files=files)
    assert r.status_code == 200
