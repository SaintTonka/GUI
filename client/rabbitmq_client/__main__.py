import sys
from PyQt5.QtWidgets import QApplication
from client.rabbitmq_client.window import Window
from client.rabbitmq_client.client import Communicate

async def main():
    app = QApplication(sys.argv)

    # Создаем объект коммуникации для передачи данных между потоками
    communicate = Communicate()

    # Создаем главное окно приложения
    window = Window(communicate)
    window.show()

    # Запускаем основной цикл приложения
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()