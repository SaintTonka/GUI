import pika.channel
from rabbitmq_server.config import (
    get_connection,
    configure_logging
)

import logging
import pika
import time

log = logging.getLogger(__name__)

def produce_msg (channel: pika.channel.Channel):
    queue = channel.queue_declare(queue="news")
    message_body = f"Hello! {time.time()}"
    log.info("Publish: %s", message_body)
    channel.basic_publish(
        exchange="",
        routing_key="news",
        body=message_body,
    )
    log.warning("Published %s", message_body)

def main():
    configure_logging(level=logging.INFO)
    with get_connection() as connection:
        log.info("Start: %s", connection)
        with connection.channel() as channel:
            log.info("New Channel: %s", channel)
            produce_msg(channel=channel)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.warning("BB")