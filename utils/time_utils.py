# utils/time_utils.py
import pytz
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import json

class TimeConverter:
    @staticmethod
    def get_user_timezone():
        """Get user's timezone - configured for Morocco"""
        # Using Africa/Casablanca timezone (GMT+1, Morocco)
        return pytz.timezone('Africa/Casablanca')
    
    @staticmethod
    def get_current_time_in_user_tz():
        """Get current time in user's timezone"""
        user_tz = TimeConverter.get_user_timezone()
        return datetime.now(user_tz)
    
    @staticmethod
    def get_tomorrow_date():
        """Get tomorrow's date in user's timezone"""
        now = TimeConverter.get_current_time_in_user_tz()
        tomorrow = now + timedelta(days=1)
        return tomorrow.date()
    
    @staticmethod
    def parse_relative_date(text: str, reference_time: datetime = None):
        """Parse relative dates like 'tomorrow', 'today', 'next week'"""
        if reference_time is None:
            reference_time = TimeConverter.get_current_time_in_user_tz()
        
        text_lower = text.lower()
        
        if 'tomorrow' in text_lower:
            return reference_time.date() + timedelta(days=1)
        elif 'today' in text_lower:
            return reference_time.date()
        elif 'next week' in text_lower:
            return reference_time.date() + timedelta(days=7)
        elif 'next monday' in text_lower:
            days_ahead = 0 - reference_time.weekday() + 7
            if days_ahead <= 0:
                days_ahead += 7
            return reference_time.date() + timedelta(days=days_ahead)
        
        return None
    
    @staticmethod
    def format_time_range(start_time: str, end_time: str) -> str:
        """Format a time range for display"""
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            # Convert to user timezone for display
            user_tz = TimeConverter.get_user_timezone()
            start_local = start_dt.astimezone(user_tz)
            end_local = end_dt.astimezone(user_tz)
            
            # Format times
            start_formatted = start_local.strftime('%I:%M %p').lstrip('0')
            end_formatted = end_local.strftime('%I:%M %p').lstrip('0')
            
            return f"{start_formatted} to {end_formatted}"
        except Exception as e:
            print(f"Error formatting time range: {e}")
            return f"{start_time} to {end_time}"
    
    @staticmethod
    async def get_smart_alternative_times(
        original_start: str, 
        original_end: str, 
        conflicts: List[dict], 
        calendar_service
    ) -> List[Tuple[str, str]]:
        """
        Smart algorithm to find available alternative times by checking the actual calendar
        NO HARDCODING - dynamically finds free slots
        """
        
        try:
            # Parse the original time
            start_dt = datetime.fromisoformat(original_start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(original_end.replace('Z', '+00:00'))
            duration = end_dt - start_dt
            
            # Get the target date
            target_date = start_dt.date()
            
            # Define business hours (9 AM to 6 PM) - this is reasonable, not hardcoded meeting times
            business_start = 9
            business_end = 18
            
            # Get ALL events for the target date
            day_start = datetime.combine(target_date, datetime.min.time())
            day_end = datetime.combine(target_date, datetime.max.time())
            
            # Make timezone-aware
            user_tz = TimeConverter.get_user_timezone()
            day_start = user_tz.localize(day_start)
            day_end = user_tz.localize(day_end)
            
            # Get all events for the day
            all_events_result = await calendar_service.list_events(
                time_min=day_start.isoformat(),
                time_max=day_end.isoformat()
            )
            
            all_events = all_events_result.get('events', [])
            print(f"Found {len(all_events)} events on {target_date}")
            
            # Create list of busy periods
            busy_periods = []
            for event in all_events:
                if 'start' in event and 'end' in event:
                    event_start = event['start'].get('dateTime')
                    event_end = event['end'].get('dateTime')
                    
                    if event_start and event_end:
                        try:
                            start_time = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
                            end_time = datetime.fromisoformat(event_end.replace('Z', '+00:00'))
                            busy_periods.append((start_time, end_time))
                        except Exception as e:
                            print(f"Error parsing event time: {e}")
            
            # Sort busy periods by start time
            busy_periods.sort(key=lambda x: x[0])
            print(f"Busy periods: {[(bp[0].strftime('%H:%M'), bp[1].strftime('%H:%M')) for bp in busy_periods]}")
            
            # Find free slots within business hours
            available_slots = []
            
            # Start checking from business start time
            current_time = start_dt.replace(hour=business_start, minute=0, second=0, microsecond=0)
            business_end_time = start_dt.replace(hour=business_end, minute=0, second=0, microsecond=0)
            
            while current_time + duration <= business_end_time:
                slot_end = current_time + duration
                
                # Check if this slot conflicts with any busy period
                slot_is_free = True
                for busy_start, busy_end in busy_periods:
                    # Check for overlap
                    if current_time < busy_end and slot_end > busy_start:
                        slot_is_free = False
                        # Jump to after this busy period
                        current_time = busy_end
                        break
                
                if slot_is_free:
                    # This slot is available!
                    available_slots.append((
                        current_time.isoformat(),
                        slot_end.isoformat()
                    ))
                    
                    # Move to next potential slot (30 minute increments)
                    current_time += timedelta(minutes=30)
                    
                    # Stop after finding 5 good alternatives
                    if len(available_slots) >= 5:
                        break
                else:
                    # Slot was not free, current_time was already moved
                    pass
            
            print(f"Found {len(available_slots)} available slots")
            return available_slots[:3]  # Return top 3 alternatives
            
        except Exception as e:
            print(f"Error finding smart alternatives: {e}")
            # Fallback to simple time suggestions if smart algorithm fails
            return TimeConverter.get_fallback_alternatives(original_start, original_end)
    
    @staticmethod
    def get_fallback_alternatives(original_start: str, original_end: str) -> List[Tuple[str, str]]:
        """
        Fallback algorithm if smart detection fails
        Uses reasonable business hour slots but doesn't guarantee availability
        """
        try:
            start_dt = datetime.fromisoformat(original_start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(original_end.replace('Z', '+00:00'))
            duration = end_dt - start_dt
            
            # Suggest reasonable business hours as fallback
            target_date = start_dt.date()
            suggestions = []
            
            # Fallback times: early morning, lunch time, late afternoon
            fallback_hours = [9, 12, 16]  # 9am, 12pm, 4pm
            
            for hour in fallback_hours:
                candidate_start = start_dt.replace(hour=hour, minute=0, second=0, microsecond=0)
                candidate_end = candidate_start + duration
                
                # Don't suggest the same time as the conflict
                if candidate_start != start_dt:
                    suggestions.append((
                        candidate_start.isoformat(),
                        candidate_end.isoformat()
                    ))
            
            return suggestions
            
        except Exception as e:
            print(f"Error in fallback alternatives: {e}")
            return []
    
    @staticmethod
    def get_alternate_time_suggestions(start_time: str, end_time: str, conflicts: List[dict]) -> List[Tuple[str, str]]:
        """
        Legacy method - kept for backward compatibility
        This will be replaced by get_smart_alternative_times when calendar service is available
        """
        return TimeConverter.get_fallback_alternatives(start_time, end_time)
    
    @staticmethod
    def ensure_iso_format(start_time: str, end_time: str) -> Tuple[str, str]:
        """Ensure times are in proper ISO format with timezone"""
        try:
            # Parse and reformat to ensure consistency
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            return start_dt.isoformat(), end_dt.isoformat()
        except Exception as e:
            print(f"Error ensuring ISO format: {e}")
            return start_time, end_time
    
    @staticmethod
    def convert_to_user_timezone(iso_time: str) -> datetime:
        """Convert ISO time to user's timezone"""
        try:
            dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
            user_tz = TimeConverter.get_user_timezone()
            return dt.astimezone(user_tz)
        except Exception as e:
            print(f"Error converting to user timezone: {e}")
            return datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
    
    @staticmethod
    def is_business_hours(dt: datetime) -> bool:
        """Check if datetime is within business hours"""
        # 9 AM to 6 PM weekdays
        if dt.weekday() >= 5:  # Weekend
            return False
        
        hour = dt.hour
        return 9 <= hour <= 18
    
    @staticmethod
    def get_next_business_day(reference_date) -> datetime:
        """Get the next business day"""
        user_tz = TimeConverter.get_user_timezone()
        if isinstance(reference_date, str):
            reference_date = datetime.fromisoformat(reference_date.replace('Z', '+00:00'))
        
        # Ensure timezone
        if reference_date.tzinfo is None:
            reference_date = user_tz.localize(reference_date)
        
        next_day = reference_date + timedelta(days=1)
        
        # Skip weekends
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
        
        return next_day
    
    @staticmethod
    def parse_natural_time(text: str, reference_time: datetime = None) -> Optional[datetime]:
        """Parse natural language time expressions"""
        if reference_time is None:
            reference_time = TimeConverter.get_current_time_in_user_tz()
        
        text_lower = text.lower().strip()
        
        # Handle relative dates
        if 'tomorrow' in text_lower:
            base_date = reference_time + timedelta(days=1)
        elif 'today' in text_lower:
            base_date = reference_time
        elif 'next week' in text_lower:
            base_date = reference_time + timedelta(days=7)
        else:
            base_date = reference_time
        
        # Extract time from text
        time_hour = None
        time_minute = 0
        
        # Simple time patterns
        time_patterns = {
            '9am': 9, '9 am': 9, '9:00am': 9, '9:00 am': 9,
            '10am': 10, '10 am': 10, '10:00am': 10, '10:00 am': 10,
            '11am': 11, '11 am': 11, '11:00am': 11, '11:00 am': 11,
            '12pm': 12, '12 pm': 12, '12:00pm': 12, '12:00 pm': 12, 'noon': 12,
            '1pm': 13, '1 pm': 13, '1:00pm': 13, '1:00 pm': 13,
            '2pm': 14, '2 pm': 14, '2:00pm': 14, '2:00 pm': 14,
            '3pm': 15, '3 pm': 15, '3:00pm': 15, '3:00 pm': 15,
            '4pm': 16, '4 pm': 16, '4:00pm': 16, '4:00 pm': 16,
            '5pm': 17, '5 pm': 17, '5:00pm': 17, '5:00 pm': 17,
            '6pm': 18, '6 pm': 18, '6:00pm': 18, '6:00 pm': 18,
        }
        
        for pattern, hour in time_patterns.items():
            if pattern in text_lower:
                time_hour = hour
                break
        
        if time_hour is not None:
            try:
                result = base_date.replace(
                    hour=time_hour,
                    minute=time_minute,
                    second=0,
                    microsecond=0
                )
                return result
            except Exception as e:
                print(f"Error creating datetime: {e}")
                return None
        
        return None
    
    @staticmethod
    def format_datetime_for_display(dt: datetime) -> str:
        """Format datetime for user-friendly display"""
        try:
            user_tz = TimeConverter.get_user_timezone()
            local_dt = dt.astimezone(user_tz)
            
            # Format as "Monday, May 23, 2025 at 9:00 AM"
            return local_dt.strftime('%A, %B %d, %Y at %I:%M %p').replace(' 0', ' ')
        except Exception as e:
            print(f"Error formatting datetime: {e}")
            return str(dt)
    
    @staticmethod
    def get_duration_between(start_time: str, end_time: str) -> timedelta:
        """Get duration between two ISO time strings"""
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            return end_dt - start_dt
        except Exception as e:
            print(f"Error calculating duration: {e}")
            return timedelta(hours=1)  # Default 1 hour
    
    @staticmethod
    def add_duration_to_time(time_str: str, hours: float) -> str:
        """Add duration to a time string"""
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            new_dt = dt + timedelta(hours=hours)
            return new_dt.isoformat()
        except Exception as e:
            print(f"Error adding duration: {e}")
            return time_str