import sys
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QDialog, QApplication
from configparser import ConfigParser

class ConfigEditor(QDialog):
    def __init__(self, config_file):
        super().__init__()
        self.config_file = config_file
        self.config = ConfigParser()
        self.config.read(self.config_file)
        
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("RabbitMQ Settings"))
        self.host_input = self.create_input_field("Host", "rabbitmq", "host", layout)
        self.port_input = self.create_input_field("Port", "rabbitmq", "port", layout)
        self.user_input = self.create_input_field("User", "rabbitmq", "user", layout)
        self.password_input = self.create_input_field("Password", "rabbitmq", "password", layout)
        self.exchange_input = self.create_input_field("Exchange", "rabbitmq", "exchange", layout)

        layout.addWidget(QLabel("Logging Settings"))
        self.log_level_input = self.create_input_field("Level", "logging", "level", layout)
        self.log_file_input = self.create_input_field("File", "logging", "file", layout)

        layout.addWidget(QLabel("Client Settings"))
        self.uuid_input = self.create_input_field("UUID", "client", "uuid", layout)
        self.timeout_send_input = self.create_input_field("Timeout Send", "client", "timeout_send", layout)
        self.timeout_response_input = self.create_input_field("Timeout Response", "client", "timeout_response", layout)

        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

        self.setLayout(layout)
        self.setWindowTitle("Configuration Editor")
        self.show()

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

        self.config.set("logging", "level", self.log_level_input.text())
        self.config.set("logging", "file", self.log_file_input.text())

        self.config.set("client", "uuid", self.uuid_input.text())
        num1 = self.timeout_send_input.text()
        num2 = self.timeout_response_input.text()
        self.config.set("client", "timeout_send", num1)
        self.config.set("client", "timeout_response", num2)


        if  (not num1.isdigit() or not num2.isdigit()) or (int(num1) < 0 or int(num2) < 0):
            QMessageBox.information(self, "ERROR", "Use correct digits for timers!")
            return

        with open(self.config_file, "w") as configfile:
            self.config.write(configfile)   

        QMessageBox.information(self, "Success", "Settings saved successfully!")

    def run(self):
        return self.exec_() == QDialog.accepted

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = ConfigEditor()
    if editor.run():
        print("Saved")
    else:
        print("Not Saves")

    sys.exit(app.exec_())        

        

        


    