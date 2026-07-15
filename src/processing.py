import datetime as dt
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from .format_message import UploadResult, db_upload
from .joint_report import JointReport
from .runtime_config import AppConfig
from .utils import read_bulletin, read_station_report, safe_file_copy, safe_file_move, write_bulletin


logger = logging.getLogger(__name__)


@dataclass
class ProcessingOutcome:
    source_path: Path
    status: str
    bulletin_path: Path | None = None
    upload_result: UploadResult | None = None


class MessageProcessor:
    def __init__(self, config: AppConfig | None = None):
        self.config = config or AppConfig.from_env()
        self.config.ensure_directories()

    def process_incoming_path(self, source_path: Path) -> ProcessingOutcome | None:
        if not source_path.exists() or source_path.is_dir():
            return None

        if source_path.name.startswith("WX."):
            return None

        if not self._wait_for_stable_file(source_path):
            logger.warning("File %s never stabilized before timeout", source_path)
            return None

        claimed_path = self._claim_file(source_path, self.config.processing_dir)
        if claimed_path is None:
            return None

        return self._process_claimed_path(claimed_path, update_bulletin=True)

    def process_retry_queue(self, limit: int | None = None) -> list[ProcessingOutcome]:
        outcomes = []
        batch_limit = limit or self.config.retry_batch_size
        retry_files = sorted(
            path for path in self.config.retry_dir.iterdir() if path.is_file()
        )[:batch_limit]

        for retry_path in retry_files:
            outcome = self._process_claimed_path(retry_path, update_bulletin=False)
            outcomes.append(outcome)
        return outcomes

    def generate_bulletin(self, now: dt.datetime | None = None) -> Path:
        now = now or dt.datetime.now(dt.timezone.utc)
        bulletin = JointReport(month_day=now.strftime("%d"), hour=f"{now.strftime('%H')}00")
        path = self.config.current_bulletin_dir / f"WX.{now.strftime('%H')}"

        if path.exists():
            try:
                existing = read_bulletin(path)
                if existing.month_day == bulletin.month_day and existing.hour == bulletin.hour:
                    return path
            except Exception:
                logger.warning("Replacing invalid bulletin file %s", path)

        write_bulletin(path, bulletin)
        return path

    def cleanup_old_files(self, older_than_days: int | None = None) -> list[Path]:
        cutoff = time.time() - (older_than_days or self.config.cleanup_age_days) * 86400
        deleted: list[Path] = []

        for path in self.config.ftp_root.rglob("*"):
            if not path.is_file():
                continue
            if self._should_skip_cleanup(path):
                continue
            if path.stat().st_mtime > cutoff:
                continue
            path.unlink()
            deleted.append(path)

        return deleted

    def _process_claimed_path(self, claimed_path: Path, update_bulletin: bool) -> ProcessingOutcome:
        try:
            station_report = read_station_report(claimed_path)
        except Exception as exc:
            logger.error("Invalid station report %s: %s", claimed_path.name, exc)
            safe_file_move(claimed_path, self.config.rejected_dir)
            return ProcessingOutcome(claimed_path, "rejected")

        bulletin_path = None
        if update_bulletin:
            try:
                bulletin_path = self._update_bulletin(station_report)
            except Exception as exc:
                logger.error("Bulletin update failed for %s: %s", claimed_path.name, exc)
                safe_file_move(claimed_path, self.config.rejected_dir)
                return ProcessingOutcome(claimed_path, "rejected")

        upload_result = db_upload(station_report.get_full_msg(), self.config)
        if upload_result.success:
            safe_file_move(claimed_path, self.config.archive_dir)
            logger.info("DB updated with %s via %s", claimed_path.name, upload_result.action)
            return ProcessingOutcome(claimed_path, "archived", bulletin_path, upload_result)

        logger.error("DB upload failed for %s: %s", claimed_path.name, upload_result.error)
        if claimed_path.parent != self.config.retry_dir:
            safe_file_move(claimed_path, self.config.retry_dir)
        return ProcessingOutcome(claimed_path, "retry", bulletin_path, upload_result)

    def _update_bulletin(self, station_report) -> Path:
        now = dt.datetime.now(dt.timezone.utc)
        day_of_month = now.strftime("%d")
        target = self.config.current_bulletin_dir / f"WX.{station_report.hour}"

        if not target.exists():
            bulletin = JointReport(month_day=day_of_month, hour=f"{station_report.hour}00")
            write_bulletin(target, bulletin)

        try:
            bulletin = read_bulletin(target)
        except Exception:
            bulletin = JointReport(month_day=day_of_month, hour=f"{station_report.hour}00")
            write_bulletin(target, bulletin)
            bulletin = read_bulletin(target)

        if bulletin.month_day != day_of_month:
            bulletin = JointReport(month_day=day_of_month, hour=f"{station_report.hour}00")
            write_bulletin(target, bulletin)
            bulletin = read_bulletin(target)

        if bulletin.month_day != station_report.day:
            raise ValueError(
                f"station report out of date, expected {bulletin.month_day}, received {station_report.day}"
            )

        bulletin.update(station_report)
        write_bulletin(target, bulletin)

        safe_file_copy(target, self.config.bulletin_dir)
        if self.config.destination_dir:
            safe_file_copy(target, self.config.destination_dir)

        logger.info("Bulletin %s updated with %s", target.name, station_report.id)
        return target

    def _claim_file(self, source_path: Path, destination_dir: Path) -> Path | None:
        destination = destination_dir / source_path.name
        try:
            source_path.replace(destination)
        except FileNotFoundError:
            return None
        except PermissionError:
            return None
        return destination

    def _wait_for_stable_file(self, path: Path) -> bool:
        deadline = time.monotonic() + self.config.upload_stability_wait_seconds
        previous = None

        while True:
            if not path.exists():
                return False

            stat = path.stat()
            current = (stat.st_size, stat.st_mtime_ns)
            if previous == current:
                return True
            if time.monotonic() >= deadline:
                return False
            previous = current
            time.sleep(self.config.upload_stability_check_interval_seconds)

    def _should_skip_cleanup(self, path: Path) -> bool:
        if path.suffix in {".lock", ".tmp"}:
            return True

        try:
            relative_parts = path.relative_to(self.config.ftp_root).parts
        except ValueError:
            return True

        if relative_parts and relative_parts[0] == self.config.processing_dir.relative_to(self.config.ftp_root).parts[0]:
            return True

        return False
