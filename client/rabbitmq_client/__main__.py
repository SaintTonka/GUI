import sys
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QFileDialog
from window import Window
from client import RMQClient, Communicate
from config_params import ConfigEditor

def main():
    
    communicate = Communicate()

    app = QApplication(sys.argv)

    config_file = QFileDialog.getOpenFileName(None, "Select Configuration File", "", "Config Files (*.ini)")[0]
    if config_file:
        settings = ConfigEditor(config_file)
        settings.exec_()   

    client = RMQClient(communicate)
    window = Window(communicate, client)

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
        print("\nProgram terminated by user.")
