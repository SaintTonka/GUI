import uuid
import asyncio
import aio_pika
from aio_pika.abc import AbstractIncomingMessage
import sys
from PyQt5.QtCore import pyqtSignal, QObject, QThread
from proto import msg3_pb2

class Communicate(QObject):
    """
    Класс для создания сигналов, используемых для связи между компонентами.
    """
    received_response = pyqtSignal(int)  
    send_request = pyqtSignal(int)
    error_sygnal = pyqtSignal(str)


class RMQClient(QThread):
    """
    Основной класс клиента для взаимодействия с RabbitMQ.
    """
    def __init__(self, communicate):
        super().__init__()
        self.communicate = communicate
        self.connection = None
        self.channel = None
        self.callback_queue = None
        self.active = False

        self.check_server = False

        # Подключение сигнала к методу отправки запроса
        self.communicate.send_request.connect(self.handle_send_request)
        print("Client was connected")

    async def connect(self):
        """
        Асинхронное подключение к RabbitMQ и настройка канала.
        """
        try:
            self.connection = await aio_pika.connect_robust(f"amqp://guest:guest@localhost/")
            self.channel = await self.connection.channel()

            # Объявляем временную очередь для получения ответов от сервера
            result = await self.channel.declare_queue(exclusive=True)
            self.callback_queue = result.name

            # Начинаем прослушивание ответов от сервера
            await result.consume(self.on_response)

            self.active = True
            print(f"Connected to RabbitMQ and listening on queue: {self.callback_queue}")
        except Exception as e:
            print(f"Failed to connect to RabbitMQ: {e}")
            self.active = False

    async def test_connection(self, result):
        """
        Проверка подключения.
        """
        try:

            test_request = msg3_pb2.Request()
            test_request.return_address = self.callback_queue
            test_request.request_id = str(uuid.uuid4())
            test_request.request = "Hi"

            msg = test_request.SerializeToString()
            
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=msg,
                    reply_to=self.callback_queue,
                    correlation_id=test_request.request_id
                ),
                routing_key="bews"
            )
            print("Test request was sent")
            
            return True
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            
            return False

    
    async def send_request(self, user_input):
        """
        Отправка запроса на сервер с заданным числом.
        """
        if self.connection is None or not self.active:
            print("Connection is not active")
            await self.reconnect()
            return
        
        if not await self.test_connection():
            print ("Server connection is not active")
            await self.reconnect()
            return

        print("Request is ready to be sent")

        request = msg3_pb2.Request()
        request.return_address = self.callback_queue
        request.request_id = str(uuid.uuid4())
        request.request = user_input
        
        msg = request.SerializeToString()

        print(f"request: {request.request_id}")
        
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=msg,
                reply_to=self.callback_queue,
                correlation_id=request.request_id
            ),
            routing_key="bews"
        )
        print("Request was sent")

    async def on_response(self, message: aio_pika.IncomingMessage):
        """
        Обработка ответа с сервера.
        """
        print("Message received from server...")  
        try:
            response = msg3_pb2.Response()
            response.ParseFromString(message.body)

            print(f"Parsed response: {response}")

            if response.response == "Goida": 

                self.communicate.received_response.emit(response.response)
                self.check_server = True

            elif response.isdigit() == False and response.response != "Goida":
                
                self.check_server = False
                await self.reconnect  
        
            else:
                self.communicate.received_response.emit(response.response)    
            
            print(f"Emitted signal with response: {response.response}")
        
        except Exception as e:
            
            print(f"Failed to parse response: {e}")
            await message.nack(requeue=False)

    async def stop_connection(self):
        """
        Остановка соединения с RabbitMQ.
        """
        if self.connection:
            print("Waiting for task")
            await self.connection.close()
            self.active = False
            print("Connection closed")

    def run(self):
        """
        Этот метод запускается, когда поток стартует.
        Мы создаем новый event loop и запускаем его, чтобы обрабатывать задачи асинхронно.
        """
        self.loop = asyncio.new_event_loop()  
        asyncio.set_event_loop(self.loop)     
        self.loop.run_until_complete(self.connect())  
        self.loop.run_forever() 

    def handle_send_request(self, user_input):
        """Обработчик для отправки запроса на сервер"""
        loop = asyncio.get_event_loop()
        if user_input == "":
            return
        asyncio.run_coroutine_threadsafe(self.send_request(user_input), self.loop)

    async def reconnect(self):
        try : 
            while not self.active:
                await self.connect()
        except Exception as e:
            print("Server error")
    

