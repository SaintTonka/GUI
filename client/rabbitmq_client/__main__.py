import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread
from pathlib import Path
import signal
from rabbitmq_client.window import Window
from rabbitmq_client.client import RMQClient

class MainWindow(Window):
    def __init__(self, client):
        super().__init__(client)
        self.client = client

def main():
    app = QApplication(sys.argv)

    client = RMQClient()

    window = MainWindow(client)  

    thread = QThread()
    client.moveToThread(thread)

    thread.started.connect(client.run)

    window.show()

    thread.start()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
