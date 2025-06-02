# utils/message_parser.py
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from utils.time_utils import TimeConverter

class MessageParser:
    def __init__(self, llm_service):
        self.llm_service = llm_service
    
    async def parse(self, message: str) -> dict:
        """Parse a message with FIXED date handling and proper timezone support"""
        
        # Get current time in user's timezone - THIS FIXES THE DATE ISSUE
        now = TimeConverter.get_current_time_in_user_tz()
        tomorrow = now + timedelta(days=1)
        
        # Debug: Print current time context
        print(f"DEBUG - Current time: {now.strftime('%Y-%m-%d %H:%M %Z')}")
        print(f"DEBUG - Tomorrow will be: {tomorrow.strftime('%Y-%m-%d %Z')}")
        
        system_message = f"""
        You are a smart message parser that extracts intents and entities from natural language.
        
        CRITICAL CONTEXT:
        - Today's date: {now.strftime('%Y-%m-%d')} (a {now.strftime('%A')})
        - Tomorrow's date: {tomorrow.strftime('%Y-%m-%d')} (a {tomorrow.strftime('%A')})
        - Current time: {now.strftime('%H:%M %Z')}
        - User timezone: Africa/Casablanca (Morocco)
        
        PARSING RULES:
        1. When user says "tomorrow", they mean {tomorrow.strftime('%Y-%m-%d')}
        2. When user says "today", they mean {now.strftime('%Y-%m-%d')}
        3. All times should be returned in ISO format with timezone
        4. Default meeting duration is 1 hour
        5. Use 24-hour format internally but understand 12-hour user input
        
        EXAMPLES:
        - "tomorrow at 3pm" → start: "{tomorrow.strftime('%Y-%m-%d')}T15:00:00{now.strftime('%z')}"
        - "meeting at 9am tomorrow" → start: "{tomorrow.strftime('%Y-%m-%d')}T09:00:00{now.strftime('%z')}"
        - "schedule call today 2pm" → start: "{now.strftime('%Y-%m-%d')}T14:00:00{now.strftime('%z')}"
        """
        
        prompt = f"""
        Parse this message: "{message}"
        
        Extract these entities:
        1. intent: What does the user want to do? (schedule_event, reschedule_event, cancel_event, list_events, etc.)
        2. summary: Title/name of the event
        3. start_time_iso: Start time in ISO format with timezone
        4. end_time_iso: End time in ISO format with timezone (1 hour after start if not specified)
        5. location: Meeting location (if mentioned)
        6. description: Additional details (if any)
        
        Current datetime context: {now.isoformat()}
        Tomorrow's date: {tomorrow.strftime('%Y-%m-%d')}
        
        Return structured data with these exact field names.
        """
        
        output_schema = {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": [
                        "schedule_event", 
                        "reschedule_event", 
                        "cancel_event", 
                        "list_events", 
                        "find_free_time",
                        "update_event",
                        "get_event_details",
                        "general_query"
                    ]
                },
                "entities": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Event title/name"
                        },
                        "start_time_iso": {
                            "type": "string",
                            "description": "Start time in ISO format with timezone"
                        },
                        "end_time_iso": {
                            "type": "string", 
                            "description": "End time in ISO format with timezone"
                        },
                        "location": {
                            "type": "string",
                            "description": "Meeting location if specified"
                        },
                        "description": {
                            "type": "string",
                            "description": "Additional event details"
                        },
                        "duration_hours": {
                            "type": "number",
                            "default": 1,
                            "description": "Event duration in hours"
                        },
                        "date_mentioned": {
                            "type": "string",
                            "description": "The date string the user mentioned (today, tomorrow, etc.)"
                        }
                    }
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Confidence in the parsing (0-1)"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Explanation of how the message was parsed"
                }
            },
            "required": ["intent", "entities", "confidence"]
        }
        
        try:
            result = await self.llm_service.structured_generate(
                prompt=prompt,
                output_schema=output_schema,
                system_message=system_message
            )
            
            # Post-process and validate the result
            result = self._validate_and_fix_parsing(result, now, tomorrow)
            
            # Debug: Log the parsing result
            print(f"DEBUG - Parsed result: {json.dumps(result, indent=2)}")
            
            return result
            
        except Exception as e:
            print(f"Error in message parsing: {e}")
            # Return a basic fallback result
            return {
                "intent": "general_query",
                "entities": {},
                "confidence": 0.1,
                "reasoning": f"Parsing failed: {str(e)}"
            }
    
    def _validate_and_fix_parsing(self, result: dict, now: datetime, tomorrow: datetime) -> dict:
        """Validate and fix common parsing issues"""
        
        entities = result.get("entities", {})
        
        # Fix common timezone issues
        if "start_time_iso" in entities:
            start_time = entities["start_time_iso"]
            try:
                # Ensure proper timezone format
                if start_time and not start_time.endswith(('+', '-')) and 'T' in start_time:
                    # Add timezone if missing
                    if not any(tz in start_time for tz in ['+', '-', 'Z']):
                        # Assume user's timezone
                        user_tz_offset = now.strftime('%z')
                        entities["start_time_iso"] = start_time + user_tz_offset
                        
                # Auto-generate end time if missing
                if "end_time_iso" not in entities or not entities["end_time_iso"]:
                    try:
                        start_dt = datetime.fromisoformat(entities["start_time_iso"].replace('Z', '+00:00'))
                        duration_hours = entities.get("duration_hours", 1)
                        end_dt = start_dt + timedelta(hours=duration_hours)
                        entities["end_time_iso"] = end_dt.isoformat()
                    except Exception as e:
                        print(f"Error generating end time: {e}")
                        
            except Exception as e:
                print(f"Error fixing start time: {e}")
        
        # Validate date logic
        if "date_mentioned" in entities:
            date_mentioned = entities["date_mentioned"].lower()
            if "tomorrow" in date_mentioned:
                # Ensure start_time is actually tomorrow
                if "start_time_iso" in entities:
                    try:
                        start_dt = datetime.fromisoformat(entities["start_time_iso"].replace('Z', '+00:00'))
                        if start_dt.date() != tomorrow.date():
                            print(f"WARNING: Date mismatch - user said tomorrow but parsed as {start_dt.date()}")
                            # Fix the date
                            corrected_start = start_dt.replace(
                                year=tomorrow.year,
                                month=tomorrow.month, 
                                day=tomorrow.day
                            )
                            entities["start_time_iso"] = corrected_start.isoformat()
                            
                            # Fix end time too
                            if "end_time_iso" in entities:
                                end_dt = datetime.fromisoformat(entities["end_time_iso"].replace('Z', '+00:00'))
                                corrected_end = end_dt.replace(
                                    year=tomorrow.year,
                                    month=tomorrow.month,
                                    day=tomorrow.day
                                )
                                entities["end_time_iso"] = corrected_end.isoformat()
                    except Exception as e:
                        print(f"Error validating tomorrow date: {e}")
        
        # Set default summary if missing
        if not entities.get("summary"):
            if result.get("intent") == "schedule_event":
                entities["summary"] = "Meeting"  # Default event name
        
        # Update the result
        result["entities"] = entities
        
        return result
    
    def extract_time_from_text(self, text: str, reference_time: datetime = None) -> dict:
        """Extract time information from natural language text"""
        
        if reference_time is None:
            reference_time = TimeConverter.get_current_time_in_user_tz()
        
        # Common time patterns and their handlers
        time_patterns = {
            "tomorrow": reference_time + timedelta(days=1),
            "today": reference_time,
            "next week": reference_time + timedelta(days=7),
            "monday": self._get_next_weekday(reference_time, 0),  # Monday = 0
            "tuesday": self._get_next_weekday(reference_time, 1),
            "wednesday": self._get_next_weekday(reference_time, 2),
            "thursday": self._get_next_weekday(reference_time, 3),
            "friday": self._get_next_weekday(reference_time, 4),
        }
        
        text_lower = text.lower()
        
        # Find date reference
        target_date = None
        for pattern, date_obj in time_patterns.items():
            if pattern in text_lower:
                target_date = date_obj.date() if hasattr(date_obj, 'date') else date_obj
                break
        
        if target_date is None:
            target_date = reference_time.date()
        
        # Extract time (simple patterns)
        time_hour = None
        if "9am" in text_lower or "9 am" in text_lower:
            time_hour = 9
        elif "10am" in text_lower or "10 am" in text_lower:
            time_hour = 10
        elif "11am" in text_lower or "11 am" in text_lower:
            time_hour = 11
        elif "2pm" in text_lower or "2 pm" in text_lower:
            time_hour = 14
        elif "3pm" in text_lower or "3 pm" in text_lower:
            time_hour = 15
        elif "4pm" in text_lower or "4 pm" in text_lower:
            time_hour = 16
        elif "5pm" in text_lower or "5 pm" in text_lower:
            time_hour = 17
        
        return {
            "target_date": target_date,
            "time_hour": time_hour,
            "reference_time": reference_time
        }
    
    def _get_next_weekday(self, reference_time: datetime, weekday: int) -> datetime:
        """Get the next occurrence of a specific weekday"""
        days_ahead = weekday - reference_time.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return reference_time + timedelta(days=days_ahead)
    
    def parse_simple_time(self, text: str) -> Optional[Dict[str, Any]]:
        """Simple regex-based time parser for fallback"""
        
        text_lower = text.lower().strip()
        now = TimeConverter.get_current_time_in_user_tz()
        
        # Extract date references
        date_patterns = {
            r'\btomorrow\b': now + timedelta(days=1),
            r'\btoday\b': now,
            r'\bnext week\b': now + timedelta(days=7),
        }
        
        target_date = now.date()
        for pattern, date_obj in date_patterns.items():
            if re.search(pattern, text_lower):
                target_date = date_obj.date()
                break
        
        # Extract time using regex
        time_patterns = [
            r'(\d{1,2})\s*(?::|\.)\s*(\d{2})\s*(am|pm)',  # 3:00 pm, 9.30 am
            r'(\d{1,2})\s*(am|pm)',  # 3pm, 9am
            r'(\d{1,2})\s*(?::|\.)\s*(\d{2})',  # 15:00, 9.30 (24h)
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text_lower)
            if match:
                groups = match.groups()
                
                if len(groups) == 3:  # Hour, minute, am/pm
                    hour = int(groups[0])
                    minute = int(groups[1])
                    am_pm = groups[2]
                    
                    if am_pm == 'pm' and hour != 12:
                        hour += 12
                    elif am_pm == 'am' and hour == 12:
                        hour = 0
                        
                elif len(groups) == 2:
                    if groups[1] in ['am', 'pm']:  # Hour, am/pm
                        hour = int(groups[0])
                        minute = 0
                        am_pm = groups[1]
                        
                        if am_pm == 'pm' and hour != 12:
                            hour += 12
                        elif am_pm == 'am' and hour == 12:
                            hour = 0
                    else:  # Hour, minute (24h)
                        hour = int(groups[0])
                        minute = int(groups[1])
                
                # Create datetime
                try:
                    user_tz = TimeConverter.get_user_timezone()
                    start_dt = user_tz.localize(datetime.combine(target_date, datetime.min.time()))
                    start_dt = start_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    end_dt = start_dt + timedelta(hours=1)  # Default 1 hour duration
                    
                    return {
                        "start_time_iso": start_dt.isoformat(),
                        "end_time_iso": end_dt.isoformat(),
                        "target_date": target_date,
                        "time_hour": hour,
                        "time_minute": minute
                    }
                except Exception as e:
                    print(f"Error creating datetime: {e}")
                    continue
        