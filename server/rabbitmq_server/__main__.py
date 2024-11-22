import logging
import aio_pika
import asyncio
from .config import configure_logging, load_config
from .proto import msg_serv_pb2
from .utils import double_number

log = logging.getLogger(__name__)

async def handle_request(channel, message: aio_pika.IncomingMessage):
    """ Обрабатывает входящее сообщение от клиента. """
    async with message.process():
        try:
            req = msg_serv_pb2.Request()
            req.ParseFromString(message.body)
            log.info(f"Received Request: ID={req.request_id}, Request={req.request}")

            response = msg_serv_pb2.Response()
            response.request_id = req.request_id
            
            if hasattr(req, 'process_time_in_seconds') and req.process_time_in_seconds > 0:
                log.info(f"Processing request with delay of {req.process_time_in_seconds} seconds")
                await asyncio.sleep(req.process_time_in_seconds)

            if req.request is not None:
                # Удваиваем число и формируем ответ
                doubled_number = double_number(req.request)
                response.response = doubled_number
                log.info(f"Processed request: {req.request} -> Response: {response.response}")
            else:
                response.response = "Invalid request"
                log.error("Received an invalid request.")

            # Отправляем ответ обратно клиенту
            await channel.default_exchange.publish(
                aio_pika.Message(
                body=response.SerializeToString(),  # Сериализация объекта в строку байтов
                correlation_id=req.request_id
            ),
            routing_key=req.return_address
)

        except Exception as e:
            log.error(f"Error processing message: {e}")
            await message.nack(requeue=False)



async def main():
    """ Основная функция сервера """
    config = load_config()
    configure_logging(level=config['logging']['level'], log_file=config['logging']['file'])

    connection_string = f"amqp://{config['rabbitmq']['user']}:{config['rabbitmq']['password']}@{config['rabbitmq']['host']}:{config['rabbitmq']['port']}/"
    connection = await aio_pika.connect_robust(connection_string)
    log.info("Connected to RabbitMQ")

    async with connection:
        channel = await connection.channel()

        exchange = await channel.declare_exchange('bews', aio_pika.ExchangeType.DIRECT, durable=True, auto_delete=False)

        queue = await channel.declare_queue("bews", durable=True, auto_delete= True)

        await queue.bind(exchange, routing_key="bews")

        await queue.consume(lambda message: asyncio.create_task(handle_request(channel, message)))
        log.info(f"Server is listening on queue: {queue.name}")

        try:
            log.info("Server is running. Press Ctrl+C to stop.")
            while True:
                await asyncio.sleep(3600) 
        except KeyboardInterrupt:
            log.info("Server shutdown initiated...")

if __name__ == "__main__":
    asyncio.run(main())




    # configure_logging(level=config['logging']['level'], log_file=config['logging']['file'])

    # connection_string = f"amqp://{config['rabbitmq']['user']}:{config['rabbitmq']['password']}@{config['rabbitmq']['host']}:{config['rabbitmq']['port']}/"
    # connection = await aio_pika.connect_robust(connection_string)
    # log.info("Connected to RabbitMQ")