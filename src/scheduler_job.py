import argparse
import subprocess
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run one scheduled job with a timeout")
    parser.add_argument("--timeout", type=int, required=True)
    parser.add_argument("cron_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    if not args.cron_args:
        raise SystemExit("No cron command specified")

    command = [sys.executable, "/app/cron.py", *args.cron_args]
    completed = subprocess.run(command, timeout=args.timeout, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
