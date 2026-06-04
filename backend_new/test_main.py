import os
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from main import app, UPLOAD_DIR

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "backend_new"}


def test_upload_no_files():
    response = client.post("/upload")
    assert response.status_code == 400
    assert "No files selected" in response.json()["detail"]


def test_upload_success():
    # Create some dummy files
    regulation_content = b"Telecom regulation details"
    config_content = b'{"rtt_limit": 150}'
    log_content = b"timestamp,call_id,call_type,rtt_ms\n2026-01-01T00:00:00Z,c1,volte,100"

    files = [
        ("regulation", ("regulation.txt", regulation_content, "text/plain")),
        ("configs", ("config.json", config_content, "application/json")),
        ("logs", ("logs.csv", log_content, "text/csv")),
    ]

    response = client.post("/upload", files=files)
    assert response.status_code == 200
    
    data = response.json()
    assert "session_id" in data
    assert data["files_saved"]["regulation"] == 1
    assert data["files_saved"]["repository"] == 0
    assert data["files_saved"]["configs"] == 1
    assert data["files_saved"]["logs"] == 1
    assert data["files_saved"]["security"] == 0

    # Assert pipeline_result is present
    assert "pipeline_result" in data
    pipeline = data["pipeline_result"]
    assert "verdict" in pipeline
    assert "confidence" in pipeline
    assert "report" in pipeline
    assert "stages" in pipeline
    assert "logs" in pipeline

    session_id = data["session_id"]
    session_path = UPLOAD_DIR / session_id

    # Verify files exist on disk
    assert (session_path / "regulation" / "regulation.txt").exists()
    assert (session_path / "configs" / "config.json").exists()
    assert (session_path / "logs" / "logs.csv").exists()

    # Clean up test files
    if session_path.exists():
        shutil.rmtree(session_path)
