"""Log Scan Probe — reads and analyzes log files for metric extraction."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from probes.base import BaseProbe, EvidenceBatch, EvidenceRecord, ExecutionContext, ProbeDefinitionModel

logger = logging.getLogger(__name__)


class LogScanProbe(BaseProbe):
    """Scans log files and extracts metric evidence."""

    probe_type = "LOG_SCAN"

    async def execute(
        self, definition: ProbeDefinitionModel, context: ExecutionContext
    ) -> EvidenceBatch:
        """Execute log scan probe."""
        config = definition.config
        file_path = config.get("file_path", "")
        columns = config.get("columns", [])
        filter_spec = config.get("filter", {})
        aggregation = config.get("aggregation", {})

        # Read the log file
        records = await self._read_log_file(file_path, columns, filter_spec)

        # Create evidence batch
        batch = EvidenceBatch(
            probe_id=definition.probe_id,
            sample_count=len(records),
            records=records,
            lineage={
                "collected_by": definition.probe_id,
                "source": file_path,
                "probe_type": self.probe_type,
                "filter": filter_spec,
            },
        )

        if records:
            batch.collection_window_start = records[0].timestamp
            batch.collection_window_end = records[-1].timestamp

        return batch

    async def _read_log_file(
        self,
        file_path: str,
        columns: list[str],
        filter_spec: dict,
    ) -> list[EvidenceRecord]:
        """Read and filter a CSV log file."""
        records: list[EvidenceRecord] = []
        path = Path(file_path)

        if not path.exists():
            logger.warning(f"Log file not found: {file_path}")
            return records

        try:
            content = path.read_text()
            reader = csv.DictReader(io.StringIO(content))

            for row in reader:
                # Apply filters
                if not self._matches_filter(row, filter_spec):
                    continue

                # Extract the value column (last numeric column or specified)
                value_col = columns[-1] if columns else None
                if value_col and value_col in row:
                    try:
                        value = float(row[value_col])
                    except (ValueError, TypeError):
                        continue

                    timestamp = None
                    if "timestamp" in row:
                        try:
                            timestamp = datetime.fromisoformat(
                                row["timestamp"].replace("Z", "+00:00")
                            )
                        except ValueError:
                            timestamp = datetime.now(timezone.utc)

                    records.append(
                        EvidenceRecord(
                            timestamp=timestamp,
                            value=value,
                            metric=value_col,
                            unit="ms",  # Default for latency
                        )
                    )
        except Exception as e:
            logger.error(f"Error reading log file {file_path}: {e}")

        return records

    def _matches_filter(self, row: dict, filter_spec: dict) -> bool:
        """Check if a row matches the filter specification."""
        for key, value in filter_spec.items():
            if key in row and row[key] != value:
                return False
        return True
