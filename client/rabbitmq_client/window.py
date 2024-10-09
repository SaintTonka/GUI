from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel, QLineEdit, QPushButton
from PyQt5.QtCore import Qt

class Window(QMainWindow):
    def __init__(self, communicate):
        super().__init__()

        self.communicate = communicate
        
        self.setWindowTitle("Client")
        self.setGeometry(100, 100, 300, 200)

        self.initUI()

        self.communicate.received_response.connect(self.display_response)

    def initUI(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Создаем макет
        layout = QVBoxLayout(central_widget)

        self.label = QLabel("Введите число:")
        self.input_field = QLineEdit()
        self.send_button = QPushButton("Отправить")

        layout.addWidget(self.label)
        layout.addWidget(self.input_field)
        layout.addWidget(self.send_button)

        self.send_button.clicked.connect(self.send_request)

    def send_request(self):
        user_input = self.input_field.text()
        if user_input.isdigit():  
            self.communicate.send_request.emit(int(user_input))
            self.input_field.clear()  

    def display_response(self, response):
        self.label.setText(f"Ответ от сервера: {response}")