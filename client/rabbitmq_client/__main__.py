import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread
from pathlib import Path
import signal

sys.path.append(str(Path(__file__).resolve().parent.parent))

from rabbitmq_client.window import Window
from rabbitmq_client.client import RMQClient


def main():
    app = QApplication(sys.argv)

    config_file = 'client_config.ini'
    client = RMQClient(config_file)

    window = Window(client, config_file)

    thread = QThread()
    client.moveToThread(thread)

    thread.started.connect(client.run)

    def cleanup():
        client.stop()
        thread.quit()
        thread.wait()


    app.aboutToQuit.connect(cleanup)

    def signal_handler(sig, frame):
        app.quit()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    window.show()

    thread.start()

    try:
        sys.exit(app.exec_())
    except SystemExit:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()