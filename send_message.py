import requests
import base64
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

appId = os.getenv('SINCH_APP_ID')
accessKey = os.getenv('SINCH_ACCESS_KEY')
accessSecret = os.getenv('SINCH_ACCESS_SECRET')
projectId = os.getenv('SINCH_PROJECT_ID')
channel = os.getenv('SINCH_CHANNEL')
identity = os.getenv('SINCH_IDENTITY')

url = "https://us.conversation.api.sinch.com/v1/projects/" + projectId + "/messages:send"

data = accessKey + ":" + accessSecret
encodedBytes = base64.b64encode(data.encode("utf-8"))
accessToken = str(encodedBytes, "utf-8")

payload = {
  "app_id": appId,
  "recipient": {
      "identified_by": {
          "channel_identities": [
            {
                "channel": channel,
                "identity": identity
            }  
            ]
      }
  },
  "message": {
      "text_message": {
          "text": "Text message from Sinch Conversation API."
      }
  }  
}

headers = {
  "Content-Type": "application/json",
  "Authorization": "Basic " + accessToken
}

response = requests.post(url, json=payload, headers=headers)

data = response.json()
print(data)