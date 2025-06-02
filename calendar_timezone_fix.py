#!/usr/bin/env python3
"""
Fix time zone issues in the Google Calendar connector
"""
import os
import re

def update_calendar_connector():
    """Update the calendar connector to use the correct time zone"""
    connector_path = 'connectors/calendar_api.py'
    
    if not os.path.exists(connector_path):
        print(f"❌ Error: {connector_path} not found")
        return False
    
    # Read the current file
    with open(connector_path, 'r') as f:
        content = f.read()
    
    # Check if already using a non-UTC time zone
    if "'timeZone': 'GMT+01'" in content or "'timeZone': 'Africa/Casablanca'" in content:
        print("✅ Calendar connector is already using a non-UTC time zone")
        return True
    
    # Replace all instances of 'UTC' with your time zone
    updated_content = content.replace("'timeZone': 'UTC'", "'timeZone': 'Africa/Casablanca'")
    
    # Write the updated content
    with open(connector_path, 'w') as f:
        f.write(updated_content)
    
    print("✅ Updated calendar connector to use Africa/Casablanca time zone")
    print("   This will ensure your events are created in your local time zone")
    return True

def check_calendar_event_creation():
    """Check the calendar event creation implementation"""
    connector_path = 'connectors/calendar_api.py'
    
    if not os.path.exists(connector_path):
        print(f"❌ Error: {connector_path} not found")
        return False
    
    # Read the current file
    with open(connector_path, 'r') as f:
        content = f.read()
    
    # Print the time zone settings from the file
    create_event_method = re.search(r'def _create_event_sync\([^)]+\):(.*?)def', content, re.DOTALL)
    if create_event_method:
        create_event_code = create_event_method.group(1)
        time_zone_settings = re.findall(r"'timeZone': '([^']+)'", create_event_code)
        
        print("\nCurrent time zone settings in _create_event_sync:")
        for tz in time_zone_settings:
            print(f" - {tz}")
    
    # Find chat handler or agent code to see how it processes time
    agent_files = ['agent.py', 'chat_handler.py', 'llm_handler.py', 'intent_handler.py']
    
    print("\nChecking time processing in agent code:")
    for file in agent_files:
        if os.path.exists(file):
            with open(file, 'r') as f:
                agent_content = f.read()
            
            # Look for time parsing or scheduling code
            if "schedule" in agent_content or "calendar" in agent_content:
                print(f"Found potential time handling code in {file}")
                
                # Look for time zone handling
                if "timezone" in agent_content or "time_zone" in agent_content:
                    print(f" - {file} has time zone handling code")
                else:
                    print(f" - {file} might be missing explicit time zone handling")

def create_timezone_handling_snippet():
    """Create a snippet for better time zone handling"""
    snippet = """
# Add this to your agent's calendar handling code

def handle_time_with_timezone(time_str, user_timezone='Africa/Casablanca'):
    \"\"\"
    Process time strings with proper time zone handling
    
    Args:
        time_str: The time string from the user (e.g., "3pm", "15:00")
        user_timezone: The user's timezone (default: Africa/Casablanca for Morocco)
        
    Returns:
        ISO format datetime string with proper timezone
    \"\"\"
    import re
    from datetime import datetime, timedelta
    import pytz
    
    # Get user's timezone object
    tz = pytz.timezone(user_timezone)
    
    # Get current date in user's timezone
    now = datetime.now(tz)
    
    # Extract hour and minute from time string
    hour = None
    minute = 0
    
    # Try different formats
    am_pm_match = re.search(r'(\d+)(?::(\d+))?\s*(am|pm)', time_str.lower())
    if am_pm_match:
        hour = int(am_pm_match.group(1))
        minute = int(am_pm_match.group(2)) if am_pm_match.group(2) else 0
        if am_pm_match.group(3) == 'pm' and hour < 12:
            hour += 12
        elif am_pm_match.group(3) == 'am' and hour == 12:
            hour = 0
    else:
        # Try 24-hour format
        hour_match = re.search(r'(\d+)(?::(\d+))?', time_str)
        if hour_match:
            hour = int(hour_match.group(1))
            minute = int(hour_match.group(2)) if hour_match.group(2) else 0
    
    if hour is None:
        raise ValueError(f"Could not parse time from string: {time_str}")
    
    # Create datetime with the specified time
    event_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Handle "tomorrow" or specific dates
    if "tomorrow" in time_str.lower():
        event_time += timedelta(days=1)
    
    # Return ISO format with timezone info
    return event_time.isoformat()

# Example usage:
# start_time = handle_time_with_timezone("3pm tomorrow")
# end_time = handle_time_with_timezone("4pm tomorrow")
"""
    
    # Write the snippet to a file
    with open('timezone_handling.py', 'w') as f:
        f.write(snippet)
    
    print("\n✅ Created timezone_handling.py with better time zone handling code")
    print("   You can incorporate this into your agent's calendar handling logic")

if __name__ == "__main__":
    print("=== Calendar Time Zone Fix ===")
    
    # Update calendar connector
    update_calendar_connector()
    
    # Check event creation implementation
    check_calendar_event_creation()
    
    # Create better time zone handling snippet
    create_timezone_handling_snippet()
    
    print("\n=== Next Steps ===")
    print("1. Restart your WhatsApp AI agent")
    print("2. Test scheduling by specifying the time zone explicitly:")
    print("   Example: 'Schedule a meeting tomorrow at 3pm Morocco time'")
    print("3. For more reliable time handling, consider incorporating")
    print("   the code from timezone_handling.py into your agent")