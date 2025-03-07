import configparser
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QLabel,
    QLineEdit, QPushButton, QTextEdit, QProgressBar
)
from PyQt5.QtCore import QTimer, Qt, QFileSystemWatcher, pyqtSignal, pyqtSlot
from datetime import datetime
from rabbitmq_client.config_params import ConfigEditor
import logging
from PyQt5.QtCore import QThread, pyqtSlot
from rabbitmq_client.client import RMQClient

log = logging.getLogger(__name__)

MAX_NUMBER = 2147483647

class Window(QMainWindow):
    request_processed = pyqtSignal()
    def __init__(self):
        super().__init__()

        self.client = RMQClient()
        self.thread = QThread()

        self.client.moveToThread(self.thread)
        self.thread.started.connect(self.client.run)

        self.initUI()
        
        self.thread.start()

        self.config_path = Path(__file__).parent.parent / 'client_config.ini'
        self.config_file = configparser.ConfigParser()
        self.config_file.read(self.config_path)

        self.response_data = None

        self.setWindowTitle("Client")
        self.setGeometry(100, 100, 400, 600) 

        self.request_processed.connect(self.on_request_processed)
        self.client.received_response.connect(self.display_response)
        self.client.error_signal.connect(self.handle_error_signal)
        self.client.server_ready_signal.connect(self.on_server_ready)
        self.client.server_unavailable_signal.connect(self.on_server_unavailable)

        self.request_in_progress = False
        self.process_time_in_seconds = 0  
        self.config_editor = None

        self.request_cancelled = False 
        self.processing_request = False 

        self.file_watcher = QFileSystemWatcher([str(self.config_path)])
        self.file_watcher.fileChanged.connect(self.on_config_changed)

        self.timeout_timer = QTimer()
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self.on_timeout)

        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self.update_progress)

    def initUI(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        self.label = QLabel("Введите число:")
        self.input_field = QLineEdit()
        self.send_button = QPushButton("Отправить")

        self.label2 = QLabel("Установите время задержки (секунды):")
        self.input_field2 = QLineEdit()
        self.set_delay_button = QPushButton("Установить задержку")

        self.cancel_button = QPushButton("Отмена текущего запроса")
        self.cancel_button.setVisible(False)
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)

        self.config_button = QPushButton("Настройки клиента")

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)  
        self.timer_label = QLabel("Оставшееся время: 0 сек.")  

        layout.addWidget(self.label)
        layout.addWidget(self.input_field)
        layout.addWidget(self.send_button)
        
        layout.addWidget(self.label2)
        layout.addWidget(self.input_field2)
        layout.addWidget(self.set_delay_button)

        layout.addWidget(self.cancel_button)
        layout.addWidget(self.config_button)  
        layout.addWidget(self.log_widget)

        layout.addWidget(self.progress_bar)
        layout.addWidget(self.timer_label)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        layout.setSpacing(20)

        self.send_button.clicked.connect(self.sending_request)
        self.set_delay_button.clicked.connect(self.set_delay)
        self.cancel_button.clicked.connect(self.cancel_request)
        self.config_button.clicked.connect(self.open_config_editor)

    def closeEvent(self, event):
        self.client.stop()
        self.thread.quit()
        if not self.thread.wait(2000):
            log.error("Forced thread termination")
            self.thread.terminate()
        
        super().closeEvent(event)     

    def notify_user(self, message, success=True):
        """Уведомить пользователя о текущем статусе."""
        self.status_label.setStyleSheet("color: green;" if success else "color: red;")
        self.status_label.setText(message)
        self.log_event(message)

    def log_event(self, event_message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"{timestamp} - {event_message}"
        
        if log_message not in self.log_widget.toPlainText():
            log.debug(log_message)
            self.log_widget.append(log_message)

    def open_config_editor(self):
        """Метод для открытия редактора конфигурации."""
        self.config_editor = ConfigEditor(self.config_path, read_only=self.processing_request)
        self.config_editor.config_saved.connect(self.client.reload_config_and_reconnect, Qt.QueuedConnection)
        self.config_editor.config_saved.connect(self.on_config_changed) 
        self.config_editor.setWindowModality(Qt.ApplicationModal)
        self.config_editor.show()
            
    def set_logging_level(self):
        """Настроить уровень логирования в зависимости от конфигурации."""
        level = self.config_file.get('logging', 'level', fallback='INFO').upper()
        levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }

        log.setLevel(levels.get(level, logging.INFO))

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        log.handlers = []
        log.addHandler(handler)

    @pyqtSlot()
    def on_config_changed(self):
        """Обработчик изменений в конфигурационном файле."""
        self.config_file.read(self.config_path)
        try:
            self.timeout_response = self.config_file.getint('server', 'timeout_response')
            self.set_logging_level()

        except ValueError as e:
            self.log_event(f"Ошибка при чтении таймаутов: {e}")

    def log_event(self, event_message):
        """Запись события в лог с учетом уровня логирования."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log.debug(f"{timestamp} - {event_message}")
        self.log_widget.append(f"{timestamp} - {event_message}")

    @pyqtSlot()
    def on_server_ready(self):
        """Разблокировать UI и обновить статус, когда сервер готов."""
        self.notify_user("Сервер готов! Теперь можно отправлять запросы.", success=True)
        self.unlock_ui()

    @pyqtSlot()
    def on_server_unavailable(self):
        """Обработка ситуации, когда сервер становится недоступен."""
        self.notify_user("Сервер недоступен.", success=False)
        self.unlock_ui() 

    @pyqtSlot(str)
    def handle_error_signal(self, error_message):
        """Обработка ошибок."""
        self.notify_user(error_message, success=False)
        self.log_event(f"Ошибка: {error_message}")

    def set_delay(self):
        """Устанавливает задержку обработки на сервере, заданную пользователем."""
        delay_text = self.input_field2.text().strip()
        try:
            delay = int(delay_text) if delay_text else 0
            if delay < 0:
                raise ValueError
            self.process_time_in_seconds = delay
            self.label2.setText(f"Задержка установлена: {self.process_time_in_seconds} сек.")
            self.log_event(f"Установлена задержка: {self.process_time_in_seconds} сек.")
        except ValueError:
            self.label2.setText("Введите корректное число для задержки.")
            self.log_event("Попытка установить некорректное значение задержки.")

    def start_timer(self):
        if self.process_time_in_seconds == 0:
            self.progress_bar.setVisible(False)
            self.timer_label.setText("Оставшееся время: 0 сек.")
            self.process_timer.stop()
        else:
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(self.process_time_in_seconds)
            self.progress_bar.setValue(self.process_time_in_seconds)
            self.timer_label.setText(f"Оставшееся время: {self.process_time_in_seconds} сек.")
            self.process_timer.start(1000)  

        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.start(self.timeout_response * 1000)

 
    @pyqtSlot()
    def update_progress(self):
        """Обновляет прогресс-бар и отображение оставшегося времени."""
        current_value = self.progress_bar.value()
        if current_value > 0:
            self.progress_bar.setValue(current_value - 1)
            self.timer_label.setText(f"Оставшееся время: {current_value - 1} сек.")
        else:
            self.process_timer.stop()

    @pyqtSlot()
    def on_timeout(self):
        """Обрабатывает истечение времени ожидания ответа от сервера."""
        self.notify_user("Время ожидания истекло. Сервер может быть недоступен.", success=False)
        self.unlock_ui()
        self.request_processed.emit()

    def sending_request(self):
        """Отправляет запрос."""
        if not self.client._running:
            self.notify_user("Сервер недоступен. Невозможно отправить запрос.", success=False)
            return
        
        text = self.input_field.text().strip()
        if text == "":
            self.notify_user("Введите число!", success=False)
            return

        try:
            number = int(text)
            if number > MAX_NUMBER or number < -MAX_NUMBER:
                self.notify_user("Введите число, не превышающее 2147483647 и не меньшее -2147483647!", success=False)
                return
        except ValueError:
            self.notify_user("Введите корректное целое число!", success=False)
            return
        
        delay = self.process_time_in_seconds if self.process_time_in_seconds > 0 else 0
        self.log_event(f"Отправка запроса с числом: {number}")
        self.processing_request = True
        self.client.send_request_signal.emit(str(number), delay)
        self.start_timer()
        self.lock_ui()

    @pyqtSlot(int)
    def display_response(self, response):
        """Сохраняет и отображает ответ от сервера."""
        if self.request_cancelled:
            self.request_cancelled = False
            return 

        log.debug(f"Получен ответ от сервера: {response}")
        
        if response is None:
            self.notify_user("Ответ от сервера не получен. Сервер может быть недоступен.", success=False)
            self.unlock_ui()
        else:    
            self.response_data = response
            self.notify_user(f"Ответ от сервера: {self.response_data}", success=True)
            self.timeout_timer.stop()
            self.process_timer.stop()
            self.timer_label.setText("Оставшееся время: 0 сек.")
            self.progress_bar.setValue(0)
            self.unlock_ui()
        
        self.request_processed.emit()

    @pyqtSlot(bool)
    def cancel_request(self):
        """Отмена текущего запроса."""
        self.timeout_timer.stop()
        self.request_cancelled = True
        self.processing_request = False
        self.process_timer.stop()
        self.notify_user("Запрос отменен.", success=False)
        self.progress_bar.setValue(0)
        self.timer_label.setText("Оставшееся время: 0 сек.")
        if self.response_data:
            self.log_event(f"Был получен ответ от сервера {self.response_data}")
        else:
            self.log_event(f"Сервер не успел обработать запрос")
        self.unlock_ui()

        self.request_processed.emit()

    def on_request_processed(self):
        """Обработчик сигнала, который обновляет флаг после завершения запроса."""
        self.processing_request = False
        self.unlock_ui()

    def lock_ui(self):
        """Блокирует элементы управления интерфейса."""
        self.set_ui_state(False)

    def unlock_ui(self):
        """Разблокирует элементы управления интерфейса."""
        self.set_ui_state(True)

    def set_ui_state(self, enabled):
        self.send_button.setEnabled(enabled)
        self.input_field.setEnabled(enabled)
        self.set_delay_button.setEnabled(enabled)
        self.input_field2.setEnabled(enabled)
        self.cancel_button.setVisible(not enabled)