import logging
import aio_pika
import asyncio
from pathlib import Path
from rabbitmq_server.server_state import ServerContext, WaitingState, load_server_config
from rabbitmq_server.config import configure_logging

log = logging.getLogger(__name__)

async def main():
    """Основная функция сервера"""

    config = load_server_config()
    configure_logging(level=config['logging']['level'], log_file=config['logging']['file'])

    rabbit_config = config['rabbitmq']
    connection_string = (
        f"amqp://{rabbit_config['user']}:{rabbit_config['password']}"
        f"@{rabbit_config['host']}:{rabbit_config['port']}/"
    )

    connection = await aio_pika.connect_robust(connection_string)
    log.info("Connected to RabbitMQ")

    async with connection:
        channel = await connection.channel()

        # Настройка контекста сервера
        context = ServerContext(channel, config)
        context.set_state(WaitingState())

        exchange = await channel.declare_exchange(
            rabbit_config['exchange'],
            aio_pika.ExchangeType.DIRECT,
            durable=True,
            auto_delete=False
        )
        log.info(f"Exchange '{rabbit_config['exchange']}' declared.")

        queue = await channel.declare_queue(
            rabbit_config['exchange'],
            durable=True,
            auto_delete=True
        )

        await queue.bind(exchange, routing_key=rabbit_config['exchange'])

        await queue.consume(lambda message: asyncio.create_task(context.handle_request(message)))
        log.info(f"Server is listening on queue: {queue.name}")

        try:
            log.info("Server is running. Press Ctrl+C to stop.")
            while True:
                await asyncio.sleep(3600)
        except KeyboardInterrupt:
            log.info("Server shutdown initiated...")

if __name__ == "__main__":
    asyncio.run(main())
