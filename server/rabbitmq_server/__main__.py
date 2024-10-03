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

from server.rabbitmq_server.proto import msg2_pb2 

log = logging.getLogger(__name__)

async def handle_request(
        channel,
        message: aio_pika.IncomingMessage       
):
    try:
        req = msg2_pb2.Request()
        req.ParseFromString(message.body)
        log.info(f"Received {req}")

        response = msg2_pb2.Response()
        response.request_id = req.request_id
        response.response = req.request * 2

        # this will continued 


async def main():
    configure_logging(level=logging.INFO)
    connection = await aio_pika.connect_robust("amqp://guest:guest@localhost/")
    log.info("Connected to RabbitMQ")

    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue("news")

        await queue.consume(lambda message: asyncio.create_task(handle_request(channel, message)))
    
            

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.warning("BB")