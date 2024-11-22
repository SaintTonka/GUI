import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from rabbitmq_client.window import Window
from rabbitmq_client.client import RMQClient


def main():
    app = QApplication(sys.argv)

    config_file = 'client_config.ini'
    client = RMQClient(config_file)
    window = Window(client, config_file)

    client.start_client()  # Запускаем клиента

    window.show()

    try:
        sys.exit(app.exec_())
    finally:
        client.stop_client() 

if __name__ == "__main__":
    main()

