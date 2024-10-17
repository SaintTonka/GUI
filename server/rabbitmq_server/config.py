import pika
import logging

RMQ_HOST = "localhost"
RMQ_PORT = 5672
RMQ_USER = "guest"
RMQ_PASSWORD = "guest"

connection_params = pika.ConnectionParameters(
    host=RMQ_HOST,
    port=RMQ_PORT,
    credentials=pika.PlainCredentials(RMQ_USER, RMQ_PASSWORD)
)


def configure_logging(level:int = logging.INFO):
    logging.basicConfig(
        level = level,
        datefmt="%Y-%m-%d %H-%M-%S",
        format='%(asctime)s - %(levelname)s - %(name)s: %(message)s'
    )
