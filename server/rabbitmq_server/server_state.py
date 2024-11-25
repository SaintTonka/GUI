from abc import ABC, abstractmethod
import logging
import asyncio
import aio_pika
from .proto import msg_serv_pb2
from .utils import double_number

log = logging.getLogger(__name__)

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
        """Обрабатывает входящее сообщение от клиента."""
        async with message.process():
            try:
                req = msg_serv_pb2.Request()
                req.ParseFromString(message.body)
                log.info(f"Received Request: ID={req.request_id}, Request={req.request}")

                response = msg_serv_pb2.Response()
                response.request_id = req.request_id

                timeout_response = int(context.config['server'].get('timeout_response', fallback=0))

                if hasattr(req, 'process_time_in_seconds') and req.process_time_in_seconds > 0:
                    log.info(f"Processing request with delay of {req.process_time_in_seconds} seconds")
                    await asyncio.sleep(req.process_time_in_seconds + timeout_response)

                if req.request is not None:
                    doubled_number = double_number(req.request)
                    response.response = doubled_number
                    log.info(f"Processed request: {req.request} -> Response: {response.response}")
                else:
                    response.response = "Invalid request"
                    log.error("Received an invalid request.")

                await context.channel.default_exchange.publish(
                    aio_pika.Message(
                        body=response.SerializeToString(),
                        correlation_id=req.request_id
                    ),
                    routing_key=req.return_address
                )

            except Exception as e:
                log.error(f"Error processing message: {e}")
                await message.nack(requeue=False)
