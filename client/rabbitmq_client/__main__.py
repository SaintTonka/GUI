import pika.channel
from server.rabbitmq_server.config import (
    get_connection,
    configure_logging
)
from server.rabbitmq_server.proto import msg_pb2

import logging
import pika
import time
import sys
import threading
import pika
import uuid
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication
from window import Window 

class Communicate(QObject):
    received_response = pyqtSignal(int)

class RMQClient(threading.Thread):
    def __init__(self, communicate, user_input):
        super().__init__()
        self.communicate = communicate
        self.user_input = user_input
        self.connection = None
        self.channel = None
        self.callback_queue = None

    def run(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()

        res = self.channel.queue_declare(queue = 'pp', exclusive=True)
        self.callback_queue = res.method.queue

        self.channel.basic_consume(
            queue = self.callback_queue,
            on_message_callback=self.on_response, 
            auto_ack=True
        )

        self.send_request(self.user_input)

        self.channel.start_consuming()

    def send_request(self,user_input):
        request = msg_pb2.Request
        request.return_address = self.callback_queue
        request.request_id = str(uuid.uuid4)
        request.request = user_input

        message = request.SerializeToString()

        self.channel.basic_publish(
            exchange='',
            routing_key="news",
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=request.request_id
            ),
            body=message
        )

    def on_response(self,ch,metehod, props, body):
        response = msg_pb2.Response()
        response.ParseFromString(body)

        self.communicate.received_response.emit(response.response)

        self.connection.close()

def main():
    # Инициализируем Qt-приложение
    app = QApplication(sys.argv)

    # Создаем объект коммуникации для передачи сигнала между потоками
    communicate = Communicate()

    # Создаем и показываем главное окно (импортируемое из window.py)
    window = Window(communicate)
    window.show()

    # Запуск главного цикла Qt-приложения
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()        