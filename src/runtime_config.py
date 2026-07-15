import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)

TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_\.]*$")


def _expand_legacy_tokens(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None

    value = os.path.expandvars(raw_value)
    replacements = {
        "{BASE_FOLDER}": os.getenv("BASE_FOLDER", ""),
        "${BASE_FOLDER}": os.getenv("BASE_FOLDER", ""),
        "{FTP_DATA}": os.getenv("FTP_DATA", ""),
        "${FTP_DATA}": os.getenv("FTP_DATA", ""),
    }
    for token, replacement in replacements.items():
        if replacement:
            value = value.replace(token, replacement)
    return value


def _resolve_path(raw_value: str | None, root: Path, default_relative: str | None = None) -> Path | None:
    value = _expand_legacy_tokens(raw_value)
    if not value:
        if default_relative is None:
            return None
        candidate = root / default_relative
    else:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = root / candidate

    return candidate.resolve()


def _validate_under_root(path: Path | None, root: Path, label: str) -> None:
    if path is None:
        return

    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay within DATA_ROOT ({root}), got {path}") from exc


@dataclass(frozen=True)
class AppConfig:
    data_root: Path
    ftp_root: Path
    incoming_dir: Path
    bulletin_dir: Path
    archive_dir: Path
    rejected_dir: Path
    retry_dir: Path
    processing_dir: Path
    current_bulletin_dir: Path
    destination_dir: Path | None
    db_table: str | None
    db_connstring: str | None
    upload_stability_wait_seconds: int
    upload_stability_check_interval_seconds: int
    db_connect_timeout_seconds: int
    db_query_timeout_seconds: int
    retry_batch_size: int
    cleanup_age_days: int
    bulletin_job_timeout_seconds: int
    retry_job_timeout_seconds: int
    cleanup_job_timeout_seconds: int

    @classmethod
    def from_env(cls) -> "AppConfig":
        root_raw = (
            os.getenv("DATA_ROOT")
            or _expand_legacy_tokens(os.getenv("BASE_FOLDER"))
            or "."
        )
        data_root = Path(root_raw)
        if not data_root.is_absolute():
            data_root = Path.cwd() / data_root
        data_root = data_root.resolve()

        ftp_root = _resolve_path(os.getenv("FTP_DATA"), data_root, "ftp")
        incoming_dir = _resolve_path(os.getenv("REPORT_DATA"), data_root, "ftp/uploads")
        bulletin_dir = _resolve_path(os.getenv("BULLETIN_DATA"), data_root, "ftp/bulletins")
        archive_dir = _resolve_path(os.getenv("REPORT_BACKUP_DATA"), data_root, "ftp/processed")
        rejected_dir = _resolve_path(
            os.getenv("REJECTED_REPORT_DATA") or os.getenv("INVALID_PROCESSED_REPORTS"),
            data_root,
            "ftp/invalid",
        )
        retry_dir = _resolve_path(os.getenv("RETRY_REPORT_DATA"), data_root, "ftp/retry")
        processing_dir = _resolve_path(os.getenv("CLAIMED_REPORT_DATA"), data_root, "ftp/processing")
        current_bulletin_dir = _resolve_path(os.getenv("PROCESSING_FOLDER"), data_root, "ftp/current-bulletins")
        destination_dir = _resolve_path(os.getenv("DESTINATION_FOLDER"), data_root, None)

        for label, path in (
            ("FTP_DATA", ftp_root),
            ("REPORT_DATA", incoming_dir),
            ("BULLETIN_DATA", bulletin_dir),
            ("REPORT_BACKUP_DATA", archive_dir),
            ("REJECTED_REPORT_DATA", rejected_dir),
            ("RETRY_REPORT_DATA", retry_dir),
            ("CLAIMED_REPORT_DATA", processing_dir),
            ("PROCESSING_FOLDER", current_bulletin_dir),
        ):
            _validate_under_root(path, data_root, label)

        for legacy_name in (
            "BASE_FOLDER",
            "FTP_DATA",
            "REPORT_DATA",
            "BULLETIN_DATA",
            "REPORT_BACKUP_DATA",
            "INVALID_PROCESSED_REPORTS",
            "PROCESSING_FOLDER",
        ):
            if os.getenv(legacy_name):
                logger.warning("Using legacy path variable %s; DATA_ROOT-based layout is preferred", legacy_name)

        db_table = os.getenv("DB_Table") or os.getenv("DB_TABLE")
        if db_table and not TABLE_NAME_PATTERN.fullmatch(db_table):
            raise ValueError(f"Invalid DB table name: {db_table}")

        return cls(
            data_root=data_root,
            ftp_root=ftp_root,
            incoming_dir=incoming_dir,
            bulletin_dir=bulletin_dir,
            archive_dir=archive_dir,
            rejected_dir=rejected_dir,
            retry_dir=retry_dir,
            processing_dir=processing_dir,
            current_bulletin_dir=current_bulletin_dir,
            destination_dir=destination_dir,
            db_table=db_table,
            db_connstring=os.getenv("DB_CONNSTRING"),
            upload_stability_wait_seconds=max(1, int(os.getenv("UPLOAD_STABILITY_WAIT_SECONDS", "30"))),
            upload_stability_check_interval_seconds=max(1, int(os.getenv("UPLOAD_STABILITY_CHECK_INTERVAL_SECONDS", "2"))),
            db_connect_timeout_seconds=max(1, int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "10"))),
            db_query_timeout_seconds=max(1, int(os.getenv("DB_QUERY_TIMEOUT_SECONDS", "30"))),
            retry_batch_size=max(1, int(os.getenv("RETRY_BATCH_SIZE", "20"))),
            cleanup_age_days=max(1, int(os.getenv("CLEANUP_AGE_DAYS", "1"))),
            bulletin_job_timeout_seconds=max(1, int(os.getenv("BULLETIN_JOB_TIMEOUT_SECONDS", "300"))),
            retry_job_timeout_seconds=max(1, int(os.getenv("RETRY_JOB_TIMEOUT_SECONDS", "240"))),
            cleanup_job_timeout_seconds=max(1, int(os.getenv("CLEANUP_JOB_TIMEOUT_SECONDS", "45"))),
        )

    def ensure_directories(self) -> None:
        for path in (
            self.data_root,
            self.ftp_root,
            self.incoming_dir,
            self.bulletin_dir,
            self.archive_dir,
            self.rejected_dir,
            self.retry_dir,
            self.processing_dir,
            self.current_bulletin_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

        if self.destination_dir:
            self.destination_dir.mkdir(parents=True, exist_ok=True)
