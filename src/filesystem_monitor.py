import time, os, logging, time, datetime
from watchdog.observers.polling import PollingObserver 
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from .utils import read_bulletin, read_station_report, write_bulletin, get_safe_path, safe_file_move, safe_file_copy
from .format_message import db_upload
from .joint_report import JointReport

logger = logging.getLogger(__name__)

class EventHandler(FileSystemEventHandler):

    def on_created(self, event):
        # avoid fast reading
        time.sleep(5)
        if not event.is_directory:
            try:
                # for testing purposes ignore WX files
                if event.src_path[-5:-3] == "WX":
                    return
                
                report = Path(event.src_path)
                station_report = read_station_report(report.absolute())
                hour = station_report.hour
                day_of_month = datetime.datetime.now(datetime.timezone.utc).strftime("%d")

                bulletin_path = os.getenv('PROCESSING_FOLDER') or '.'
                target = get_safe_path(bulletin_path) / f'WX.{hour}'

                if not target.exists():
                    logger.info(f"Bulletin not found {target} while processing {report.name}")
                    

                    bulletin = JointReport(month_day=day_of_month, hour=hour)
                    write_bulletin(target, bulletin)
                    #safe_file_move(event.src_path, os.getenv('INVALID_PROCESSED_REPORTS'))
                    return
                
                bulletin = read_bulletin(target.absolute())

                if bulletin.month_day != day_of_month:
                    target.unlink()
                    bulletin = JointReport(month_day=day_of_month, hour=hour)
                    write_bulletin(target, bulletin)
                    bulletin = read_bulletin(target.absolute())
            
                if bulletin.month_day != station_report.day:
                    safe_file_move(event.src_path, os.getenv('INVALID_PROCESSED_REPORTS'))
                    logger.error(f"station report out of date, expected: {bulletin.month_day} recieved {station_report.day} while processing {report.name}")
                    return

                bulletin.update(station_report)
                target.unlink()
                write_bulletin(target.absolute(), bulletin)
                
                safe_file_copy(target.absolute(), os.getenv('BULLETIN_DATA'))
                safe_file_move(event.src_path, os.getenv('REPORT_BACKUP_DATA'))

                if len(os.getenv('DESTINATION_FOLDER') or "") > 0:     
                    safe_file_copy(target.absolute(), os.getenv('DESTINATION_FOLDER'))

                logger.info(f"Bulletin {target.name} Updated with {report.name}")

                db_upload(station_report.get_full_msg())

                logger.info(f"DB updated with {report.name}")
            except Exception as e:
                logger.error(f"An error ocurred during the processing of {report.name} report, {e}")
                safe_file_move(event.src_path, os.getenv('INVALID_PROCESSED_REPORTS'))

class FileSystemWatcher:

    def __init__(self, path: str):
        self.watcher = PollingObserver()
        get_safe_path(path)
        self.path = path

    def main_loop(self):
        count = 0
        while True:
            event_handler = EventHandler()
            self.watcher.schedule(event_handler, self.path)
            self.watcher.daemon = True
            self.watcher.start()
            try:
                while True:
                    time.sleep(5)
            except Exception as e:
                self.watcher.stop()
                time.sleep(2**count * 10)
                logger.error(f"Watcher Stopped with error{e}")
                count +=1
            finally:
                if count == 5:
                    break
        


