import logging
import aio_pika
import asyncio
from config import configure_logging
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
        if req.request == "Hi":
            response.response = "Goida"
        else:
            response.response = req.request * 2

        response.request_id = req.request_id

        msg = response.SerializeToString()

        await channel.default_exchange.publish(
            aio_pika.Message(
                body=msg,
                correlation_id=req.request_id
            ),
            routing_key=req.return_address
        )

        log.info(f"Sent response: {response} to {req.return_address}")
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
        queue = await channel.declare_queue("bews")

        # Запуск асинхронного потребления сообщений с обработчиком handle_request
        await queue.consume(lambda message: asyncio.create_task(handle_request(channel, message)))
        log.info(f"Server is listening on queue: {queue.name}")

        # Удерживаем соединение активным
        try:
            while True:
                await asyncio.sleep(3600)  # Удерживаем программу запущенной
        except KeyboardInterrupt:
            log.info("Server shutdown initiated...")

if __name__ == "__main__":
    asyncio.run(main())
