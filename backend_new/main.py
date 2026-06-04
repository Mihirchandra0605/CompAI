"""
backend_new/main.py

Receives uploaded compliance files from the React frontend,
stores them, triggers demo_run.py as a subprocess,
and returns the full pipeline results to the frontend.
"""

import os
import uuid
import shutil
import logging
import asyncio
import json
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

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


async def run_demo_pipeline() -> dict:
    """
    Spawn demo_run.py as an asyncio subprocess from the project root.
    Wait for it to finish, then read and return pipeline_output.json.
    """
    logger.info("Spawning demo_run.py …")

    proc = await asyncio.create_subprocess_exec(
        "python", "demo_run.py",
        cwd=str(PROJECT_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    stdout, _ = await proc.communicate()
    terminal_output = stdout.decode(errors="replace") if stdout else ""

    if proc.returncode != 0:
        logger.error(f"demo_run.py exited with code {proc.returncode}")
        logger.error(terminal_output)
        raise RuntimeError(
            f"Pipeline script failed (exit {proc.returncode}).\n{terminal_output[-1000:]}"
        )

    logger.info("demo_run.py finished successfully.")

    # Read the output JSON written by demo_run.py
    if not OUTPUT_FILE.exists():
        raise RuntimeError(
            "Pipeline ran but pipeline_output.json was not created. "
            "Check demo_run.py for errors."
        )

    return json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))


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
    2. Save all files to uploads/<session_id>/ (for reference).
    3. Run demo_run.py as a subprocess.
    4. Return the pipeline results to the frontend.
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

    # ── 2. Save files ────────────────────────────────────────────────────
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

    # ── 3. Run demo_run.py ───────────────────────────────────────────────
    try:
        pipeline_result = await run_demo_pipeline()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # ── 4. Return results ────────────────────────────────────────────────
    return {
        "session_id":      session_id,
        "files_saved":     files_saved,
        "pipeline_result": pipeline_result,
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
