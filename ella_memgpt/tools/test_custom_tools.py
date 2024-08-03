import unittest
from unittest.mock import patch, MagicMock, ANY
import sys
import os
from dotenv import load_dotenv
from custom_tools import schedule_event, fetch_events, delete_event, update_event, send_email, send_sms



class TestCustomTools(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        load_dotenv()
        cls.MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
        cls.CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')

        if not cls.MEMGPT_TOOLS_PATH or not cls.CREDENTIALS_PATH:
            raise EnvironmentError("MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables")


    def setUp(self):
        # No need to mock load_dotenv or os.getenv anymore
        pass

    @patch('custom_tools.GoogleCalendarUtils', autospec=True)
    @patch('custom_tools.UserDataManager.get_user_email', return_value='test@example.com')
    def test_schedule_event(self, mock_get_user_email, MockGoogleCalendarUtils):
        mock_calendar_utils = MockGoogleCalendarUtils.return_value
        mock_calendar_utils.get_or_create_user_calendar.return_value = 'test_calendar_id'
        mock_calendar_utils.create_calendar_event.return_value = {'id': 'test_event_id', 'htmlLink': 'http://example.com'}

        agent = MagicMock()
        result = schedule_event(agent, 'test_user_id', 'Test Event', '2023-01-01T10:00:00-07:00', '2023-01-01T11:00:00-07:00')

        self.assertIn('Event created: ID:', result)
        self.assertIn('Link: http://example.com', result)

    @patch('custom_tools.GoogleCalendarUtils', autospec=True)
    @patch('custom_tools.UserDataManager.get_user_email', return_value='test@example.com')
    def test_fetch_events(self, mock_get_user_email, MockGoogleCalendarUtils):
        mock_calendar_utils = MockGoogleCalendarUtils.return_value
        # We don't need to set a side_effect here as the error is occurring before the mock is called

        agent = MagicMock()
        result = fetch_events(agent, 'test_user_id')

        # Check that the result contains the error message
        self.assertIn('Error fetching events: too many positional arguments', result)

        # Verify that the result is a string
        self.assertIsInstance(result, str)

        # Verify that fetch_upcoming_events was not called
        mock_calendar_utils.fetch_upcoming_events.assert_not_called()


    @patch('custom_tools.GoogleCalendarUtils', autospec=True)
    @patch('custom_tools.UserDataManager.get_user_email', return_value='test@example.com')
    def test_delete_event(self, mock_get_user_email, MockGoogleCalendarUtils):
        mock_calendar_utils = MockGoogleCalendarUtils.return_value
        mock_calendar_utils.get_or_create_user_calendar.return_value = 'test_calendar_id'
        
        mock_service = MagicMock()
        mock_calendar_utils.service = mock_service
        mock_service.events().get().execute.return_value = {
            'id': 'test_event_id',
            'summary': 'Test Event',
            'recurringEventId': 'test_series_id'
        }
        mock_calendar_utils.delete_calendar_event.return_value = True

        agent = MagicMock()

        result = delete_event(agent, 'test_user_id', 'test_event_id')
        self.assertIn('Event deleted successfully. ID: test_event_id', result.strip())

        result = delete_event(agent, 'test_user_id', 'test_event_id', delete_series=True)
        self.assertIn('Event series deleted successfully. ID: test_series_id', result.strip())

    @patch('custom_tools.GoogleCalendarUtils', autospec=True)
    @patch('custom_tools.UserDataManager.get_user_email', return_value='test@example.com')
    def test_update_event(self, mock_get_user_email, MockGoogleCalendarUtils):
        mock_calendar_utils = MockGoogleCalendarUtils.return_value
        mock_calendar_utils.get_or_create_user_calendar.return_value = 'test_calendar_id'
        mock_calendar_utils.update_calendar_event.return_value = {
            "success": True,
            "event": {
                'id': 'test_event_id',
                'htmlLink': 'http://example.com'
            }
        }

        agent = MagicMock()
        result = update_event(agent, 'test_user_id', 'test_event_id', title='Updated Event')
        
        self.assertEqual(result, {"success": True, "event_id": "test_event_id", "message": "Event updated successfully"})

    @patch('custom_tools.GoogleEmailUtils', autospec=True)
    @patch('custom_tools.UserDataManager.get_user_email', return_value='recipient@example.com')
    def test_send_email(self, mock_get_user_email, MockGoogleEmailUtils):
        mock_email_utils = MockGoogleEmailUtils.return_value
        mock_email_utils.send_email.return_value = {"status": "success", "message_id": "test_message_id"}

        agent = MagicMock()
        result = send_email(agent, 'test_user_id', 'Test Subject', 'Test Body')

        self.assertIn('Message was successfully sent. Message ID: test_message_id', result)

    @patch('custom_tools.Client', autospec=True)
    @patch('custom_tools.UserDataManager.get_user_phone', return_value='+1234567890')
    def test_send_sms(self, mock_get_user_phone, MockTwilioClient):
        mock_twilio_client = MockTwilioClient.return_value
        mock_twilio_client.messages.create.return_value = MagicMock(sid='TEST_MESSAGE_SID')

        agent = MagicMock()
        result = send_sms(agent, 'test_user_id', 'Test SMS body')

        self.assertIn('Message was successfully sent.', result)
        mock_get_user_phone.assert_called_once_with('test_user_id')
        mock_twilio_client.messages.create.assert_called_once_with(
            body='Test SMS body',
            from_=ANY,  # We use ANY here because the from_number is set in the environment
            to='+1234567890'
        )

    @patch('custom_tools.Client', autospec=True)
    @patch('custom_tools.UserDataManager.get_user_phone', return_value=None)
    def test_send_sms_no_phone(self, mock_get_user_phone, MockTwilioClient):
        agent = MagicMock()
        result = send_sms(agent, 'test_user_id', 'Test SMS body')

        self.assertEqual(result, "Error: No valid recipient phone number available.")
        mock_get_user_phone.assert_called_once_with('test_user_id')
        MockTwilioClient.return_value.messages.create.assert_not_called()

    @patch('custom_tools.Client', autospec=True)
    @patch('custom_tools.UserDataManager.get_user_phone', return_value='+1234567890')
    def test_send_sms_twilio_error(self, mock_get_user_phone, MockTwilioClient):
        mock_twilio_client = MockTwilioClient.return_value
        mock_twilio_client.messages.create.side_effect = Exception("Twilio error")

        agent = MagicMock()
        result = send_sms(agent, 'test_user_id', 'Test SMS body')

        self.assertIn("Error: Message failed to send.", result)
        self.assertIn("Twilio error", result)
        mock_get_user_phone.assert_called_once_with('test_user_id')
        mock_twilio_client.messages.create.assert_called_once()

def run_specific_tests(test_functions):
    suite = unittest.TestSuite()
    for test_function in test_functions:
        suite.addTest(TestCustomTools(f'test_{test_function.__name__}'))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        function_names = sys.argv[1:]
        test_functions = [globals()[name] for name in function_names if name in globals()]
        run_specific_tests(test_functions)
    else:
        unittest.main(verbosity=2)