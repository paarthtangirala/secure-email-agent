import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import dateutil.parser
from googleapiclient.errors import HttpError
from config import config
from auth import GoogleAuth

class CalendarManager:
    def __init__(self, auth_manager: GoogleAuth):
        self.auth = auth_manager
        self.service = None

        # Patterns for extracting calendar events from emails
        self.datetime_patterns = [
            r'(\w+day),?\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})?\s+at\s+(\d{1,2}):(\d{2})\s*(am|pm)',
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})?\s+at\s+(\d{1,2}):(\d{2})\s*(am|pm)',
            r'(\d{1,2})/(\d{1,2})/(\d{2,4})\s+at\s+(\d{1,2}):(\d{2})\s*(am|pm)',
            r'tomorrow\s+at\s+(\d{1,2}):(\d{2})\s*(am|pm)',
            r'next\s+(\w+day)\s+at\s+(\d{1,2}):(\d{2})\s*(am|pm)',
        ]

        self.meeting_keywords = [
            'meeting', 'interview', 'appointment', 'call', 'conference',
            'discussion', 'session', 'briefing', 'presentation', 'demo'
        ]

        self.location_patterns = [
            r'at\s+([A-Za-z0-9\s,.-]+(?:room|building|floor|office|center|hall))',
            r'location:?\s*([A-Za-z0-9\s,.-]+)',
            r'venue:?\s*([A-Za-z0-9\s,.-]+)',
            r'zoom\s+link:?\s*(https?://[^\s]+)',
            r'teams\s+link:?\s*(https?://[^\s]+)',
            r'google\s+meet:?\s*(https?://[^\s]+)'
        ]

    def get_service(self):
        """Get Google Calendar service"""
        if not self.service:
            self.service = self.auth.get_calendar_service()
        return self.service

    def extract_calendar_events(self, email_data: Dict) -> List[Dict]:
        """Extract potential calendar events from email content"""
        events = []

        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        sender = email_data.get('sender', '')

        combined_text = f"{subject} {body}"

        # Check if this email likely contains meeting/event information
        if not self._contains_meeting_info(combined_text):
            return events

        # Extract datetime information
        datetime_info = self._extract_datetime(combined_text)

        # Extract location information
        location = self._extract_location(combined_text)

        # Extract event title
        title = self._extract_event_title(subject, body)

        # Extract attendees
        attendees = self._extract_attendees(body, sender)

        if datetime_info:
            event = {
                'summary': title,
                'start': datetime_info['start'],
                'end': datetime_info['end'],
                'location': location,
                'description': self._create_description(email_data),
                'attendees': attendees,
                'source_email_id': email_data.get('id'),
                'confidence': self._calculate_confidence(combined_text),
                'needs_confirmation': True
            }
            events.append(event)

        return events

    def _contains_meeting_info(self, text: str) -> bool:
        """Check if text contains meeting-related keywords"""
        text_lower = text.lower()

        # Check for meeting keywords
        for keyword in self.meeting_keywords:
            if keyword in text_lower:
                return True

        # Check for time patterns
        time_patterns = [
            r'\d{1,2}:\d{2}\s*(am|pm)',
            r'\d{1,2}(am|pm)',
            r'at\s+\d',
            r'tomorrow',
            r'next\s+\w+day'
        ]

        for pattern in time_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def _extract_datetime(self, text: str) -> Optional[Dict]:
        """Extract start and end datetime from text"""
        try:
            # Try to find explicit datetime patterns
            for pattern in self.datetime_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    match = matches[0]
                    start_time = self._parse_datetime_match(match)
                    if start_time:
                        # Default to 1-hour duration if no end time specified
                        end_time = start_time + timedelta(hours=1)

                        return {
                            'start': {
                                'dateTime': start_time.isoformat(),
                                'timeZone': 'America/New_York'  # You may want to detect this
                            },
                            'end': {
                                'dateTime': end_time.isoformat(),
                                'timeZone': 'America/New_York'
                            }
                        }

            # Try using dateutil for more flexible parsing
            time_candidates = re.findall(
                r'(?:on|at|from)?\s*(\w+day,?\s+\w+\s+\d{1,2},?\s+\d{4}\s+at\s+\d{1,2}:\d{2}\s*(?:am|pm))',
                text, re.IGNORECASE
            )

            for candidate in time_candidates:
                try:
                    start_time = dateutil.parser.parse(candidate, fuzzy=True)
                    end_time = start_time + timedelta(hours=1)

                    return {
                        'start': {
                            'dateTime': start_time.isoformat(),
                            'timeZone': 'America/New_York'
                        },
                        'end': {
                            'dateTime': end_time.isoformat(),
                            'timeZone': 'America/New_York'
                        }
                    }
                except:
                    continue

        except Exception as e:
            print(f"Error extracting datetime: {e}")

        return None

    def _parse_datetime_match(self, match: tuple) -> Optional[datetime]:
        """Parse a datetime match tuple into datetime object"""
        try:
            # This is a simplified parser - you'd want to handle all pattern variations
            if len(match) >= 3:
                # Handle different match formats based on the pattern
                # This is a basic implementation
                date_str = ' '.join(str(x) for x in match if x)
                return dateutil.parser.parse(date_str, fuzzy=True)
        except:
            pass
        return None

    def _extract_location(self, text: str) -> str:
        """Extract meeting location from text"""
        for pattern in self.location_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0].strip()

        # Look for common video call indicators
        if 'zoom' in text.lower():
            return 'Zoom Meeting'
        elif 'teams' in text.lower():
            return 'Microsoft Teams'
        elif 'google meet' in text.lower():
            return 'Google Meet'

        return ''

    def _extract_event_title(self, subject: str, body: str) -> str:
        """Extract or generate event title"""
        # First try to use subject if it looks like a meeting title
        subject_lower = subject.lower()

        meeting_indicators = ['meeting', 'interview', 'call', 'discussion', 'session']
        for indicator in meeting_indicators:
            if indicator in subject_lower:
                return subject

        # Look for meeting titles in the body
        title_patterns = [
            r'(?:meeting|interview|call)\s*:?\s*([^.\n]+)',
            r'subject\s*:?\s*([^.\n]+)',
            r'regarding\s*:?\s*([^.\n]+)'
        ]

        for pattern in title_patterns:
            matches = re.findall(pattern, body, re.IGNORECASE)
            if matches:
                return matches[0].strip()

        # Default to subject
        return subject

    def _extract_attendees(self, body: str, sender: str) -> List[Dict]:
        """Extract attendee information"""
        attendees = []

        # Add sender as attendee
        if sender:
            attendees.append({'email': sender})

        # Look for other email addresses in the body
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, body)

        for email in emails:
            if email != sender:
                attendees.append({'email': email})

        return attendees

    def _create_description(self, email_data: Dict) -> str:
        """Create event description from email data"""
        description = f"Event created from email: {email_data.get('subject', '')}\n\n"
        description += f"From: {email_data.get('sender', '')}\n"
        description += f"Original email body:\n{email_data.get('body', '')[:500]}"

        if len(email_data.get('body', '')) > 500:
            description += "...\n\n[Truncated]"

        return description

    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence score for event extraction"""
        confidence = 0.5
        text_lower = text.lower()

        # Boost confidence for explicit meeting keywords
        meeting_count = sum(1 for keyword in self.meeting_keywords if keyword in text_lower)
        confidence += meeting_count * 0.1

        # Boost for time indicators
        if re.search(r'\d{1,2}:\d{2}\s*(am|pm)', text_lower):
            confidence += 0.2

        # Boost for location indicators
        if any(re.search(pattern, text_lower) for pattern in self.location_patterns):
            confidence += 0.1

        # Boost for attendee information
        if re.search(r'@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text):
            confidence += 0.1

        return min(confidence, 1.0)

    def create_calendar_event(self, event_data: Dict) -> Optional[str]:
        """Create an event in Google Calendar"""
        try:
            service = self.get_service()

            # Prepare event for Google Calendar API
            event = {
                'summary': event_data['summary'],
                'start': event_data['start'],
                'end': event_data['end'],
                'description': event_data['description']
            }

            if event_data.get('location'):
                event['location'] = event_data['location']

            if event_data.get('attendees'):
                event['attendees'] = event_data['attendees']

            # Create the event
            created_event = service.events().insert(calendarId='primary', body=event).execute()

            # Save event creation record
            self._save_created_event_record(created_event, event_data)

            return created_event.get('id')

        except HttpError as error:
            print(f'An error occurred creating calendar event: {error}')
            return None

    def _save_created_event_record(self, created_event: Dict, original_data: Dict):
        """Save a record of created events for tracking"""
        records = config.load_encrypted_json("created_events")

        if 'events' not in records:
            records['events'] = []

        record = {
            'calendar_event_id': created_event.get('id'),
            'source_email_id': original_data.get('source_email_id'),
            'created_at': datetime.now().isoformat(),
            'summary': created_event.get('summary'),
            'confidence': original_data.get('confidence', 0.5)
        }

        records['events'].append(record)
        config.save_encrypted_json("created_events", records)

    def get_upcoming_events(self, days_ahead: int = 7) -> List[Dict]:
        """Get upcoming calendar events"""
        try:
            service = self.get_service()

            # Calculate time range
            now = datetime.utcnow().isoformat() + 'Z'
            time_max = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'

            events_result = service.events().list(
                calendarId='primary',
                timeMin=now,
                timeMax=time_max,
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            return events_result.get('items', [])

        except HttpError as error:
            print(f'An error occurred fetching calendar events: {error}')
            return []

    def check_conflicts(self, proposed_event: Dict) -> List[Dict]:
        """Check for calendar conflicts with a proposed event"""
        try:
            service = self.get_service()

            start_time = proposed_event['start']['dateTime']
            end_time = proposed_event['end']['dateTime']

            # Query for existing events in the time range
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            conflicts = []
            for event in events_result.get('items', []):
                if event.get('start') and event.get('end'):
                    conflicts.append({
                        'id': event['id'],
                        'summary': event.get('summary', 'No title'),
                        'start': event['start'],
                        'end': event['end']
                    })

            return conflicts

        except HttpError as error:
            print(f'An error occurred checking conflicts: {error}')
            return []