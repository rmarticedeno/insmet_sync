import os
from src import FileSystemWatcher

watch = FileSystemWatcher(os.getenv('FTP_DATA') or '.')
watch.main_loop()