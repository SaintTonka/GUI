from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QLabel, QLineEdit,
    QPushButton, QTextEdit, QProgressBar
)
from PyQt5.QtCore import QTimer
from datetime import datetime
from math import inf
from config_params import ConfigEditor 
import sys

MAX_NUMBER = inf  # Максимальное число, если необходимо

class Window(QMainWindow):
    def __init__(self, communicate, client, config_file):
        super().__init__()

        self.communicate = communicate
        self.client = client
        self.config_file = config_file  

        self.setWindowTitle("Client")
        self.setGeometry(100, 100, 400, 300)

        self.initUI()

        self.communicate.received_response.connect(self.display_response)
        self.communicate.server_ready_signal.connect(self.on_server_ready)
        self.communicate.error_signal.connect(self.handle_error_signal)
        self.communicate.server_unavailable_signal.connect(self.on_server_unavailable)

        self.request_in_progress = False
        self.server_ready = False
        self.process_time_in_seconds = 0
        self.remaining_time = 0
        self.total_wait_time = 0
        self.cancelled_request = False

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
        self.config_button = QPushButton("Настройки клиента")

        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)

        layout.addWidget(self.label)
        layout.addWidget(self.input_field)
        layout.addWidget(self.send_button)

        layout.addWidget(self.label2)
        layout.addWidget(self.input_field2)
        layout.addWidget(self.set_delay_button)

        layout.addWidget(self.cancel_button)
        layout.addWidget(self.config_button)  
        layout.addWidget(self.log_widget)

        self.send_button.clicked.connect(self.sending_request)
        self.set_delay_button.clicked.connect(self.set_delay)
        self.cancel_button.clicked.connect(self.cancel_request)
        self.config_button.clicked.connect(self.open_config_editor)  

        self.timer = QTimer()
        self.timer.timeout.connect(self.updateTimer)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.lock_ui()
        self.notify_user("Ожидание готовности сервера...", success=False)

    def open_config_editor(self):
        """
        Метод для открытия редактора конфигурации.
        """
        editor = ConfigEditor(self.config_file)
        editor.exec_()  

    def closeEvent(self, event):
        """Обработка закрытия окна: остановка клиента и закрытие соединений."""
        self.notify_user("Завершение работы клиента...", success=False)
        self.client.stop_client()
        event.accept()

    def lock_ui(self):
        self.send_button.setEnabled(False)
        self.input_field.setEnabled(False)
        self.set_delay_button.setEnabled(False)
        self.input_field2.setEnabled(False)
        self.cancel_button.setEnabled(True)

    def unlock_ui(self):
        self.send_button.setEnabled(True)
        self.input_field.setEnabled(True)
        self.set_delay_button.setEnabled(True)
        self.input_field2.setEnabled(True)
        self.cancel_button.setEnabled(True)

    def log_event(self, event_message):
        """Запись события в лог."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_widget.append(f"{timestamp} - {event_message}")

    def on_server_ready(self):
        """Разблокировать UI и обновить статус, когда сервер готов."""
        self.server_ready = True
        self.notify_user("Сервер готов! Теперь можно отправлять запросы.", success=True)
        self.unlock_ui()

    def on_server_unavailable(self):
        """Обработка ситуации, когда сервер становится недоступен."""
        self.server_ready = False
        self.notify_user("Сервер недоступен.", success=False)
        self.lock_ui()
        self.progress_bar.setValue(0)  

    def handle_error_signal(self, error_message):
        """Обработка ошибок."""
        self.notify_user(error_message, success=False)
        self.log_event(f"Ошибка: {error_message}")

    def set_delay(self):
        """Устанавливает задержку обработки на сервере, заданную пользователем."""
        delay_text = self.input_field2.text().strip()
        try:
            delay = int(delay_text)
            if 0 <= delay <= 3600:
                self.process_time_in_seconds = delay
                self.label2.setText(f"Задержка установлена: {self.process_time_in_seconds} сек.")
                self.log_event(f"Установлена задержка: {self.process_time_in_seconds} сек.")
            else:
                raise ValueError
        except ValueError:
            self.label2.setText("Введите корректное число для задержки.")
            self.log_event("Попытка установить некорректное значение задержки.")

    def start_timer(self, total_time):
        """Запускает таймер и отсчет времени ожидания ответа от сервера."""
        self.total_wait_time = total_time
        self.remaining_time = total_time
        self.progress_bar.setValue(0)
        self.timer.start(1000)

    def updateTimer(self):
        self.remaining_time -= 1

        if self.total_wait_time > 0:
            elapsed_time = self.total_wait_time - self.remaining_time
            progress_percentage = int((elapsed_time / self.total_wait_time) * 100)
            if progress_percentage > 100:
                progress_percentage = 100  
        else:
            progress_percentage = 100

        self.progress_bar.setValue(progress_percentage)
        self.label.setText(f"Ожидается ответ... Оставшееся время: {self.remaining_time} сек.")

        if self.remaining_time <= 0:
            self.timer.stop()
            self.label.setText("Время ожидания истекло.")
            self.log_event("Время ожидания ответа от сервера истекло.")
            self.request_in_progress = False
            self.unlock_ui()

    def sending_request(self):
        """Отправляет запрос немедленно."""
        if not self.server_ready:
            self.notify_user("Сервер недоступен. Невозможно отправить запрос.", success=False)
            return

        text = self.input_field.text().strip()
        if text == "":
            self.display_response("Введите число!")
            return

        try:
            number = int(text)
            if number > MAX_NUMBER:
                self.display_response(f"Введите целое число не превышающее {MAX_NUMBER}!")
                self.log_event("Попытка отправить некорректное число.")
                return
        except ValueError:
            self.display_response("Введите корректное целое число!")
            self.log_event("Попытка отправить некорректное число.")
            return

        if self.request_in_progress:
            self.display_response("Ожидается ответ на предыдущий запрос.")
            self.log_event("Попытка отправить новый запрос при активном запросе.")
            return

        self.log_event(f"Отправка запроса с числом: {number}")
        self.request_in_progress = True
        self.lock_ui()

        self.communicate.send_request.emit(str(number), self.process_time_in_seconds)
        self.input_field.clear()
        self.log_event(f"Запрос отправлен: {number} с задержкой {self.process_time_in_seconds} сек.")

        total_wait_time = self.process_time_in_seconds + self.client.timeout_response
        if total_wait_time <= 0:
            total_wait_time = 1  
        self.start_timer(total_wait_time)

    def display_response(self, response):
        if self.cancelled_request:
            self.log_event(f"Ответ был проигнорирован, так как запрос был отменен: {response}")
            self.cancelled_request = False
            return
        self.label.setText(f"Ответ от сервера: {response}")
        self.log_event(f"Ответ от сервера: {response}")
        self.request_in_progress = False
        self.progress_bar.setValue(100)  
        self.unlock_ui()
        self.timer.stop()

    def cancel_request(self):
        """Отмена текущего запроса."""
        if not self.request_in_progress:
            return
        self.request_in_progress = False
        self.cancelled_request = True
        self.timer.stop()
        self.progress_bar.setValue(0)
        self.label.setText("Запрос отменен.")
        self.log_event("Запрос был отменен.")
        self.unlock_ui()

    def notify_user(self, message, success=True):
        """Уведомить пользователя о текущем статусе."""
        if success:
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setStyleSheet("color: red;")
        self.status_label.setText(message)
        self.log_event(message)
