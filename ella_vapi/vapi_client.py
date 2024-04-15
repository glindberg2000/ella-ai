import httpx
from dotenv import load_dotenv
import os
import yaml
import logging

# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()
vapi_base_api_url = os.getenv("VAPI_API_URL", "https://api.vapi.ai")
vapi_api_key = os.getenv("VAPI_API_KEY", "")

class VAPIClient:
    def __init__(self):
        self.base_url = vapi_base_api_url
        self.api_key = vapi_api_key
        self.client = httpx.AsyncClient(headers={"Authorization": f"Bearer {self.api_key}"})
        self.configs = self.load_yaml_configs('ella_vapi/assistants.yaml')

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
