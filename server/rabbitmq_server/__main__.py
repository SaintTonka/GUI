# server/rabbitmq_server/__main__.py

import logging
import aio_pika
import asyncio
from pathlib import Path
from .config import configure_logging, load_config
from .server_state import ServerContext, WaitingState

log = logging.getLogger(__name__)

async def main():
    """Основная функция сервера"""
    config_path = Path(__file__).parent.parent.parent / 'client' / 'client_config.ini'
    log.info(f"Config path: {config_path}")

    config = load_config(path=config_path)
    configure_logging(level=config['logging']['level'], log_file=config['logging']['file'])

    rabbit_config = config['rabbitmq']
    connection_string = (
        f"amqp://{rabbit_config['user']}:{rabbit_config['password']}"
        f"@{rabbit_config['host']}:{rabbit_config['port']}/"
    )

    connection = await aio_pika.connect_robust(connection_string)
    log.info("Connected to RabbitMQ")

    async with connection:
        # Инициализация канала
        channel = await connection.channel()

        # Настройка контекста сервера
        context = ServerContext(channel, config)
        context.set_state(WaitingState())

        # Объявление обмена (exchange)
        exchange = await channel.declare_exchange(
            'bews',
            aio_pika.ExchangeType.DIRECT,
            durable=True,
            auto_delete=False
        )

        # Объявление очереди (queue)
        queue = await channel.declare_queue(
            "bews",
            durable=True,
            auto_delete=True
        )

        # Привязка очереди к обмену
        await queue.bind(exchange, routing_key="bews")

        # Начало потребления сообщений
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
