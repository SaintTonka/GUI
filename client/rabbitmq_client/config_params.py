import sys
import pathlib
import uuid
import logging
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QDialog, QApplication, QComboBox
from configparser import ConfigParser
from PyQt5.QtCore import pyqtSignal


class ConfigEditor(QDialog):
    config_saved = pyqtSignal()
    editing_allowed = True

    def __init__(self, config_file="client_config.ini", read_only = False):
        super().__init__()
        self.config_file = pathlib.Path(__file__).parent.parent / "client_config.ini"
        self.config = ConfigParser()

        if not self.config.read(self.config_file):
            self.create_default_config()

        self.read_only = read_only    

        self.initUI()

        # Настройка логирования
        self.set_logging_level()
        self.update_editability()

    def create_default_config(self):
        self.config.add_section("rabbitmq")
        self.config.set("rabbitmq", "host", "localhost")
        self.config.set("rabbitmq", "port", "5672")
        self.config.set("rabbitmq", "user", "guest")
        self.config.set("rabbitmq", "password", "guest")
        self.config.set("rabbitmq", "exchange", "bews")

        self.config.add_section("logging")
        self.config.set("logging", "level", "INFO")

        self.config.add_section("client")
        self.config.set("client", "uuid", str(uuid.uuid4()))
        self.config.set("client", "timeout_connect", "10")

        self.config.add_section("server")
        self.config.set("server", "timeout_response", "10")

    def initUI(self):
        layout = QVBoxLayout()

        # RabbitMQ Settings
        layout.addWidget(QLabel("RabbitMQ Settings"))
        self.host_input = self.create_input_field("Host", "rabbitmq", "host", layout)
        self.port_input = self.create_input_field("Port", "rabbitmq", "port", layout)
        self.user_input = self.create_input_field("User", "rabbitmq", "user", layout)
        self.password_input = self.create_input_field("Password", "rabbitmq", "password", layout)
        self.exchange_input = self.create_input_field("Exchange", "rabbitmq", "exchange", layout)

        # Logging Settings
        layout.addWidget(QLabel("Logging Settings"))
        self.log_level_input = QComboBox(self)
        self.log_level_input.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_input.setCurrentText(self.config.get("logging", "level", fallback="INFO"))
        layout.addWidget(QLabel("Logging Level"))
        layout.addWidget(self.log_level_input)

        # Client Settings
        layout.addWidget(QLabel("Client Settings"))
        self.uuid_input = self.create_input_field("UUID", "client", "uuid", layout)

        self.uuid_button = QPushButton("Сгенерировать UUID", self)
        self.uuid_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.uuid_button.clicked.connect(self.generate_uuid) 
        layout.addWidget(self.uuid_button)

        self.timeout_connect_input = self.create_input_field("Timeout Connect", "client", "timeout_connect", layout)

        layout.addWidget(QLabel("Server Settings"))
        self.timeout_response_input = self.create_input_field("Timeout Response", "server", "timeout_response", layout)

        # Save Button
        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self.save_settings)
        layout.addWidget(self.save_button)

        self.setLayout(layout)
        self.setWindowTitle("Configuration Editor")
    
    def create_input_field(self, label, section, option, layout):
        layout.addWidget(QLabel(label))
        line_edit = QLineEdit()
        line_edit.setText(self.config.get(section, option, fallback=""))
        layout.addWidget(line_edit)
        return line_edit

    def save_settings(self):
        self.config.set("rabbitmq", "host", self.host_input.text())
        self.config.set("rabbitmq", "port", self.port_input.text())
        self.config.set("rabbitmq", "user", self.user_input.text())
        self.config.set("rabbitmq", "password", self.password_input.text())
        self.config.set("rabbitmq", "exchange", self.exchange_input.text())
        self.config.set("logging", "level", self.log_level_input.currentText())
        self.config.set("client", "uuid", self.uuid_input.text())

        try:
            timeout_connect = int(self.timeout_connect_input.text())
            timeout_response = int(self.timeout_response_input.text())

            if timeout_connect < 0 or timeout_response < 0:
                raise ValueError("Timeouts must be positive.")

            self.config.set("client", "timeout_connect", str(timeout_connect))
            self.config.set("server", "timeout_response", str(timeout_response))

            with open(self.config_file, "w") as configfile:
                self.config.write(configfile)

            QMessageBox.information(self, "Success", "Настройки сохранены!")

            self.config_saved.emit()
            logging.info("The signal is here")

        except ValueError as e:
            QMessageBox.information(self, "ERROR", f"Invalid input: {str(e)}")
        except Exception as e:
            QMessageBox.information(self, "ERROR", f"Failed to save settings: {str(e)}")

    def generate_uuid(self):
        """Генерирует новый UUID и обновляет поле ввода."""
        new_uuid = str(uuid.uuid4())
        self.uuid_input.setText(new_uuid)

    def set_logging_level(self):
        """Настроить уровень логирования в зависимости от конфигурации."""
        level = self.config.get('logging', 'level', fallback='INFO').upper()
        levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }

        logging.getLogger().handlers.clear()

        logging.basicConfig(level=levels.get(level, logging.INFO))

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)  
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logging.getLogger().addHandler(console_handler)

    def update_editability(self):
        """Обновляем доступность редактирования в зависимости от флага read_only."""
        if self.read_only:
            self.set_ui_state(False) 
        else:
            self.set_ui_state(True)    

    def set_ui_state(self, enabled):
        """Управляет состоянием интерфейса (доступность для редактирования)."""
        inputs = [
            self.host_input, self.port_input, self.user_input, self.password_input,
            self.exchange_input, self.uuid_input, self.timeout_connect_input, self.timeout_response_input
        ]

        for input_widget in inputs:
            input_widget.setReadOnly(not enabled) 

        self.log_level_input.setDisabled(not enabled) 
        self.uuid_button.setDisabled(not enabled)
        self.save_button.setDisabled(not enabled)