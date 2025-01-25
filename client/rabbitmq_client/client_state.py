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
        try:
            client.connect_to_rabbitmq()
            client.change_state(ConnectedState())
        except Exception as e:
            client.logger.error(f"Error while connecting: {e}")
            client.change_state(ErrorState())

    def disconnect(self, client):
        client.logger.warning("Client is already disconnected.")

    def send_request(self, client, user_input, delay):
        client.logger.error("Cannot send request, client is disconnected.")

    def receive_response(self, client, response):
        client.logger.error("Cannot receive response, client is disconnected.")

    def handle_error(self, client, error):
        client.logger.error(f"Error occurred in DisconnectedState: {error}")
        client.change_state(ErrorState())

class ConnectingState(ClientState):
    def connect(self, client):
        client.logger.info("Client is already attempting to connect.")
        if not isinstance(client.state, ConnectedState):
            client.change_state(ConnectedState())

    def disconnect(self, client):
        client.logger.info("Disconnecting...")
        if client.connection and client.connection.is_open:
            client.connection.close()
        client.change_state(DisconnectedState())

    def send_request(self, client, user_input, delay):
        client.logger.warning("Client is connecting, queuing request.")
        client.send_request(user_input, delay)
        client.chanhe_state(PendingResponseState())

    def receive_response(self, client, response):
        client.logger.warning("Client is connecting, cannot receive responses yet.")

    def handle_error(self, client, error):
        client.logger.error(f"Error occurred in ConnectingState: {error}")
        client.change_state(ErrorState())

class ConnectedState(ClientState):
    def connect(self, client):
        client.logger.warning("Client is already connected.")

    def disconnect(self, client):
        client.logger.info("Disconnecting...")
        client.connection.close()
        client.change_state(DisconnectedState())

    def send_request(self, client, user_input, delay):
        client.logger.debug(f"Sending request: {user_input} with delay: {delay}")

    def receive_response(self, client, response):
        client.logger.debug(f"Sending request:")
        try:
            client.received_response.emit(response)
        except Exception as e:
            client.logger.error(f"Error receiving response: {e}")

    def handle_error(self, client, error):
        client.logger.error(f"Error occurred in ConnectedState: {error}")
        client.change_state(ErrorState())      

class PendingResponseState(ClientState):
    def connect(self, client):
        client.logger.warning("Already connected and awaiting a response.")

    def disconnect(self, client):
        client.logger.info("Disconnecting while waiting for a response...")
        client.connection.close()
        client.change_state(DisconnectedState())

    def send_request(self, client, user_input, delay):
        client.logger.warning("Request denied: awaiting a previous response.")

    def receive_response(self, client, response):
        client.logger.info("Response received, processing...")
        client.received_response.emit(response)
        client.change_state(ConnectedState())

    def handle_error(self, client, error):
        client.logger.error(f"Error while awaiting response: {error}")
        client.change_state(ErrorState())

class ErrorSendState(ClientState):
    def connect(self, client):
        client.logger.info("Retrying connection after send error...")
        client.connect_to_rabbitmq()
        client.change_state(ConnectingState())

    def disconnect(self, client):
        client.logger.info("Disconnecting due to send error...")
        if client.connection and client.connection.is_open:
            client.connection.close()
        client.change_state(DisconnectedState())

    def send_request(self, client, user_input, delay):
        client.logger.error("Cannot send request due to send error.")

    def receive_response(self, client, response):
        client.logger.error("Unexpected response in ErrorSendState. Ignoring response.")

    def handle_error(self, client, error):
        client.logger.error(f"Error occurred in ErrorSendState: {error}")
        client.change_state(ErrorState())

class ErrorState(ClientState):
    def connect(self, client):
        if client.connection and client.connection.is_open:
            client.logger.info("Connection already open. Moving to ConnectedState.")
            client.change_state(ConnectedState())
        else:
            try:
                client.logger.info("Reconnecting to RabbitMQ...")
                client.connect_to_rabbitmq()
                client.change_state(ConnectingState())
            except Exception as e:
                client.logger.error(f"Reconnection failed: {e}")
                client.change_state(ErrorState())

    def disconnect(self, client):
        client.logger.info("Disconnecting due to error...")
        if client.connection and client.connection.is_open:
            client.connection.close()
        client.change_state(DisconnectedState())

    def send_request(self, client, user_input, delay):
        client.logger.error("Cannot send request due to error state.")

    def receive_response(self, client, response):
        client.logger.error("Cannot receive response due to error state.")

    def handle_error(self, client, error):
        client.logger.error(f"Already in ErrorState, cannot handle further errors: {error}")
