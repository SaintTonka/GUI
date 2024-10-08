import sys

# Путь к модулям PyQt
sys.path.append(r"Z:\Qt\5.15.2\mingw81_64\bin")
sys.path.append(r'C:\Users\username\AppData\Local\Programs\Python\PythonXX\Lib\site-packages\PyQt5')

from rabbitmq_client import RMQClient
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit
from PyQt5.QtCore import pyqtSignal, QObject

class Communicate(QObject):
    # Определение сигналов
    send_request = pyqtSignal(int)
    received_response = pyqtSignal(int)

class Window(QMainWindow):

    def __init__(self, communicate):
        super().__init__()

        # Сначала инициализируем объект Communicate
        self.communicate = communicate

        # Затем создаем клиента RMQClient и передаем объект Communicate
        self.client = RMQClient(self.communicate)

        # Привязка сигналов к методам
        self.communicate.send_request.connect(self.client.handle_send_request)
        self.communicate.received_response.connect(self.display_response)

        # Настройка интерфейса
        self.setGeometry(500, 500, 500, 500)
        self.setWindowTitle("Input")

        # Кнопка для отправки числа
        self.button = QtWidgets.QPushButton(self)
        self.button.setText("Enter your number")
        self.button.move(30, 150)
        self.button.setMinimumWidth(150)
        self.button.clicked.connect(self.send_request)
        
        # Поле ввода для числа
        self.qle = QLineEdit(self)
        self.qle.move(60, 100)
        self.qle.setPlaceholderText("Enter a number")

        # Метка для отображения результата
        self.lbl = QLabel(self)
        self.lbl.move(60, 40)
        self.lbl.setText("Answer: ")

    def send_request(self):
        # Метод для обработки нажатия на кнопку
        try:
            user_input = int(self.qle.text())  # Считываем введенное число
            self.communicate.send_request.emit(user_input)  # Посылаем сигнал
        except ValueError:
            # Обработка некорректного ввода
            self.lbl.setText("Wrong input")
            self.lbl.adjustSize()
            return       

    def display_response(self, res):
        # Метод для отображения полученного ответа
        self.lbl.setText(f"Response: {res}")
        self.lbl.adjustSize()
