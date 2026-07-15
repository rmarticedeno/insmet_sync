import logging

from src import FileSystemWatcher
from src.runtime_config import AppConfig

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        logging.StreamHandler()
    ]
)

config = AppConfig.from_env()
config.ensure_directories()
watch = FileSystemWatcher(str(config.incoming_dir), config=config)
watch.main_loop()
