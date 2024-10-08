import sys
import asyncio
from PyQt5.QtWidgets import QApplication
from window import Window
from client import Communicate, RMQClient

async def main():
    app = QApplication(sys.argv)

    # Создаем объект коммуникации для передачи данных между потоками
    communicate = Communicate()

    client = RMQClient(communicate)
    await client.connect()

    # Создаем главное окно приложения
    window = Window(communicate)
    window.show()

    # Запускаем основной цикл приложения
    sys.exit(app.exec_())

if __name__ == "__main__":
    asyncio.run(main())
