#vapi_client.py
import os
import yaml
import logging
import httpx
import jwt
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import uuid
import phonenumbers
from phonenumbers import NumberParseException

# Load environment variables
load_dotenv()

# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VAPIClient:
    def __init__(self):
        self.base_url = os.getenv("VAPI_API_URL", "https://api.vapi.ai")
        self.org_id = os.getenv("VAPI_ORG_ID")
        self.private_key = os.getenv("VAPI_PRIVATE_KEY")
        self.vapi_tools_path = os.getenv('VAPI_TOOLS_PATH', '.')
        
        if not self.org_id:
            raise ValueError("VAPI_ORG_ID environment variable is not set")
        if not self.private_key:
            raise ValueError("VAPI_PRIVATE_KEY environment variable is not set")
        
        # Validate private key format
        try:
            uuid.UUID(self.private_key)
        except ValueError:
            raise ValueError("VAPI_PRIVATE_KEY is not in a valid UUID format")
        
        self.token = None
        self.token_expiry = 0
        self.client = httpx.AsyncClient()
        self.phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID")  # The ID of your Vapi phone number
        config_file_path = os.path.join(self.vapi_tools_path, 'assistants.yaml')
        self.configs = self.load_yaml_configs(config_file_path)

    def load_yaml_configs(self, file_path):
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)

    def get_template(self, preset_name):
        return self.configs['templates'].get(preset_name, {})
    
    def apply_customizations(self, base_config, customizations):
        for key, value in customizations.items():
            if isinstance(value, dict):
                base_config[key] = self.apply_customizations(base_config.get(key, {}), value)
            else:
                base_config[key] = value
        return base_config

    def generate_jwt_token(self):
        now = datetime.utcnow()
        expiration = now + timedelta(hours=1)
        payload = {
            "orgId": self.org_id,
            "iat": int(now.timestamp()),
            "exp": int(expiration.timestamp())
        }
        try:
            logging.info(f"Generating JWT token with payload: {payload}")
            # Use the private key as a secret for HMAC-based JWT
            self.token = jwt.encode(payload, self.private_key, algorithm="HS256")
            self.token_expiry = expiration.timestamp()
            logging.info("JWT token generated successfully")
        except Exception as e:
            logging.error(f"Failed to generate JWT token: {str(e)}")
            raise

    async def get_headers(self) -> Dict[str, str]:
        if not self.token or time.time() > self.token_expiry:
            self.generate_jwt_token()
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    async def make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint}"
        headers = await self.get_headers()
        
        async with self.client as client:
            response = await client.request(method, url, json=data, headers=headers)
            if response.is_success:
                return response.json()
            else:
                logging.error(f"HTTP error occurred: {response.status_code} {response.text}")
                return {"error": "Request failed", "status_code": response.status_code, "details": response.text}


    async def list_assistants(self):
        return await self.make_request("GET", "assistant")
 
    async def create_assistant(self, preset_name, customizations={}):
        template = self.get_template(preset_name)
        final_config = self.apply_customizations(template, customizations)
        logging.info(f"Creating assistant with config: {final_config}")
        return await self.make_request("POST", "assistant", final_config)

    async def start_call(self,
                         name: str,
                         assistant_id: str,
                         customer_number: str,
                         assistant_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Validate and format the phone number to E.164
        customer_number = self.format_to_e164(customer_number)
        if not customer_number:
            logging.error("Invalid customer phone number provided.")
            return {"error": "Invalid customer phone number."}

        # Prepare payload
        payload = {
            "name": name,
            "assistantId": assistant_id,
            "phoneNumberId": self.phone_number_id,
            "assistantOverrides": assistant_overrides,
            "customer": {"number": customer_number}
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        logging.info(f"Starting call with payload: {payload}")
        return await self.make_request("POST", "call", payload)

    def format_to_e164(self, phone_number: str) -> Optional[str]:
        """
        Formats the given phone number to E.164 format.
        
        Args:
            phone_number (str): The phone number to format.
        
        Returns:
            Optional[str]: The formatted phone number in E.164 format, or None if invalid.
        """
        try:
            parsed_number = phonenumbers.parse(phone_number, "US")  # Default to "US", change as needed
            if phonenumbers.is_possible_number(parsed_number) and phonenumbers.is_valid_number(parsed_number):
                return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
            else:
                logging.warning(f"Phone number is not valid or possible: {phone_number}")
                return None
        except NumberParseException as e:
            logging.error(f"Error parsing phone number: {phone_number}, error: {e}")
            return None

    async def close(self):
        """
        Close the HTTP client to release resources.
        """
        await self.client.aclose()
        logging.info("VAPI client closed successfully.")

        

async def main():
    try:
        client = VAPIClient()
        customizations = {
            "voice": {
                "voiceId": "custom-voice"
            },
            "name": "Asteria preset"
        }
        result = await client.create_assistant('asteria', customizations)
        print(result)
        await client.close()
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

