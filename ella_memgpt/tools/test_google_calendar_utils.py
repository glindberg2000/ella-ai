import unittest
from unittest import mock
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import os
import sys
from dotenv import load_dotenv
from googleapiclient.errors import HttpError


class TestGoogleCalendarUtils(unittest.TestCase):

    def setUp(self):
        # Load environment variables
        load_dotenv()
        self.MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
        self.CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')

        if not self.MEMGPT_TOOLS_PATH or not self.CREDENTIALS_PATH:
            self.fail("Error: MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables")

        # Add MEMGPT_TOOLS_PATH to sys.path if not already present
        if self.MEMGPT_TOOLS_PATH not in sys.path:
            sys.path.append(self.MEMGPT_TOOLS_PATH)

        self.GCAL_TOKEN_PATH = os.path.join(self.CREDENTIALS_PATH, 'gcal_token.json')
        self.GOOGLE_CREDENTIALS_PATH = os.path.join(self.CREDENTIALS_PATH, 'google_api_credentials.json')

    @patch('google_utils.build')
    @patch('google_utils.UserDataManager.get_user_email', return_value='testuser@gmail.com')
    def test_create_event(self, mock_get_user_email, mock_build):
        from google_utils import GoogleCalendarUtils

        # Mock the Google Calendar API service
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock the service's events().insert().execute() method
        mock_service.events().insert().execute.return_value = {
            'id': 'test_event_id',
            'htmlLink': 'http://test.event.link'
        }

        # Create an instance of GoogleCalendarUtils
        calendar_utils = GoogleCalendarUtils(self.GCAL_TOKEN_PATH, self.GOOGLE_CREDENTIALS_PATH)

        # Create a test event
        event_data = {
            'summary': 'Test Event',
            'start': {'dateTime': (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z'},
            'end': {'dateTime': (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat() + 'Z'},
        }

        result = calendar_utils.create_calendar_event('test_calendar_id', event_data)
        self.assertTrue(result['success'])
        self.assertEqual(result['id'], 'test_event_id')
        self.assertIn('http://test.event.link', result['htmlLink'])

    @patch('google_utils.build')
    @patch('google_utils.UserDataManager.get_user_email', return_value='testuser@gmail.com')
    def test_create_recurring_event(self, mock_get_user_email, mock_build):
        from google_utils import GoogleCalendarUtils

        # Mock the Google Calendar API service
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock the service's events().insert().execute() method
        mock_service.events().insert().execute.return_value = {
            'id': 'test_recurring_event_id',
            'htmlLink': 'http://test.recurring.event.link'
        }

        # Create an instance of GoogleCalendarUtils
        calendar_utils = GoogleCalendarUtils(self.GCAL_TOKEN_PATH, self.GOOGLE_CREDENTIALS_PATH)

        # Create a test recurring event
        event_data = {
            'summary': 'Test Recurring Event',
            'start': {'dateTime': (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z'},
            'end': {'dateTime': (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat() + 'Z'},
            'recurrence': ['RRULE:FREQ=DAILY;COUNT=5']
        }

        result = calendar_utils.create_calendar_event('test_calendar_id', event_data)
        self.assertTrue(result['success'])
        self.assertEqual(result['id'], 'test_recurring_event_id')
        self.assertIn('http://test.recurring.event.link', result['htmlLink'])

    @patch('google_utils.build')
    @patch('google_utils.UserDataManager.get_user_email', return_value='testuser@gmail.com')
    def test_fetch_upcoming_events(self, mock_get_user_email, mock_build):
        from google_utils import GoogleCalendarUtils

        # Mock the Google Calendar API service
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock the service's events().list().execute() method for both single and recurring events
        mock_service.events().list().execute.return_value = {
            'items': [
                {'summary': 'Test Event', 'start': {'dateTime': '2024-07-28T10:00:00Z'}, 'end': {'dateTime': '2024-07-28T11:00:00Z'}, 'id': 'test_event_id'},
                {'summary': 'Test Recurring Event', 'start': {'dateTime': '2024-07-28T10:00:00Z'}, 'end': {'dateTime': '2024-07-28T11:00:00Z'}, 'id': 'test_recurring_event_instance_id', 'recurringEventId': 'test_recurring_event_id'}
            ],
            'nextPageToken': 'next_token',
            'prevPageToken': 'prev_token'
        }

        # Create an instance of GoogleCalendarUtils
        calendar_utils = GoogleCalendarUtils(self.GCAL_TOKEN_PATH, self.GOOGLE_CREDENTIALS_PATH)

        # Test with default parameters
        result = calendar_utils.fetch_upcoming_events('test_user_id')
        self.assertIsInstance(result, dict)
        self.assertIn('items', result)
        self.assertIn('nextPageToken', result)
        self.assertIn('prevPageToken', result)
        self.assertEqual(len(result['items']), 2)
        self.assertEqual(result['items'][0]['summary'], 'Test Event')
        self.assertEqual(result['items'][0]['id'], 'test_event_id')
        self.assertEqual(result['items'][1]['summary'], 'Test Recurring Event')
        self.assertEqual(result['items'][1]['id'], 'test_recurring_event_instance_id')
        self.assertEqual(result['items'][1]['recurringEventId'], 'test_recurring_event_id')
        self.assertEqual(result['nextPageToken'], 'next_token')
        self.assertEqual(result['prevPageToken'], 'prev_token')

        # Test with custom parameters
        custom_time_min = '2024-07-27T00:00:00Z'
        custom_time_max = '2024-07-29T23:59:59Z'
        custom_max_results = 5
        custom_page_token = 'custom_token'

        calendar_utils.fetch_upcoming_events('test_user_id', max_results=custom_max_results, 
                                            time_min=custom_time_min, time_max=custom_time_max, 
                                            page_token=custom_page_token)

        # Verify that the API was called with the correct parameters
        mock_service.events().list.assert_called_with(
            calendarId=mock.ANY,
            timeMin=custom_time_min,
            timeMax=custom_time_max,
            maxResults=custom_max_results,
            singleEvents=True,
            orderBy='startTime',
            pageToken=custom_page_token
        )

        # Test error handling
        mock_service.events().list().execute.side_effect = Exception("API Error")
        error_result = calendar_utils.fetch_upcoming_events('test_user_id')
        self.assertEqual(error_result, {"items": [], "nextPageToken": None, "prevPageToken": None})

        
        @patch('google_utils.build')
        @patch('google_utils.UserDataManager.get_user_email', return_value='testuser@gmail.com')
        def test_delete_event(self, mock_get_user_email, mock_build):
            from google_utils import GoogleCalendarUtils

            # Mock the Google Calendar API service
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock the service's events().delete().execute() method
            mock_service.events().delete().execute.return_value = None

            # Create an instance of GoogleCalendarUtils
            calendar_utils = GoogleCalendarUtils(self.GCAL_TOKEN_PATH, self.GOOGLE_CREDENTIALS_PATH)

            result = calendar_utils.delete_calendar_event('test_user_id', 'test_event_id')
            self.assertTrue(result['success'])
            self.assertEqual(result['message'], 'Event deleted successfully')

        @patch('google_utils.build')
        @patch('google_utils.UserDataManager.get_user_email', return_value='testuser@gmail.com')
        def test_delete_recurring_event(self, mock_get_user_email, mock_build):
            from google_utils import GoogleCalendarUtils

            # Mock the Google Calendar API service
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock the service's events().get().execute() method
            mock_service.events().get().execute.return_value = {
                'id': 'test_recurring_event_instance_id',
                'recurringEventId': 'test_recurring_event_id'
            }
            # Mock the service's events().delete().execute() method
            mock_service.events().delete().execute.return_value = None

            # Create an instance of GoogleCalendarUtils
            calendar_utils = GoogleCalendarUtils(self.GCAL_TOKEN_PATH, self.GOOGLE_CREDENTIALS_PATH)

            result = calendar_utils.delete_calendar_event('test_user_id', 'test_recurring_event_instance_id', delete_series=True)
            self.assertTrue(result['success'])
            self.assertEqual(result['message'], 'Event series deleted successfully. ID: test_recurring_event_id')

        @patch('google_utils.build')
        @patch('google_utils.UserDataManager.get_user_email', return_value='testuser@gmail.com')
        def test_update_event(self, mock_get_user_email, mock_build):
            from google_utils import GoogleCalendarUtils

            # Mock the Google Calendar API service
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock the service's events().patch().execute() method
            mock_service.events().patch().execute.return_value = {
                'id': 'test_event_id',
                'summary': 'Updated Event',
                'htmlLink': 'http://test.event.link'
            }

            # Create an instance of GoogleCalendarUtils
            calendar_utils = GoogleCalendarUtils(self.GCAL_TOKEN_PATH, self.GOOGLE_CREDENTIALS_PATH)

            # Define the event update data
            event_data = {
                'summary': 'Updated Event',
                'start': {'dateTime': (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z'},
                'end': {'dateTime': (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat() + 'Z'},
            }

            # Test updating a single event
            result = calendar_utils.update_calendar_event('test_user_id', 'test_event_id', event_data)
            self.assertTrue(result['success'])
            self.assertEqual(result['message'], 'Event updated successfully')
            self.assertEqual(result['event']['summary'], 'Updated Event')

        @patch('google_utils.build')
        @patch('google_utils.UserDataManager.get_user_email', return_value='testuser@gmail.com')
        def test_update_recurring_event(self, mock_get_user_email, mock_build):
            from google_utils import GoogleCalendarUtils

            # Mock the Google Calendar API service
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock the service's events().get().execute() method for fetching the event
            mock_service.events().get().execute.return_value = {
                'id': 'test_recurring_event_instance_id',
                'recurringEventId': 'test_recurring_event_id'
            }

            # Mock the service's events().patch().execute() method for updating the event
            mock_service.events().patch().execute.return_value = {
                'id': 'test_recurring_event_id',
                'summary': 'Updated Recurring Event',
                'htmlLink': 'http://test.recurring.event.link'
            }

            # Create an instance of GoogleCalendarUtils
            calendar_utils = GoogleCalendarUtils(self.GCAL_TOKEN_PATH, self.GOOGLE_CREDENTIALS_PATH)

            # Define the event update data
            event_data = {
                'summary': 'Updated Recurring Event',
                'start': {'dateTime': (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z'},
                'end': {'dateTime': (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat() + 'Z'},
            }

            # Test updating a recurring event
            result = calendar_utils.update_calendar_event('test_user_id', 'test_recurring_event_instance_id', event_data, update_series=True)
            self.assertTrue(result['success'])
            self.assertEqual(result['message'], 'Event series updated successfully. ID: test_recurring_event_id')
            self.assertEqual(result['event']['summary'], 'Updated Recurring Event')

        @patch('google_utils.build')
        @patch('google_utils.UserDataManager.get_user_email', return_value='testuser@gmail.com')
        def test_invalid_event_data(self, mock_get_user_email, mock_build):
            from google_utils import GoogleCalendarUtils

            # Mock the Google Calendar API service
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock the service's events().insert().execute() method to raise an error
            mock_service.events().insert().execute.side_effect = HttpError(MagicMock(status=400), b'Bad Request')

            # Create an instance of GoogleCalendarUtils
            calendar_utils = GoogleCalendarUtils(self.GCAL_TOKEN_PATH, self.GOOGLE_CREDENTIALS_PATH)

            # Create an event with invalid data
            event_data = {
                'summary': 'Test Event',
                'start': {'dateTime': 'invalid_datetime'},
                'end': {'dateTime': 'invalid_datetime'},
            }

            result = calendar_utils.create_calendar_event('test_calendar_id', event_data)
            self.assertFalse(result['success'])
            self.assertIn('Error creating event', result['message'])

        @patch('google_utils.build')
        @patch('google_utils.UserDataManager.get_user_email', return_value='testuser@gmail.com')
        def test_non_existent_event(self, mock_get_user_email, mock_build):
            from google_utils import GoogleCalendarUtils

            # Mock the Google Calendar API service
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock the service's events().get().execute() method to raise a 404 error
            mock_service.events().get().execute.side_effect = HttpError(MagicMock(status=404), b'Not Found')

            # Create an instance of GoogleCalendarUtils
            calendar_utils = GoogleCalendarUtils(self.GCAL_TOKEN_PATH, self.GOOGLE_CREDENTIALS_PATH)

            # Try to update a non-existent event
            event_data = {
                'summary': 'Updated Event',
                'start': {'dateTime': (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z'},
                'end': {'dateTime': (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat() + 'Z'},
            }

            result = calendar_utils.update_calendar_event('test_user_id', 'non_existent_event_id', event_data)
            self.assertFalse(result['success'])
            self.assertIn('Error updating event', result['message'])

        @patch('google_utils.build')
        @patch('google_utils.UserDataManager.get_user_email', return_value='testuser@gmail.com')
        def test_permission_error(self, mock_get_user_email, mock_build):
            from google_utils import GoogleCalendarUtils

            # Mock the Google Calendar API service
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock the service's events().insert().execute() method to raise a permission error
            mock_service.events().insert().execute.side_effect = HttpError(MagicMock(status=403), b'Forbidden')

            # Create an instance of GoogleCalendarUtils
            calendar_utils = GoogleCalendarUtils(self.GCAL_TOKEN_PATH, self.GOOGLE_CREDENTIALS_PATH)

            # Create an event with valid data
            event_data = {
                'summary': 'Test Event',
                'start': {'dateTime': (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z'},
                'end': {'dateTime': (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat() + 'Z'},
            }

            result = calendar_utils.create_calendar_event('test_calendar_id', event_data)
            self.assertFalse(result['success'])
            self.assertIn('Error creating event', result['message'])

if __name__ == '__main__':
    unittest.main(verbosity=2)