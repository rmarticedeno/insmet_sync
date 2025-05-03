import re, shutil, logging
from pathlib import Path
from .constans import END_OF_MESSAGE, NEWMESSAGEHEADER, TERRESTIALREPORTID, END_OF_REPORT
from .joint_report import JointReport
from .station_report import StationReport

logger = logging.getLogger(__name__)

def get_oneline_message(path: str):
    with open(path, 'r') as f:
        lines = f.readlines()

    cleaned_lines = [x.strip() for x in lines]

    message = ' '.join(cleaned_lines)
    message = re.split(END_OF_MESSAGE, message, flags=re.IGNORECASE)[0].strip()
    return message

def read_station_report(path):
    with open(path, 'r') as f:
        data = f.read()
        
        msg = " ".join(data.split())             # quito los espacios múltiples, saltos de línea, etc
        valid = False

        index = msg.find(TERRESTIALREPORTID)                # verifico que el fichero es un mensaje FM12 SYNOP
        if index != -1:
            msg = msg[index:]
            valid = True     
        
        index = msg.find(TERRESTIALREPORTID.lower())                # verifico que el fichero es un mensaje FM12 SYNOP
        if not valid and index != -1:
            msg = msg[index:]
            valid = True                 # quito todo lo que está antes de 'AAXX'
            
        if valid:
            day = msg[5:7]              # día de la observación
            hour = msg[7:9]
            station_id = msg.split(' ')[2]
    
            index = msg.find(END_OF_REPORT)
            if index != -1:
                msg = msg[:index]        # encontré el signo '=', quito las cadenas que hayan a continuación porque no pertenecen al código FM12 SYNOP
            else:                               # no encontré el signo '=', hay un error no fatal y busco la cadena 'NNNN' de fin de mensaje por si faltó el signo '='
                index = msg.find(END_OF_MESSAGE)
                if index != -1:
                    msg = msg[:index]  # encontré la cadena 'NNNN', quito las cadenas que hayan a continuación porque no pertenecen al código FM12 SYNOP

            msg = msg[11:]                      # quito los grupos AAXX YYGGiw al mensaje
            msg = msg + '='                     # agrego '=' al final para cumplir el formato de bloque
            msg = msg.replace(' =', '=')        # quito el espacio delante del signo '='

            return StationReport(station_id, msg, day, hour)
        
        raise Exception(f"{TERRESTIALREPORTID} not found")

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
        while END_OF_REPORT not in stationstr:
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

        # skip start of block
        f.readline()
        # skip AAXX line
        f.readline()

        result.national_stations = read_bulletin_stations(f)

    return result

def write_bulletin(path, bulletin):
    with open(path, '+w', newline='\r\n') as w:
            w.write(str(bulletin))

def get_safe_path(path):
    _path = Path(path)

    if not _path.exists():
        _path.mkdir(parents=True, exist_ok=True)

    return _path

def safe_file_move(file_path, destination_path):
    try:
        path = get_safe_path(destination_path)
        path2 = Path(file_path)
        destination = Path(destination_path) / path2.name
        if destination.exists():
            destination.unlink()
        shutil.move(file_path, path)
    except Exception as e:
        logging.error(f"An error ocurred during the movement of {file_path} to {destination_path} with error {e}")

def safe_file_copy(file_path, destination_path):
    try:
        path = get_safe_path(destination_path)
        path2 = Path(file_path)
        destination = Path(destination_path) / path2.name
        if destination.exists():
            destination.unlink()
        shutil.copy(file_path, path)
    except Exception as e:
        logging.error(f"An error ocurred during the copy of {file_path} to {destination_path} with error {e}")