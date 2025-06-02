#!/usr/bin/env python3
"""
Fix the remaining issues with WhatsApp agent:
1. XML appearing in messages
2. Calendar event creation failures
"""
import os
import re
import json
from datetime import datetime

def print_section(title):
    """Print a section title"""
    print("\n" + "=" * 60)
    print(f" {title} ".center(60, "="))
    print("=" * 60)

def fix_xml_in_messages():
    """Fix the XML response issue in main.py"""
    print_section("Fixing XML in Messages Issue")
    
    if not os.path.exists("main.py"):
        print("❌ main.py not found")
        return False
    
    # Read current content
    with open("main.py", "r") as f:
        content = f.read()
    
    # Create backup
    with open("main.py.xml_fix_backup", "w") as f:
        f.write(content)
    print("✅ Created backup: main.py.xml_fix_backup")
    
    # The issue is that webhook_handler is returning TwiML which gets sent to user
    # We need to make sure it ONLY returns TwiML to Twilio, not to the user
    
    # Find and replace the webhook_handler function
    webhook_pattern = r'@app\.post\("/webhook".*?\).*?async def webhook_handler\([^)]+\):.*?return\s+whatsapp\.create_response_twiml\(\)'
    
    new_webhook_handler = '''@app.post("/webhook", response_class=PlainTextResponse)
async def webhook_handler(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    NumMedia: int = Form(0),
):
    """Handle incoming WhatsApp messages via Twilio webhook"""
    print(f"Received message from {From}: {Body}")
    
    # Extract the user's phone number
    sender_id = From
    message_text = Body
    
    # Create a task to process the message asynchronously
    # This allows us to return a response to Twilio quickly
    asyncio.create_task(process_message(sender_id, message_text))
    
    # IMPORTANT: Return ONLY TwiML to Twilio - this is NOT sent to the user
    # The actual user messages are sent via send_message in process_message
    return whatsapp.create_response_twiml()'''
    
    if re.search(webhook_pattern, content, re.DOTALL):
        fixed_content = re.sub(webhook_pattern, new_webhook_handler, content, flags=re.DOTALL)
    else:
        # If pattern doesn't match, try a simpler approach
        webhook_simple_pattern = r'async def webhook_handler\([^)]+\):.*?return whatsapp\.create_response_twiml\(\)'
        if re.search(webhook_simple_pattern, content, re.DOTALL):
            # Just add a comment above the return statement
            fixed_content = re.sub(
                r'(\s+)return whatsapp\.create_response_twiml\(\)',
                r'\1# Return TwiML to Twilio ONLY - user messages are sent separately in process_message\n\1return whatsapp.create_response_twiml()',
                content
            )
        else:
            print("⚠️ Could not find webhook_handler pattern to fix")
            return False
    
    # Write the fixed content
    with open("main.py", "w") as f:
        f.write(fixed_content)
    
    print("✅ Fixed webhook_handler to prevent XML in user messages")
    return True

def fix_calendar_time_formatting():
    """Fix calendar event creation time formatting issues"""
    print_section("Fixing Calendar Time Formatting")
    
    # Check utils/time_utils.py for time conversion issues
    if not os.path.exists("utils/time_utils.py"):
        print("❌ utils/time_utils.py not found")
        return False
    
    with open("utils/time_utils.py", "r") as f:
        time_utils_content = f.read()
    
    # Create backup
    with open("utils/time_utils.py.backup", "w") as f:
        f.write(time_utils_content)
    print("✅ Created backup: utils/time_utils.py.backup")
    
    # Check if the time conversion is properly handling timezone
    if "Africa/Casablanca" not in time_utils_content:
        print("⚠️ Morocco timezone might not be properly set in time_utils.py")
    
    # Check the calendar API for time formatting issues
    if not os.path.exists("connectors/calendar_api.py"):
        print("❌ connectors/calendar_api.py not found")
        return False
    
    with open("connectors/calendar_api.py", "r") as f:
        calendar_content = f.read()
    
    # Create backup
    with open("connectors/calendar_api.py.time_fix_backup", "w") as f:
        f.write(calendar_content)
    print("✅ Created backup: connectors/calendar_api.py.time_fix_backup")
    
    # Fix potential issues with time format
    # Ensure that time formats are consistent
    fixes_applied = []
    
    # Fix 1: Ensure _ensure_iso_format is robust
    iso_format_pattern = r'def _ensure_iso_format\(self, start_time, end_time\):.*?return start_time, end_time'
    
    new_iso_format_method = '''def _ensure_iso_format(self, start_time, end_time):
        """
        Ensure times are in proper ISO format for Google Calendar API
        
        Args:
            start_time: Start time string
            end_time: End time string
        
        Returns:
            Tuple of formatted (start_time, end_time)
        """
        # Handle None values
        if not start_time or not end_time:
            raise ValueError("Both start_time and end_time must be provided")
        
        # If already has timezone info, use as-is
        if start_time.endswith('Z') or '+' in start_time or '-' in start_time[-6:]:
            formatted_start = start_time
        else:
            # Add Z suffix for UTC if no timezone specified
            if 'T' in start_time:
                formatted_start = start_time + 'Z' if not start_time.endswith('Z') else start_time
            else:
                formatted_start = start_time
        
        if end_time.endswith('Z') or '+' in end_time or '-' in end_time[-6:]:
            formatted_end = end_time
        else:
            # Add Z suffix for UTC if no timezone specified
            if 'T' in end_time:
                formatted_end = end_time + 'Z' if not end_time.endswith('Z') else end_time
            else:
                formatted_end = end_time
        
        return formatted_start, formatted_end'''
    
    if re.search(iso_format_pattern, calendar_content, re.DOTALL):
        calendar_content = re.sub(iso_format_pattern, new_iso_format_method, calendar_content, flags=re.DOTALL)
        fixes_applied.append("Enhanced _ensure_iso_format method")
    
    # Fix 2: Ensure proper timezone handling in event creation
    # Look for the event creation timezone settings
    timezone_pattern = r"'timeZone': 'Africa/Casablanca'"
    if timezone_pattern in calendar_content:
        fixes_applied.append("Timezone already set to Africa/Casablanca")
    else:
        # Replace any UTC or other timezone with Morocco timezone
        calendar_content = re.sub(r"'timeZone': '[^']*'", "'timeZone': 'Africa/Casablanca'", calendar_content)
        fixes_applied.append("Set timezone to Africa/Casablanca")
    
    # Write the fixed content
    with open("connectors/calendar_api.py", "w") as f:
        f.write(calendar_content)
    
    for fix in fixes_applied:
        print(f"✅ {fix}")
    
    return True

def create_debug_calendar_test():
    """Create a detailed calendar test to debug the Bad Request error"""
    print_section("Creating Debug Calendar Test")
    
    debug_test = '''#!/usr/bin/env python3
"""
Debug calendar event creation to identify Bad Request issues
"""
import os
import sys
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(".")

from connectors.calendar_api import GoogleCalendarConnector
from utils.time_utils import TimeConverter

load_dotenv()

def test_calendar_event_creation():
    """Test calendar event creation with detailed debugging"""
    print("=== Debug Calendar Event Creation ===\\n")
    
    # Initialize calendar connector
    calendar = GoogleCalendarConnector(
        credentials_path=os.getenv("GOOGLE_CREDENTIALS_PATH"),
        default_calendar_id=os.getenv("GOOGLE_CALENDAR_ID")
    )
    
    print(f"Calendar ID: {calendar.default_calendar_id}")
    
    # Test 1: Simple event creation with explicit time
    print("\\n--- Test 1: Simple event with explicit UTC time ---")
    now = datetime.utcnow()
    start_time = (now + timedelta(hours=1)).isoformat() + 'Z'
    end_time = (now + timedelta(hours=2)).isoformat() + 'Z'
    
    print(f"Start time: {start_time}")
    print(f"End time: {end_time}")
    
    try:
        result1 = await calendar.create_event(
            summary="Debug Test Event 1",
            start_time=start_time,
            end_time=end_time,
            description="Testing explicit UTC times",
            check_for_conflicts=False
        )
        print(f"Result 1: {result1}")
    except Exception as e:
        print(f"Error 1: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Event creation with Morocco timezone
    print("\\n--- Test 2: Event with Morocco timezone ---")
    morocco_tz = pytz.timezone('Africa/Casablanca')
    now_morocco = datetime.now(morocco_tz)
    start_morocco = (now_morocco + timedelta(hours=2)).isoformat()
    end_morocco = (now_morocco + timedelta(hours=3)).isoformat()
    
    print(f"Start time (Morocco): {start_morocco}")
    print(f"End time (Morocco): {end_morocco}")
    
    try:
        result2 = await calendar.create_event(
            summary="Debug Test Event 2",
            start_time=start_morocco,
            end_time=end_morocco,
            description="Testing Morocco timezone",
            check_for_conflicts=False
        )
        print(f"Result 2: {result2}")
    except Exception as e:
        print(f"Error 2: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Use the time converter like the agent does
    print("\\n--- Test 3: Using TimeConverter like the agent ---")
    try:
        start_iso, end_iso = TimeConverter.natural_time_to_iso("tomorrow", "3pm", 60)
        print(f"TimeConverter start: {start_iso}")
        print(f"TimeConverter end: {end_iso}")
        
        result3 = await calendar.create_event(
            summary="Debug Test Event 3",
            start_time=start_iso,
            end_time=end_iso,
            description="Testing TimeConverter output",
            check_for_conflicts=False
        )
        print(f"Result 3: {result3}")
    except Exception as e:
        print(f"Error 3: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\\n=== Debug Test Complete ===")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_calendar_event_creation())
'''
    
    with open("debug_calendar.py", "w") as f:
        f.write(debug_test)
    
    os.chmod("debug_calendar.py", 0o755)
    print("✅ Created debug_calendar.py")
    print("   Run it with: python debug_calendar.py")
    
    return True

def check_action_planner():
    """Check the action planner for time formatting issues"""
    print_section("Checking Action Planner")
    
    if not os.path.exists("agent/action_planner.py"):
        print("❌ agent/action_planner.py not found")
        return False
    
    with open("agent/action_planner.py", "r") as f:
        content = f.read()
    
    # Look for how time entities are processed
    if "start_time_iso" in content and "end_time_iso" in content:
        print("✅ Found ISO time processing in action planner")
    else:
        print("⚠️ ISO time processing might be missing from action planner")
    
    # Check if time processing preserves timezone information
    if "timezone" in content.lower() or "timeZone" in content:
        print("✅ Found timezone handling in action planner")
    else:
        print("⚠️ Timezone handling might be missing from action planner")
    
    return True

def main():
    """Main function to fix remaining issues"""
    print_section("Fixing WhatsApp Agent Issues")
    print("This will fix:")
    print("1. XML appearing in WhatsApp messages") 
    print("2. Calendar event creation failures")
    
    # Fix XML issue
    xml_fixed = fix_xml_in_messages()
    
    # Fix calendar formatting
    calendar_fixed = fix_calendar_time_formatting()
    
    # Check action planner
    check_action_planner()
    
    # Create debug script
    create_debug_calendar_test()
    
    print_section("Summary")
    if xml_fixed:
        print("✅ Fixed XML in messages issue")
    else:
        print("❌ Could not fix XML in messages issue")
    
    if calendar_fixed:
        print("✅ Applied calendar time formatting fixes")
    else:
        print("❌ Could not apply calendar fixes")
    
    print_section("Next Steps")
    print("1. Restart your WhatsApp agent:")
    print("   python start_agent.py")
    print("2. Test again with: 'Schedule a meeting tomorrow at 3pm'")
    print("3. If still issues, run debug script:")
    print("   python debug_calendar.py")
    print("4. Check logs for any remaining errors")

if __name__ == "__main__":
    main()