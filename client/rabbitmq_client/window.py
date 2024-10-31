from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QLabel, QLineEdit,
    QPushButton, QTextEdit, QProgressBar, QMessageBox
)
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from datetime import datetime
from math import inf

MAX_NUMBER = inf # В данном случае это введено лишь для того, чтобы в случае вовзращения ответу типа инт, модно было присвоидить определенное значение

class Window(QMainWindow):
    def __init__(self, communicate, client):
        super().__init__()

        self.communicate = communicate
        self.client = client
        
        self.setWindowTitle("Client")
        self.setGeometry(100, 100, 400, 300)

        self.initUI()

        self.communicate.received_response.connect(self.display_response)
        self.communicate.server_ready_signal.connect(self.on_server_ready)
        self.communicate.error_signal.connect(self.handle_error_signal)

        self.request_in_progress = False
        self.server_ready = False
        self.process_time_in_seconds = 0
        self.remaining_time = 0
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

        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)

        layout.addWidget(self.label)
        layout.addWidget(self.input_field)
        layout.addWidget(self.send_button)

        layout.addWidget(self.label2)
        layout.addWidget(self.input_field2)
        layout.addWidget(self.set_delay_button)

        layout.addWidget(self.cancel_button)
        layout.addWidget(self.log_widget)

        self.send_button.clicked.connect(self.sending_request)
        self.set_delay_button.clicked.connect(self.set_delay)
        self.cancel_button.clicked.connect(self.cancel_request)

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

    
    def closeEvent(self, event):
        """Закрытие окна: останавливаем клиент и закрываем соединения."""
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
        """Запись события в лог"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_widget.append(f"{timestamp} - {event_message}")

    def on_server_ready(self):
        """Разблокировать UI, когда сервер готов"""
        self.server_ready = True
        self.notify_user("Сервер готов! Теперь можно отправлять запросы.", success=True)
        self.unlock_ui()

    def handle_error_signal(self, error_message):
        """Обработка сигнала ошибки"""
        self.notify_user(error_message, success=False)
        self.log_event(f"Ошибка: {error_message}")    

    def set_delay(self):
        """Устанавливает задержку перед отправкой запроса, заданную пользователем."""
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

    def start_timer(self):
        """Запускает таймер и отсчет времени"""
        self.remaining_time = self.process_time_in_seconds
        self.progress_bar.setMaximum(self.process_time_in_seconds)
        self.progress_bar.setValue(0)  # Начальное значение прогресса
        self.timer.start(1000)

    def updateTimer(self):
        self.remaining_time -= 1
        self.progress_bar.setValue(self.process_time_in_seconds - self.remaining_time) 
        self.label.setText(f"Ожидается ответ... Оставшееся время: {self.remaining_time} сек.")
        if self.remaining_time <= 0:
            self.timer.stop()
            self.send_delayed_request()

    def sending_request(self):
        """Отправляет запрос немедленно или с задержкой"""
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

        if self.process_time_in_seconds > 0:
            self.start_timer()
        else:
            self.send_delayed_request()

    def send_delayed_request(self):
        """Отправка запроса после задержки или немедленно"""
        try:
            number = int(self.input_field.text().strip())
            if number > MAX_NUMBER:
                self.display_response(f"Введите целое число не превышающее {MAX_NUMBER}!")
                self.log_event("Попытка отправить некорректное число.")
                self.request_in_progress = False
                self.unlock_ui()
                return

            self.communicate.send_request.emit(str(number), self.process_time_in_seconds)
            self.input_field.clear()  
            self.log_event(f"Запрос отправлен: {number} с задержкой {self.process_time_in_seconds} сек.")
        except ValueError:
            self.display_response("Введите корректное целое число!")
            self.log_event("Попытка отправить некорректное число.")
            self.request_in_progress = False
            self.unlock_ui()

    def display_response(self, response):
        if self.cancelled_request:
            self.log_event(f"Ответ был проигнорирован, так как запрос был отменен: {response}")
            self.cancelled_request = False
            return
        self.label.setText(f"Ответ от сервера: {response}")
        self.log_event(f"Ответ от сервера: {response}")
        self.request_in_progress = False
        self.progress_bar.reset() 
        self.unlock_ui()

    def cancel_request(self):
        """Отмена текущего запроса"""
        if not self.request_in_progress:
            return
        self.request_in_progress = False
        self.timer.stop()
        self.progress_bar.reset()  
        self.label.setText("Запрос отменен.")
        self.log_event("Запрос был отменен.")
        self.unlock_ui()


    def notify_user(self, message, success=True):
            """Уведомить пользователя о текущем статусе"""
            if success:
                self.status_label.setStyleSheet("color: green;")
            else:
                self.status_label.setStyleSheet("color: red;")
            self.status_label.setText(message)
            self.log_event(message)
