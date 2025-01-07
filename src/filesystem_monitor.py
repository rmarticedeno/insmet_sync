import time, os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
from pathlib import Path
from .utils import read_bulletin, read_station_report, write_bulletin

class EventHandler(FileSystemEventHandler):
    
    @staticmethod
    def on_created(event):
        print(event)
        if not event.is_directory:
            report = Path(event.src_path)
            hour = report.name[-2:]

            bulletin_path = os.getenv('BULLETIN_DATA') or '.'
            target = Path(bulletin_path) / f'WX.{hour}'

            if not target.exists():
                print(f"Bulletin not found {target}")
                return
            
            bulletin = read_bulletin(target.absolute())
            station_report = read_station_report(report.absolute())

            bulletin.update(station_report)

            target.unlink()

            write_bulletin(target.absolute(), bulletin)
            print(f"Bulletin {target.name} Updated with {report.name}")

class FileSystemWatcher:

    def __init__(self, path: str):
        self.watcher = Observer()
        self.path = path

    def main_loop(self):
        event_handler = EventHandler()
        self.watcher.schedule(event_handler, self.path, recursive = True)
        self.watcher.start()
        try:
            while True:
                time.sleep(5)
        except:
            self.watcher.stop()
            print("Watcher Stopped")
 
        self.watcher.join()

