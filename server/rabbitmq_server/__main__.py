import logging
import aio_pika
import asyncio
from config import configure_logging, load_config
from proto import msg_serv_pb2  

log = logging.getLogger(__name__)

async def handle_request(channel, message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            req = msg_serv_pb2.Request()
            req.ParseFromString(message.body)
            log.info(f"Received Request: ID={req.request_id}, Request={req.request}, Return Address={req.return_address}")

            response = msg_serv_pb2.Response()
            response.request_id = req.request_id

            if req.request == "Hi":
                response.response = "Hello"  # Код готовности сервера
                log.info(f"Sent response: {response.response} (Server Ready) to {req.return_address}")
            else:
                if req.HasField("proccess_time_in_seconds") and req.proccess_time_in_seconds > 0:
                    log.info(f"Processing request for {req.proccess_time_in_seconds} seconds")
                    await asyncio.sleep(req.proccess_time_in_seconds)

                response.response = str(int(req.request) * 2)  # Преобразуем ответ в строку
                log.info(f"Sent response: {response.response} to {req.return_address}")

            msg = response.SerializeToString()

            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=msg,
                    correlation_id=req.request_id
                ),
                routing_key=req.return_address  # Отправляем на callback очередь клиента
            )
        except Exception as e:
            log.error(f"Error processing message: {e}")
            await message.nack(requeue=False)

async def main():
    config = load_config()
    configure_logging(level=config['log_level'], log_file=config['log_file'])
    connection_string = f"amqp://{config['rmq_user']}:{config['rmq_password']}@{config['rmq_host']}:{config['rmq_port']}/"
    connection = await aio_pika.connect_robust(connection_string)
    log.info("Connected to RabbitMQ")

    async with connection:
        channel = await connection.channel()
        
        # Объявляем Exchange 'bews' типа 'direct'
        exchange = await channel.declare_exchange("bews", aio_pika.ExchangeType.DIRECT, durable=True)
        
        # Объявляем очередь 'bews'
        queue = await channel.declare_queue("bews", durable=True)
        
        # Привязываем очередь 'bews' к Exchange 'bews' с routing_key 'bews'
        await queue.bind(exchange, routing_key="bews")

        await queue.consume(lambda message: asyncio.create_task(handle_request(channel, message)))
        log.info(f"Server is listening on queue: {queue.name}")

        try:
            while True:
                await asyncio.sleep(3600) 
        except KeyboardInterrupt:
            log.info("Server shutdown initiated...")

if __name__ == "__main__":
    asyncio.run(main())
