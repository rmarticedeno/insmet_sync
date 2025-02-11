import os, logging
from src import FileSystemWatcher

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        logging.StreamHandler()
    ]
)

watch = FileSystemWatcher(os.getenv('REPORT_DATA') or '.')
watch.main_loop()