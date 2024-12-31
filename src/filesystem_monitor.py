import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class EventHandler(FileSystemEventHandler):
    
    @staticmethod
    def on_created(self, event):
        print(f"File created: {event.src_path}")

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

