import os
import sys
import uuid
import configparser
import logging
from PyQt5.QtCore import pyqtSignal, QObject, QThread
import pika
import queue
from .proto import msg_client_pb2
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import threading

class Communicate(QObject):
    received_response = pyqtSignal(str)
    send_request = pyqtSignal(str, float)
    error_signal = pyqtSignal(str)
    server_ready_signal = pyqtSignal()
    server_unavailable_signal = pyqtSignal()

class ConfigFileWatcher(FileSystemEventHandler):
    def __init__(self, config_file, client):
        self.config_file = config_file
        self.client = client

    def on_modified(self, event):
        if event.src_path == self.config_file:
            print(f"Файл {self.config_file} был изменен. Перезагрузка приложения...")
            self.client.restart_application()  

def start_watchdog(config_file, client):
    event_handler = ConfigFileWatcher(config_file, client)
    observer = Observer()
    observer.schedule(event_handler, path=config_file, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

class RMQClient(QThread):
    def __init__(self, communicate, config_file='client_config.ini'):
        super().__init__()
        self.communicate = communicate
        self.config_file = config_file
        self.load_config()  # Загружаем конфигурацию
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

        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=self.log_level,
            filename=self.log_file,
            filemode='a',
            format='%(asctime)s - %(levelname)s - %(name)s: %(message)s',
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Запускаем поток для наблюдения за конфигурацией
        watchdog_thread = threading.Thread(target=start_watchdog, args=(self.config_file, self))
        watchdog_thread.daemon = True
        watchdog_thread.start()

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
        self.timeout_response = config.getint('client', 'timeout_response', fallback=10)

        with open(config_file_path, 'w') as configfile:
            config.write(configfile)

        self.client_uuid = self.client_uuid

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

            result = self.channel.queue_declare(queue=self.client_uuid, exclusive=True)
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

    def restart_application(self):
        """ Перезапус"""
        self._running = False
        self.quit()
        self.wait()
        python = sys.executable
        os.execv(python, [python] + sys.argv) 

    def send_hi_to_serv(self):
        try:
            request = msg_client_pb2.Request()
            request.return_address = self.client_uuid
            request.request_id = str(uuid.uuid4())  
            request.request = "PING"
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
            request.return_address = self.client_uuid
            request.request_id = str(uuid.uuid4())  
            request.request = str(user_input)
            if delay > 0:
                request.process_time_in_seconds = int(delay)

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
            self.communicate.error_signal.emit(f"Error sending request: {e}")

    def handle_send_request(self, user_input, delay):
        self.send_queue.put((user_input, delay))

    def on_response(self, ch, method, props, body):
        self.logger.info(f"Received message on queue: {self.callback_queue}")
        try:
            response = msg_client_pb2.Response()
            response.ParseFromString(body)
            self.logger.info(f"Received response: {response.response} for request ID: {response.request_id}, correlation_id={props.correlation_id}")

            # Сравнение correlation_id
            if props.correlation_id == response.request_id:
                if response.response == "PONG":
                    self.logger.info("Received heartbeat response PONG from server.")
                    self.server_available = True
                    self.last_pong_received = time.time()
                    if not self.server_ready:
                        self.server_ready = True
                        self.communicate.server_ready_signal.emit()
                else:
                    self.communicate.received_response.emit(response.response)
            else:
                self.logger.error(f"Unexpected correlation_id: {props.correlation_id}")
                self.communicate.error_signal.emit(f"Unexpected correlation_id: {props.correlation_id}")
        except Exception as e:
            self.logger.error(f"Error processing response: {e}")
            self.communicate.error_signal.emit(f"Error processing response: {e}")



    def reconnect_to_rabbitmq(self):
        if self.connection and self.connection.is_open:
            self.connection.close()

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