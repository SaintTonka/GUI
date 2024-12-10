import configparser
import pathlib
import logging

log = logging.getLogger(__name__)

def load_config(path=None):
    """Загружает конфигурацию из указанного ini-файла."""
    if path is None:
        path = pathlib.Path(__file__).parent.parent / 'server_config.ini' 

    if not path.exists():
        raise FileNotFoundError(f"Config file {path} not found!")

    config = configparser.ConfigParser()
    config.read(path)


    required_sections = ['rabbitmq', 'logging']
    for section in required_sections:
        if section not in config:
            raise KeyError(f"Missing required section '{section}' in config file.")

    rabbitmq_config = config['rabbitmq']
    logging_config = config['logging']

    return {
        'rabbitmq': rabbitmq_config,
        'logging': logging_config
    }

def configure_logging(level='INFO', log_file='Log_File.log'):
    """Настройка логирования для сервера."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file)
        ]
    )
    log.info(f"Logging configured. Level: {level}, Log file: {log_file}")
