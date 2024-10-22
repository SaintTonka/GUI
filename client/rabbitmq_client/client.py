import uuid
import configparser
import logging
import os
from PyQt5.QtCore import pyqtSignal, QObject, QThread
import pika
from proto import msg3_pb2

class Communicate(QObject):
    """
    Класс для создания сигналов, используемых для связи между компонентами.
    """
    received_response = pyqtSignal(int)
    send_request = pyqtSignal(int)
    error_signal = pyqtSignal(str)
    server_ready_signal = pyqtSignal()

class RMQClient(QThread):
    def __init__(self, communicate, config_file='client_config.ini'):
        super().__init__()
        self.communicate = communicate
        self.config_file = config_file
        self.load_config()
        self.connection = None
        self.channel = None
        self.callback_queue = None
        self.active = False
        self.check_server = False
        self._running = True

        self.communicate.send_request.connect(self.handle_send_request)

    def load_config(self):
        config = configparser.ConfigParser()
        config.read(self.config_file)
        
        self.rmq_host = config.get('rabbitmq', 'host', fallback='localhost')
        self.rmq_port = config.getint('rabbitmq', 'port', fallback=5672)
        self.rmq_user = config.get('rabbitmq', 'user', fallback='guest')
        self.rmq_password = config.get('rabbitmq', 'password', fallback='guest')
        self.exchange = config.get('rabbitmq', 'exchange', fallback='bews')
        
        self.log_level_str = config.get('logging', 'level', fallback='INFO')
        self.log_file = config.get('logging', 'file', fallback='client.log')
        self.log_level = getattr(logging, self.log_level_str.upper(), logging.INFO)

        logging.basicConfig(
            level=self.log_level,
            filename=self.log_file,
            filemode='a',
            format='%(asctime)s - %(levelname)s - %(name)s: %(message)s',
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.logger = logging.getLogger(__name__)

        if not config.has_section('client'):
            config.add_section('client')

        if config.has_option('client', 'uuid') and config.get('client', 'uuid'):
            self.client_uuid = config.get('client', 'uuid')
        else:
            self.client_uuid = str(uuid.uuid4())
            config.set('client', 'uuid', self.client_uuid)
            with open(self.config_file, 'w') as configfile:
                config.write(configfile)
            self.logger.info(f"Generated new UUID for client: {self.client_uuid}")

        self.timeout_send = config.getint('client', 'timeout_send', fallback=5)
        self.timeout_response = config.getint('client', 'timeout_response', fallback=10)

    def run(self):
        try:
            credentials = pika.PlainCredentials(self.rmq_user, self.rmq_password)
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.rmq_host,
                    port=self.rmq_port,
                    credentials=credentials
                )
            )
            self.channel = self.connection.channel()

            self.channel.exchange_declare(exchange=self.exchange, exchange_type='direct', durable=True)

            result = self.channel.queue_declare(queue='', exclusive=True)
            self.callback_queue = result.method.queue

            self.channel.queue_bind(exchange=self.exchange, queue=self.callback_queue)

            self.channel.basic_consume(
                queue=self.callback_queue,
                on_message_callback=self.on_response,
                auto_ack=True
            )

            self.active = True
            self.logger.info(f"Connected to RabbitMQ and listening on queue: {self.callback_queue}")

            while self._running:
                if not self.check_server:
                    self.send_hi_to_serv()
                try:
                    self.connection.process_data_events(time_limit=1)
                except pika.exceptions.AMQPError as e:
                    self.logger.error(f"AMQP Error: {e}")
                    self.communicate.error_signal.emit(f"AMQP Error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to connect to RabbitMQ: {e}")
            self.communicate.error_signal.emit(f"Failed to connect to RabbitMQ: {e}")
            self.active = False

    def send_hi_to_serv(self):
        try:
            request = msg3_pb2.Request()
            request.return_address = self.callback_queue
            request.request_id = str(uuid.uuid4())
            request.request = 0  

            msg = request.SerializeToString()

            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=self.exchange,  
                properties=pika.BasicProperties(
                    reply_to=self.callback_queue,
                    correlation_id=request.request_id
                ),
                body=msg
            )
            self.logger.info("Sent 'Hi' to server for readiness check.")
        except Exception as e:
            self.logger.error(f"Error sending 'Hi': {e}")
            self.communicate.error_signal.emit(f"Error sending 'Hi': {e}")

    def handle_send_request(self, user_input):
        if not self.active:
            self.logger.error("Connection is not active.")
            self.communicate.error_signal.emit("Connection is not active.")
            return

        try:
            request = msg3_pb2.Request()
            request.return_address = self.callback_queue
            request.request_id = str(uuid.uuid4())
            request.request = int(user_input)

            msg = request.SerializeToString()

            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=self.exchange,
                properties=pika.BasicProperties(
                    reply_to=self.callback_queue,
                    correlation_id=request.request_id
                ),
                body=msg
            )
            self.logger.info(f"Sent request: {user_input}")
        except Exception as e:
            self.logger.error(f"Error sending request: {e}")
            self.communicate.error_signal.emit(f"Error sending request: {e}")

    def on_response(self, ch, method, props, body):
        try:
            response = msg3_pb2.Response()
            response.ParseFromString(body)
            self.logger.info(f"Received response: {response.response} for request ID: {response.request_id}")

            if response.response == 1 and not self.check_server:
                self.check_server = True
                self.communicate.server_ready_signal.emit()
                self.logger.info("Server is ready.")
            else:
                self.communicate.received_response.emit(response.response)
        except Exception as e:
            self.logger.error(f"Error processing response: {e}")
            self.communicate.error_signal.emit(f"Error processing response: {e}")

    def stop_client(self):
        self._running = False
        try:
            if self.connection and self.connection.is_open:
                self.connection.close()
                self.logger.info("Connection to RabbitMQ closed.")
        except Exception as e:
            self.logger.error(f"Error closing connection: {e}")
        self.quit()
        self.wait()
