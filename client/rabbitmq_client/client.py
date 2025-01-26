import uuid
import configparser
import logging, time
from PyQt5.QtCore import QObject, pyqtSignal, Qt, QCoreApplication, pyqtSlot, QMetaObject, Q_ARG, QMutex, QMutexLocker
import pika
from pathlib import Path
from rabbitmq_client.config_params import ConfigEditor
from rabbitmq_client.proto import msg_client_pb2
from rabbitmq_client.client_state import DisconnectedState, ConnectingState, ConnectedState, ErrorState, PendingResponseState, ErrorSendState

class RMQClient(QObject):
    received_response = pyqtSignal(int)
    error_signal = pyqtSignal(str)
    server_ready_signal = pyqtSignal()
    server_unavailable_signal = pyqtSignal()
    send_request_signal = pyqtSignal(str, int)

    def __init__(self, config_file='client_config.ini'):
        super().__init__()
        self.config_file = config_file
        self.load_config()
        self.connection = None
        self.channel = None
        self._running = False 
        self.send_request_signal.connect(self.send_request, Qt.QueuedConnection)
        self.config_editor = ConfigEditor(config_file, read_only=False)
        self.config_editor.config_saved.connect(self.reload_config_and_reconnect, Qt.QueuedConnection)
        self.state = DisconnectedState()
        self._mutex = QMutex()
        self._consumer_tag = None 

        self.logger = logging.getLogger(__name__)
        self.logger.propagate = False 

        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)  
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s: %(message)s')
        console_handler.setFormatter(formatter)

        if not self.logger.hasHandlers(): 
            self.logger.addHandler(console_handler)

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

        self.client_uuid = config.get('client', 'uuid', fallback=str(uuid.uuid4()))
        config.set('client', 'uuid', self.client_uuid)  

        self.rmq_host = config.get('rabbitmq', 'host', fallback='localhost')
        self.rmq_port = config.getint('rabbitmq', 'port', fallback=5672)
        self.rmq_user = config.get('rabbitmq', 'user', fallback='guest')
        self.rmq_password = config.get('rabbitmq', 'password', fallback='guest')
        self.exchange = config.get('rabbitmq', 'exchange', fallback='bews')

        self.log_level_str = config.get('logging', 'level', fallback='INFO')
        self.log_level = getattr(logging, self.log_level_str.upper(), logging.INFO)

        self.timeout_connect = config.getfloat('client', 'timeout_connect', fallback=10)
        self.timeout_request = config.getint('client', 'timeout_request', fallback=10)

        with open(config_file_path, 'w') as configfile:
            config.write(configfile)

    def close_connection(self):
        """Закрывает старое соединение и канал, если они открыты."""
        try:
            if self.channel and self._consumer_tag:
                self.channel.basic_cancel(self._consumer_tag)
                self._consumer_tag = None
            if self.connection and self.connection.is_open:
                self.connection.close()
                self.logger.info("Old connection closed.")
            if self.channel and self.channel.is_open:
                self.channel.close()
                self.logger.info("Old channel closed.")
        except Exception as e:
            self.logger.error(f"Error while closing old connection: {e}")
        finally:
            self.connection = None
            self.channel = None

    def change_state(self, new_state):
        self.logger.debug(f"Changing state from {self.state.__class__.__name__} to {new_state.__class__.__name__}")
        self.state = new_state
   
    def run(self):
        self._mutex.lock()
        self._running = True
        self._mutex.unlock()
        
        while True:
            self._mutex.lock()
            if not self._running:
                self._mutex.unlock()
                break
            self._mutex.unlock()
            
            if not self.connect_to_rabbitmq():
                time.sleep(5)
                continue
                
            try:
                while True:
                    self._mutex.lock()
                    if not self._running:
                        self._mutex.unlock()
                        break
                    self._mutex.unlock()
                    
                    self.connection.process_data_events(time_limit=1)
                    QCoreApplication.processEvents()
            except Exception as e:
                self.logger.error(f"Connection error: {str(e)}")
            finally:
                self.close_connection()

    def stop(self):
        self._running = False
        self.close_connection()

    def connect_to_rabbitmq(self):
        if isinstance(self.state, ConnectedState):
            self.logger.warning("Already connected. Skipping...")
            return True

        if isinstance(self.state, ConnectingState):
            self.logger.warning("Resetting connection state...")
            self.change_state(DisconnectedState())

        self.load_config()
        start_time = time.time()
        
        while time.time() - start_time <= self.timeout_connect:
            try:
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=self.rmq_host,
                        port=self.rmq_port,
                        credentials=pika.PlainCredentials(self.rmq_user, self.rmq_password)
                    )
                )
                
                self.channel = self.connection.channel()
                self.channel.exchange_declare(exchange=self.exchange, exchange_type='direct', durable=True)
                self.channel.queue_declare(queue=self.client_uuid, exclusive=True, auto_delete=True, durable=False)

                if self._consumer_tag:
                    self.channel.basic_cancel(self._consumer_tag)

                self._consumer_tag = self.channel.basic_consume(
                    queue=self.client_uuid, 
                    on_message_callback=self.on_response, 
                    auto_ack=True
                )

                self.logger.info("Connection established successfully")
                self.change_state(ConnectedState())
                self.server_ready_signal.emit()
                return True
                
            except (pika.exceptions.AMQPConnectionError, ConnectionResetError) as e:
                self.logger.error(f"Connection error: {str(e)}")
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Unexpected error: {str(e)}")
                self.change_state(ErrorState())
                time.sleep(1)

        self.logger.error("Connection timeout after retries")
        self.change_state(ErrorState())
        return False


    def setup_channel(self):
        """Настроить каналы для отправки и получения сообщений."""
        self.channel.exchange_declare(exchange=self.exchange, exchange_type='direct', durable=True)
        self.logger.info(f"Exchange '{self.exchange}' declared.")

    @pyqtSlot(str,int)
    def send_request(self, user_input, delay):
        """Метод для отправки запроса."""
        with QMutexLocker(self._mutex):
            if not self._running:
                self.emit_error_signal("Client is stopping")
                return
            
        if isinstance(self.state, PendingResponseState):
            self.logger.warning("Request is already sent.")
            return True
        
        if self.channel and self.connection.is_open:
            try:
                request = msg_client_pb2.Request()
                request.request = int(user_input)
                request.return_address = self.client_uuid
                request.request_id = str(uuid.uuid4())
                request.process_time_in_seconds = delay
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
                self.log_request_sent(user_input, delay) 
            except Exception as e:
                self.emit_error_signal(f"Error sending request: {e}")
                self.change_state(ErrorSendState())
        else:
            self.emit_error_signal("Cannot send request: Channel or connection is not open.")
            self.change_state(ErrorSendState())

    def log_request_sent(self, user_input, delay):
        """Логирует отправленный запрос."""
        self.logger.info(f"Sent request: {user_input} with delay: {delay} sec")

    def on_response(self, ch, method, properties, body):
        """Обрабатывает ответ от сервера."""
        try:
            self.logger.info(f"Received raw response body: {body}")
            response = msg_client_pb2.Response()

            response.ParseFromString(body)

            self.logger.info(f"Parsed response: {response.response} for request ID: {properties.correlation_id}")
            self.received_response.emit(response.response)

            self.change_state(ConnectedState())

        except Exception as e:
            self.emit_error_signal(f"Error processing response: {e}")

    def emit_error_signal(self, message):
        """Централизованный метод для отправки сигнала об ошибке."""
        self.logger.error(message)
        self.error_signal.emit(message)
    
    @pyqtSlot()
    def reload_config_and_reconnect(self):

        QMetaObject.invokeMethod(self, "actual_reload_config_and_reconnect", Qt.QueuedConnection)

    @pyqtSlot()
    def actual_reload_config_and_reconnect(self):
        old_uuid = self.client_uuid
        old_port = self.rmq_port
        old_host = self.rmq_host
        old_exchange = self.exchange
        self.load_config()

        if self.client_uuid != old_uuid or self.rmq_host != old_host or self.rmq_port != old_port or self.exchange != old_exchange:
            self.logger.info("Client configuration changed. Reconnecting...")
            self.close_connection() 
            self._running = True
            self.change_state(ConnectingState())  

            if self.connect_to_rabbitmq():
                self.logger.info("Successfully reconnected to RabbitMQ")
            else:
                self.logger.error("Failed to reconnect to RabbitMQ")
                self.change_state(DisconnectedState()) 

    def stop(self):
        with QMutexLocker(self._mutex): 
            self._running = False
        
        self.close_connection()
        self.logger.info("Client stopped")

        if self.connection and self.connection.is_open:
            try:
                self.connection.close()
            except Exception as e:
                self.logger.error(f"Error closing connection: {e}")      