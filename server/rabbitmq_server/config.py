import configparser
import pathlib
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

log = logging.getLogger(__name__)

def load_config(path=None):
    """Загружает конфигурацию из указанного ini-файла."""
    if path is None:
        path = pathlib.Path(__file__).parent.parent.parent / 'client' / 'client_config.ini'

    if not path.exists():
        raise FileNotFoundError(f"Config file {path} not found!")

    config = configparser.ConfigParser()
    config.read(path)

    required_sections = ['rabbitmq', 'logging', 'server', 'client']
    for section in required_sections:
        if section not in config:
            raise KeyError(f"Missing required section '{section}' in config file.")

    rabbitmq_config = config['rabbitmq']
    logging_config = config['logging']
    server_config = config['server']
    client_config = config['client']

    return {
        'rabbitmq': rabbitmq_config,
        'logging': logging_config,
        'server': server_config,
        'client': client_config
    }

def configure_logging(level, log_file):
    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file)
        ]
    )

class ConfigFileHandler(FileSystemEventHandler):
    """Класс для обработки изменений в конфигурационном файле."""
    
    def __init__(self, context, config_path):
        self.context = context
        self.config_path = config_path

    def on_modified(self, event):
        if event.src_path == str(self.config_path):
            log.info(f"Config file {self.config_path} has been modified. Reloading...")
            config = load_config(path=self.config_path)
            self.context.update_config(config)

def start_config_file_monitoring(context, config_path):
    """Запускает мониторинг изменений конфигурационного файла."""
    event_handler = ConfigFileHandler(context, config_path)
    observer = Observer()
    observer.schedule(event_handler, str(config_path.parent), recursive=False)
    observer.start()
    return observer
