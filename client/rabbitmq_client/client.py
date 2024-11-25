import os
import sys
import uuid
import configparser
import logging
from PyQt5.QtCore import QObject, pyqtSignal
import pika
import queue
from pathlib import Path
from .proto import msg_client_pb2

class RMQClient(QObject):
    received_response = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    server_ready_signal = pyqtSignal()
    server_unavailable_signal = pyqtSignal()

    def __init__(self, config_file='client_config.ini'):
        super().__init__()
        self.config_file = config_file
        self.load_config()
        self.connection = None
        self.channel = None
        self.send_queue = queue.Queue()
        self._running = True

        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=self.log_level,
            filename=self.log_file,
            filemode='a',
            format='%(asctime)s - %(levelname)s - %(name)s: %(message)s',
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.logger.info("Logging initialized for RMQClient.")

    def load_config(self):
        config = configparser.ConfigParser()

        config_file_path = Path(__file__).parent.parent / self.config_file

        if not config_file_path.exists():
            self.logger.error(f"Config file not found: {config_file_path}")
            return

        config.read(config_file_path)

        if not config.has_section('client'):
            config.add_section('client')

        self.rmq_host = config.get('rabbitmq', 'host', fallback='localhost')
        self.rmq_port = config.getint('rabbitmq', 'port', fallback=5672)
        self.rmq_user = config.get('rabbitmq', 'user', fallback='guest')
        self.rmq_password = config.get('rabbitmq', 'password', fallback='guest')
        self.exchange = config.get('rabbitmq', 'exchange', fallback='bews')

        self.log_level_str = config.get('logging', 'level', fallback='INFO')
        self.log_file = config.get('logging', 'file', fallback='client.log')
        self.log_level = getattr(logging, self.log_level_str.upper(), logging.INFO)

        self.client_uuid = config.get('client', 'uuid', fallback=str(uuid.uuid4()))
        config.set('client', 'uuid', self.client_uuid)
        self.timeout_send = config.getint('client', 'timeout_send', fallback=10)
        self.timeout_request = config.getint('client', 'timeout_request', fallback=10)

        with open(config_file_path, 'w') as configfile:
            config.write(configfile)

        self.client_uuid = self.client_uuid

    def run(self):
        """ Основной цикл клиента. """
        try:
            self.connect_to_rabbitmq()
            self.setup_channel()

            self.server_ready_signal.emit()

            while self._running:
                # Обработка событий RabbitMQ
                self.connection.process_data_events(time_limit=1)

                try:
                    user_input, delay = self.send_queue.get_nowait()
                    self.send_request(user_input, delay)
                except queue.Empty:
                    pass

        except Exception as e:
            self.logger.error(f"Error in client run loop: {e}")
            self.error_signal.emit(str(e))
            self.server_unavailable_signal.emit()
            self._running = False

    def connect_to_rabbitmq(self):
        """ Устанавливает соединение с RabbitMQ. """
        credentials = pika.PlainCredentials(self.rmq_user, self.rmq_password)
        parameters = pika.ConnectionParameters(
            host=self.rmq_host,
            port=self.rmq_port,
            credentials=credentials
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.client_uuid, durable=True, exclusive=True)  # Создаем очередь для ответов
        self.channel.basic_consume(queue=self.client_uuid, on_message_callback=self.on_response, auto_ack=True)

        self.logger.info("Connected to RabbitMQ")

    def setup_channel(self):
        """ Настраивает каналы для отправки и получения сообщений. """
        self.channel.exchange_declare(exchange=self.exchange, exchange_type='direct', durable=True)
        self.logger.info(f"Exchange '{self.exchange}' declared.")

    def send_request(self, user_input, delay):
        """ Отправляет запрос на сервер. """
        try:
            request = msg_client_pb2.Request()
            request.request = int(user_input)  # Запрос (число)
            request.return_address = self.client_uuid
            request.request_id = str(uuid.uuid4())
            request.process_time_in_seconds = delay  # Отправляем задержку

            msg = request.SerializeToString()

            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=self.exchange,
                properties=pika.BasicProperties(
                    reply_to=self.client_uuid,
                    correlation_id=request.request_id
                ),
                body=msg
            )
            self.logger.info(f"Sent request: {user_input} with delay: {delay} sec")
        except Exception as e:
            self.logger.error(f"Error sending request: {e}")
            self.error_signal.emit(f"Error sending request: {e}")

    def on_response(self, ch, method, properties, body):
        """ Обрабатывает ответ от сервера. """
        try:
            response = msg_client_pb2.Response()
            response.ParseFromString(body)

            self.logger.info(f"Received response: {response.response} for request ID: {properties.correlation_id}")
            self.received_response.emit(str(response.response))
        except Exception as e:
            self.logger.error(f"Error processing response: {e}")
            self.error_signal.emit(f"Error processing response: {e}")

    def handle_send_request(self, user_input, delay):
        """ Обрабатывает сигнал на отправку запроса. """
        self.send_queue.put((user_input, delay))
        self.logger.debug(f"Request queued: {user_input} with delay: {delay}")

    def stop(self):
        """ Останавливает клиента. """
        self._running = False
        try:
            if self.connection and self.connection.is_open:
                self.logger.info("Closing RabbitMQ connection...")
                self.connection.close()
        except pika.exceptions.StreamLostError as e:
            self.logger.error(f"Stream connection lost while closing: {e}")
        except Exception as e:
            self.logger.error(f"Error while stopping client: {e}")
        finally:
            self.logger.info("Client stopped successfully.")

    def restart_application(self):
        """ Перезапускает приложение. """
        self.logger.info("Restarting application...")
        self.stop()
        python = sys.executable
        os.execl(python, python, *sys.argv)