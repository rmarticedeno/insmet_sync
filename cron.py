#!/usr/local/bin/python

import argparse
import logging
import sys

from src.processing import MessageProcessor
from src.runtime_config import AppConfig


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[logging.StreamHandler()],
)


def build_parser():
    parser = argparse.ArgumentParser(description="Operational cron commands for insmet_sync")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("generate-bulletin")

    retry_parser = subparsers.add_parser("retry-db")
    retry_parser.add_argument("--limit", type=int, default=None)

    cleanup_parser = subparsers.add_parser("cleanup")
    cleanup_parser.add_argument("--older-than-days", type=int, default=None)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    processor = MessageProcessor(AppConfig.from_env())

    if args.command == "generate-bulletin":
        path = processor.generate_bulletin()
        logging.getLogger(__name__).info("Bulletin ready at %s", path)
        return 0

    if args.command == "retry-db":
        outcomes = processor.process_retry_queue(limit=args.limit)
        failures = [item for item in outcomes if item.status == "retry"]
        return 1 if failures else 0

    if args.command == "cleanup":
        processor.cleanup_old_files(older_than_days=args.older_than_days)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
