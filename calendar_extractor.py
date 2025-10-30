#!/usr/bin/env python3
"""
Calendar Extractor - Extract meeting information and auto-propose responses
Part of MailMaestro-level intelligence layer
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from config import config

class CalendarExtractor:
    """Extract meeting details and propose calendar responses"""
    
    def __init__(self, model_router=None):
        self.client = OpenAI()
        self.model_router = model_router
        
        # Meeting indicators
        self.meeting_keywords = [
            "meeting", "call", "zoom", "teams", "meet", "conference",
            "appointment", "interview", "demo", "presentation",
            "sync", "standup", "review", "discussion"
        ]
        
        # Time patterns
        self.time_patterns = [
            r"(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)",
            r"(\d{1,2})\s*(am|pm|AM|PM)",
            r"(\d{1,2}):(\d{2})",
            r"(\d{1,2})\s*(?:o'clock|oclock)"
        ]
        
        # Date patterns
        self.date_patterns = [
            r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
            r"(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}",
            r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}",
            r"\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?",
            r"(?:today|tomorrow|next\s+\w+day)"
        ]
        
        # Platform patterns
        self.platform_patterns = {
            "zoom": r"zoom\.us/[j/]+(\d+)",
            "teams": r"teams\.microsoft\.com",
            "meet": r"meet\.google\.com/[a-z-]+",
            "webex": r"webex\.com",
            "gotomeeting": r"gotomeeting\.com"
        }
    
    def extract_meeting_info(self, email_text: str, email_metadata: Dict = None) -> Optional[Dict]:
        """
        Extract meeting information from email content
        
        Args:
            email_text: Email body text
            email_metadata: Subject, sender, etc.
            
        Returns:
            Meeting dict with title, start, end, location, attendees, confidence
            None if no meeting detected
        """
        try:
            # Quick check for meeting indicators
            if not self._has_meeting_indicators(email_text):
                return None
            
            # Extract components
            meeting_info = {
                "title": self._extract_title(email_text, email_metadata),
                "start_time": self._extract_start_time(email_text),
                "end_time": self._extract_end_time(email_text),
                "location": self._extract_location(email_text),
                "platform": self._extract_platform(email_text),
                "attendees": self._extract_attendees(email_text, email_metadata),
                "description": self._extract_description(email_text),
                "confidence": 0.0
            }
            
            # Calculate confidence score
            meeting_info["confidence"] = self._calculate_confidence(meeting_info, email_text)
            
            # Only return if confidence >= 0.7
            if meeting_info["confidence"] >= 0.7:
                return meeting_info
            
            return None
            
        except Exception as e:
            print(f"Error extracting meeting info: {e}")
            return None
    
    def propose_calendar_response(self, meeting_info: Dict, user_context: Dict = None) -> Dict:
        """
        Propose automatic response for meeting invitation
        
        Args:
            meeting_info: Extracted meeting details
            user_context: User preferences, calendar availability
            
        Returns:
            Response proposal with action and message
        """
        try:
            confidence = meeting_info.get("confidence", 0.0)
            
            # High confidence meeting with clear details
            if confidence >= 0.9 and meeting_info.get("start_time"):
                action = "accept_and_add"
                message = f"Confirmed — I'll add '{meeting_info['title']}' to my calendar."
                
            # Medium confidence meeting
            elif confidence >= 0.7:
                action = "tentative_add"
                message = f"I see a meeting invitation. Should I add '{meeting_info['title']}' to your calendar?"
                
            # Low confidence or missing details
            else:
                action = "request_clarification"
                message = "I noticed this might be a meeting invitation, but need more details about the time."
            
            return {
                "action": action,
                "message": message,
                "confidence": confidence,
                "auto_reply": confidence >= 0.9,
                "calendar_event": meeting_info
            }
            
        except Exception as e:
            print(f"Error proposing response: {e}")
            return {"action": "none", "message": "", "confidence": 0.0}
    
    def _has_meeting_indicators(self, email_text: str) -> bool:
        """Quick check for meeting-related content"""
        text_lower = email_text.lower()
        
        # Check for meeting keywords
        keyword_count = sum(1 for keyword in self.meeting_keywords if keyword in text_lower)
        
        # Check for time/date patterns
        has_time = any(re.search(pattern, email_text, re.IGNORECASE) for pattern in self.time_patterns)
        has_date = any(re.search(pattern, email_text, re.IGNORECASE) for pattern in self.date_patterns)
        
        return keyword_count >= 1 and (has_time or has_date)
    
    def _extract_title(self, email_text: str, email_metadata: Dict = None) -> str:
        """Extract meeting title"""
        if email_metadata and email_metadata.get("subject"):
            subject = email_metadata["subject"]
            # Clean common meeting prefixes
            title = re.sub(r"^(re:|fwd:|meeting:?|call:?|zoom:?)\s*", "", subject, flags=re.IGNORECASE)
            return title.strip()
        
        # Try to extract from first line
        lines = email_text.split('\n')
        for line in lines[:3]:
            if any(keyword in line.lower() for keyword in self.meeting_keywords):
                return line.strip()[:100]
        
        return "Meeting"
    
    def _extract_start_time(self, email_text: str) -> Optional[str]:
        """Extract meeting start time"""
        text_lines = email_text.split('\n')
        
        for line in text_lines:
            # Look for time patterns
            for pattern in self.time_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    # Try to find associated date
                    date_str = self._find_date_near_time(line, email_text)
                    time_str = match.group(0)
                    
                    # Parse and format
                    try:
                        parsed_time = self._parse_datetime(date_str, time_str)
                        return parsed_time.isoformat() if parsed_time else None
                    except:
                        continue
        
        return None
    
    def _extract_end_time(self, email_text: str) -> Optional[str]:
        """Extract meeting end time"""
        # Look for duration or end time
        duration_patterns = [
            r"(\d+)\s*(?:hour|hr|h)",
            r"(\d+)\s*(?:minute|min|m)",
            r"(\d+):(\d+)\s*(?:to|until|-)\s*(\d+):(\d+)"
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, email_text, re.IGNORECASE)
            if match:
                # For now, assume 1 hour if not specified
                start_time = self._extract_start_time(email_text)
                if start_time:
                    try:
                        start_dt = datetime.fromisoformat(start_time)
                        end_dt = start_dt + timedelta(hours=1)
                        return end_dt.isoformat()
                    except:
                        pass
        
        return None
    
    def _extract_location(self, email_text: str) -> str:
        """Extract meeting location"""
        # Check for platform links first
        platform = self._extract_platform(email_text)
        if platform != "in-person":
            return platform
        
        # Look for location patterns
        location_patterns = [
            r"(?:location|where|room|address):\s*(.{5,50})",
            r"(?:at|in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:room|building|office)",
            r"room\s+(\w+)",
            r"(\d+\s+[A-Za-z\s]+(?:street|st|avenue|ave|road|rd))"
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, email_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "TBD"
    
    def _extract_platform(self, email_text: str) -> str:
        """Extract meeting platform"""
        for platform, pattern in self.platform_patterns.items():
            if re.search(pattern, email_text, re.IGNORECASE):
                return platform.title()
        
        # Check for generic virtual meeting indicators
        virtual_indicators = ["virtual", "online", "remote", "video call", "phone call"]
        for indicator in virtual_indicators:
            if indicator in email_text.lower():
                return "Virtual"
        
        return "In-person"
    
    def _extract_attendees(self, email_text: str, email_metadata: Dict = None) -> List[str]:
        """Extract meeting attendees"""
        attendees = []
        
        if email_metadata:
            sender = email_metadata.get("sender", "")
            if sender:
                attendees.append(sender)
        
        # Look for email addresses in text
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        emails = re.findall(email_pattern, email_text)
        attendees.extend(emails)
        
        return list(set(attendees))  # Remove duplicates
    
    def _extract_description(self, email_text: str) -> str:
        """Extract meeting description/agenda"""
        lines = email_text.split('\n')
        
        # Look for agenda or description sections
        description_lines = []
        in_agenda = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            if any(keyword in line_lower for keyword in ["agenda", "topics", "discussion", "purpose"]):
                in_agenda = True
                continue
            
            if in_agenda and line.strip():
                description_lines.append(line.strip())
            
            if len(description_lines) >= 5:  # Limit description length
                break
        
        return '\n'.join(description_lines) if description_lines else email_text[:200]
    
    def _find_date_near_time(self, time_line: str, full_text: str) -> str:
        """Find date associated with time mention"""
        # First check the same line
        for pattern in self.date_patterns:
            match = re.search(pattern, time_line, re.IGNORECASE)
            if match:
                return match.group(0)
        
        # Check nearby lines in full text
        lines = full_text.split('\n')
        for i, line in enumerate(lines):
            if time_line.strip() in line:
                # Check previous and next lines
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    for pattern in self.date_patterns:
                        match = re.search(pattern, lines[j], re.IGNORECASE)
                        if match:
                            return match.group(0)
        
        return "today"  # Default assumption
    
    def _parse_datetime(self, date_str: str, time_str: str) -> Optional[datetime]:
        """Parse date and time strings into datetime object"""
        try:
            today = datetime.now()
            
            # Parse date
            date_str = date_str.lower().strip()
            if "today" in date_str:
                target_date = today.date()
            elif "tomorrow" in date_str:
                target_date = (today + timedelta(days=1)).date()
            elif "monday" in date_str:
                days_ahead = 0 - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                target_date = (today + timedelta(days=days_ahead)).date()
            # Add more date parsing logic here
            else:
                target_date = today.date()  # Default to today
            
            # Parse time
            time_match = re.search(r"(\d{1,2}):?(\d{0,2})\s*(am|pm|AM|PM)?", time_str)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                ampm = time_match.group(3)
                
                if ampm and ampm.lower() == "pm" and hour != 12:
                    hour += 12
                elif ampm and ampm.lower() == "am" and hour == 12:
                    hour = 0
                
                return datetime.combine(target_date, datetime.min.time().replace(hour=hour, minute=minute))
            
            return None
            
        except Exception:
            return None
    
    def _calculate_confidence(self, meeting_info: Dict, email_text: str) -> float:
        """Calculate confidence score for meeting extraction"""
        score = 0.0
        
        # Has time information
        if meeting_info.get("start_time"):
            score += 0.4
        
        # Has location/platform
        if meeting_info.get("location") and meeting_info["location"] != "TBD":
            score += 0.2
        
        # Has clear title
        if meeting_info.get("title") and len(meeting_info["title"]) > 3:
            score += 0.2
        
        # Meeting keywords present
        text_lower = email_text.lower()
        keyword_count = sum(1 for keyword in self.meeting_keywords if keyword in text_lower)
        score += min(keyword_count * 0.1, 0.3)
        
        # Has attendees
        if meeting_info.get("attendees") and len(meeting_info["attendees"]) > 1:
            score += 0.1
        
        return min(score, 1.0)

    def extract_multiple_meetings(self, email_text: str, email_metadata: Dict = None) -> List[Dict]:
        """Extract multiple meetings from a single email"""
        meetings = []
        
        # Split email into sections and check each
        sections = re.split(r'\n\s*\n', email_text)
        
        for section in sections:
            if len(section.strip()) > 50:  # Skip very short sections
                meeting = self.extract_meeting_info(section, email_metadata)
                if meeting:
                    meetings.append(meeting)
        
        return meetings