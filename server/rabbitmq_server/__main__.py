import pika.channel
from rabbitmq_server.config import (
    get_connection,
    configure_logging
)

import logging
import pika
import aio_pika
import asyncio
import time
import uuid

from proto import msg2_pb2

log = logging.getLogger(__name__)

async def handle_request(channel, message: aio_pika.IncomingMessage):
    try:
        req = msg2_pb2.Request()
        req.ParseFromString(message.body)
        log.info(f"Received {req}")
        
        if req.proccess_time_in_seconds:
            await asyncio.sleep(req.proccess_time_in_seconds)
        
        response = msg2_pb2.Response()
        response.request_id = req.request_id
        response.response = req.request * 2
        
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=response.SerializeToString(),
                correlation_id=req.request_id
            ),
            routing_key=req.return_address
        )
        
        log.info(f"Sent response: {response}")
        await message.ack()
    except Exception as e:
        log.error(f"Error processing message: {e}")
        await message.nack(requeue=False)



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