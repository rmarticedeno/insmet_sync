import os
from src import FileSystemWatcher

watch = FileSystemWatcher(os.getenv('REPORT_DATA') or '.')
watch.main_loop()