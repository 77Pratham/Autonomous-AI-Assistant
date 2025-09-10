import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)

@dataclass
class CalendarEvent:
    """Calendar event data structure"""
    title: str
    start_time: datetime
    end_time: datetime
    description: str = ""
    location: str = ""
    attendees: List[str] = None
    all_day: bool = False
    
    def __post_init__(self):
        if self.attendees is None:
            self.attendees = []

class CalendarIntegration:
    """
    Handles Google Calendar integration for scheduling and event management.
    Can be extended to work with other calendar services.
    """
    
    def __init__(self):
        """Initialize calendar integration"""
        self.service = None
        self.credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        self.mock_mode = True  # Set to False when real API is configured
        self.events_db = []  # Mock event storage
        
        if self.credentials_path and os.path.exists(self.credentials_path):
            try:
                self._setup_google_calendar()
                self.mock_mode = False
            except Exception as e:
                logger.warning(f"Failed to setup Google Calendar, using mock mode: {e}")
        else:
            logger.info("Google Calendar credentials not found, using mock mode")

    def _setup_google_calendar(self):
        """Setup Google Calendar API client"""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            
            SCOPES = ['https://www.googleapis.com/auth/calendar']
            
            creds = None
            token_path = 'data/token.json'
            
            # Load existing token
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            # Build the service
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("Google Calendar API setup successful")
            
        except ImportError:
            logger.error("Google API client libraries not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to setup Google Calendar API: {e}")
            raise

    def create_event(self, event: CalendarEvent, calendar_id: str = 'primary') -> Dict[str, Any]:
        """
        Create a calendar event.
        
        Args:
            event: CalendarEvent object with event details
            calendar_id: Calendar ID (default: 'primary')
            
        Returns:
            Dictionary with operation status and event details
        """
        try:
            if self.mock_mode:
                return self._create_event_mock(event)
            
            # Create event for Google Calendar API
            event_body = {
                'summary': event.title,
                'description': event.description,
                'location': event.location,
                'start': {
                    'dateTime': event.start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': event.end_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'attendees': [{'email': email} for email in event.attendees],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 10},       # 10 minutes before
                    ],
                },
            }
            
            # Handle all-day events
            if event.all_day:
                event_body['start'] = {'date': event.start_time.date().isoformat()}
                event_body['end'] = {'date': event.end_time.date().isoformat()}
            
            # Create the event
            created_event = self.service.events().insert(
                calendarId=calendar_id, 
                body=event_body
            ).execute()
            
            result = {
                'status': 'success',
                'message': f'Event "{event.title}" created successfully',
                'event_id': created_event.get('id'),
                'event_link': created_event.get('htmlLink'),
                'created_time': datetime.now().isoformat(),
                'event_details': {
                    'title': event.title,
                    'start_time': event.start_time.isoformat(),
                    'end_time': event.end_time.isoformat(),
                    'description': event.description,
                    'location': event.location,
                    'attendees': event.attendees
                }
            }
            
            logger.info(f"Created calendar event: {event.title}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to create calendar event: {e}"
            logger.error(error_msg)
            return {'status': 'error', 'message': str(e)}

    def _create_event_mock(self, event: CalendarEvent) -> Dict[str, Any]:
        """Mock implementation for creating events"""
        event_id = f"mock_event_{len(self.events_db) + 1}"
        
        mock_event = {
            'id': event_id,
            'title': event.title,
            'start_time': event.start_time.isoformat(),
            'end_time': event.end_time.isoformat(),
            'description': event.description,
            'location': event.location,
            'attendees': event.attendees,
            'all_day': event.all_day,
            'created_time': datetime.now().isoformat()
        }
        
        self.events_db.append(mock_event)
        
        return {
            'status': 'success',
            'message': f'Event "{event.title}" created successfully (mock mode)',
            'event_id': event_id,
            'event_link': f'https://calendar.google.com/mock/{event_id}',
            'created_time': datetime.now().isoformat(),
            'event_details': {
                'title': event.title,
                'start_time': event.start_time.isoformat(),
                'end_time': event.end_time.isoformat(),
                'description': event.description,
                'location': event.location,
                'attendees': event.attendees
            }
        }

    def get_upcoming_events(self, days_ahead: int = 7, max_results: int = 20) -> Dict[str, Any]:
        """
        Get upcoming events from calendar.
        
        Args:
            days_ahead: Number of days to look ahead
            max_results: Maximum number of events to return
            
        Returns:
            Dictionary with events list and metadata
        """
        try:
            if self.mock_mode:
                return self._get_upcoming_events_mock(days_ahead, max_results)
            
            # Calculate time range
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            # Call Google Calendar API
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Process events
            processed_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                processed_events.append({
                    'id': event.get('id'),
                    'title': event.get('summary', 'No Title'),
                    'start_time': start,
                    'end_time': end,
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'attendees': [attendee.get('email') for attendee in event.get('attendees', [])],
                    'creator': event.get('creator', {}).get('email', ''),
                    'event_link': event.get('htmlLink', '')
                })
            
            return {
                'status': 'success',
                'events': processed_events,
                'total_count': len(processed_events),
                'date_range': {
                    'from': time_min,
                    'to': time_max
                },
                'message': f'Found {len(processed_events)} upcoming events'
            }
            
        except Exception as e:
            error_msg = f"Failed to get upcoming events: {e}"
            logger.error(error_msg)
            return {'status': 'error', 'message': str(e)}

    def _get_upcoming_events_mock(self, days_ahead: int, max_results: int) -> Dict[str, Any]:
        """Mock implementation for getting upcoming events"""
        now = datetime.now()
        time_max = now + timedelta(days=days_ahead)
        
        # Filter mock events
        upcoming_events = []
        for event in self.events_db:
            event_start = datetime.fromisoformat(event['start_time'])
            if now <= event_start <= time_max:
                upcoming_events.append(event)
        
        # Sort by start time and limit results
        upcoming_events.sort(key=lambda x: x['start_time'])
        upcoming_events = upcoming_events[:max_results]
        
        return {
            'status': 'success',
            'events': upcoming_events,
            'total_count': len(upcoming_events),
            'date_range': {
                'from': now.isoformat(),
                'to': time_max.isoformat()
            },
            'message': f'Found {len(upcoming_events)} upcoming events (mock mode)'
        }

    def parse_natural_language_event(self, command: str) -> Optional[CalendarEvent]:
        """
        Parse natural language command to extract event details.
        
        Args:
            command: Natural language command (e.g., "Schedule meeting with John tomorrow at 3pm")
            
        Returns:
            CalendarEvent object if parsing successful, None otherwise
        """
        try:
            # Initialize event details
            title = "New Event"
            description = ""
            location = ""
            attendees = []
            start_time = None
            end_time = None
            all_day = False
            
            # Extract title/subject
            title_patterns = [
                r'(?:schedule|create|add|book)\s+(?:a\s+)?(.+?)(?:\s+(?:with|for|at|on|tomorrow|today|next week))',
                r'(?:meeting|appointment|event)\s+(.+?)(?:\s+(?:with|for|at|on|tomorrow|today))',
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    title = match.group(1).strip().title()
                    break
            
            # Extract attendees
            attendee_patterns = [
                r'with\s+([A-Za-z\s,]+?)(?:\s+(?:at|on|for|tomorrow|today|next))',
                r'(?:invite|include)\s+([A-Za-z\s,@.]+)',
            ]
            
            for pattern in attendee_patterns:
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    attendee_text = match.group(1)
                    # Split by commas and clean up
                    attendees = [name.strip() for name in attendee_text.split(',') if name.strip()]
                    break
            
            # Extract time information
            time_patterns = [
                r'at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)',
                r'(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))',
                r'(tomorrow|today|next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))',
            ]
            
            time_match = None
            day_match = None
            
            for pattern in time_patterns:
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    time_text = match.group(1)
                    if any(word in time_text.lower() for word in ['tomorrow', 'today', 'next']):
                        day_match = time_text
                    else:
                        time_match = time_text
                    break
            
            # Parse date
            base_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)  # Default 9 AM
            
            if day_match:
                if 'tomorrow' in day_match.lower():
                    base_date = base_date + timedelta(days=1)
                elif 'today' in day_match.lower():
                    base_date = base_date
                elif 'next' in day_match.lower():
                    # Simple next week logic
                    base_date = base_date + timedelta(days=7)
            
            # Parse time
            if time_match:
                time_clean = time_match.replace(' ', '').lower()
                
                # Extract hour and minute
                if ':' in time_clean:
                    time_parts = time_clean.split(':')
                    hour = int(time_parts[0])
                    minute = int(time_parts[1][:2])  # Take first 2 digits
                else:
                    hour = int(''.join(filter(str.isdigit, time_clean)))
                    minute = 0
                
                # Handle AM/PM
                if 'pm' in time_clean and hour != 12:
                    hour += 12
                elif 'am' in time_clean and hour == 12:
                    hour = 0
                
                base_date = base_date.replace(hour=hour, minute=minute)
            
            start_time = base_date
            
            # Default duration: 1 hour
            end_time = start_time + timedelta(hours=1)
            
            # Extract duration if specified
            duration_patterns = [
                r'for\s+(\d+)\s*(?:hours?|hrs?|h)',
                r'for\s+(\d+)\s*(?:minutes?|mins?|m)',
                r'(\d+)\s*(?:hours?|hrs?|h)\s*(?:long|duration)',
                r'(\d+)\s*(?:minutes?|mins?|m)\s*(?:long|duration)',
            ]
            
            for pattern in duration_patterns:
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    duration_value = int(match.group(1))
                    if 'hour' in pattern or 'hr' in pattern:
                        end_time = start_time + timedelta(hours=duration_value)
                    else:  # minutes
                        end_time = start_time + timedelta(minutes=duration_value)
                    break
            
            # Extract location
            location_patterns = [
                r'(?:at|in)\s+([A-Za-z0-9\s,.-]+?)(?:\s+(?:with|for|tomorrow|today|next|$))',
                r'location\s*[:=]\s*([A-Za-z0-9\s,.-]+)',
            ]
            
            for pattern in location_patterns:
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    location = match.group(1).strip()
                    break
            
            # Create and return event
            event = CalendarEvent(
                title=title,
                start_time=start_time,
                end_time=end_time,
                description=f"Event created from command: {command}",
                location=location,
                attendees=attendees,
                all_day=all_day
            )
            
            logger.info(f"Parsed event: {title} at {start_time}")
            return event
            
        except Exception as e:
            logger.error(f"Failed to parse natural language event: {e}")
            return None

    def schedule_meeting(self, title: str, attendees: List[str], 
                        start_time: datetime, duration_hours: float = 1.0,
                        location: str = "", description: str = "") -> Dict[str, Any]:
        """
        Convenience method to schedule a meeting.
        
        Args:
            title: Meeting title
            attendees: List of attendee emails
            start_time: Meeting start time
            duration_hours: Meeting duration in hours
            location: Meeting location
            description: Meeting description
            
        Returns:
            Dictionary with operation status
        """
        try:
            end_time = start_time + timedelta(hours=duration_hours)
            
            event = CalendarEvent(
                title=title,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location,
                attendees=attendees
            )
            
            return self.create_event(event)
            
        except Exception as e:
            error_msg = f"Failed to schedule meeting: {e}"
            logger.error(error_msg)
            return {'status': 'error', 'message': str(e)}

    def get_today_schedule(self) -> Dict[str, Any]:
        """Get today's schedule"""
        return self.get_upcoming_events(days_ahead=1)

    def get_week_schedule(self) -> Dict[str, Any]:
        """Get this week's schedule"""
        return self.get_upcoming_events(days_ahead=7)

    def find_free_time_slots(self, date: datetime, duration_hours: float = 1.0, 
                           working_hours: tuple = (9, 17)) -> Dict[str, Any]:
        """
        Find available time slots on a given date.
        
        Args:
            date: Date to check for free slots
            duration_hours: Required duration for the slot
            working_hours: Working hours range (start_hour, end_hour)
            
        Returns:
            Dictionary with available time slots
        """
        try:
            # Get events for the specific date
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            if self.mock_mode:
                # Mock implementation
                events = [e for e in self.events_db 
                         if start_of_day <= datetime.fromisoformat(e['start_time']) < end_of_day]
            else:
                # Real API implementation would go here
                events = []  # Placeholder
            
            # Create working hour slots
            start_hour, end_hour = working_hours
            work_start = start_of_day.replace(hour=start_hour)
            work_end = start_of_day.replace(hour=end_hour)
            
            # Generate potential slots
            free_slots = []
            current_time = work_start
            
            while current_time + timedelta(hours=duration_hours) <= work_end:
                # Check if this slot conflicts with any event
                slot_end = current_time + timedelta(hours=duration_hours)
                
                is_free = True
                for event in events:
                    event_start = datetime.fromisoformat(event['start_time'])
                    event_end = datetime.fromisoformat(event['end_time'])
                    
                    # Check for overlap
                    if (current_time < event_end and slot_end > event_start):
                        is_free = False
                        break
                
                if is_free:
                    free_slots.append({
                        'start_time': current_time.isoformat(),
                        'end_time': slot_end.isoformat(),
                        'duration_hours': duration_hours
                    })
                
                # Move to next 30-minute slot
                current_time += timedelta(minutes=30)
            
            return {
                'status': 'success',
                'date': date.date().isoformat(),
                'free_slots': free_slots,
                'total_slots': len(free_slots),
                'working_hours': working_hours,
                'requested_duration': duration_hours
            }
            
        except Exception as e:
            error_msg = f"Failed to find free time slots: {e}"
            logger.error(error_msg)
            return {'status': 'error', 'message': str(e)}


# Convenience functions
def create_meeting_from_command(command: str) -> Dict[str, Any]:
    """
    Create a meeting from natural language command.
    
    Args:
        command: Natural language command
        
    Returns:
        Dictionary with operation result
    """
    calendar = CalendarIntegration()
    
    try:
        # Parse the command
        event = calendar.parse_natural_language_event(command)
        
        if not event:
            return {
                'status': 'error',
                'message': 'Could not parse the meeting details from the command'
            }
        
        # Create the event
        result = calendar.create_event(event)
        
        # Add parsing details to result
        result['parsed_details'] = {
            'original_command': command,
            'extracted_title': event.title,
            'extracted_time': event.start_time.isoformat(),
            'extracted_attendees': event.attendees,
            'extracted_location': event.location
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating meeting from command: {e}")
        return {'status': 'error', 'message': str(e)}


def get_daily_schedule() -> Dict[str, Any]:
    """Get today's schedule"""
    calendar = CalendarIntegration()
    return calendar.get_today_schedule()


def schedule_quick_meeting(title: str, attendee_emails: List[str], 
                         hours_from_now: int = 1) -> Dict[str, Any]:
    """
    Schedule a quick meeting starting in specified hours.
    
    Args:
        title: Meeting title
        attendee_emails: List of attendee email addresses
        hours_from_now: Hours from now to start the meeting
        
    Returns:
        Dictionary with operation result
    """
    calendar = CalendarIntegration()
    start_time = datetime.now() + timedelta(hours=hours_from_now)
    
    return calendar.schedule_meeting(
        title=title,
        attendees=attendee_emails,
        start_time=start_time,
        duration_hours=1.0
    )