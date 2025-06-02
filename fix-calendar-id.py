#!/usr/bin/env python3
"""
Fix Google Calendar ID usage and test calendar permissions
"""
import os
import json
import sys
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta

def print_section(title):
    """Print a section title"""
    print("\n" + "=" * 50)
    print(f" {title} ".center(50, "="))
    print("=" * 50)

def extract_service_account_email():
    """Extract service account email from credentials file"""
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
    
    if not os.path.exists(credentials_path):
        print(f"❌ Credentials file not found: {credentials_path}")
        return None
    
    try:
        with open(credentials_path, "r") as f:
            creds_data = json.load(f)
            
        client_email = creds_data.get("client_email")
        if not client_email:
            print("❌ Could not find client_email in credentials file")
            return None
            
        print(f"✅ Found service account email: {client_email}")
        return client_email
    except Exception as e:
        print(f"❌ Error reading credentials file: {str(e)}")
        return None

def check_calendar_connector():
    """Check the GoogleCalendarConnector implementation"""
    print_section("Checking Calendar Connector")
    
    if not os.path.exists("connectors/calendar_api.py"):
        print("❌ connectors/calendar_api.py file not found")
        return
    
    # Read the file content
    with open("connectors/calendar_api.py", "r") as f:
        content = f.read()
    
    # Check for how the calendar_id is handled
    calendar_id_pattern = r"calendar_id = calendar_id or self\.default_calendar_id"
    if calendar_id_pattern in content:
        print("✅ Found proper calendar_id fallback pattern")
    else:
        print("⚠️ Could not find expected calendar_id fallback pattern")
    
    # Check for any hard-coded "primary" calendar IDs
    primary_pattern = r"calendarId=['\"]{1}primary['\"]{1}"
    primary_matches = content.count("calendarId='primary'") + content.count('calendarId="primary"')
    
    if primary_matches > 0:
        print(f"⚠️ Found {primary_matches} instances of hard-coded 'primary' calendar ID")
        print("   This could cause events to be created in the wrong calendar")
    else:
        print("✅ No hard-coded 'primary' calendar IDs found")

def test_calendar_permissions():
    """Test calendar permissions and proper calendar ID usage"""
    print_section("Testing Calendar Permissions")
    
    # Load environment variables
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID")
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
    
    print(f"Calendar ID from .env: {calendar_id}")
    print(f"Credentials path: {credentials_path}")
    
    # Load credentials
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path, 
        scopes=['https://www.googleapis.com/auth/calendar']
    )
    
    # Build service
    service = build('calendar', 'v3', credentials=credentials)
    
    # Try to access the specified calendar
    try:
        calendar_info = service.calendars().get(calendarId=calendar_id).execute()
        print(f"✅ Successfully accessed calendar: {calendar_info.get('summary')}")
    except Exception as e:
        print(f"❌ Error accessing calendar: {str(e)}")
        print("\n⚠️ This suggests your service account doesn't have permission to access this calendar")
        print("   You need to share your calendar with the service account email")
        return
    
    # Create a test event in the specified calendar
    try:
        # Create event for 15 minutes from now
        now = datetime.utcnow()
        start_time = (now + timedelta(minutes=15)).isoformat() + 'Z'
        end_time = (now + timedelta(minutes=45)).isoformat() + 'Z'
        
        event = {
            'summary': 'Test Event - Calendar ID Fix',
            'description': 'This is a test event to verify calendar ID usage',
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
        }
        
        # Insert the event
        print(f"Creating test event in calendar: {calendar_id}")
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"✅ Successfully created event: {created_event.get('htmlLink')}")
        
        # Offer to delete the event
        delete_event = input("Do you want to delete this test event? (y/n): ").lower() == 'y'
        if delete_event:
            service.events().delete(calendarId=calendar_id, eventId=created_event['id']).execute()
            print("✅ Test event deleted")
    
    except Exception as e:
        print(f"❌ Error creating event: {str(e)}")

def check_calendar_config_in_code():
    """Check how the calendar ID is passed to the calendar connector functions"""
    print_section("Checking Calendar Usage in Main Code")
    
    if not os.path.exists("main.py"):
        print("❌ main.py file not found")
        return
    
    # Read the file content
    with open("main.py", "r") as f:
        content = f.read()
    
    # Check if calendar ID is ever overridden when calling APIs
    calendar_api_calls = content.count("calendar_id=") + content.count("calendarId=")
    
    if calendar_api_calls > 0:
        print(f"⚠️ Found {calendar_api_calls} explicit calendar_id parameters in API calls")
        print("   Check these to make sure they're not overriding your desired calendar ID")
    else:
        print("✅ No explicit calendar_id overrides found in API calls")
    
    # Check action execution
    execute_action_pattern = r"async def execute_action_plan.*?for action in action_plan\.actions.*?\n\s+service = action_planner\.available_services\.get\(service_name\)"
    if re.search(execute_action_pattern, content, re.DOTALL):
        print("✅ Found correct action execution pattern")
    else:
        print("⚠️ Could not find expected action execution pattern")

def fix_calendar_connector():
    """Fix issues with the calendar connector"""
    print_section("Fixing Calendar Connector")
    
    if not os.path.exists("connectors/calendar_api.py"):
        print("❌ Cannot fix: connectors/calendar_api.py file not found")
        return
    
    # Read the file content
    with open("connectors/calendar_api.py", "r") as f:
        content = f.read()
    
    # Make a backup
    with open("connectors/calendar_api.py.bak", "w") as f:
        f.write(content)
    print("✅ Created backup at connectors/calendar_api.py.bak")
    
    # Replace hard-coded "primary" calendar IDs
    fixed_content = content.replace("calendarId='primary'", "calendarId=calendar_id")
    fixed_content = fixed_content.replace('calendarId="primary"', "calendarId=calendar_id")
    
    # Fix init method to ensure default calendar ID is used
    init_pattern = r"def __init__\(self, credentials_path: str, default_calendar_id: str = None\):.*?self\.default_calendar_id = default_calendar_id or os\.getenv\(\"GOOGLE_CALENDAR_ID\".*?\)"
    
    if re.search(init_pattern, content, re.DOTALL):
        fixed_init = """def __init__(self, credentials_path: str, default_calendar_id: str = None):
        self.credentials_path = credentials_path
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path, 
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        self.service = build('calendar', 'v3', credentials=self.credentials)
        
        # Get the user's calendar ID from environment or use the provided default
        self.default_calendar_id = default_calendar_id or os.getenv("GOOGLE_CALENDAR_ID")
        
        print(f"Initialized Enhanced Google Calendar Connector with default calendar ID: {self.default_calendar_id}")"""
        
        fixed_content = re.sub(init_pattern, fixed_init, fixed_content, flags=re.DOTALL)
    
    # Write the fixed content
    with open("connectors/calendar_api.py", "w") as f:
        f.write(fixed_content)
    print("✅ Fixed potential calendar ID issues in calendar connector")

def main():
    """Main function"""
    print_section("Google Calendar ID Fix")
    
    # Load environment variables
    load_dotenv()
    
    # Extract service account email
    service_account_email = extract_service_account_email()
    
    if service_account_email:
        print("\n📝 IMPORTANT: Make sure your calendar is shared with this service account email:")
        print(f"   {service_account_email}")
        print("\n   If it's not shared, follow these steps:")
        print("   1. Go to Google Calendar in your browser")
        print("   2. Find your calendar in the left sidebar")
        print("   3. Click the three dots next to it and select 'Settings and sharing'")
        print("   4. Scroll down to 'Share with specific people'")
        print("   5. Click 'Add people' and add the service account email above")
        print("   6. Give it 'Make changes to events' permission")
        print("   7. Click 'Send'")
    
    # Check how calendar ID is handled in code
    check_calendar_connector()
    check_calendar_config_in_code()
    
    # Ask if user wants to fix issues
    if input("\nWould you like to apply potential fixes? (y/n): ").lower() == 'y':
        fix_calendar_connector()
    
    # Test calendar permissions
    if input("\nWould you like to test calendar permissions? (y/n): ").lower() == 'y':
        test_calendar_permissions()
    
    print_section("Next Steps")
    print("1. Make sure your calendar is shared with the service account")
    print("2. Restart your WhatsApp AI Agent")
    print("3. Test creating a calendar event via WhatsApp")

if __name__ == "__main__":
    import re  # Import at top wasn't working with the function_calls system
    main()