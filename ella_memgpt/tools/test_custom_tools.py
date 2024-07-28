import unittest
from unittest.mock import patch, MagicMock
from custom_tools import schedule_event, fetch_events, delete_event, update_event, send_email
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class TestCustomTools(unittest.TestCase):

    @patch('custom_tools.GoogleCalendarUtils', autospec=True)
    @patch('custom_tools.UserDataManager.get_user_email', return_value='test@example.com')
    def test_schedule_event(self, mock_get_user_email, MockGoogleCalendarUtils):
        mock_calendar_utils = MockGoogleCalendarUtils.return_value
        mock_calendar_utils.get_or_create_user_calendar.return_value = 'test_calendar_id'
        mock_calendar_utils.create_calendar_event.return_value = {'id': 'test_event_id', 'htmlLink': 'http://example.com'}

        agent = MagicMock()
        result = schedule_event(agent, 'test_user_id', 'Test Event', '2023-01-01T10:00:00-07:00', '2023-01-01T11:00:00-07:00')

        self.assertIn('Event created: ID: test_event_id', result)
        self.assertIn('Link: http://example.com', result)

    @patch('custom_tools.GoogleCalendarUtils', autospec=True)
    @patch('custom_tools.UserDataManager.get_user_email', return_value='test@example.com')
    def test_fetch_events(self, mock_get_user_email, MockGoogleCalendarUtils):
        mock_calendar_utils = MockGoogleCalendarUtils.return_value
        mock_calendar_utils.fetch_upcoming_events.return_value = [
            {
                'summary': 'Test Event',
                'start': '2023-01-01T10:00:00-07:00',
                'end': '2023-01-01T11:00:00-07:00',
                'description': 'A test event',
                'location': 'Test Location',
                'id': 'test_event_id',
                'htmlLink': 'http://example.com'
            }
        ]

        agent = MagicMock()
        result = fetch_events(agent, 'test_user_id')

        self.assertIn('Title: Test Event', result)
        self.assertIn('Start: 2023-01-01T10:00:00-07:00', result)
        self.assertIn('End: 2023-01-01T11:00:00-07:00', result)
        self.assertIn('Description: A test event', result)
        self.assertIn('Location: Test Location', result)
        self.assertIn('Event ID: test_event_id', result)
        self.assertIn('Event Link: http://example.com', result)

    @patch('custom_tools.GoogleCalendarUtils', autospec=True)
    @patch('custom_tools.UserDataManager.get_user_email', return_value='test@example.com')
    def test_delete_event(self, mock_get_user_email, MockGoogleCalendarUtils):
        mock_calendar_utils = MockGoogleCalendarUtils.return_value
        mock_calendar_utils.get_or_create_user_calendar.return_value = 'test_calendar_id'
        
        # Mock the nested service events get and execute methods
        mock_service = MagicMock()
        mock_calendar_utils.service = mock_service
        mock_service.events().get().execute.return_value = {
            'id': 'test_event_id',
            'summary': 'Test Event',
            'recurringEventId': 'test_series_id'
        }
        mock_calendar_utils.delete_calendar_event.return_value = True

        agent = MagicMock()

        # Test deleting an individual event
        result = delete_event(agent, 'test_user_id', 'test_event_id')
        print(f"Result: '{result}'")
        self.assertIn('Event deleted successfully. ID: test_event_id', result.strip())

        # Test deleting a series of events
        result = delete_event(agent, 'test_user_id', 'test_event_id', delete_series=True)
        print(f"Result: '{result}'")
        self.assertIn('Event series deleted successfully. ID: test_series_id', result.strip())

    @patch('custom_tools.GoogleCalendarUtils', autospec=True)
    @patch('custom_tools.UserDataManager.get_user_email', return_value='test@example.com')
    def test_update_event(self, mock_get_user_email, MockGoogleCalendarUtils):
        mock_calendar_utils = MockGoogleCalendarUtils.return_value
        mock_calendar_utils.get_or_create_user_calendar.return_value = 'test_calendar_id'
        
        # Mock the nested service events get and execute methods
        mock_service = MagicMock()
        mock_calendar_utils.service = mock_service
        mock_service.events().get().execute.return_value = {
            'id': 'test_event_id',
            'summary': 'Test Event',
            'recurringEventId': 'test_series_id'
        }
        
        # Mock update for single event
        mock_calendar_utils.update_calendar_event.return_value = {
            "success": True,
            "message": "Event updated successfully",
            "event": {
                'id': 'test_event_id',
                'htmlLink': 'http://example.com'
            }
        }
        
        agent = MagicMock()
        result = update_event(agent, 'test_user_id', 'test_event_id', title='Updated Event', update_series=False)
        print(f"Result: '{result}'")
        self.assertIn('Event updated successfully. ID: test_event_id', result.strip())
        self.assertIn('Link: http://example.com', result.strip())

        # Mock update for series event
        mock_calendar_utils.update_calendar_event.return_value = {
            "success": True,
            "message": "Event updated successfully",
            "event": {
                'id': 'test_series_id',
                'htmlLink': 'http://example.com'
            }
        }
        
        result = update_event(agent, 'test_user_id', 'test_event_id', title='Updated Series Event', update_series=True)
        print(f"Result: '{result}'")
        self.assertIn('Event updated successfully. ID: test_series_id', result.strip())
        self.assertIn('Link: http://example.com', result.strip())

    @patch('custom_tools.GoogleEmailUtils', autospec=True)
    @patch('custom_tools.UserDataManager.get_user_email', return_value='recipient@example.com')
    def test_send_email(self, mock_get_user_email, MockGoogleEmailUtils):
        mock_email_utils = MockGoogleEmailUtils.return_value
        mock_email_utils.send_email.return_value = {"status": "success", "message_id": "test_message_id"}

        agent = MagicMock()
        result = send_email(agent, 'test_user_id', 'Test Subject', 'Test Body')

        self.assertIn('Message was successfully sent. Message ID: test_message_id', result)

if __name__ == '__main__':
    unittest.main()