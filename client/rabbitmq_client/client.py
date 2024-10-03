import pika
import uuid
import asyncio
import aio_pika
from PyQt5.QtCore import pyqtSignal, QObject, QThread
from server.rabbitmq_server.proto import msg_pb2

class Communicate(QObject):
    received_response = pyqtSignal(int)  # Сигнал для передачи ответа в GUI

class RMQClient(QThread):
    def __init__(self, communicate):
        super().__init__()
        self.communicate = communicate
        self.connection = None
        self.channel = None
        self.callback_queue = None
        self.active = False

    async def run(self):
        """Устанавливаем соединение с RabbitMQ и инициализируем канал."""
        
        self.connection = await aio_pika.connect_robust("amqp://guest:guest@localhost/")
        self.channel = await self.connection.channel()

            # Объявляем временную очередь для получения ответов от сервера
        result = await self.channel.declare_queue(exclusive=True)
        self.callback_queue = result.name

            # Начинаем прослушивание ответов от сервера
        await result.consume(self.on_response)

        self.active = True
        self.channel.start_consuming()  # Ожидание ответов
        

    async def send_request(self, user_input):
        """Отправка запроса на сервер"""
        if self.connection is None or not self.active:
            print("Connection is not active")
            return

        # Создаем сообщение Protobuf
        request = msg_pb2.Request()
        request.return_address = self.callback_queue
        request.request_id = str(uuid.uuid4())
        request.request = user_input

        # Сериализация запроса
        message = request.SerializeToString()

        # Отправляем запрос на сервер
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=message,
                reply_to=self.callback_queue,
                correlation_id=request.request_id
            ),
            routing_key="news"
        )

    async def on_response(self, message: aio_pika.IncomingMessage):
        """Обработка ответа с сервера"""
        response = msg_pb2.Response()
        response.ParseFromString(message.body)
        self.received_response.emit(response.response)
        await message.ack()

    async def stop_connection(self):
        """Остановка соединения с RabbitMQ"""
        await self.connection.close()