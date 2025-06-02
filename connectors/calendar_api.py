# connectors/calendar_api.py
"""Enhanced Google Calendar Connector with additional features"""

import os
import json
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv
from utils.time_utils import TimeConverter

# Load environment variables
load_dotenv()

class GoogleCalendarConnector:
    """Enhanced connector for Google Calendar API with additional features"""
    
    def __init__(self, credentials_path: str, default_calendar_id: str = None):
        self.credentials_path = credentials_path
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path, 
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        self.service = build('calendar', 'v3', credentials=self.credentials)
        
        # Get the user's calendar ID from environment or use the provided default
        self.default_calendar_id = default_calendar_id or os.getenv("GOOGLE_CALENDAR_ID")
        
        print(f"Initialized Enhanced Google Calendar Connector with default calendar ID: {self.default_calendar_id}")
        
        print(f"Initialized Enhanced Google Calendar Connector with default calendar ID: {self.default_calendar_id}")
        
    async def execute(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a method on the Enhanced Google Calendar API
        
        Args:
            method: The method to execute
            params: Parameters for the method
            
        Returns:
            The result of the operation
        """
        method_map = {
            # Standard methods
            'list_events': self.list_events,
            'create_event': self.create_event,
            'update_event': self.update_event,
            'delete_event': self.delete_event,
            'check_conflicts': self.check_conflicts,
            
            # Enhanced methods
            'create_event_with_attendees': self.create_event_with_attendees,
            'find_free_time': self.find_free_time,
            'search_events': self.search_events,
            'reschedule_event': self.reschedule_event,
        }
        
        if method not in method_map:
            return {"error": f"Unknown method: {method}"}
        
        try:
            return await method_map[method](**params)
        except Exception as e:
            return {"error": str(e)}
            
    def _ensure_iso_format(self, start_time, end_time):
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
        
        return formatted_start, formatted_end

    async def list_events(self, 
                         time_min: Optional[str] = None,
                         time_max: Optional[str] = None,
                         max_results: int = 10,
                         calendar_id: str = None) -> Dict[str, Any]:
        """
        List upcoming events from the calendar
        
        Args:
            time_min: Start time (ISO format)
            time_max: End time (ISO format)
            max_results: Maximum number of events to return
            calendar_id: Calendar ID to query (uses default if None)
            
        Returns:
            List of calendar events
        """
        # Use the provided calendar_id or fall back to the default
        calendar_id = calendar_id or self.default_calendar_id
        
        # Set default time range if not provided
        if time_min is None:
            time_min = datetime.now(TimeConverter.TIMEZONE).isoformat()
        
        if time_max is None:
            time_max = (datetime.now(TimeConverter.TIMEZONE) + timedelta(days=7)).isoformat()
        
        # Ensure times are in ISO format
        time_min, time_max = self._ensure_iso_format(time_min, time_max)
        
        # Execute in a thread pool to avoid blocking
        return await asyncio.to_thread(self._list_events_sync, time_min, time_max, max_results, calendar_id)

    def _list_events_sync(self, time_min, time_max, max_results, calendar_id):
        """Synchronous implementation of list_events"""
        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            formatted_events = []
            
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                formatted_events.append({
                    'id': event['id'],
                    'summary': event.get('summary', 'No title'),
                    'start': start,
                    'end': end,
                    'location': event.get('location', ''),
                    'description': event.get('description', '')
                })
            
            return {
                "status": "success",
                "count": len(formatted_events),
                "events": formatted_events
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to list events: {str(e)}"
            }

    # === Enhanced Event Creation Methods ===
    
    async def create_event_with_attendees(self, 
                                       summary: str,
                                       start_time: str,
                                       end_time: str,
                                       attendees: List[str] = None,
                                       description: str = "",
                                       location: str = "",
                                       add_conferencing: bool = False,
                                       calendar_id: str = None,
                                       check_for_conflicts: bool = True) -> Dict[str, Any]:
        """
        Create a new calendar event with attendees and optional video conferencing
        
        Args:
            summary: Event title
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            attendees: List of attendee email addresses
            description: Event description
            location: Event location
            add_conferencing: Whether to add Google Meet conferencing
            calendar_id: Calendar ID (uses default if None)
            check_for_conflicts: Whether to check for conflicting events
            
        Returns:
            Details of the created event
        """
        # Use the provided calendar_id or fall back to the default
        calendar_id = calendar_id or self.default_calendar_id

        # Format the times if needed to ensure proper ISO format
        start_time, end_time = self._ensure_iso_format(start_time, end_time)

        # Check for conflicts if requested
        if check_for_conflicts:
            conflicts = await self.check_conflicts(start_time, end_time, calendar_id)
            
            if conflicts["status"] == "success" and conflicts["has_conflicts"]:
                return {
                    "status": "conflict",
                    "message": f"Found {conflicts['count']} conflicting events in the specified time range",
                    "conflicts": conflicts["conflicts"]
                }
        
        # Execute in a thread pool to avoid blocking
        return await asyncio.to_thread(
            self._create_rich_event_sync, 
            summary, start_time, end_time, attendees, description, 
            location, add_conferencing, calendar_id
        )
    
    def _create_rich_event_sync(self, summary, start_time, end_time, 
                            attendees, description, location, 
                            add_conferencing, calendar_id):
        """Synchronous implementation of create_event_with_attendees"""
        try:
            # Determine if the time format includes a time component or just a date
            time_format = 'dateTime' if 'T' in start_time else 'date'
            
            # Create the event body
            event_body = {
                'summary': summary,
                'location': location,
                'description': description,
                'start': {
                    time_format: start_time,
                    'timeZone': 'Africa/Casablanca',
                },
                'end': {
                    time_format: end_time,
                    'timeZone': 'Africa/Casablanca',
                }
            }
            
            # Add attendees if provided
            if attendees:
                event_body['attendees'] = [{'email': email} for email in attendees]
            
            # Add conferencing if requested
            if add_conferencing:
                event_body['conferenceData'] = {
                    'createRequest': {
                        'requestId': f'meet-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                }
                
                # Set the conference data version
                conferenceDataVersion = 1
            else:
                conferenceDataVersion = 0
            
            # Insert the event
            event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_body,
                conferenceDataVersion=conferenceDataVersion,
                sendUpdates='all' if attendees else 'none'
            ).execute()
            
            # Format the response
            response = {
                "status": "success",
                "message": "Event created successfully",
                "event": {
                    "id": event['id'],
                    "summary": event.get('summary', 'No title'),
                    "start": event['start'].get('dateTime', event['start'].get('date')),
                    "end": event['end'].get('dateTime', event['end'].get('date')),
                    "location": event.get('location', ''),
                    "description": event.get('description', ''),
                    "html_link": event.get('htmlLink', '')
                }
            }
            
            # Add conferencing info if present
            if 'conferenceData' in event:
                conf_data = event['conferenceData']
                if 'entryPoints' in conf_data:
                    for entry in conf_data['entryPoints']:
                        if entry.get('entryPointType') == 'video':
                            response["event"]["conference_link"] = entry.get('uri', '')
                            break
            
            # Add attendee info if present
            if 'attendees' in event:
                response["event"]["attendees"] = [
                    {"email": attendee.get('email')} 
                    for attendee in event.get('attendees', [])
                ]
            
            return response
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create event: {str(e)}"
            }
    
    # === Calendar Management Feature Methods ===
    
    async def find_free_time(self, 
                            date: str = None,
                            time_min: str = None,
                            time_max: str = None,
                            duration_minutes: int = 60,
                            calendar_id: str = None) -> Dict[str, Any]:
        """
        Find free time slots on a specific date or time range
        
        Args:
            date: Date to check (natural language, e.g., 'tomorrow')
            time_min: Start time range (ISO format)
            time_max: End time range (ISO format)
            duration_minutes: Minimum duration of free time slot in minutes
            calendar_id: Calendar ID to query (uses default if None)
            
        Returns:
            List of available time slots
        """
        # Use the provided calendar_id or fall back to the default
        calendar_id = calendar_id or self.default_calendar_id
        
        # For debugging
        print(f"Finding free time with parameters: date={date}, time_min={time_min}, time_max={time_max}, duration_minutes={duration_minutes}")
        
        # If date is provided, generate time_min and time_max for that day
        if date and not (time_min and time_max):
            # Convert natural language date to start/end timestamps for the day
            now = datetime.now()
            
            if date.lower() == "today":
                date_obj = now.date()
            elif date.lower() == "tomorrow":
                date_obj = (now + timedelta(days=1)).date()
            else:
                # Try to parse as a date
                try:
                    # Simple date parsing for common formats
                    if '/' in date:  # MM/DD/YYYY or MM/DD
                        parts = date.split('/')
                        if len(parts) == 3:  # MM/DD/YYYY
                            date_obj = datetime(int(parts[2]), int(parts[0]), int(parts[1])).date()
                        else:  # MM/DD
                            date_obj = datetime(now.year, int(parts[0]), int(parts[1])).date()
                    elif '-' in date:  # YYYY-MM-DD
                        parts = date.split('-')
                        date_obj = datetime(int(parts[0]), int(parts[1]), int(parts[2])).date()
                    else:
                        # Default to tomorrow if parsing fails
                        date_obj = (now + timedelta(days=1)).date()
                except Exception as e:
                    print(f"Date parsing error: {str(e)}")
                    # Default to tomorrow if parsing fails
                    date_obj = (now + timedelta(days=1)).date()
            
            # Set the time range for the date (8am - 8pm)
            day_start = datetime.combine(date_obj, datetime.min.time().replace(hour=8, minute=0))
            day_end = datetime.combine(date_obj, datetime.min.time().replace(hour=20, minute=0))
            
            # Convert to ISO format
            time_min = day_start.isoformat() + 'Z'
            time_max = day_end.isoformat() + 'Z'
        
        # Ensure times are in ISO format
        if time_min and time_max:
            time_min, time_max = self._ensure_iso_format(time_min, time_max)
        else:
            # Default to next 24 hours if no time range specified
            now = datetime.now()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=1)).isoformat() + 'Z'
        
        print(f"Using time range: {time_min} to {time_max}")
        
        # Get events for the time range
        events_result = await self.list_events(
            time_min=time_min,
            time_max=time_max,
            max_results=100,
            calendar_id=calendar_id
        )
        
        if events_result.get("status") != "success":
            return {
                "status": "error",
                "message": f"Failed to list events: {events_result.get('message', 'Unknown error')}"
            }
        
        # Extract events
        events = events_result.get("events", [])
        print(f"Retrieved {len(events)} events from calendar")
        
        # Convert start and end times to datetime objects
        start_dt = datetime.fromisoformat(time_min.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(time_max.replace('Z', '+00:00'))
        
        # Extract busy times from events
        busy_times = []
        for event in events:
            # Get event start and end times
            event_start = event.get("start")
            event_end = event.get("end")
            
            # Skip if missing start or end
            if not event_start or not event_end:
                continue
                
            # Convert to datetime objects
            try:
                if 'T' in event_start:  # DateTime format
                    event_start_dt = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
                else:  # Date-only format
                    event_start_dt = datetime.fromisoformat(f"{event_start}T00:00:00+00:00")
                
                if 'T' in event_end:  # DateTime format
                    event_end_dt = datetime.fromisoformat(event_end.replace('Z', '+00:00'))
                else:  # Date-only format
                    event_end_dt = datetime.fromisoformat(f"{event_end}T23:59:59+00:00")
                    
                busy_times.append((event_start_dt, event_end_dt))
            except Exception as e:
                print(f"Error parsing event time: {str(e)}")
                # Skip events with invalid dates
                continue
        
        # Sort busy times by start time
        busy_times.sort(key=lambda x: x[0])
        print(f"Extracted {len(busy_times)} busy time periods")
        
        # Find free slots between busy times
        free_slots = []
        current_time = start_dt
        
        # Check for a slot at the beginning
        if not busy_times or busy_times[0][0] > current_time:
            first_busy_start = busy_times[0][0] if busy_times else end_dt
            slot_duration = (first_busy_start - current_time).total_seconds() / 60
            
            if slot_duration >= duration_minutes:
                free_slots.append({
                    "start": current_time.isoformat(),
                    "end": first_busy_start.isoformat(),
                    "duration_minutes": int(slot_duration)
                })
        
        # Check for slots between busy times
        for i in range(len(busy_times)):
            current_busy_end = busy_times[i][1]
            
            # Update current_time to the end of this busy period
            if current_busy_end > current_time:
                current_time = current_busy_end
            
            # If there's another busy period, check for a free slot between them
            if i + 1 < len(busy_times):
                next_busy_start = busy_times[i+1][0]
                
                # Calculate duration of potential free slot
                slot_duration = (next_busy_start - current_time).total_seconds() / 60
                
                # If the free slot is long enough, add it
                if slot_duration >= duration_minutes:
                    free_slots.append({
                        "start": current_time.isoformat(),
                        "end": next_busy_start.isoformat(),
                        "duration_minutes": int(slot_duration)
                    })
        
        # Check for a slot at the end
        if current_time < end_dt:
            slot_duration = (end_dt - current_time).total_seconds() / 60
            
            if slot_duration >= duration_minutes:
                free_slots.append({
                    "start": current_time.isoformat(),
                    "end": end_dt.isoformat(),
                    "duration_minutes": int(slot_duration)
                })
        
        print(f"Found {len(free_slots)} free time slots")
        
        # Add human-readable time to each slot
        for slot in free_slots:
            slot_start = datetime.fromisoformat(slot["start"].replace('Z', '+00:00'))
            slot_end = datetime.fromisoformat(slot["end"].replace('Z', '+00:00'))
            
            slot["readable_time"] = (
                f"{slot_start.strftime('%A, %B %d, %Y')}, "
                f"{slot_start.strftime('%I:%M %p')} - {slot_end.strftime('%I:%M %p')}"
            )
        
        return {
            "status": "success",
            "date_range": {
                "start": time_min,
                "end": time_max
            },
            "free_slots": free_slots,
            "count": len(free_slots)
        }
    
    async def search_events(self, 
                          query: str,
                          time_min: Optional[str] = None,
                          time_max: Optional[str] = None,
                          max_results: int = 10,
                          calendar_id: str = None) -> Dict[str, Any]:
        """
        Search for events matching a query
        
        Args:
            query: Search query (e.g., "meeting with John")
            time_min: Start time (ISO format)
            time_max: End time (ISO format)
            max_results: Maximum number of events to return
            calendar_id: Calendar ID to query (uses default if None)
            
        Returns:
            List of matching events
        """
        # Use the provided calendar_id or fall back to the default
        calendar_id = calendar_id or self.default_calendar_id
        
        # Set default time range if not provided
        if time_min is None:
            time_min = datetime.now(TimeConverter.TIMEZONE).isoformat()
        
        if time_max is None:
            time_max = (datetime.now(TimeConverter.TIMEZONE) + timedelta(days=30)).isoformat()
        
        # Ensure times are in ISO format
        time_min, time_max = self._ensure_iso_format(time_min, time_max)
        
        # Execute in a thread pool to avoid blocking
        return await asyncio.to_thread(
            self._search_events_sync, 
            query, time_min, time_max, max_results, calendar_id
        )
    
    def _search_events_sync(self, query, time_min, time_max, max_results, calendar_id):
        """Synchronous implementation of search_events"""
        try:
            # Get all events in the time range
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results * 2,  # Get more than needed to filter
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Filter events by query
            query_terms = query.lower().split()
            matched_events = []
            
            for event in events:
                event_text = (
                    event.get('summary', '') + ' ' +
                    event.get('description', '') + ' ' +
                    event.get('location', '')
                ).lower()
                
                # Check for attendees if available
                if 'attendees' in event:
                    for attendee in event['attendees']:
                        event_text += ' ' + attendee.get('email', '') + ' ' + attendee.get('displayName', '')
                
                # Check if all query terms are in the event text
                if all(term in event_text for term in query_terms):
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    end = event['end'].get('dateTime', event['end'].get('date'))
                    
                    matched_events.append({
                        'id': event['id'],
                        'summary': event.get('summary', 'No title'),
                        'start': start,
                        'end': end,
                        'location': event.get('location', ''),
                        'description': event.get('description', ''),
                        'html_link': event.get('htmlLink', '')
                    })
                    
                    # Add readable times
                    if 'T' in start:
                        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        matched_events[-1]['readable_start'] = start_dt.strftime('%A, %B %d, %Y, %I:%M %p')
                    
                    # Limit to max_results
                    if len(matched_events) >= max_results:
                        break
            
            return {
                "status": "success",
                "query": query,
                "count": len(matched_events),
                "events": matched_events
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to search events: {str(e)}"
            }
    
    async def reschedule_event(self,
                             event_id: str,
                             new_start_time: str,
                             new_end_time: Optional[str] = None,
                             calendar_id: str = None,
                             check_for_conflicts: bool = True) -> Dict[str, Any]:
        """
        Reschedule an existing event to a new time
        
        Args:
            event_id: ID of the event to reschedule
            new_start_time: New start time (ISO format)
            new_end_time: New end time (ISO format, optional if preserving duration)
            calendar_id: Calendar ID (uses default if None)
            check_for_conflicts: Whether to check for conflicting events
            
        Returns:
            Details of the updated event
        """
        # Use the provided calendar_id or fall back to the default
        calendar_id = calendar_id or self.default_calendar_id
        
        # Ensure time is in ISO format
        new_start_time, _ = self._ensure_iso_format(new_start_time, new_start_time)
        
        # Execute in a thread pool to avoid blocking
        return await asyncio.to_thread(
            self._reschedule_event_sync, 
            event_id, new_start_time, new_end_time, calendar_id, check_for_conflicts
        )
    
    def _reschedule_event_sync(self, event_id, new_start_time, new_end_time, calendar_id, check_for_conflicts):
        """Synchronous implementation of reschedule_event"""
        try:
            # First get the existing event
            event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            
            # If no new end time is provided, preserve the original duration
            if not new_end_time:
                original_start = event['start'].get('dateTime', event['start'].get('date'))
                original_end = event['end'].get('dateTime', event['end'].get('date'))
                
                if 'T' in original_start and 'T' in original_end:
                    # Calculate original duration
                    start_dt = datetime.fromisoformat(original_start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(original_end.replace('Z', '+00:00'))
                    duration = end_dt - start_dt
                    
                    # Add duration to new start time
                    new_start_dt = datetime.fromisoformat(new_start_time.replace('Z', '+00:00'))
                    new_end_dt = new_start_dt + duration
                    new_end_time = new_end_dt.isoformat()
                else:
                    # For all-day events, keep the same duration in days
                    start_date = datetime.fromisoformat(original_start)
                    end_date = datetime.fromisoformat(original_end)
                    duration_days = (end_date - start_date).days
                    
                    new_start_date = datetime.fromisoformat(new_start_time)
                    new_end_date = new_start_date + timedelta(days=duration_days)
                    new_end_time = new_end_date.isoformat()
            
            # Check for conflicts if requested
            if check_for_conflicts:
                if 'T' in new_start_time:  # Only check conflicts for time-based events (not all-day)
                    # Use the existing class method, but we'll need to do it directly since we're in a sync method
                    events_result = self.service.events().list(
                        calendarId=calendar_id,
                        timeMin=new_start_time,
                        timeMax=new_end_time,
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()
                    
                    events = events_result.get('items', [])
                    conflicts = []
                    
                    for conflict_event in events:
                        # Skip the event we're rescheduling
                        if conflict_event['id'] == event_id:
                            continue
                            
                        conflicts.append({
                            'id': conflict_event['id'],
                            'summary': conflict_event.get('summary', 'No title'),
                            'start': conflict_event['start'].get('dateTime', conflict_event['start'].get('date')),
                            'end': conflict_event['end'].get('dateTime', conflict_event['end'].get('date')),
                        })
                    
                    if conflicts:
                        return {
                            "status": "conflict",
                            "message": f"Found {len(conflicts)} conflicting events in the new time range",
                            "conflicts": conflicts
                        }
            
            # Update the event times
            time_format = 'dateTime' if 'T' in new_start_time else 'date'
            event['start'] = {
                time_format: new_start_time,
                'timeZone': 'Africa/Casablanca'
            }
            
            event['end'] = {
                time_format: new_end_time,
                'timeZone': 'Africa/Casablanca'
            }
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event,
                sendUpdates='all' if 'attendees' in event else 'none'
            ).execute()
            
            # Format the response
            return {
                "status": "success",
                "message": "Event rescheduled successfully",
                "event": {
                    "id": updated_event['id'],
                    "summary": updated_event.get('summary', 'No title'),
                    "start": updated_event['start'].get('dateTime', updated_event['start'].get('date')),
                    "end": updated_event['end'].get('dateTime', updated_event['end'].get('date')),
                    "location": updated_event.get('location', ''),
                    "description": updated_event.get('description', ''),
                    "html_link": updated_event.get('htmlLink', '')
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to reschedule event: {str(e)}"
            }
    
    # Standard methods from original GoogleCalendarConnector
    async def create_event(self, 
                          summary: str,
                          start_time: str,
                          end_time: str,
                          description: str = "",
                          location: str = "",
                          calendar_id: str = None,
                          check_for_conflicts: bool = True) -> Dict[str, Any]:
        """
        Create a new calendar event
        
        Args:
            summary: Event title
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            description: Event description
            location: Event location
            calendar_id: Calendar ID (uses default if None)
            check_for_conflicts: Whether to check for conflicting events
            
        Returns:
            Details of the created event
        """
        # Use the provided calendar_id or fall back to the default
        calendar_id = calendar_id or self.default_calendar_id

        # Debug input parameters
        print(f"Creating event with parameters:")
        print(f"  summary: {summary}")
        print(f"  start_time: {start_time}")
        print(f"  end_time: {end_time}")
        print(f"  check_for_conflicts: {check_for_conflicts}")

        # Check for conflicts if requested
        if check_for_conflicts:
            print("Checking for conflicts before creating event...")
            conflicts = await self.check_conflicts(start_time, end_time, calendar_id)
            
            print(f"Conflict check result: {json.dumps(conflicts, indent=2)}")
            
            if conflicts["status"] == "success" and conflicts["has_conflicts"]:
                print(f"Found {conflicts['count']} conflicting events!")
                return {
                    "status": "conflict",
                    "message": f"Found {conflicts['count']} conflicting events in the specified time range",
                    "conflicts": conflicts["conflicts"]
                }
        else:
            print("Skipping conflict check as requested")
        
        # Format the times if needed to ensure proper ISO format
        start_time, end_time = self._ensure_iso_format(start_time, end_time)
        
        # Execute in a thread pool to avoid blocking
        return await asyncio.to_thread(
            self._create_event_sync, 
            summary, start_time, end_time, description, location, calendar_id
        )
    
    def _create_event_sync(self, summary, start_time, end_time, description, location, calendar_id):
        """Synchronous implementation of create_event"""
        try:
            # Determine if the time format includes a time component or just a date
            time_format = 'dateTime' if 'T' in start_time else 'date'
            
            event_body = {
                'summary': summary,
                'location': location,
                'description': description,
                'start': {
                    time_format: start_time,
                    'timeZone': 'Africa/Casablanca',
                },
                'end': {
                    time_format: end_time,
                    'timeZone': 'Africa/Casablanca',
                }
            }
            
            event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()
            
            # Format the response
            return {
                "status": "success",
                "message": "Event created successfully",
                "event": {
                    "id": event['id'],
                    "summary": event.get('summary', 'No title'),
                    "start": event['start'].get('dateTime', event['start'].get('date')),
                    "end": event['end'].get('dateTime', event['end'].get('date')),
                    "location": event.get('location', ''),
                    "description": event.get('description', ''),
                    "html_link": event.get('htmlLink', '')
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create event: {str(e)}"
            }

    async def update_event(self,
                          event_id: str,
                          summary: Optional[str] = None,
                          start_time: Optional[str] = None,
                          end_time: Optional[str] = None,
                          description: Optional[str] = None,
                          location: Optional[str] = None,
                          calendar_id: str = None) -> Dict[str, Any]:
        """
        Update an existing calendar event
        
        Args:
            event_id: ID of the event to update
            summary: New event title (optional)
            start_time: New start time (optional)
            end_time: New end time (optional)
            description: New description (optional)
            location: New location (optional)
            calendar_id: Calendar ID (uses default if None)
            
        Returns:
            Details of the updated event
        """
        # Use the provided calendar_id or fall back to the default
        calendar_id = calendar_id or self.default_calendar_id
        
        # Execute in a thread pool to avoid blocking
        return await asyncio.to_thread(
            self._update_event_sync, 
            event_id, summary, start_time, end_time, description, location, calendar_id
        )
    
    def _update_event_sync(self, event_id, summary, start_time, end_time, description, location, calendar_id):
        """Synchronous implementation of update_event"""
        try:
            # First get the existing event
            event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            
            # Update fields if provided
            if summary is not None:
                event['summary'] = summary
                
            if description is not None:
                event['description'] = description
                
            if location is not None:
                event['location'] = location
                
            if start_time is not None:
                # Format the time if needed
                if 'T' in start_time:
                    start_time, _ = self._ensure_iso_format(start_time, start_time)
                
                time_format = 'dateTime' if 'T' in start_time else 'date'
                event['start'] = {
                    time_format: start_time,
                    'timeZone': 'Africa/Casablanca'
                }
                
            if end_time is not None:
                # Format the time if needed
                if 'T' in end_time:
                    _, end_time = self._ensure_iso_format(end_time, end_time)
                
                time_format = 'dateTime' if 'T' in end_time else 'date'
                event['end'] = {
                    time_format: end_time,
                    'timeZone': 'Africa/Casablanca'
                }
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            # Format the response
            return {
                "status": "success",
                "message": "Event updated successfully",
                "event": {
                    "id": updated_event['id'],
                    "summary": updated_event.get('summary', 'No title'),
                    "start": updated_event['start'].get('dateTime', updated_event['start'].get('date')),
                    "end": updated_event['end'].get('dateTime', updated_event['end'].get('date')),
                    "location": updated_event.get('location', ''),
                    "description": updated_event.get('description', ''),
                    "html_link": updated_event.get('htmlLink', '')
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to update event: {str(e)}"
            }
    
    async def delete_event(self, 
                          event_id: str, 
                          calendar_id: str = None) -> Dict[str, Any]:
        """
        Delete a calendar event
        
        Args:
            event_id: ID of the event to delete
            calendar_id: Calendar ID (uses default if None)
            
        Returns:
            Status of the operation
        """
        # Use the provided calendar_id or fall back to the default
        calendar_id = calendar_id or self.default_calendar_id
        
        # Execute in a thread pool to avoid blocking
        return await asyncio.to_thread(self._delete_event_sync, event_id, calendar_id)
    
    def _delete_event_sync(self, event_id, calendar_id):
        """Synchronous implementation of delete_event"""
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            return {
                "status": "success",
                "message": "Event deleted successfully",
                "event_id": event_id
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to delete event: {str(e)}"
            }
            
    async def check_conflicts(self, start_time: str, end_time: str, calendar_id: str = None) -> Dict[str, Any]:
        """
        Check for conflicting events in the specified time range
        
        Args:
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            calendar_id: Calendar ID to query (uses default if None)
            
        Returns:
            Dict with conflict information
        """
        # Use the provided calendar_id or fall back to the default
        calendar_id = calendar_id or self.default_calendar_id
        
        # Ensure times are in ISO format
        start_time, end_time = self._ensure_iso_format(start_time, end_time)
        
        # Debug info
        print(f"Checking conflicts for time range: {start_time} to {end_time}")
        
        # Execute in a thread pool to avoid blocking
        return await asyncio.to_thread(
            self._check_conflicts_sync, 
            start_time, end_time, calendar_id
        )
    
    def _check_conflicts_sync(self, start_time, end_time, calendar_id):
        """
        Synchronous implementation of check_conflicts with enhanced debugging
        """
        try:
            # Query events that overlap with the specified time range
            print(f"Executing calendar API query for conflicts with parameters:")
            print(f"  calendarId: {calendar_id}")
            print(f"  timeMin: {start_time}")
            print(f"  timeMax: {end_time}")
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            conflicts = []
            
            # Debug the API response
            print(f"Calendar API returned {len(events)} potential conflicts")
            
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                print(f"Found potential conflict: {event.get('summary', 'No title')} - {start} to {end}")
                
                conflicts.append({
                    'id': event['id'],
                    'summary': event.get('summary', 'No title'),
                    'start': start,
                    'end': end
                })
            
            return {
                "status": "success",
                "has_conflicts": len(conflicts) > 0,
                "conflicts": conflicts,
                "count": len(conflicts)
            }
        
        except Exception as e:
            print(f"Error checking conflicts: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to check conflicts: {str(e)}"
            }