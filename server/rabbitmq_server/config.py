import configparser
import logging

def configure_logging(level=logging.INFO, log_file='server.log'):
    logging.basicConfig(
        level=level,
        filename=log_file,
        filemode='a',
        format='%(asctime)s - %(levelname)s - %(name)s: %(message)s',
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console = logging.StreamHandler()
    console.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s: %(message)s', "%Y-%m-%d %H:%M:%S")
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

def load_config(config_file='server_config.ini'):
    config = configparser.ConfigParser()
    config.read(config_file)
    
    rmq_host = config.get('rabbitmq', 'host', fallback='localhost')
    rmq_port = config.getint('rabbitmq', 'port', fallback=5672)
    rmq_user = config.get('rabbitmq', 'user', fallback='guest')
    rmq_password = config.get('rabbitmq', 'password', fallback='guest')
    
    log_level_str = config.get('logging', 'level', fallback='INFO')
    log_file = config.get('logging', 'file', fallback='server.log')
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    return {
        'rmq_host': rmq_host,
        'rmq_port': rmq_port,
        'rmq_user': rmq_user,
        'rmq_password': rmq_password,
        'log_level': log_level,
        'log_file': log_file
    }
