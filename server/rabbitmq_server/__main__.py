import pika.channel
from rabbitmq_server.config import (
    get_connection,
    configure_logging
)

import logging
import pika
import aio_pika
import time
import uuid

log = logging.getLogger(__name__)

async def handle_request(
        channel,
        message: aio_pika.IncomingMessage       
):
    try:
        req = request_response_pb2.Request()
        req.ParseFromString(message.body)
        log.info(f"Received {req}")

        response = request_response_pb2.Response()
        # this will continued 


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