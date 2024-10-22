import sys
from PyQt5.QtWidgets import QApplication
from window import Window
from client import RMQClient, Communicate

def main():
    communicate = Communicate()

    app = QApplication(sys.argv)
    
    client = RMQClient(communicate)
    client.start()  

    window = Window(communicate, client)
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
