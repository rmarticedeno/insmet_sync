import contextlib
import logging
import os
import re
import shutil
import time
from pathlib import Path

from .constans import END_OF_MESSAGE, END_OF_REPORT, NEWMESSAGEHEADER, TERRESTIALREPORTID
from .joint_report import JointReport
from .station_report import StationReport


logger = logging.getLogger(__name__)


def get_safe_path(path):
    resolved = Path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def get_oneline_message(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        cleaned_lines = [line.strip() for line in handle.readlines()]

    message = " ".join(cleaned_lines)
    return re.split(END_OF_MESSAGE, message, flags=re.IGNORECASE)[0].strip()


def read_station_report(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = handle.read()

    msg = " ".join(data.split())
    valid = False

    for marker in (TERRESTIALREPORTID, TERRESTIALREPORTID.lower()):
        index = msg.find(marker)
        if index != -1:
            msg = msg[index:]
            valid = True
            break

    if not valid:
        raise ValueError(f"{TERRESTIALREPORTID} not found")

    day = msg[5:7]
    hour = msg[7:9]
    station_id = msg.split(" ")[2]

    index = msg.find(END_OF_REPORT)
    if index != -1:
        msg = msg[:index]
    else:
        index = msg.find(END_OF_MESSAGE)
        if index != -1:
            msg = msg[:index]

    msg = msg[11:]
    msg = f"{msg}="
    msg = msg.replace(" =", "=")
    return StationReport(station_id, msg, day, hour)


def _read_bulletin_stations(handle):
    stations = []

    while True:
        station_line = handle.readline()
        if station_line == "":
            return stations

        station_line = station_line.strip()
        if len(station_line) == 0:
            break

        station_id = station_line.split(" ")[0]
        station = StationReport(station_id)

        if "nil" in station_line:
            stations.append(station)
            continue

        data = station_line
        while END_OF_REPORT not in station_line:
            station_line = handle.readline()
            if station_line == "":
                raise ValueError("Unexpected EOF while reading bulletin station report")
            station_line = station_line.strip()
            data += f"\n{station_line}"

        station.message = data
        stations.append(station)

    return stations


def read_bulletin(path):
    result = JointReport()

    with open(path, "r", encoding="utf-8") as handle:
        header = handle.readline()
        if header == "":
            raise ValueError("Bulletin is empty")

        line2 = handle.readline().strip()
        parts = line2.split(" ")
        if len(parts) < 3:
            raise ValueError("Invalid bulletin header")

        report_time = parts[2]
        result.month_day = report_time[:2]
        result.hour = report_time[2:]

        if handle.readline() == "":
            raise ValueError("Bulletin ended before OMM station block")

        result.omm_stations = _read_bulletin_stations(handle)

        while True:
            next_line = handle.readline()
            if next_line == "":
                raise ValueError("Bulletin ended before national block header")
            if NEWMESSAGEHEADER in next_line:
                break

        if handle.readline() == "":
            raise ValueError("Bulletin missing national header line")
        if handle.readline() == "":
            raise ValueError("Bulletin missing national AAXX line")

        result.national_stations = _read_bulletin_stations(handle)

    return result


@contextlib.contextmanager
def advisory_lock(lock_path: Path, retry_delay_seconds: float = 0.2, timeout_seconds: float = 15.0):
    deadline = time.monotonic() + timeout_seconds
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for lock {lock_path}")
            time.sleep(retry_delay_seconds)

    try:
        os.write(fd, str(os.getpid()).encode("ascii"))
        yield
    finally:
        os.close(fd)
        with contextlib.suppress(FileNotFoundError):
            lock_path.unlink()


def write_bulletin(path, bulletin):
    target = Path(path)
    temp_path = target.with_suffix(f"{target.suffix}.tmp")
    lock_path = target.with_suffix(f"{target.suffix}.lock")

    with advisory_lock(lock_path):
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_path, "w", encoding="utf-8", newline="\r\n") as handle:
            handle.write(str(bulletin))
        os.replace(temp_path, target)


def safe_file_move(file_path, destination_path):
    try:
        path = get_safe_path(destination_path)
        source = Path(file_path)
        destination = path / source.name
        if destination.exists():
            destination.unlink()
        shutil.move(str(source), str(destination))
        return destination
    except Exception as exc:
        logger.error(
            "An error occurred during the movement of %s to %s with error %s",
            file_path,
            destination_path,
            exc,
        )
        return None


def safe_file_copy(file_path, destination_path):
    try:
        path = get_safe_path(destination_path)
        source = Path(file_path)
        destination = path / source.name
        if destination.exists():
            destination.unlink()
        shutil.copy2(str(source), str(destination))
        return destination
    except Exception as exc:
        logger.error(
            "An error occurred during the copy of %s to %s with error %s",
            file_path,
            destination_path,
            exc,
        )
        return None
