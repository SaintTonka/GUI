import configparser
import pathlib
import logging

def load_config():
    config_path = pathlib.Path(__file__).parent.parent.parent / 'client' / 'client_config.ini'

    if not config_path.exists():
        raise FileNotFoundError(f"Config file {config_path} not found!")

    config = configparser.ConfigParser()
    config.read(config_path)

    rabbitmq_config = config['rabbitmq']
    logging_config = config['logging']
    client_config = config['client']

    return {
        'rabbitmq': rabbitmq_config,
        'logging': logging_config,
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

