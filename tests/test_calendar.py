# test_calendar.py
import os
import asyncio
import sys
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

# Get the Google Calendar credentials path
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")

# Check if the credentials path is set
if not GOOGLE_CREDENTIALS_PATH:
    print("Error: GOOGLE_CREDENTIALS_PATH not found in environment variables.")
    print("Please add it to your .env file.")
    sys.exit(1)

print("Google Calendar API Test Script")
print("==============================")
print(f"Credentials Path: {GOOGLE_CREDENTIALS_PATH}")

# Check if the credentials file exists
if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
    print(f"❌ Error: Credentials file not found at {GOOGLE_CREDENTIALS_PATH}")
    print("Please make sure the file exists and the path is correct.")
    sys.exit(1)

def test_calendar_connection():
    """Test connection to Google Calendar API"""
    try:
        print("\nTesting connection to Google Calendar API...")
        
        # Load credentials
        print("Loading credentials...")
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH, 
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        # Build service
        print("Building service...")
        service = build('calendar', 'v3', credentials=credentials)
        
        # Test connection by listing calendars
        print("Listing calendars...")
        calendars = service.calendarList().list().execute()
        
        if 'items' in calendars:
            print("✅ Successfully connected to Google Calendar API!")
            print(f"Found {len(calendars['items'])} calendars:")
            for calendar in calendars['items']:
                print(f" - {calendar['summary']} ({calendar['id']})")
            return True
        else:
            print("✅ Connected to Google Calendar API but found no calendars.")
            print("You may need to share calendars with the service account email.")
            return True
            
    except Exception as e:
        print(f"❌ Error connecting to Google Calendar API: {str(e)}")
        
        if "invalid_grant" in str(e):
            print("\nTroubleshooting authentication issues:")
            print("1. Make sure your service account credentials are valid")
            print("2. Check if the credentials have been revoked or expired")
            print("3. Verify that the Google Calendar API is enabled in your Google Cloud project")
        elif "access_denied" in str(e):
            print("\nTroubleshooting access issues:")
            print("1. Make sure the service account has the correct permissions")
            print("2. Verify that the Google Calendar API is enabled for your project")
        
        return False

def create_test_event():
    """Create a test event in the primary calendar"""
    try:
        print("\nAttempting to create a test event...")
        
        # Load credentials
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH, 
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        # Build service
        service = build('calendar', 'v3', credentials=credentials)
        
        # Define calendar ID
        # For service accounts, you need to explicitly share a calendar
        # with the service account, or use a calendar created by the service account
        calendar_id = 'primary'  # You might need to change this
        
        # Define event details
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)
        
        event = {
            'summary': 'Test Event - WhatsApp AI Agent',
            'description': 'This is a test event created by the WhatsApp AI Agent test script.',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            }
        }
        
        # Create the event
        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        
        print("✅ Test event created successfully!")
        print(f"Event details:")
        print(f" - Title: {event['summary']}")
        print(f" - Time: {event['start']['dateTime']} to {event['end']['dateTime']}")
        print(f" - Calendar: {calendar_id}")
        
        # Ask if user wants to delete the test event
        delete_event = input("\nDo you want to delete this test event? (y/n): ").lower()
        if delete_event == 'y' or delete_event == 'yes':
            service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
            print("✅ Test event deleted successfully!")
        
        return True
    except Exception as e:
        print(f"❌ Error creating test event: {str(e)}")
        
        if "notFound" in str(e):
            print("\nTroubleshooting calendar not found issues:")
            print("1. For service accounts, you need to explicitly share a calendar with the service account email")
            print("2. Try specifying a different calendar ID instead of 'primary'")
            print("3. The service account may not have a 'primary' calendar")
        
        return False

# Execute tests
if __name__ == "__main__":
    connection_ok = test_calendar_connection()
    
    if connection_ok:
        print("\nConnection test successful!")
        
        # Ask if the user wants to create a test event
        create_event = input("\nDo you want to create a test event? (y/n): ").lower()
        if create_event == 'y' or create_event == 'yes':
            create_test_event()
        else:
            print("Skipping event creation test.")
    else:
        print("\nConnection test failed. Please fix the issues before continuing.")