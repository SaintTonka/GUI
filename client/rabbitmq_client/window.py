# window.py
# -*- coding: utf-8 -*-
import uuid, os, sys
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QLabel,
    QLineEdit, QPushButton, QTextEdit, QProgressBar
)
from PyQt5.QtCore import QTimer, Qt
from datetime import datetime
from .config_params import ConfigEditor

MAX_NUMBER = 2147483647

class Window(QMainWindow):
    def __init__(self, client, config_file):
        super().__init__()

        self.client = client
        self.config_file = config_file

        self.setWindowTitle("Client")
        self.setGeometry(100, 100, 400, 300)

        self.initUI()

        # Подключаем сигналы к слотам
        self.client.received_response.connect(self.display_response)
        self.client.error_signal.connect(self.handle_error_signal)
        self.client.server_ready_signal.connect(self.on_server_ready)
        self.client.server_unavailable_signal.connect(self.on_server_unavailable)

        self.request_in_progress = False
        self.process_time_in_seconds = 0
        self.remaining_time = 0
        self.total_wait_time = 0
        self.config_editor = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)

    def initUI(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Элементы управления
        self.label = QLabel("Введите число:")
        self.input_field = QLineEdit()
        self.send_button = QPushButton("Отправить")

        self.label2 = QLabel("Установите время задержки (секунды):")
        self.input_field2 = QLineEdit()
        self.set_delay_button = QPushButton("Установить задержку")

        self.cancel_button = QPushButton("Отмена текущего запроса")
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)

        self.config_button = QPushButton("Настройки клиента")

        self.label3 = QLabel("UUID клиента")
        self.uuid_input = QLineEdit(self)  
        self.uuid_input.setReadOnly(True)  
        self.uuid_button = QPushButton("Сгенерировать UUID", self)
        self.uuid_button.setStyleSheet("background-color: #4CAF50; color: white;")
        layout.addWidget(self.uuid_input)

        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        # Добавление элементов на экран
        layout.addWidget(self.label)
        layout.addWidget(self.input_field)
        layout.addWidget(self.send_button)
        
        layout.addWidget(self.label2)
        layout.addWidget(self.input_field2)
        layout.addWidget(self.set_delay_button)
        
        layout.addWidget(self.label3)
        layout.addWidget(self.uuid_input)
        layout.addWidget(self.uuid_button)

        layout.addWidget(self.cancel_button)
        layout.addWidget(self.config_button)  
        layout.addWidget(self.log_widget)
        layout.addWidget(self.progress_bar)

        # Подключаем кнопки к методам
        self.send_button.clicked.connect(self.sending_request)
        self.set_delay_button.clicked.connect(self.set_delay)
        self.cancel_button.clicked.connect(self.cancel_request)
        self.config_button.clicked.connect(self.open_config_editor)
        self.uuid_button.clicked.connect(self.generate_uuid)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        layout.setSpacing(20)

    def notify_user(self, message, success=True):
        """ Уведомить пользователя о текущем статусе. """
        self.status_label.setStyleSheet("color: green;" if success else "color: red;")
        self.status_label.setText(message)
        self.log_event(message)

    def log_event(self, event_message):
        """ Запись события в лог. """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_widget.append(f"{timestamp} - {event_message}")

    def open_config_editor(self):
        """Метод для открытия редактора конфигурации."""
        if self.config_editor is None:
            self.config_editor = ConfigEditor(self.config_file)  
            self.config_editor.config_saved.connect(self.on_config_saved)

        self.config_editor.setWindowModality(Qt.ApplicationModal)
        self.config_editor.show()

    def restart_application(self):
        """ Перезапуск приложения. """
        self.log_event("Перезапуск приложения...")
        self.client.stop_client() 
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def on_config_saved(self):
        """Когда конфигурация сохранена, перезапускаем приложение"""
        self.client.restart_application()  

    def on_server_ready(self):
        """ Разблокировать UI и обновить статус, когда сервер готов. """
        self.notify_user("Сервер готов! Теперь можно отправлять запросы.", success=True)
        self.unlock_ui()  # Разблокировать элементы управления

    def on_server_unavailable(self):
        """ Обработка ситуации, когда сервер становится недоступен. """
        self.notify_user("Сервер недоступен.", success=False)
        self.lock_ui()  # Заблокировать элементы управления

    def handle_error_signal(self, error_message):
        """ Обработка ошибок. """
        self.notify_user(error_message, success=False)
        self.log_event(f"Ошибка: {error_message}")

    def set_delay(self):
        """ Устанавливает задержку обработки на сервере, заданную пользователем. """
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
        """ Запускает таймер и отсчет времени ожидания ответа от сервера. """
        self.wait_time = self.process_time_in_seconds
        self.remaining_time = self.wait_time + self.client.timeout_response
        self.progress_bar.setMaximum(self.wait_time) 
        self.progress_bar.setValue(self.wait_time)   
        self.timer.start(1000) 

    def update_timer(self):
        """ Обновляет таймер каждую секунду и управляет состоянием прогресс-бара. """
        self.remaining_time -= 1
        self.progress_bar.setValue(self.remaining_time)

        if self.remaining_time < 0:
            self.timer.stop()
            self.notify_user("Время ожидания истекло. Сервер может быть недоступен.", success=False)


    def sending_request(self):
        """ Отправляет запрос """
        if not self.client._running:
            self.notify_user("Сервер недоступен. Невозможно отправить запрос.", success=False)
            return

        text = self.input_field.text().strip()
        if text == "":
            self.notify_user("Введите число!", success=False)
            return
        
        if int(text) > MAX_NUMBER or int(text) < -(MAX_NUMBER):
            self.notify_user("Введите число, не превышающее 2147483647 и не меньшее -2147483647!", success=False)
            return

        try:
            number = int(text)
        except ValueError:
            self.notify_user("Введите корректное целое число!", success=False)
            return

        self.log_event(f"Отправка запроса с числом: {number}")

        # Расчёт времени ожидания
        if self.process_time_in_seconds > 0:
            self.total_wait_time = self.process_time_in_seconds + self.client.timeout_response
        else:
            self.total_wait_time = self.client.timeout_response

        self.client.send_queue.put((str(number), self.process_time_in_seconds))  # Отправка запроса
        self.start_timer()  # Установка таймера

    def display_response(self, response):
        """ Отображает ответ от сервера. """
        self.notify_user(f"Ответ от сервера: {response}", success=True)
        self.timer.stop()  
        self.progress_bar.setValue(0)

    def cancel_request(self):
        """ Отмена текущего запроса. """
        self.timer.stop()
        self.log_event("Запрос отменен.")
        self.notify_user("Запрос отменен.", success=False)

    def lock_ui(self):
        """ Блокирует элементы управления интерфейса. """
        self.send_button.setEnabled(False)
        self.input_field.setEnabled(False)
        self.set_delay_button.setEnabled(False)
        self.input_field2.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.config_button.setEnabled(False)

    def unlock_ui(self):
        """ Разблокирует элементы управления интерфейса. """
        self.send_button.setEnabled(True)
        self.input_field.setEnabled(True)
        self.set_delay_button.setEnabled(True)
        self.input_field2.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self.config_button.setEnabled(True)

    def generate_uuid(self):
        """Генерация UUID для клиента"""
        self.uuid_input.setText(str(uuid.uuid4()))
