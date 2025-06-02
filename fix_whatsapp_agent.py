#!/usr/bin/env python3
"""
WhatsApp AI Agent Fix - Diagnoses and repairs issues with the agent
"""
import os
import sys
import re
import json
from pprint import pprint
import subprocess
import traceback

def print_section(title):
    """Print a section title"""
    print("\n" + "=" * 50)
    print(f" {title} ".center(50, "="))
    print("=" * 50)

def check_twilio_connector():
    """Check the TwilioWhatsAppConnector implementation"""
    print_section("Checking Twilio Connector")
    
    # Check if the file exists
    if not os.path.exists("connectors/whatsapp.py"):
        print("❌ connectors/whatsapp.py file not found")
        return False
    
    # Read the file content
    with open("connectors/whatsapp.py", "r") as f:
        content = f.read()
    
    # Check for common issues
    issues = []
    
    # Check for TwiML response generation
    if "create_response_twiml" not in content:
        issues.append("Method 'create_response_twiml' not found")
    
    # Check for proper TwiML response format
    twiml_pattern = r"def create_response_twiml.*?return\s+([^;]+)"
    twiml_match = re.search(twiml_pattern, content, re.DOTALL)
    
    if twiml_match:
        twiml_return = twiml_match.group(1).strip()
        print(f"✅ Found TwiML response creation: {twiml_return}")
        
        # Check if it's properly returned as a string
        if not ("str(response)" in twiml_return or "string" in twiml_return.lower()):
            issues.append("TwiML response might not be properly returned as a string")
    else:
        issues.append("Cannot find TwiML response generation code")
    
    # Check the send_message method
    send_message_pattern = r"async def send_message\([^)]+\):(.*?)(?:async def|\Z)"
    send_message_match = re.search(send_message_pattern, content, re.DOTALL)
    
    if send_message_match:
        send_message_code = send_message_match.group(1)
        print(f"✅ Found send_message method")
        
        # Check if it sends TwiML in message content
        if "TwiML" in send_message_code or "Response" in send_message_code:
            issues.append("send_message method might be including TwiML in the message content")
    else:
        issues.append("Cannot find send_message implementation")
    
    # Report issues
    if issues:
        print("\n⚠️ Found issues with Twilio connector:")
        for issue in issues:
            print(f"  - {issue}")
        
        return False
    else:
        print("✅ Twilio connector looks good")
        return True

def check_webhook_handler():
    """Check the webhook handler implementation"""
    print_section("Checking Webhook Handler")
    
    # Check if the file exists
    if not os.path.exists("main.py"):
        print("❌ main.py file not found")
        return False
    
    # Read the file content
    with open("main.py", "r") as f:
        content = f.read()
    
    # Check for common issues
    issues = []
    
    # Check for TwiML handling in webhook_handler
    webhook_pattern = r"async def webhook_handler\([^)]+\):(.*?)(?:async def|\Z)"
    webhook_match = re.search(webhook_pattern, content, re.DOTALL)
    
    if webhook_match:
        webhook_code = webhook_match.group(1)
        print("✅ Found webhook_handler method")
        
        # Check if it properly separates TwiML response from user content
        if "create_response_twiml" in webhook_code:
            print("✅ Found call to create_response_twiml")
        else:
            issues.append("webhook_handler doesn't call create_response_twiml")
    else:
        issues.append("Cannot find webhook_handler implementation")
    
    # Report issues
    if issues:
        print("\n⚠️ Found issues with webhook handler:")
        for issue in issues:
            print(f"  - {issue}")
        
        return False
    else:
        print("✅ Webhook handler looks good")
        return True

def fix_twilio_connector():
    """Fix issues with the Twilio connector"""
    print_section("Fixing Twilio Connector")
    
    if not os.path.exists("connectors/whatsapp.py"):
        print("❌ Cannot fix: connectors/whatsapp.py file not found")
        return False
    
    # Read the file content
    with open("connectors/whatsapp.py", "r") as f:
        content = f.read()
    
    # Make a backup
    with open("connectors/whatsapp.py.bak", "w") as f:
        f.write(content)
    print("✅ Created backup at connectors/whatsapp.py.bak")
    
    # Fix the create_response_twiml method
    fixed_content = re.sub(
        r"def create_response_twiml\([^)]*\):[^}]*?return[^}]*?(?=\n\s*@|def|\Z)",
        """@staticmethod
    def create_response_twiml(message: str = "") -> str:
        \"\"\"
        Create a TwiML response for an incoming message
        
        Args:
            message: Optional message to send back
            
        Returns:
            TwiML response as string
        \"\"\"
        response = MessagingResponse()
        if message:
            response.message(message)
        return str(response)
        
    """,
        content
    )
    
    # Write the fixed content
    with open("connectors/whatsapp.py", "w") as f:
        f.write(fixed_content)
    print("✅ Fixed create_response_twiml method")
    
    return True

def fix_webhook_handler():
    """Fix issues with the webhook handler"""
    print_section("Fixing Webhook Handler")
    
    if not os.path.exists("main.py"):
        print("❌ Cannot fix: main.py file not found")
        return False
    
    # Read the file content
    with open("main.py", "r") as f:
        content = f.read()
    
    # Make a backup
    with open("main.py.bak", "w") as f:
        f.write(content)
    print("✅ Created backup at main.py.bak")
    
    # Fix the webhook_handler function
    webhook_pattern = r"async def webhook_handler\([^)]+\):(.*?)(?=\n\s*@|async def|\Z)"
    
    if re.search(webhook_pattern, content):
        fixed_content = re.sub(
            webhook_pattern,
            """async def webhook_handler(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    NumMedia: int = Form(0),
):
    \"\"\"Handle incoming WhatsApp messages via Twilio webhook\"\"\"
    print(f"Received message from {From}: {Body}")
    
    # Extract the user's phone number
    sender_id = From
    message_text = Body
    
    # Create a task to process the message asynchronously
    # This allows us to return a response to Twilio quickly
    asyncio.create_task(process_message(sender_id, message_text))
    
    # Return empty TwiML response - this is sent to Twilio, not to the user
    return whatsapp.create_response_twiml()
    
""",
            content,
            flags=re.DOTALL
        )
        
        # Write the fixed content
        with open("main.py", "w") as f:
            f.write(fixed_content)
        print("✅ Fixed webhook_handler method")
        
        return True
    else:
        print("❌ Could not find webhook_handler pattern to fix")
        return False

def create_test_script():
    """Create a test script to verify Twilio response formatting"""
    print_section("Creating Test Script")
    
    test_script = """#!/usr/bin/env python3
\"\"\"
Test TwiML response formatting
\"\"\"
import os
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse
from connectors.whatsapp import TwilioWhatsAppConnector

# Load environment variables
load_dotenv()

def test_twiml_response():
    \"\"\"Test TwiML response formatting\"\"\"
    print("\\n=== Testing TwiML Response Formatting ===\\n")
    
    # Create a basic TwiML response
    response = MessagingResponse()
    twiml_str = str(response)
    
    print(f"Basic TwiML response: {twiml_str}")
    
    # Create a TwiML response with a message
    response_with_msg = MessagingResponse()
    response_with_msg.message("This is a test message")
    twiml_with_msg_str = str(response_with_msg)
    
    print(f"TwiML with message: {twiml_with_msg_str}")
    
    # Test the connector's create_response_twiml method
    whatsapp = TwilioWhatsAppConnector()
    connector_twiml = whatsapp.create_response_twiml()
    
    print(f"Connector TwiML response: {connector_twiml}")
    
    # Verify the connector's response is a string
    is_string = isinstance(connector_twiml, str)
    print(f"Connector response is a string: {is_string}")
    
    print("\\n=== Test Complete ===\\n")

if __name__ == "__main__":
    test_twiml_response()
"""
    
    # Write the test script
    with open("test_twiml.py", "w") as f:
        f.write(test_script)
    
    # Make it executable
    os.chmod("test_twiml.py", 0o755)
    
    print("✅ Created test script at test_twiml.py")
    print("   Run it with: python test_twiml.py")
    
    return True

def check_calendar_connector():
    """Test Google Calendar connectivity"""
    print_section("Checking Google Calendar")
    
    if not os.path.exists(".env"):
        print("⚠️ .env file not found, creating minimal example")
        with open(".env.example", "w") as f:
            f.write("""# Google Calendar credentials
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CREDENTIALS_PATH=path/to/credentials.json
GOOGLE_CALENDAR_ID=your_calendar_id@gmail.com

# Twilio WhatsApp credentials
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890

# Service configuration
PORT=8000
""")
        print("✅ Created .env.example file")
    
    try:
        # Get environment variables
        load_dotenv = __import__('dotenv').load_dotenv
        load_dotenv()
        
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
        calendar_id = os.getenv("GOOGLE_CALENDAR_ID")
        
        if not credentials_path or not os.path.exists(credentials_path):
            print(f"❌ Google credentials file not found: {credentials_path}")
            print("   Please check your GOOGLE_CREDENTIALS_PATH in .env")
            return False
        
        if not calendar_id:
            print("❌ GOOGLE_CALENDAR_ID not set in .env")
            return False
        
        print(f"✅ Found credentials at: {credentials_path}")
        print(f"✅ Calendar ID: {calendar_id}")
        
        # Create a simplified test script
        calendar_test = """#!/usr/bin/env python3
\"\"\"
Test Google Calendar connectivity
\"\"\"
import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

def test_calendar():
    \"\"\"Test Google Calendar connectivity\"\"\"
    print("\\n=== Testing Google Calendar Connectivity ===\\n")
    
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
    print(f"\\nCalendar information:\\n{calendar_info}")
    
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
        print('\\nNo upcoming events found.')
    else:
        print('\\nUpcoming events:')
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f"  {start}: {event.get('summary', 'No title')}")
    
    print("\\n=== Test Complete ===\\n")

if __name__ == "__main__":
    test_calendar()
"""
        
        # Write the test script
        with open("test_calendar.py", "w") as f:
            f.write(calendar_test)
        
        # Make it executable
        os.chmod("test_calendar.py", 0o755)
        
        print("✅ Created calendar test script at test_calendar.py")
        print("   Run it with: python test_calendar.py")
        
        return True
    
    except Exception as e:
        print(f"❌ Error checking calendar: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Run the fix script"""
    print_section("WhatsApp AI Agent Fix")
    print("This script will diagnose and fix issues with your WhatsApp AI Agent")
    
    # Check components
    twilio_ok = check_twilio_connector()
    webhook_ok = check_webhook_handler()
    
    # Fix issues if needed
    fixes_needed = not (twilio_ok and webhook_ok)
    
    if fixes_needed:
        print("\n⚠️ Issues detected. Applying fixes...")
        
        if not twilio_ok:
            fix_twilio_connector()
        
        if not webhook_ok:
            fix_webhook_handler()
        
        # Create test scripts
        create_test_script()
    else:
        print("\n✅ All components look good!")
    
    # Check calendar connectivity
    check_calendar_connector()
    
    print_section("Next Steps")
    print("1. Run the test scripts to verify your setup:")
    print("   - python test_twiml.py")
    print("   - python test_calendar.py")
    print("2. Restart your WhatsApp AI Agent:")
    print("   - python start_agent.py")
    print("3. Test sending messages through WhatsApp")
    print("\nIf issues persist, check your .env file configuration")
    print("and ensure all required services are running.")

if __name__ == "__main__":
    main()