from dataclasses import dataclass
import logging
import os

import pyodbc

from .parsing import parse_fm12
from .runtime_config import AppConfig


logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    success: bool
    action: str
    error: str | None = None
    warnings: list[str] | None = None
    parse_discrepancies: dict | None = None


def db_upload(msg, config: AppConfig | None = None):
    cfg = config or AppConfig.from_env()

    if not cfg.db_connstring or not cfg.db_table:
        return UploadResult(
            success=False,
            action="skipped",
            error="Database configuration is missing",
        )

    parse_result = parse_fm12(msg)
    if not parse_result.ok:
        return UploadResult(
            success=False,
            action="parse_failed",
            error="; ".join(parse_result.errors),
            warnings=parse_result.warnings,
            parse_discrepancies=parse_result.discrepancies,
        )

    payload = parse_result.payload
    obs_time = payload["obs_time"]
    station_id = payload["station_id"]

    columns = ", ".join(payload.keys())
    placeholders = ", ".join(["?"] * len(payload))
    update_assignments = ", ".join(f"{column} = ?" for column in payload.keys())
    query_select = f"SELECT 1 FROM {cfg.db_table} WHERE obs_time = ? AND station_id = ?"
    query_insert = f"INSERT INTO {cfg.db_table} ({columns}) VALUES ({placeholders})"
    query_update = f"UPDATE {cfg.db_table} SET {update_assignments} WHERE obs_time = ? AND station_id = ?"

    try:
        with pyodbc.connect(cfg.db_connstring, timeout=cfg.db_connect_timeout_seconds) as conn:
            with conn.cursor() as cursor:
                cursor.timeout = cfg.db_query_timeout_seconds
                exists = cursor.execute(query_select, (obs_time, station_id)).fetchone() is not None
                if exists:
                    cursor.execute(query_update, tuple(payload.values()) + (obs_time, station_id))
                    action = "updated"
                else:
                    cursor.execute(query_insert, tuple(payload.values()))
                    action = "inserted"
                conn.commit()
        return UploadResult(
            success=True,
            action=action,
            warnings=parse_result.warnings,
            parse_discrepancies=parse_result.discrepancies,
        )
    except Exception as exc:
        logger.exception("Database upload failed")
        return UploadResult(
            success=False,
            action="db_failed",
            error=str(exc),
            warnings=parse_result.warnings,
            parse_discrepancies=parse_result.discrepancies,
        )
