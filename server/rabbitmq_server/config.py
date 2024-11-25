import configparser
import pathlib
import logging

def load_config(path=None):
    """Загружает конфигурацию из указанного ini-файла."""
    if path is None:
        path = pathlib.Path(__file__).parent.parent.parent / 'client' / 'rabbitmq_client' / 'client_config.ini'

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
