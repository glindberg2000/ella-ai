import logging

class InputProcessor:
    def __init__(self):
        pass

    def handle_input(self, message_content: str, source: str) -> str:
        """
        Handle the input by normalizing and processing it based on the source.

        Parameters:
        - message_content: The raw input message.
        - source: The source of the input (e.g., "chainlit", "email", "voice").

        Returns:
        - str: The processed response.
        """
        # Normalize the input based on the source
        normalized_message = self._normalize_input(message_content, source)
        logging.info(f"Normalized message from {source}: {normalized_message}")

        # Process the normalized message
        response = self._process_message(normalized_message)
        logging.info(f"Processed response: {response}")

        return response

    def _normalize_input(self, message_content: str, source: str) -> str:
        """
        Normalize the input data based on the source.

        Parameters:
        - message_content: The raw input message.
        - source: The source of the input (e.g., "chainlit", "email", "voice").

        Returns:
        - str: The normalized message.
        """
        logging.info(f"Normalizing input from {source}")
        # Example normalization logic based on source
        if source == "chainlit":
            return message_content.strip().lower()
        elif source == "email":
            return message_content.replace("\n", " ").strip().lower()
        elif source == "voice":
            return message_content.strip().capitalize()
        else:
            return message_content.strip()

    def _process_message(self, normalized_message: str) -> str:
        """
        Process the normalized message to determine the response.

        Returns:
        - str: The response message.
        """
        logging.info("Processing message")
        if "email" in normalized_message:
            return "This seems to be an email request."
        elif "call" in normalized_message:
            return "This seems to be a voice call request."
        else:
            return f"Echo: {normalized_message}"