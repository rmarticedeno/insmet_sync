import logging
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from .processing import MessageProcessor
from .runtime_config import AppConfig


logger = logging.getLogger(__name__)


class EventHandler(FileSystemEventHandler):
    def __init__(self, watcher: "FileSystemWatcher"):
        self.watcher = watcher

    def on_created(self, event):
        if not event.is_directory:
            self.watcher.mark_pending(Path(event.src_path))

    def on_modified(self, event):
        if not event.is_directory:
            self.watcher.mark_pending(Path(event.src_path))


class FileSystemWatcher:
    def __init__(self, path: str | None = None, config: AppConfig | None = None):
        self.config = config or AppConfig.from_env()
        self.processor = MessageProcessor(self.config)
        self.path = Path(path) if path else self.config.incoming_dir
        self.pending_paths: set[Path] = set()
        self.observer = PollingObserver()

    def mark_pending(self, path: Path) -> None:
        if path.is_dir():
            return
        self.pending_paths.add(path)

    def _scan_backlog(self):
        for path in self.path.iterdir():
            if path.is_file():
                self.pending_paths.add(path)

    def main_loop(self):
        event_handler = EventHandler(self)
        self.observer.schedule(event_handler, str(self.path), recursive=False)
        self.observer.daemon = True
        self.observer.start()
        logger.info("Watching %s for incoming FM-12 reports", self.path)

        try:
            while True:
                self._scan_backlog()
                pending = sorted(self.pending_paths)
                self.pending_paths.clear()
                for path in pending:
                    self.processor.process_incoming_path(path)
                time.sleep(self.config.upload_stability_check_interval_seconds)
        except KeyboardInterrupt:
            logger.info("Stopping watcher")
        finally:
            self.observer.stop()
            self.observer.join()
