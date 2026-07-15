import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.format_message import UploadResult
from src.parsing import DB_COLUMNS, parse_fm12
from src.processing import MessageProcessor
from src.runtime_config import AppConfig
from src.utils import read_bulletin, read_station_report


def make_config(root: Path) -> AppConfig:
    ftp_root = root / "ftp"
    return AppConfig(
        data_root=root,
        ftp_root=ftp_root,
        incoming_dir=ftp_root / "uploads",
        bulletin_dir=ftp_root / "bulletins",
        archive_dir=ftp_root / "processed",
        rejected_dir=ftp_root / "invalid",
        retry_dir=ftp_root / "retry",
        processing_dir=ftp_root / "processing",
        current_bulletin_dir=ftp_root / "current-bulletins",
        destination_dir=None,
        db_table="observations",
        db_connstring="Driver=fake",
        upload_stability_wait_seconds=1,
        upload_stability_check_interval_seconds=1,
        db_connect_timeout_seconds=1,
        db_query_timeout_seconds=1,
        retry_batch_size=20,
        cleanup_age_days=1,
        bulletin_job_timeout_seconds=300,
        retry_job_timeout_seconds=240,
        cleanup_job_timeout_seconds=45,
    )


class ParseTests(unittest.TestCase):
    def test_parse_fm12_preserves_89_field_contract(self):
        report = read_station_report("SN342.15")
        result = parse_fm12(report.get_full_msg())
        self.assertTrue(result.ok)
        self.assertEqual(tuple(result.payload.keys()), DB_COLUMNS)
        self.assertEqual(len(result.payload), 89)
        self.assertEqual(result.payload["station_id"], "78342")
        self.assertEqual(result.payload["surface_wind_speed"], 1)


class BulletinTests(unittest.TestCase):
    def test_read_bulletin_raises_on_truncated_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bulletin_path = Path(tmpdir) / "WX.15"
            bulletin_path.write_text("ZCZC 123\nSMCU20 MUHV 061500\nAAXX 06151\n78156 12345", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_bulletin(bulletin_path)


class ProcessorTests(unittest.TestCase):
    def test_db_failure_routes_file_to_retry_without_losing_bulletin(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_config(Path(tmpdir))
            processor = MessageProcessor(config)
            incoming_file = config.incoming_dir / "SN342.15"
            incoming_file.parent.mkdir(parents=True, exist_ok=True)
            current_day = dt.datetime.now(dt.timezone.utc).strftime("%d")
            report_text = Path("SN342.15").read_text(encoding="utf-8").replace("AAXX 06150", f"AAXX {current_day}150", 1)
            incoming_file.write_text(report_text, encoding="utf-8")

            with mock.patch("src.processing.db_upload", return_value=UploadResult(False, "db_failed", "boom")):
                outcome = processor.process_incoming_path(incoming_file)

            self.assertIsNotNone(outcome)
            self.assertEqual(outcome.status, "retry")
            self.assertTrue((config.retry_dir / "SN342.15").exists())
            self.assertTrue((config.bulletin_dir / "WX.15").exists())

    def test_cleanup_skips_processing_and_lock_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = make_config(Path(tmpdir))
            processor = MessageProcessor(config)
            old_processing = config.processing_dir / "old.report"
            old_lock = config.ftp_root / "current-bulletins" / "WX.15.lock"
            old_archive = config.archive_dir / "old.report"
            for path in (old_processing, old_lock, old_archive):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x", encoding="utf-8")
                old_time = 1
                Path(path).touch()
                import os

                os.utime(path, (old_time, old_time))

            deleted = processor.cleanup_old_files(older_than_days=1)
            self.assertIn(old_archive, deleted)
            self.assertTrue(old_processing.exists())
            self.assertTrue(old_lock.exists())


if __name__ == "__main__":
    unittest.main()
