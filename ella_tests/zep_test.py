# Import necessary modules from Zep Python SDK and ChainLit.
import os
from zep_python import ZepClient
from zep_python.memory import Memory, Session
from zep_python.message import Message
from zep_python.user import CreateUserRequest




# Retrieve API keys from environment variables.
ZEP_API_KEY = os.environ.get("ZEP_API_KEY")

print("zep key:",ZEP_API_KEY)

zep = ZepClient(api_key=ZEP_API_KEY)
# Get all attributes of the module
module_attributes = dir(zep)
# Optionally, you can filter to only get class names
module_classes = [attr for attr in module_attributes if attr[0].isupper()]

print("Available classes in the module:")
print(module_classes)
