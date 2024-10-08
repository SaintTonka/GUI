import sys
from PyQt5.QtWidgets import QApplication
from window import Window
from rabbitmq_client import RMQClient, Communicate
import asyncio

def main():
    communicate = Communicate()
    client = RMQClient(communicate)

    # Запуск асинхронного клиента RabbitMQ в отдельном потоке
    client.start()  # Правильный запуск потока

    app = QApplication(sys.argv)
    window = Window(communicate)
    window.show()

    # Запуск Qt приложения
    app.exec_()

    # Завершаем соединение при закрытии GUI
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.stop_connection())

if __name__ == "__main__":
    main()
