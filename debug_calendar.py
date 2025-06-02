#!/usr/bin/env python3
"""
Debug calendar event creation to identify Bad Request issues
"""
import os
import sys
import asyncio
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(".")

from connectors.calendar_api import GoogleCalendarConnector
from utils.time_utils import TimeConverter

load_dotenv()

async def test_calendar_event_creation():
    """Test calendar event creation with detailed debugging"""
    print("=== Debug Calendar Event Creation ===\n")
    
    # Initialize calendar connector
    calendar = GoogleCalendarConnector(
        credentials_path=os.getenv("GOOGLE_CREDENTIALS_PATH"),
        default_calendar_id=os.getenv("GOOGLE_CALENDAR_ID")
    )
    
    print(f"Calendar ID: {calendar.default_calendar_id}")
    
    # Test 1: Simple event creation with explicit time
    print("\n--- Test 1: Simple event with explicit UTC time ---")
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
    print("\n--- Test 2: Event with Morocco timezone ---")
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
    print("\n--- Test 3: Using TimeConverter like the agent ---")
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
    
    # Test 4: Test what the action planner would generate
    print("\n--- Test 4: Simulate Action Planner Output ---")
    try:
        # This simulates what your message parser and action planner create
        from utils.message_parser import MessageParser
        from agent.llm import LLMService
        
        llm_service = LLMService()
        parser = MessageParser(llm_service)
        
        # Parse a test message
        intent = await parser.parse("Schedule a meeting tomorrow at 3pm")
        print(f"Parsed intent: {intent}")
        
        # Check if time entities were extracted properly
        entities = intent.get("entities", {})
        if "start_time_iso" in entities and "end_time_iso" in entities:
            start_iso = entities["start_time_iso"]
            end_iso = entities["end_time_iso"]
            
            print(f"Action planner would use:")
            print(f"  Start: {start_iso}")
            print(f"  End: {end_iso}")
            
            result4 = await calendar.create_event(
                summary="Meeting",
                start_time=start_iso,
                end_time=end_iso,
                description="Testing action planner output",
                check_for_conflicts=False
            )
            print(f"Result 4: {result4}")
        else:
            print("No ISO times found in parsed intent")
            
    except Exception as e:
        print(f"Error 4: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Debug Test Complete ===")

def test_time_converter():
    """Test the TimeConverter separately"""
    print("\n=== Testing TimeConverter ===")
    
    try:
        # Test various time inputs
        test_cases = [
            ("tomorrow", "3pm", 60),
            ("today", "2pm", 30),
            ("monday", "9am", 120),
        ]
        
        for date_str, time_str, duration in test_cases:
            print(f"\nTesting: {date_str} at {time_str} for {duration} minutes")
            try:
                start_iso, end_iso = TimeConverter.natural_time_to_iso(date_str, time_str, duration)
                print(f"  Start: {start_iso}")
                print(f"  End: {end_iso}")
            except Exception as e:
                print(f"  Error: {str(e)}")
                
    except Exception as e:
        print(f"TimeConverter test failed: {str(e)}")

if __name__ == "__main__":
    print("Starting calendar debug tests...")
    
    # Test TimeConverter first
    test_time_converter()
    
    # Then test calendar operations
    asyncio.run(test_calendar_event_creation())