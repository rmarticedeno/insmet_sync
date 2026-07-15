import os
import subprocess
import sys
from pathlib import Path

from .runtime_config import AppConfig


CRONTAB_PATH = Path("/etc/crontabs/root")


def build_crontab(config: AppConfig) -> str:
    return "\n".join(
        [
            "SHELL=/bin/sh",
            "PATH=/usr/local/bin:/usr/bin:/bin",
            "CRON_TZ=UTC",
            f"0 * * * * {sys.executable} /app/src/scheduler_job.py --timeout {config.bulletin_job_timeout_seconds} generate-bulletin",
            f"*/5 * * * * {sys.executable} /app/src/scheduler_job.py --timeout {config.retry_job_timeout_seconds} retry-db --limit {config.retry_batch_size}",
            f"59 * * * * {sys.executable} /app/src/scheduler_job.py --timeout {config.cleanup_job_timeout_seconds} cleanup --older-than-days {config.cleanup_age_days}",
            "",
        ]
    )


def main():
    config = AppConfig.from_env()
    config.ensure_directories()
    CRONTAB_PATH.write_text(build_crontab(config), encoding="utf-8")
    os.execvp("crond", ["crond", "-f", "-l", "2"])


if __name__ == "__main__":
    main()
