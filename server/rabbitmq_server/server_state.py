from abc import ABC, abstractmethod
import logging
import aio_pika
import asyncio
import configparser
from pathlib import Path
from rabbitmq_server.proto import msg_serv_pb2
from rabbitmq_server.utils import double_number
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

log = logging.getLogger(__name__)

config_path = Path(__file__).parent.parent.parent / 'client' / 'client_config.ini'

def load_server_config():
    config = configparser.ConfigParser()
    config.read(config_path)
    log.info(f"Loaded server configuration from {config_path}")
    return config

class ConfigChangeHandler(FileSystemEventHandler):
    def __init__(self, context):
        super().__init__()
        self.context = context

    def on_modified(self, event):
        if Path(event.src_path) == config_path:
            log.info("Config file modified. Reloading configuration.")
            self.context.update_config()

class ServerState(ABC):
    @abstractmethod
    async def handle_request(self, context: 'ServerContext', message: aio_pika.IncomingMessage):
        pass

class ServerContext:
    def __init__(self, channel, config):
        self.channel = channel
        self.config = config
        self.state = None
        self.observer = Observer()
        self.event_handler = ConfigChangeHandler(self)
        self.start_watchdog()

    def set_state(self, state: ServerState):
        self.state = state

    def start_watchdog(self):
        """Запуск наблюдателя за конфигурационным файлом."""
        self.observer.schedule(self.event_handler, str(config_path.parent), recursive=False)
        self.observer.start()
        log.info(f"Started watchdog on {config_path.parent}")

    def stop_watchdog(self):
        """Остановка наблюдателя."""
        self.observer.stop()
        self.observer.join()

    def update_config(self):
        """Метод для обновления конфигурации сервера."""
        self.config = load_server_config()
        log.info("Server configuration updated.")
        timeout_response = self.config['server'].get('timeout_response', fallback='0')
        log.info(f"New timeout_response: {timeout_response} сек.")

    async def handle_request(self, message: aio_pika.IncomingMessage):
        if self.state is not None:
            await self.state.handle_request(self, message)
        else:
            log.error("State is not set.")

class WaitingState(ServerState):
    async def handle_request(self, context: ServerContext, message: aio_pika.IncomingMessage):
        """Обрабатывает входящее сообщение от клиента с учетом актуальной конфигурации."""
        async with message.process():
            try:
                req = msg_serv_pb2.Request()
                req.ParseFromString(message.body)
                log.info(f"Received Request: ID={req.request_id}, Request={req.request}")

                response = msg_serv_pb2.Response()
                response.request_id = req.request_id

                # Получаем значение тайм-аута для ответа от сервера из конфигурации
                timeout_response_str = context.config['server'].get('timeout_response', fallback='0')
                try:
                    timeout_response = int(timeout_response_str)
                except ValueError:
                    log.error(f"Invalid timeout_response value: {timeout_response_str}. Using 0.")
                    timeout_response = 0
                log.info(f"timeout_response: {timeout_response} сек.")

                # Получаем значение process_time_in_seconds из запроса
                process_time = getattr(req, 'process_time_in_seconds', 0)
                log.info(f"process_time_in_seconds: {process_time} сек.")

                # Вычисляем общее время задержки
                sleep_time = timeout_response + process_time
                log.info(f"Total sleep_time: {sleep_time} сек.")

                if sleep_time > 0:
                    log.info(f"Processing request with total delay of {sleep_time} seconds")
                    await asyncio.sleep(sleep_time)
                    log.info(f"Finished sleeping for {sleep_time} seconds")

                # Обработка запроса
                if req.request is not None:
                    doubled_number = double_number(req.request)
                    response.response = doubled_number
                    log.info(f"Processed request: {req.request} -> Response: {response.response}")
                else:
                    response.response = "Invalid request"
                    log.error("Received an invalid request.")

                # Отправляем ответ
                await context.channel.default_exchange.publish(
                    aio_pika.Message(
                        body=response.SerializeToString(),
                        correlation_id=req.request_id
                    ),
                    routing_key=req.return_address
                )
                log.info(f"Sent response for Request ID={req.request_id}")

            except Exception as e:
                log.error(f"Error processing message: {e}")
                await message.nack(requeue=False)
