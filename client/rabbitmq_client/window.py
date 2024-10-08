import sys 

sys.path.append(r"Z:\Qt\5.15.2\mingw81_64\bin")
sys.path.append(r'C:\Users\username\AppData\Local\Programs\Python\PythonXX\Lib\site-packages\PyQt5')

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QLabel, QLineEdit, QPushButton
from PyQt5.QtCore import pyqtSignal, QObject


class Window(QMainWindow):

    def __init__(self, communicate):
        super().__init__()

        self.setGeometry(500, 500, 500, 500)
        self.setWindowTitle("Input")

        self.button = QtWidgets.QPushButton(self)
        self.button.setText("Enter your number")
        self.button.move(30, 150)
        self.button.setMinimumWidth(150)
        self.button.clicked.connect(self.send_req)
        
        self.qle = QLineEdit(self)
        self.qle.move(60, 100)
        self.qle.setPlaceholderText("Enter a number")
        
        self.lbl = QLabel(self)
        self.lbl.move(60, 40)
        self.lbl.setText("Answer: ")
        
        
        self.communicate = communicate

        self.communicate.received_response.connect(self.display_response)

    # def onChanged(self, text):

    #     self.lbl.setText(text)
    #     self.lbl.adjustSize()

    def send_req(self):
        try:
            user_input = int(self.qle.text())
        except ValueError:
            self.lbl.setText("Wrong input")
            self.lbl.adjustSize()
            return        

    def display_response(self, res):
        self.lbl.setText(f"Response: {res}")
        self.lbl.adjustSize()   
