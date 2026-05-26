"""File/artifact storage abstraction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ArtifactStorage:
    """Simple file-based artifact storage for V1."""

    def __init__(self, base_path: str = "./data/artifacts") -> None:
        self._base = Path(base_path)
        self._base.mkdir(parents=True, exist_ok=True)

    async def store(self, run_id: str, artifact_type: str, content: str) -> str:
        """Store an artifact and return its path."""
        run_dir = self._base / run_id
        run_dir.mkdir(exist_ok=True)
        path = run_dir / f"{artifact_type}.json"
        path.write_text(content)
        return str(path)

    async def load(self, run_id: str, artifact_type: str) -> str | None:
        """Load an artifact by run ID and type."""
        path = self._base / run_id / f"{artifact_type}.json"
        if path.exists():
            return path.read_text()
        return None

    async def list_artifacts(self, run_id: str) -> list[str]:
        """List all artifacts for a run."""
        run_dir = self._base / run_id
        if run_dir.exists():
            return [f.stem for f in run_dir.glob("*.json")]
        return []
