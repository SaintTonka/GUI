import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread
from rabbitmq_client.window import Window

from rabbitmq_client.client import RMQClient, Communicate


def main():
    communicate = Communicate()

    app = QApplication(sys.argv)

    config_file = 'client_config.ini'

    thread = QThread()
    client = RMQClient(communicate, config_file)
    window = Window(communicate, client, config_file)  

    client.start()
    window.show()

    try:
        sys.exit(app.exec())
    finally:
        client.stop_client()
        print("Application closed")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nПрограмма остановлена пользователем.")
