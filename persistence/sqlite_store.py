"""SQLite-based state store for V1 persistence."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import aiosqlite

from domain.compliance_state import ComplianceState
from domain.execution_context import ExecutionContext

from .base import AbstractStateStore


class SQLiteStateStore(AbstractStateStore):
    """SQLite implementation of the state store for V1."""

    def __init__(self, db_path: str = "./data/compliai.db") -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def _init_db(self) -> None:
        """Initialize database tables."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS compliance_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    state_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(state_id, version)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    node_name TEXT NOT NULL,
                    state_data TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS execution_contexts (
                    run_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def save_state(self, state: ComplianceState) -> None:
        await self._init_db()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO compliance_states (state_id, version, data) VALUES (?, ?, ?)",
                (state.state_id, state.version.version, state.model_dump_json()),
            )
            await db.commit()

    async def load_state(self, state_id: str, version: int | None = None) -> ComplianceState | None:
        await self._init_db()
        async with aiosqlite.connect(self._db_path) as db:
            if version is not None:
                cursor = await db.execute(
                    "SELECT data FROM compliance_states WHERE state_id = ? AND version = ?",
                    (state_id, version),
                )
            else:
                cursor = await db.execute(
                    "SELECT data FROM compliance_states WHERE state_id = ? ORDER BY version DESC LIMIT 1",
                    (state_id,),
                )
            row = await cursor.fetchone()
            if row:
                return ComplianceState.model_validate_json(row[0])
            return None

    async def list_versions(self, state_id: str) -> list[int]:
        await self._init_db()
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT version FROM compliance_states WHERE state_id = ? ORDER BY version",
                (state_id,),
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def save_checkpoint(self, run_id: str, node_name: str, state: ComplianceState) -> str:
        await self._init_db()
        checkpoint_id = str(uuid.uuid4())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO checkpoints (checkpoint_id, run_id, node_name, state_data) VALUES (?, ?, ?, ?)",
                (checkpoint_id, run_id, node_name, state.model_dump_json()),
            )
            await db.commit()
        return checkpoint_id

    async def load_checkpoint(self, checkpoint_id: str) -> tuple[str, ComplianceState] | None:
        await self._init_db()
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT node_name, state_data FROM checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,),
            )
            row = await cursor.fetchone()
            if row:
                state = ComplianceState.model_validate_json(row[1])
                return (row[0], state)
            return None

    async def save_execution_context(self, ctx: ExecutionContext) -> None:
        await self._init_db()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO execution_contexts (run_id, data) VALUES (?, ?)",
                (ctx.run_id, ctx.model_dump_json()),
            )
            await db.commit()

    async def load_execution_context(self, run_id: str) -> ExecutionContext | None:
        await self._init_db()
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT data FROM execution_contexts WHERE run_id = ?",
                (run_id,),
            )
            row = await cursor.fetchone()
            if row:
                return ExecutionContext.model_validate_json(row[0])
            return None
