#!/usr/bin/env python3
"""
Calendar Event Detector and Creator
Automatically detects meeting/event invitations and creates Google Calendar events
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from auth import GoogleAuth
import json

class CalendarDetector:
    def __init__(self):
        self.meeting_patterns = [
            r'meeting\s+(on|at|for)\s+([^.!?]+)',
            r'call\s+(on|at|for)\s+([^.!?]+)',
            r'conference\s+(on|at|for)\s+([^.!?]+)',
            r'appointment\s+(on|at|for)\s+([^.!?]+)',
            r'interview\s+(on|at|for)\s+([^.!?]+)',
            r'session\s+(on|at|for)\s+([^.!?]+)',
            r'demo\s+(on|at|for)\s+([^.!?]+)',
            r'presentation\s+(on|at|for)\s+([^.!?]+)',
            r'sync\s+(on|at|for)\s+([^.!?]+)',
            r'standup\s+(on|at|for)\s+([^.!?]+)',
            r'retrospective\s+(on|at|for)\s+([^.!?]+)',
            r'review\s+(on|at|for)\s+([^.!?]+)',
        ]

        # Date patterns
        self.date_patterns = [
            r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)[\s,]*(\d{1,2})(st|nd|rd|th)?',
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',
            r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})',
            r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[\s.]+(\d{1,2})',
            r'(\d{1,2})(st|nd|rd|th)\s+(of\s+)?(january|february|march|april|may|june|july|august|september|october|november|december)',
            r'tomorrow\s+at\s+(\d{1,2}:\d{2})',
            r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'this\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
        ]

        # Time patterns
        self.time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)',
            r'(\d{1,2})\s*(am|pm|AM|PM)',
            r'at\s+(\d{1,2}):(\d{2})',
            r'at\s+(\d{1,2})\s*(am|pm|AM|PM)',
        ]

        # Duration patterns
        self.duration_patterns = [
            r'(\d+)\s*hour[s]?',
            r'(\d+)\s*min[utes]*',
            r'(\d+)h\s*(\d+)m',
            r'for\s+(\d+)\s*(hour[s]?|min[utes]*)',
        ]

        self.auth = GoogleAuth()

    def is_meeting_invitation(self, subject: str, body: str) -> bool:
        """Detect if email is a meeting/event invitation"""
        content = f"{subject} {body}".lower()

        # Check for meeting keywords
        meeting_keywords = [
            'meeting', 'call', 'conference', 'appointment', 'interview',
            'session', 'demo', 'presentation', 'sync', 'standup',
            'retrospective', 'review', 'catch up', 'check in'
        ]

        # Check for calendar-related keywords
        calendar_keywords = [
            'calendar', 'invite', 'invitation', 'schedule', 'scheduled',
            'book', 'booking', 'reserve', 'reservation', 'confirm',
            'reschedule', 'postpone', 'move', 'change time'
        ]

        # Check for time indicators
        time_indicators = [
            'tomorrow', 'today', 'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday', 'next week', 'this week',
            'am', 'pm', ':', 'o\'clock', 'time', 'when'
        ]

        has_meeting = any(keyword in content for keyword in meeting_keywords)
        has_calendar = any(keyword in content for keyword in calendar_keywords)
        has_time = any(indicator in content for indicator in time_indicators)

        return (has_meeting and has_time) or (has_calendar and has_time)

    def extract_meeting_details(self, subject: str, body: str) -> Dict:
        """Extract meeting details from email content"""
        content = f"{subject} {body}"

        details = {
            'title': self.extract_title(subject, body),
            'date': self.extract_date(content),
            'time': self.extract_time(content),
            'duration': self.extract_duration(content),
            'location': self.extract_location(content),
            'attendees': self.extract_attendees(content),
            'description': self.extract_description(subject, body)
        }

        return details

    def extract_title(self, subject: str, body: str) -> str:
        """Extract meeting title"""
        # Use subject as default title
        title = subject.strip()

        # Remove common email prefixes
        prefixes = ['re:', 'fwd:', 'fw:', 'meeting:', 'call:', 'invite:']
        for prefix in prefixes:
            if title.lower().startswith(prefix):
                title = title[len(prefix):].strip()

        # If subject is generic, extract from body
        generic_subjects = ['meeting', 'call', 'conference', 'appointment', 'invite']
        if any(title.lower().startswith(generic) for generic in generic_subjects):
            # Try to find more specific title in body
            body_lines = body.split('\n')[:5]  # Check first 5 lines
            for line in body_lines:
                if 'subject:' in line.lower() or 'title:' in line.lower():
                    extracted = line.split(':', 1)[1].strip()
                    if len(extracted) > 5:
                        title = extracted
                        break

        return title[:100]  # Limit length

    def extract_date(self, content: str) -> Optional[str]:
        """Extract date from content"""
        content_lower = content.lower()

        # Check for relative dates
        if 'tomorrow' in content_lower:
            return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'today' in content_lower:
            return datetime.now().strftime('%Y-%m-%d')

        # Check for day names
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day in enumerate(days):
            if f'next {day}' in content_lower:
                days_ahead = (i - datetime.now().weekday() + 7) % 7
                if days_ahead == 0:
                    days_ahead = 7
                target_date = datetime.now() + timedelta(days=days_ahead)
                return target_date.strftime('%Y-%m-%d')
            elif f'this {day}' in content_lower:
                days_ahead = (i - datetime.now().weekday()) % 7
                target_date = datetime.now() + timedelta(days=days_ahead)
                return target_date.strftime('%Y-%m-%d')

        # Check for specific date patterns
        for pattern in self.date_patterns:
            match = re.search(pattern, content_lower)
            if match:
                try:
                    # Parse based on pattern type
                    if '/' in match.group() or '-' in match.group():
                        # Format: MM/DD/YYYY or DD/MM/YYYY
                        parts = re.split('[/-]', match.group())
                        if len(parts) == 3:
                            month, day, year = parts
                            if len(year) == 2:
                                year = '20' + year
                            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                except:
                    continue

        return None

    def extract_time(self, content: str) -> Optional[str]:
        """Extract time from content"""
        for pattern in self.time_patterns:
            match = re.search(pattern, content.lower())
            if match:
                try:
                    if len(match.groups()) >= 2:
                        hour = int(match.group(1))
                        minute = int(match.group(2)) if match.group(2) else 0

                        # Handle AM/PM
                        if len(match.groups()) >= 3 and match.group(3):
                            if match.group(3).lower() == 'pm' and hour != 12:
                                hour += 12
                            elif match.group(3).lower() == 'am' and hour == 12:
                                hour = 0

                        return f"{hour:02d}:{minute:02d}"
                except:
                    continue

        return None

    def extract_duration(self, content: str) -> int:
        """Extract duration in minutes"""
        for pattern in self.duration_patterns:
            match = re.search(pattern, content.lower())
            if match:
                try:
                    if 'hour' in match.group():
                        return int(match.group(1)) * 60
                    elif 'min' in match.group():
                        return int(match.group(1))
                    elif 'h' in match.group() and 'm' in match.group():
                        hours = int(match.group(1))
                        minutes = int(match.group(2))
                        return hours * 60 + minutes
                except:
                    continue

        return 30  # Default 30 minutes

    def extract_location(self, content: str) -> Optional[str]:
        """Extract location from content"""
        location_patterns = [
            r'location:\s*([^\n]+)',
            r'where:\s*([^\n]+)',
            r'room:\s*([^\n]+)',
            r'address:\s*([^\n]+)',
            r'at\s+([^,\n]+(?:building|room|office|street|avenue|road|way))',
            r'https?://[^\s]+zoom[^\s]*',
            r'https?://[^\s]+teams[^\s]*',
            r'https?://[^\s]+meet[^\s]*',
        ]

        for pattern in location_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if len(location) > 5:
                    return location[:200]  # Limit length

        return None

    def extract_attendees(self, content: str) -> List[str]:
        """Extract attendee emails from content"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        return list(set(emails))  # Remove duplicates

    def extract_description(self, subject: str, body: str) -> str:
        """Extract description from email"""
        # Use first few lines of body as description
        lines = body.split('\n')
        description_lines = []

        for line in lines[:10]:  # Max 10 lines
            line = line.strip()
            if line and not line.startswith('>') and not line.startswith('--'):
                description_lines.append(line)
                if len(' '.join(description_lines)) > 500:
                    break

        description = ' '.join(description_lines)
        return description[:500] if description else subject

    def create_calendar_event(self, meeting_details: Dict, sender_email: str) -> Optional[str]:
        """Create Google Calendar event"""
        try:
            # Get credentials
            creds = self.auth.get_credentials()
            if not creds:
                return None

            service = build('calendar', 'v3', credentials=creds)

            # Prepare event data
            event_data = {
                'summary': meeting_details['title'],
                'description': f"Auto-created from email\n\n{meeting_details['description']}",
            }

            # Add date/time
            if meeting_details['date'] and meeting_details['time']:
                start_datetime = f"{meeting_details['date']}T{meeting_details['time']}:00"

                # Calculate end time
                duration_minutes = meeting_details['duration']
                start_dt = datetime.fromisoformat(start_datetime)
                end_dt = start_dt + timedelta(minutes=duration_minutes)

                event_data['start'] = {
                    'dateTime': start_datetime,
                    'timeZone': 'America/New_York',  # TODO: Auto-detect timezone
                }
                event_data['end'] = {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'America/New_York',
                }
            else:
                # All-day event if no time specified
                event_data['start'] = {'date': meeting_details['date'] or datetime.now().strftime('%Y-%m-%d')}
                event_data['end'] = {'date': meeting_details['date'] or datetime.now().strftime('%Y-%m-%d')}

            # Add location
            if meeting_details['location']:
                event_data['location'] = meeting_details['location']

            # Add attendees
            attendees = []
            if sender_email:
                attendees.append({'email': sender_email})
            for email in meeting_details['attendees']:
                if email != sender_email:  # Don't duplicate sender
                    attendees.append({'email': email})

            if attendees:
                event_data['attendees'] = attendees

            # Create event
            event = service.events().insert(calendarId='primary', body=event_data).execute()

            return event.get('htmlLink')

        except Exception as e:
            print(f"Error creating calendar event: {e}")
            return None

    def process_email(self, email_data: Dict) -> Optional[Dict]:
        """Process email and create calendar event if it's a meeting invitation"""
        subject = email_data.get('subject', '')
        body = email_data.get('body_text', '')
        sender = email_data.get('sender', '')

        if self.is_meeting_invitation(subject, body):
            meeting_details = self.extract_meeting_details(subject, body)

            # Create calendar event
            event_link = self.create_calendar_event(meeting_details, sender)

            if event_link:
                return {
                    'created': True,
                    'event_link': event_link,
                    'meeting_details': meeting_details,
                    'message': f"✅ Calendar event created: {meeting_details['title']}"
                }
            else:
                return {
                    'created': False,
                    'meeting_details': meeting_details,
                    'message': f"❌ Failed to create calendar event for: {meeting_details['title']}"
                }

        return None

# Test the calendar detector
if __name__ == "__main__":
    detector = CalendarDetector()

    # Test with sample meeting invitation
    test_email = {
        'subject': 'Team Meeting Tomorrow',
        'body_text': '''Hi team,

Let's have our weekly sync meeting tomorrow at 2:00 PM in the conference room.

We'll discuss the project updates and plan for next week.

Thanks,
John''',
        'sender': 'john@company.com'
    }

    result = detector.process_email(test_email)
    if result:
        print(f"Meeting detected: {result['message']}")
        print(f"Details: {result['meeting_details']}")
    else:
        print("No meeting detected in this email")