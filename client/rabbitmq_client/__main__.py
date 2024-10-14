import sys
from PyQt5.QtWidgets import QApplication
from window import Window
from client import RMQClient, Communicate

def main():
    communicate = Communicate()

    app = QApplication(sys.argv)
    
    client = RMQClient(communicate)
    client.start()  

    window = Window(communicate)
    window.show()

    try:
        sys.exit(app.exec())
    finally:
        client.quit()
        client.wait()  
        print("Application closed")

if __name__ == "__main__":
    main()
