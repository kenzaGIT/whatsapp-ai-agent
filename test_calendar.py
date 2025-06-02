#!/usr/bin/env python3
"""
Test Google Calendar connectivity
"""
import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

def test_calendar():
    """Test Google Calendar connectivity"""
    print("\n=== Testing Google Calendar Connectivity ===\n")
    
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID")
    
    print(f"Using credentials from: {credentials_path}")
    print(f"Calendar ID: {calendar_id}")
    
    # Load credentials
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path, 
        scopes=['https://www.googleapis.com/auth/calendar']
    )
    
    # Build service
    service = build('calendar', 'v3', credentials=credentials)
    
    # Get calendar info
    calendar_info = service.calendars().get(calendarId=calendar_id).execute()
    print(f"\nCalendar information:\n{calendar_info}")
    
    # List upcoming events
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=now,
        maxResults=5,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    if not events:
        print('\nNo upcoming events found.')
    else:
        print('\nUpcoming events:')
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f"  {start}: {event.get('summary', 'No title')}")
    
    print("\n=== Test Complete ===\n")

if __name__ == "__main__":
    test_calendar()
