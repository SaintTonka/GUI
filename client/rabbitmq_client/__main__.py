import pika.channel
from server.rabbitmq_server.config import (
    get_connection,
    configure_logging
)

import logging
import pika
import time

log = logging.getLogger(__name__)

def proccess_new_message(
        ch: pika.channel.Channel,
        method,
        properties,
        body: bytes,
):
    log.info("ch: %s", ch)
    log.info("method: %s", method)
    log.info("properties: %s", properties)
    log.info("body: %s", body)
    
    ch.basic_ack(delivery_tag=method.delivery_tag)

    log.warning("Finish %r", body)
    

def consume_messages(channel: pika.channel.Channel) ->None:
    channel.basic_consume(
        queue="news",
        on_message_callback= proccess_new_message,
        auto_ack=False
    )
    log.warning("Waiting")
    channel.start_consuming()
 

def main():
    configure_logging(level=logging.INFO)
    with get_connection() as connection:
        log.info("Start: %s", connection)
        with connection.channel() as channel:
            log.info("New Channel: %s", channel)
            consume_messages(channel=channel)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.warning("BB")