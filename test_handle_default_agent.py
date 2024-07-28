import unittest
import os
import logging
from unittest.mock import MagicMock, patch
from ella_memgpt.extendedRESTclient import ExtendedRESTClient
from memgpt.client.admin import Admin as AdminRESTClient
from agent_creation import handle_default_agent

# Configuration
BASE_URL = os.getenv("MEMGPT_API_URL", "http://localhost:8080")
MASTER_API_KEY = os.getenv("MEMGPT_SERVER_PASS", "ilovememgpt1")
default_preset = os.getenv('DEFAULT_PRESET', 'ella_3')

# Custom tools for testing purposes
def custom_tool_1(self):
    return "Custom tool 1 executed"

def custom_tool_2(self):
    return "Custom tool 2 executed"

CUSTOM_TOOLS = [custom_tool_1, custom_tool_2]

class TestHandleDefaultAgent(unittest.TestCase):

    @patch('ella_memgpt.extendedRESTclient.ExtendedRESTClient')
    @patch('memgpt.client.admin.AdminRESTClient')
    def test_handle_default_agent(self, MockAdminRESTClient, MockExtendedRESTClient):
        # Setup
        mock_admin_api = MockAdminRESTClient.return_value
        mock_user_api = MockExtendedRESTClient.return_value

        # Mock responses for admin API
        mock_admin_api.create_user.return_value = MagicMock(user_id="test_user_id", api_key="test_api_key")
        
        # Mock responses for user API
        mock_user_api.list_agents.return_value = MagicMock(num_agents=0, agents=[])
        mock_user_api.create_agent.return_value = MagicMock(id="test_agent_id")
        mock_user_api.create_tool = MagicMock()

        # Mock functions for memory creation
        memory = MagicMock()
        
        with patch('memgpt.memory.ChatMemory', return_value=memory):
            # Call the function to test
            memgpt_user_id = "test_user_id"
            user_api_key = "test_api_key"
            result = handle_default_agent(memgpt_user_id, mock_user_api)

        # Assertions
        self.assertEqual(result, "test_agent_id")
        mock_user_api.create_agent.assert_called_once()
        self.assertEqual(mock_user_api.create_tool.call_count, len(CUSTOM_TOOLS))

if __name__ == '__main__':
    unittest.main()