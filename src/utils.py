import re
from pathlib import Path
from .constans import END_OF_MESSAGE, NEWMESSAGEHEADER
from .joint_report import JointReport
from .station_report import StationReport

def get_oneline_message(path: str):
    with open(path, 'r') as f:
        lines = f.readlines()

    cleaned_lines = [x.strip() for x in lines]

    message = ' '.join(cleaned_lines)
    message = re.split(END_OF_MESSAGE, message, flags=re.IGNORECASE)[0].strip()
    return message

def read_bulletin_stations(f):
    stations = []

    while True:
        stationstr = f.readline().strip()

        if len(stationstr) == 0:
            break    

        station_id = stationstr.split(' ')[0]
        station = StationReport(station_id)

        if 'nil' in stationstr:
            stations.append(station)
            continue

        data = stationstr
        while '=' not in stationstr:
            stationstr = f.readline().strip()
            data += f'\n{stationstr}'

        station.message = data
        stations.append(station)

    return stations

def read_bulletin(path):
    result = JointReport()

    with open(path, 'r') as f:
        # skip line 1
        f.readline()
        line2 = f.readline().strip()
        report_time = line2.split(' ')[2]
        result.month_day = report_time[:2]
        result.hour = report_time[2:]
        # skip line 3
        f.readline()

        result.omm_stations = read_bulletin_stations(f)

        # skip lines until next report
        next_line = f.readline()
        while NEWMESSAGEHEADER not in next_line:
            next_line = f.readline()

        result.national_stations = read_bulletin_stations(f)

    return result

def write_bulletin(path, bulletin):
    destination = Path(path) / f'WX.{bulletin.hour[:2]}'
    with open(destination, '+w', newline='\r\n') as w:
            w.write(str(bulletin))