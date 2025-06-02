# create_specific_event.py
import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz

# Load environment variables
load_dotenv()

# Get the credentials path
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
print(f"Using credentials from: {GOOGLE_CREDENTIALS_PATH}")

# Load credentials
credentials = service_account.Credentials.from_service_account_file(
    GOOGLE_CREDENTIALS_PATH, 
    scopes=['https://www.googleapis.com/auth/calendar']
)

# Build service
service = build('calendar', 'v3', credentials=credentials)

# Create an event for today at noon in local time
local_tz = pytz.timezone('Africa/Casablanca')  # Morocco timezone
now = datetime.now(local_tz)
start_time = now.replace(hour=12, minute=0, second=0, microsecond=0)
end_time = start_time + timedelta(hours=1)

# Format times in RFC3339 format
start_time_str = start_time.isoformat()
end_time_str = end_time.isoformat()

# Create the event
event = {
    'summary': 'TEST EVENT - VERY VISIBLE',
    'location': 'Google Calendar Test',
    'description': 'This is a test event created by the WhatsApp AI Agent to verify calendar integration.',
    'start': {
        'dateTime': start_time_str,
        'timeZone': 'Africa/Casablanca',
    },
    'end': {
        'dateTime': end_time_str,
        'timeZone': 'Africa/Casablanca',
    },
    'reminders': {
        'useDefault': True,
    },
    'visibility': 'public',
    'transparency': 'opaque',  # Show as busy
    'colorId': '11'  # Red color
}

print(f"Creating event: {event['summary']}")
print(f"Start time: {start_time_str}")
print(f"End time: {end_time_str}")
print(f"Calendar: primary")

try:
    created_event = service.events().insert(calendarId='primary', body=event).execute()
    print(f"\n✅ Event created successfully!")
    print(f"Event ID: {created_event['id']}")
    print(f"Event Link: {created_event.get('htmlLink', 'Not available')}")
    
    # Now verify we can retrieve the event we just created
    print("\nVerifying event creation by retrieving event details...")
    retrieved_event = service.events().get(calendarId='primary', eventId=created_event['id']).execute()
    print(f"Retrieved event summary: {retrieved_event['summary']}")
    print(f"Retrieved event start time: {retrieved_event['start']['dateTime']}")
    
    print("\nListing all events for today to verify visibility...")
    today_min = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today_max = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
    
    events_result = service.events().list(
        calendarId='primary',
        timeMin=today_min,
        timeMax=today_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    if not events:
        print("No events found for today.")
    else:
        print(f"Found {len(events)} events for today:")
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f"- {start}: {event['summary']} (ID: {event['id']})")
    
except Exception as e:
    print(f"❌ Error creating or retrieving event: {str(e)}")

print("\nTest complete. Please check your Google Calendar for the test event.")