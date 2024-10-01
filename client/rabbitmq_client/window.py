from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QLabel, QLineEdit
import sys



class Window(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setGeometry(500, 500, 500, 500)
        self.setWindowTitle("Input")
        self.button = QtWidgets.QPushButton(self)
        self.qle = QLineEdit(self)
        self.lbl = QLabel(self)
        self.initUI()


    def initUI(self):

        self.button.setText("Enter your number")
        self.button.move(30, 150)
        self.button.setMinimumWidth(150)

        self.qle.move(60, 100)
        self.lbl.move(60, 40)

        self.qle.textChanged[str].connect(self.onChanged)

        self.setGeometry(250, 250, 250, 250)
        self.setWindowTitle('Enter')
        self.show()


    def onChanged(self, text):

        self.lbl.setText(text)
        self.lbl.adjustSize()


if __name__ == '__main__':

    app = QApplication(sys.argv)
    ex = Window()
    sys.exit(app.exec_())
