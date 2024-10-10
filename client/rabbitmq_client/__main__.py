import sys
from PyQt5.QtWidgets import QApplication
from window import Window
from client import RMQClient, Communicate
import asyncio

def main():
    communicate = Communicate()
    app = QApplication(sys.argv)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    client = RMQClient(communicate)

    loop.run_until_complete(client.connect())
  
    window = Window(communicate)
    window.show()

    try:
        sys.exit(app.exec())
    finally:
        loop.run_until_complete(client.stop_connection())
        loop.close()    

if __name__ == "__main__":
    main()