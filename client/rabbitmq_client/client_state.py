from abc import ABC, abstractmethod


class ClientState(ABC):
    @abstractmethod
    def connect(self, client):
        pass

    @abstractmethod
    def disconnect(self, client):
        pass

    @abstractmethod
    def send_request(self, client, user_input, delay):
        pass

    @abstractmethod
    def receive_response(self, client, response):
        pass

    @abstractmethod
    def handle_error(self, client, error):
        pass


class DisconnectedState(ClientState):
    def connect(self, client):
        client.logger.info("Attempting to connect to RabbitMQ...")
        client.reconnect_to_rabbitmq()
        client.change_state(ConnectingState())

    def disconnect(self, client):
        client.logger.warning("Client is already disconnected.")
        
    def send_request(self, client, user_input, delay):
        client.logger.error("Cannot send request, client is disconnected.")
        
    def receive_response(self, client, response):
        client.logger.error("Cannot receive response, client is disconnected.")
        
    def handle_error(self, client, error):
        client.logger.error(f"Error occurred in DisconnectedState: {error}")


class ConnectingState(ClientState):
    def connect(self, client):
        client.logger.info("Client is already attempting to connect.")
        
    def disconnect(self, client):
        client.logger.info("Disconnecting...")
        client.connection.close()
        client.change_state(DisconnectedState())

    def send_request(self, client, user_input, delay):
        client.logger.warning("Client is connecting, cannot send requests yet.")

    def receive_response(self, client, response):
        client.logger.warning("Client is connecting, cannot receive responses yet.")
        
    def handle_error(self, client, error):
        client.logger.error(f"Error occurred in ConnectingState: {error}")


class ConnectedState(ClientState):
    def connect(self, client):
        client.logger.warning("Client is already connected.")
        
    def disconnect(self, client):
        client.logger.info("Disconnecting...")
        client.connection.close()
        client.change_state(DisconnectedState())

    def send_request(self, client, user_input, delay):
        client._send_request(user_input, delay)

    def receive_response(self, client, response):
        client.communicate.received_response.emit(response)
        
    def handle_error(self, client, error):
        client.logger.error(f"Error occurred in ConnectedState: {error}")


class ErrorState(ClientState):
    def connect(self, client):
        client.logger.info("Reconnecting to RabbitMQ...")
        client.reconnect_to_rabbitmq()
        client.change_state(ConnectingState())
        
    def disconnect(self, client):
        client.logger.info("Disconnecting due to error...")
        client.connection.close()
        client.change_state(DisconnectedState())

    def send_request(self, client, user_input, delay):
        client.logger.error("Cannot send request due to error state.")

    def receive_response(self, client, response):
        client.logger.error("Cannot receive response due to error state.")

    def handle_error(self, client, error):
        client.logger.error(f"Already in ErrorState, cannot handle further errors: {error}")