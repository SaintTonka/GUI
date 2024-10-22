from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QLabel, QLineEdit,
    QPushButton, QTextEdit, QProgressBar, QMessageBox
)
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from datetime import datetime

class Window(QMainWindow):
    def __init__(self, communicate, client):
        super().__init__()

        self.communicate = communicate
        self.client = client

        self.setWindowTitle("Client")
        self.setGeometry(100, 100, 500, 500)

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
        """Блокировка интерфейса до готовности сервера"""
        self.send_button.setEnabled(False)
        self.input_field.setEnabled(False)
        self.set_delay_button.setEnabled(False)
        self.input_field2.setEnabled(False)
        self.cancel_button.setEnabled(False)

    def unlock_ui(self):
        """Разблокировка интерфейса после подтверждения готовности сервера"""
        self.send_button.setEnabled(True)
        self.input_field.setEnabled(True)
        self.set_delay_button.setEnabled(True)
        self.input_field2.setEnabled(True)
        self.cancel_button.setEnabled(True)

    def handle_error_signal(self, error_message):
        """Обработка сигнала ошибки"""
        self.notify_user(error_message, success=False)
        self.log_event(f"Ошибка: {error_message}")

    def error_window(self, error_message):
        """Окно для отображения критической ошибки"""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setText(error_message)
        msg_box.setWindowTitle("Ошибка")
        msg_box.exec()

    def notify_user(self, message, success=True):
        """Уведомить пользователя о текущем статусе"""
        if success:
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setStyleSheet("color: red;")
        self.status_label.setText(message)
        self.log_event(message)

    def log_event(self, event_message):
        """Запись события в лог"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_widget.append(f"{timestamp} - {event_message}")

    def on_server_ready(self):
        """Разблокировать UI, когда сервер готов"""
        self.server_ready = True
        self.notify_user("Сервер готов! Теперь можно отправлять запросы.", success=True)
        self.unlock_ui()

    def sending_request(self):
        """Отправляет запрос только если сервер готов"""
        if not self.server_ready:
            self.notify_user("Сервер не готов. Пожалуйста, подождите...", success=False)
            return

        text = self.input_field.text().strip()
        if not text:
            self.notify_user("Введите число!", success=False)
            return

        if not text.isdigit() or int(text) > 1073741824:
            self.notify_user("Введите целое число не превышающее 1073741824!", success=False)
            self.log_event("Попытка отправить некорректное число.")
            return

        if self.request_in_progress:
            self.notify_user("Ожидается ответ на предыдущий запрос.", success=False)
            self.log_event("Попытка отправить новый запрос при активном запросе.")
            return

        self.request_in_progress = True
        self.lock_ui()

        self.log_event(f"Отправка запроса с числом: {text}")

        self.communicate.send_request.emit(int(text))

        if self.process_time_in_seconds > 0:
            self.start_timer()
        else:
            self.remaining_time = self.client.timeout_response
            self.progress_bar.setMaximum(self.remaining_time)
            self.progress_bar.setValue(self.remaining_time)
            self.timer.start(1000)

    def set_delay(self):
        """Устанавливает задержку перед отправкой запроса, заданную пользователем."""
        delay_text = self.input_field2.text().strip()
        if delay_text.isdigit() and 0 <= int(delay_text) <= 3600:
            self.process_time_in_seconds = int(delay_text)
            self.label2.setText(f"Задержка установлена: {self.process_time_in_seconds} сек.")
            self.log_event(f"Установлена задержка: {self.process_time_in_seconds} сек.")
        else:
            self.label2.setText("Введите корректное число для задержки.")
            self.log_event("Попытка установить некорректное значение задержки.")

    def start_timer(self):
        """Запускает таймер ожидания ответа от сервера"""
        self.remaining_time = self.client.timeout_response
        self.progress_bar.setMaximum(self.remaining_time)
        self.progress_bar.setValue(self.remaining_time)
        self.timer.start(1000)  

    def updateTimer(self):
        """Обновляет таймер и прогресс бар"""
        self.remaining_time -= 1
        self.progress_bar.setValue(self.remaining_time)
        if self.remaining_time <= 0:
            self.timer.stop()
            self.cancel_request(timeout=True)

    def cancel_request(self, timeout=False):
        """Отмена текущего запроса"""
        if not self.request_in_progress:
            return
        self.request_in_progress = False
        self.timer.stop()
        self.progress_bar.reset()
        if timeout:
            self.notify_user("Время ожидания ответа истекло.", success=False)
            self.log_event("Время ожидания ответа истекло.")
        else:
            self.notify_user("Запрос отменен пользователем.", success=False)
            self.log_event("Запрос был отменен пользователем.")
        self.unlock_ui()

    def display_response(self, response):
        """Отображает ответ от сервера"""
        if not self.request_in_progress:
            self.log_event(f"Получен ответ на отмененный запрос: {response}")
            return
        self.timer.stop()
        self.progress_bar.reset()
        self.notify_user(f"Ответ от сервера: {response}", success=True)
        self.log_event(f"Ответ от сервера: {response}")
        self.request_in_progress = False
        self.unlock_ui()
