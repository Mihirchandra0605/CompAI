"""Config Scan Probe — reads and validates configuration files."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from probes.base import BaseProbe, EvidenceBatch, EvidenceRecord, ExecutionContext, ProbeDefinitionModel

logger = logging.getLogger(__name__)


class ConfigScanProbe(BaseProbe):
    """Scans configuration files and extracts key-value evidence."""

    probe_type = "CONFIG_SCAN"

    async def execute(
        self, definition: ProbeDefinitionModel, context: ExecutionContext
    ) -> EvidenceBatch:
        """Execute config scan probe."""
        config = definition.config
        file_path = config.get("file_path", "")
        json_paths = config.get("json_paths", [])  # JSONPath-like keys to extract

        records = await self._scan_config(file_path, json_paths)

        batch = EvidenceBatch(
            probe_id=definition.probe_id,
            sample_count=len(records),
            records=records,
            collected_at=datetime.now(timezone.utc),
            lineage={
                "collected_by": definition.probe_id,
                "source": file_path,
                "probe_type": self.probe_type,
            },
        )

        return batch

    async def _scan_config(
        self, file_path: str, json_paths: list[str]
    ) -> list[EvidenceRecord]:
        """Read a JSON config file and extract specified paths."""
        records: list[EvidenceRecord] = []
        path = Path(file_path)

        if not path.exists():
            logger.warning(f"Config file not found: {file_path}")
            return records

        try:
            data = json.loads(path.read_text())

            if json_paths:
                # Extract specific paths
                for jp in json_paths:
                    value = self._resolve_path(data, jp)
                    if value is not None:
                        records.append(
                            EvidenceRecord(
                                timestamp=datetime.now(timezone.utc),
                                value=value if isinstance(value, (int, float, bool)) else str(value),
                                metric=jp,
                                metadata={"path": jp, "source": file_path},
                            )
                        )
            else:
                # Extract all leaf values
                self._extract_leaves(data, "", records, file_path)

        except Exception as e:
            logger.error(f"Error reading config file {file_path}: {e}")

        return records

    def _resolve_path(self, data: Any, path: str) -> Any:
        """Resolve a dot-notation path in a nested dict."""
        keys = path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def _extract_leaves(
        self, data: Any, prefix: str, records: list[EvidenceRecord], source: str
    ) -> None:
        """Recursively extract all leaf values from a nested dict."""
        if isinstance(data, dict):
            for key, value in data.items():
                new_prefix = f"{prefix}.{key}" if prefix else key
                self._extract_leaves(value, new_prefix, records, source)
        elif isinstance(data, (int, float, bool, str)):
            records.append(
                EvidenceRecord(
                    timestamp=datetime.now(timezone.utc),
                    value=data if isinstance(data, (int, float, bool)) else data,
                    metric=prefix,
                    metadata={"path": prefix, "source": source},
                )
            )
