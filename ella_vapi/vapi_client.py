import os
import yaml
import logging
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

vapi_base_api_url = os.getenv("VAPI_API_URL", "https://api.vapi.ai")
vapi_api_key = os.getenv("VAPI_API_KEY", "")

class VAPIClient:
    def __init__(self):
        self.base_url = vapi_base_api_url
        self.api_key = vapi_api_key
        self.client = httpx.AsyncClient(headers={"Authorization": f"Bearer {self.api_key}"})
        self.configs = self.load_yaml_configs('ella_vapi/assistants.yaml')
        self.phone_number_id = "90c7adbe-7c4a-4c4c-9447-08c4b7fa02a9"  # The ID of your Vapi phone number

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
    
    async def list_assistants(self):
        url = f"{self.base_url}/assistant"
        response = await self.client.get(url)
        return response.json() if response.is_success else {"error": "Request failed", "status_code": response.status_code}
 
    async def create_assistant(self, preset_name, customizations={}):
        template = self.get_template(preset_name)
        final_config = self.apply_customizations(template, customizations)
        logging.info(f"Creating assistant with config: {final_config}")
        url = f"{self.base_url}/assistant"
        response = await self.client.post(url, json=final_config)
        return response.json() if response.is_success else {"error": "Request failed", "status_code": response.status_code, "details": response.text}

    async def start_call(self,
                         name: str,
                         assistant_id: str,
                         customer_number: str,
                         assistant_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Start a call using the Vapi REST API.

        :param name: Name of the call (for reference)
        :param assistant_id: ID of the existing assistant to use
        :param customer_number: Phone number of the customer to call
        :param assistant_overrides: Overrides for the assistant settings
        :return: API response as a dictionary
        """
        payload = {
            "name": name,
            "assistantId": assistant_id,
            "phoneNumberId": self.phone_number_id,
            "assistantOverrides": assistant_overrides,
            "customer": {"number": customer_number}
        }

        # Remove None values from payload
        payload = {k: v for k, v in payload.items() if v is not None}

        logging.info(f"Starting call with payload: {payload}")

        response = await self.client.post(f"{self.base_url}/call", json=payload)
        if response.is_success:
            return response.json()
        else:
            logging.error(f"HTTP error occurred: {response.status_code} {response.text}")
            return {"error": "Request failed", "status_code": response.status_code, "details": response.text}

    async def stop_call(self, call_id: str) -> Dict[str, Any]:
        """
        Stop an ongoing call.

        :param call_id: ID of the call to stop
        :return: API response as a dictionary
        """
        response = await self.client.delete(f"{self.base_url}/call/{call_id}")
        if response.is_success:
            return {"success": True, "message": "Call stopped successfully"}
        else:
            logging.error(f"HTTP error occurred: {response.status_code} {response.text}")
            return {"error": "Request failed", "status_code": response.status_code, "details": response.text}

    async def close(self):
        await self.client.aclose()

async def main():
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
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
# import httpx
# from dotenv import load_dotenv
# import os
# import yaml
# import logging

# # Set up basic configuration for logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# load_dotenv()
# vapi_base_api_url = os.getenv("VAPI_API_URL", "https://api.vapi.ai")
# vapi_api_key = os.getenv("VAPI_API_KEY", "")

# class VAPIClient:
#     def __init__(self):
#         self.base_url = vapi_base_api_url
#         self.api_key = vapi_api_key
#         self.client = httpx.AsyncClient(headers={"Authorization": f"Bearer {self.api_key}"})
#         self.configs = self.load_yaml_configs('ella_vapi/assistants.yaml')

#     def load_yaml_configs(self, file_path):
#         with open(file_path, 'r') as file:
#             return yaml.safe_load(file)

#     def get_template(self, preset_name):
#         return self.configs['templates'].get(preset_name, {})
    
#     def apply_customizations(self, base_config, customizations):
#         for key, value in customizations.items():
#             if isinstance(value, dict):
#                 base_config[key] = self.apply_customizations(base_config.get(key, {}), value)
#             else:
#                 base_config[key] = value
#         return base_config
    
#     async def list_assistants(self):
#         url = f"{self.base_url}/assistant"
#         response = await self.client.get(url)
#         return response.json() if response.is_success else {"error": "Request failed", "status_code": response.status_code}
 
#     async def create_assistant(self, preset_name, customizations={}):
#         template = self.get_template(preset_name)
#         final_config = self.apply_customizations(template, customizations)

#         logging.info(f"Creating assistant with config: {final_config}")
#         url = f"{self.base_url}/assistant"
#         response = await self.client.post(url, json=final_config)
#         return response.json() if response.is_success else {"error": "Request failed", "status_code": response.status_code, "details": response.text}

#     async def close(self):
#         await self.client.aclose()



# async def main():
#     client = VAPIClient()
#     customizations = {
#         "voice": {
#             "voiceId": "custom-voice"
#         },
#         "name": "Asteria preset"
#     }
#     result = await client.create_assistant('asteria', customizations)
#     print(result)
#     await client.close()
    
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main())