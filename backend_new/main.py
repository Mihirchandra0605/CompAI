"""
backend_new/main.py

Receives uploaded compliance files from the React frontend,
stores them, triggers demo_run.py as a subprocess,
and returns the full pipeline results to the frontend.
"""

import sys
import httpx
import uuid
import shutil
import json
import logging
from pathlib import Path
# Add project root to Python path so demo_run can be imported
sys.path.append(str(Path(__file__).parent.parent))
import os
os.environ.setdefault('LLM_MODEL', 'llama3:latest')
from demo_run import main as demo_main
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend_new")

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent                      # backend_new/
PROJECT_DIR = BASE_DIR.parent                            # CompAI root
UPLOAD_DIR  = BASE_DIR / "uploads"
OUTPUT_FILE = BASE_DIR / "pipeline_output.json"
UPLOAD_DIR.mkdir(exist_ok=True)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="CompliAI Upload & Pipeline Backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ────────────────────────────────────────────────────────────────────
def save_file(file: UploadFile, target_dir: Path) -> bool:
    """Save an uploaded file to target_dir. Returns True on success."""
    if not file.filename:
        return False
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / Path(file.filename).name
    try:
        with dest.open("wb") as buf:
            shutil.copyfileobj(file.file, buf)
        logger.info(f"Saved → {dest}")
        return True
    except Exception as e:
        logger.error(f"Error saving {file.filename}: {e}")
        return False


async def run_demo_pipeline(regulation_path: Path, latency_logs_path: Path) -> dict:
    """Execute the demo pipeline by calling demo_run's main function with provided file paths."""
    logger.info("Running demo pipeline via demo_main() …")
    result = await demo_main(regulation_path=regulation_path, latency_logs_path=latency_logs_path)
    if not isinstance(result, dict):
        raise RuntimeError("demo_main did not return a dictionary of results.")
    return result


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.post("/upload")
async def upload(
    regulation: Optional[UploadFile] = File(None),
    repository: Optional[UploadFile] = File(None),
    configs:    List[UploadFile]     = File(default=[]),
    logs:       List[UploadFile]     = File(default=[]),
    security:   List[UploadFile]     = File(default=[]),
):
    """
    1. Validate at least one file is present.
    2. Clean up ALL previous uploads so old files never bleed into new runs.
    3. Save all files to uploads/<session_id>/ (for reference).
    4. Run demo_run.py with the actual uploaded file paths.
    5. Return the pipeline results to the frontend.
    """

    # ── 1. Validate ──────────────────────────────────────────────────────
    has_files = (
        (regulation and regulation.filename) or
        (repository and repository.filename) or
        any(f.filename for f in configs) or
        any(f.filename for f in logs) or
        any(f.filename for f in security)
    )
    if not has_files:
        raise HTTPException(
            status_code=400,
            detail="Please select at least one file before uploading.",
        )

    # ── 2. Clean up previous uploads ─────────────────────────────────────
    if UPLOAD_DIR.exists():
        shutil.rmtree(UPLOAD_DIR)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # ── 3. Save files ────────────────────────────────────────────────────
    session_id  = str(uuid.uuid4())
    session_dir = UPLOAD_DIR / session_id

    files_saved = {"regulation": 0, "repository": 0,
                   "configs": 0, "logs": 0, "security": 0}

    if regulation and regulation.filename:
        if save_file(regulation, session_dir / "regulation"):
            files_saved["regulation"] += 1

    if repository and repository.filename:
        if save_file(repository, session_dir / "repository"):
            files_saved["repository"] += 1

    for f in configs:
        if f.filename and save_file(f, session_dir / "configs"):
            files_saved["configs"] += 1

    for f in logs:
        if f.filename and save_file(f, session_dir / "logs"):
            files_saved["logs"] += 1

    for f in security:
        if f.filename and save_file(f, session_dir / "security"):
            files_saved["security"] += 1

    # ── 4. Resolve uploaded file paths for demo_main ─────────────────────
    regulation_path = None
    latency_logs_path = None

    # Find the uploaded regulation file (.txt)
    reg_dir = session_dir / "regulation"
    if reg_dir.exists():
        txt_files = list(reg_dir.glob("*.txt"))
        if txt_files:
            regulation_path = txt_files[0]

    # Find the uploaded log file (.csv, .log, .txt, .json)
    logs_dir = session_dir / "logs"
    if logs_dir.exists():
        for ext in ["*.csv", "*.log", "*.txt", "*.json"]:
            found = list(logs_dir.glob(ext))
            if found:
                latency_logs_path = found[0]
                break

    # Build kwargs — only pass what was uploaded, demo_main has defaults
    kwargs = {}
    if regulation_path:
        kwargs["regulation_path"] = regulation_path
    if latency_logs_path:
        kwargs["latency_logs_path"] = latency_logs_path

    # ── 5. Run demo pipeline ─────────────────────────────────────────────
    try:
        pipeline_result = await demo_main(**kwargs)
    except Exception as e:
        logger.exception("Pipeline execution failed")
        raise HTTPException(status_code=500, detail=str(e))

    # ── 6. Return results ────────────────────────────────────────────────
    return {
        "session_id": session_id,
        "files_saved": files_saved,
        **pipeline_result,
    }


@app.get("/results")
async def get_results():
    """Return the latest pipeline_output.json (useful for debugging/refresh)."""
    if not OUTPUT_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="No pipeline results found yet. Run demo_run.py first.",
        )
    return json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "backend_new"}


@app.get("/ollama/status")
async def ollama_status():
    """Check if the local Ollama server is reachable."""
    try:
        async with httpx.AsyncClient() as client:
            # Ollama provides a simple version endpoint
            resp = await client.get("http://localhost:11434/api/version")
            if resp.status_code == 200:
                return {"ollama": "online", "details": resp.json()}
            else:
                raise HTTPException(status_code=502, detail="Ollama responded with error status")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
