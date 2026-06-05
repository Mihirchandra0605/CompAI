import json
import os
import logging
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

# Project root
BASE_DIR = Path(__file__).parent
OUTPUT_FILE = BASE_DIR / "backend_new" / "pipeline_output.json"
LOG_FILE = BASE_DIR / "logger.txt"

def load_output():
    """Read the JSON result produced by the main backend.
    Returns a dict (or an error dict if the file does not exist)."""
    if OUTPUT_FILE.exists():
        try:
            return json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            return {"error": f"Failed to parse JSON: {e}"}
    return {"error": "pipeline_output.json not found – run the pipeline first."}

def load_logs():
    """Read the logger.txt file. Return its content or a placeholder."""
    if LOG_FILE.exists():
        try:
            return LOG_FILE.read_text(encoding="utf-8")
        except Exception as e:
            return f"Failed to read logs: {e}"
    return "No logs available yet."

# Set up logging to both console and file (logger.txt)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

# Tee stdout/stderr so print statements also go to logger.txt
_log_file_handle = open(LOG_FILE, "a", encoding="utf-8")

class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()
    def isatty(self):
        return False
    def fileno(self):
        return sys.__stdout__.fileno()

sys.stdout = Tee(sys.stdout, _log_file_handle)
sys.stderr = Tee(sys.stderr, _log_file_handle)


# Mount static files (CSS)
app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Templates directory
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Duplicate load_output removed - using earlier definition


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    data = load_output()
    logs = load_logs()
    # Pretty‑print JSON for the UI
    pretty_json = json.dumps(data, indent=2, ensure_ascii=False)
    return templates.TemplateResponse(
        "visualizer.html",
        {"request": request, "json_data": pretty_json, "logs": logs, "has_error": "error" in data},
    )

# Optional endpoint to fetch raw JSON (useful for JS)
@app.get("/api/result")
async def api_result():
    return load_output()
if __name__ == "__main__":
    # Completely silence uvicorn logs (startup, access, error)
    for _name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        _logger = logging.getLogger(_name)
        _logger.handlers.clear()
        _logger.propagate = False
        _logger.setLevel(logging.CRITICAL)
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_config={"version": 1, "disable_existing_loggers": True},
        log_level="critical",
        access_log=False,
    )
