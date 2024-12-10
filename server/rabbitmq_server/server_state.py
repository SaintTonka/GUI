from abc import ABC, abstractmethod
import logging
import aio_pika
import asyncio
import configparser
from pathlib import Path
from rabbitmq_server.proto import msg_serv_pb2
from rabbitmq_server.utils import double_number

log = logging.getLogger(__name__)

config_path = Path(__file__).parent.parent/ 'server_config.ini'

def load_server_config():
    config = configparser.ConfigParser()
    config.read(config_path)
    log.info(f"Loaded server configuration from {config_path}")
    return config

class ServerState(ABC):
    @abstractmethod
    async def handle_request(self, context: 'ServerContext', message: aio_pika.IncomingMessage):
        pass

class ServerContext:
    def __init__(self, channel, config):
        self.channel = channel
        self.config = config
        self.state = None

    def set_state(self, state: ServerState):
        self.state = state

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

                process_time = getattr(req, 'process_time_in_seconds', 0)

                if process_time > 0:
                    log.info(f"Processing request with total delay of {process_time} seconds")
                    await asyncio.sleep(process_time)
                    log.info(f"Finished sleeping for {process_time} seconds")

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
