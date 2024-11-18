import sys
import uuid
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QDialog, QApplication, QComboBox
from configparser import ConfigParser

class ConfigEditor(QDialog):
    def __init__(self, config_file="client_config.ini"):
        super().__init__()
        self.config_file = config_file
        self.config = ConfigParser()

        if not self.config.read(self.config_file):
            self.create_default_config()

        self.initUI()

    def create_default_config(self):
        self.config.add_section("rabbitmq")
        self.config.set("rabbitmq", "host", "localhost")
        self.config.set("rabbitmq", "port", "5672")
        self.config.set("rabbitmq", "user", "guest")
        self.config.set("rabbitmq", "password", "guest")
        self.config.set("rabbitmq", "exchange", "bews")

        self.config.add_section("logging")
        self.config.set("logging", "level", "INFO")
        self.config.set("logging", "file", "client.log")

        self.config.add_section("client")
        # Генерация UUID только при первом запуске
        self.config.set("client", "uuid", str(uuid.uuid4()))
        self.config.set("client", "timeout_send", "10")
        self.config.set("client", "timeout_response", "10")


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
        self.log_file_input = self.create_input_field("Log File", "logging", "file", layout)

        # Client Settings
        layout.addWidget(QLabel("Client Settings"))
        self.uuid_input = self.create_input_field("UUID", "client", "uuid", layout)
        self.timeout_send_input = self.create_input_field("Timeout Send", "client", "timeout_send", layout)
        self.timeout_response_input = self.create_input_field("Timeout Response", "client", "timeout_response", layout)

        # Save Button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

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
        self.config.set("logging", "file", self.log_file_input.text())
        self.config.set("client", "uuid", self.uuid_input.text())

        try:
            timeout_send = int(self.timeout_send_input.text())
            timeout_response = int(self.timeout_response_input.text())

            if timeout_send < 0 or timeout_response < 0:
                raise ValueError("Timeouts must be positive.")

            self.config.set("client", "timeout_send", str(timeout_send))
            self.config.set("client", "timeout_response", str(timeout_response))

            with open(self.config_file, "w") as configfile:
                self.config.write(configfile)
            QMessageBox.information(self, "Success", "Settings saved successfully!")
        except ValueError as e:
            QMessageBox.information(self, "ERROR", f"Invalid input: {str(e)}")
        except Exception as e:
            QMessageBox.information(self, "ERROR", f"Failed to save settings: {str(e)}")


    def run(self):
        return self.exec_() == QDialog.accepted

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = ConfigEditor()
    if editor.run():
        print("Settings saved")
    else:
        print("Settings not saved")

    sys.exit(app.exec_())
