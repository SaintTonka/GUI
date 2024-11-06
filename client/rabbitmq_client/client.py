import uuid
import configparser
import logging
from PyQt5.QtCore import pyqtSignal, QObject, QThread
import pika
import queue
from proto import msg_client_pb2
import time

class Communicate(QObject):
    """
    Class for creating signals used for communication between components.
    """
    received_response = pyqtSignal(str)
    send_request = pyqtSignal(str, float)
    error_signal = pyqtSignal(str)
    server_ready_signal = pyqtSignal()
    server_unavailable_signal = pyqtSignal()

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

        self.send_queue = queue.Queue()

        self.communicate.send_request.connect(self.handle_send_request)

        self.heartbeat_interval = 10 
        self.last_heartbeat = time.time()
        self.last_pong_received = time.time()
        self.heartbeat_timeout = 2 * self.heartbeat_interval  
        self.server_available = False
        self.server_ready = False  

    def load_config(self):
        config = configparser.ConfigParser()
        config.read(self.config_file)

        self.rmq_host = config.get('rabbitmq', 'host')
        self.rmq_port = config.getint('rabbitmq', 'port')
        self.rmq_user = config.get('rabbitmq', 'user')
        self.rmq_password = config.get('rabbitmq', 'password')
        self.exchange = config.get('rabbitmq', 'exchange')

        self.log_level_str = config.get('logging', 'level')
        self.log_file = config.get('logging', 'file')
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

        self.timeout_send = config.getint('client', 'timeout_send')
        self.timeout_response = config.getint('client', 'timeout_response')

    def run(self):
        try:
            credentials = pika.PlainCredentials(self.rmq_user, self.rmq_password)
            parameters = pika.ConnectionParameters(
                host=self.rmq_host,
                port=self.rmq_port,
                credentials=credentials,
                heartbeat=self.heartbeat_interval,
                blocked_connection_timeout=5
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            self.channel.exchange_declare(exchange=self.exchange, exchange_type='direct', durable=True)

            result = self.channel.queue_declare(queue='', exclusive=True)
            self.callback_queue = result.method.queue

            self.channel.basic_consume(
                queue=self.callback_queue,
                on_message_callback=self.on_response,
                auto_ack=True
            )

            self.active = True
            self.logger.info(f"Connected to RabbitMQ and listening on queue: {self.callback_queue}")

            self.send_hi_to_serv()  

            while self._running:
                try:
                    self.connection.process_data_events(time_limit=1)
                    current_time = time.time()

                    if current_time - self.last_heartbeat >= self.heartbeat_interval:
                        self.send_hi_to_serv()
                        self.last_heartbeat = current_time

                    if self.server_available and (current_time - self.last_pong_received) > self.heartbeat_timeout:
                        self.logger.warning("Server heartbeat timed out. Server is considered unavailable.")
                        self.server_available = False
                        self.server_ready = False
                        self.communicate.server_unavailable_signal.emit()

                    if self.connection.is_closed:
                        self.logger.warning("Connection to RabbitMQ is closed.")
                        self.communicate.error_signal.emit("Connection to RabbitMQ is closed.")
                        self.server_available = False
                        self.server_ready = False
                        self.communicate.server_unavailable_signal.emit()
                        self._running = False
                        break

                    try:
                        user_input, delay = self.send_queue.get_nowait()
                        self._send_request(user_input, delay)
                    except queue.Empty:
                        pass

                except pika.exceptions.AMQPError as e:
                    self.logger.error(f"AMQP Error: {e}")
                    self.communicate.error_signal.emit(f"AMQP Error: {e}")
                    self.server_available = False
                    self.server_ready = False
                    self.communicate.server_unavailable_signal.emit()
                    self._running = False
                except Exception as e:
                    self.logger.error(f"Unexpected error: {e}")
                    self.communicate.error_signal.emit(f"Unexpected error: {e}")
                    self.server_available = False
                    self.server_ready = False
                    self.communicate.server_unavailable_signal.emit()
                    self._running = False
        except Exception as e:
            self.logger.error(f"Failed to connect to RabbitMQ: {e}")
            self.communicate.error_signal.emit(f"Failed to connect to RabbitMQ: {e}")
            self.active = False

    def send_hi_to_serv(self):
        try:
            request = msg_client_pb2.Request()
            request.return_address = self.callback_queue
            request.request_id = str(uuid.uuid4())
            request.request = "PING" 

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
            self.logger.info("Sent heartbeat message 'PING' to server.")
        except Exception as e:
            self.logger.error(f"Error sending heartbeat: {e}")
            self.communicate.error_signal.emit(f"Error sending heartbeat: {e}")
            self.server_available = False
            self.server_ready = False
            self.communicate.server_unavailable_signal.emit()

    def _send_request(self, user_input, delay):
        try:
            request = msg_client_pb2.Request()
            request.return_address = self.callback_queue
            request.request_id = str(uuid.uuid4())
            request.request = str(user_input)
            if delay > 0:
                request.proccess_time_in_seconds = int(delay)

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
            self.logger.info(f"Sent request: {user_input} with delay: {delay} sec")
        except Exception as e:
            self.logger.error(f"Error sending request: {e}")
            self.communicate.error_signal.emit(f"Error sending request: {e}")

    def handle_send_request(self, user_input, delay):
        self.send_queue.put((user_input, delay))

    def on_response(self, ch, method, props, body):
        try:
            response = msg_client_pb2.Response()
            response.ParseFromString(body)
            self.logger.info(f"Received response: {response.response} for request ID: {response.request_id}")

            if response.response == "PONG":
                self.logger.info("Received heartbeat response PONG from server.")
                self.server_available = True
                self.last_pong_received = time.time()
                if not self.server_ready:
                    self.server_ready = True
                    self.communicate.server_ready_signal.emit()
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
