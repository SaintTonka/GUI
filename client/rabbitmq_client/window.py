from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar, QMessageBox
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from PyQt5.QtCore import Qt
from datetime import datetime


class Communicate(QObject):
    send_request = pyqtSignal(int)
    received_response = pyqtSignal(str)
    error_sygnal = pyqtSignal(str)

class Window(QMainWindow):
    def __init__(self, communicate):
        super().__init__()

        self.communicate = communicate
        
        self.setWindowTitle("Client")
        self.setGeometry(100, 100, 400, 300)

        self.initUI()

        self.communicate.received_response.connect(self.display_response)
        self.communicate.error_sygnal.connect(self.error_window)

        self.request_in_progress = False  
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

        # Лог событий
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


    def log_event(self, event_message):
        """Запись события в лог"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_widget.append(f"{timestamp} - {event_message}")

    def lock_ui(self):
        self.send_button.setEnabled(False)
        self.input_field.setEnabled(False)
        self.set_delay_button.setEnabled(False)
        self.input_field2.setEnabled(False)

    def unlock_ui(self):
        self.send_button.setEnabled(True)
        self.input_field.setEnabled(True)
        self.set_delay_button.setEnabled(True)
        self.input_field2.setEnabled(True)
    

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
        """Запускает таймер и отсчет времени"""
        self.remaining_time = self.process_time_in_seconds
        self.progress_bar.setMaximum(self.process_time_in_seconds)
        self.progress_bar.setValue(self.process_time_in_seconds)  
        self.timer.start(1000)

    def updateTimer(self):
        self.remaining_time -= 1
        self.label.setText(f"Ожидается ответ... Оставшееся время: {self.remaining_time} сек.")
        self.progress_bar.setValue(self.remaining_time) 
        if self.remaining_time <= 0:
            self.timer.stop()
            self.send_delayed_request()


    def sending_request(self):
        """Отправляет запрос немедленно или с задержкой"""
        text = self.input_field.text().strip()
        if text == "":
            self.display_response("Введите число!")
            return
        
        else:
            if not text.isdigit() and int(text) > 1073741824:
                self.display_response("Введите целое число не певышащее 1073741824!")
                self.log_event("Попытка отправить некорректное число.")
                return
            

        if self.request_in_progress:
            self.display_response("Ожидается ответ на предыдущий запрос.")
            self.log_event("Попытка отправить новый запрос при активном запросе.")
            return

        self.log_event(f"Отправка запроса с числом: {text}")
        self.request_in_progress = True
        self.lock_ui()

        if self.process_time_in_seconds > 0:
            self.start_timer()
        else:
            self.send_delayed_request()

    def send_delayed_request(self):
        """Отправка запроса после задержки или немедленно"""
        number = int(self.input_field.text().strip())

        if number > 1073741824:
            self.display_response("Введите целое число не певышащее 1073741823!")
            self.log_event("Попытка отправить некорректное число.")
            return

        self.communicate.send_request.emit(number)
        self.input_field.clear()  
        self.log_event(f"Запрос отправлен: {number}")

    def display_response(self, response):
        if self.cancelled_request == True:
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
        self.cancelled_request = True
        self.progress_bar.reset()  
        self.label.setText("Запрос отменен.")
        self.log_event("Запрос был отменен.")
        self.unlock_ui()

    def error_window(self, error_sygnal):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setText("Error connectio server!")
        msg_box.setWindowTitle("Error message")
        msg_box.exec()    
