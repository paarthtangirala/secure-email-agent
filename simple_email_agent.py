#!/usr/bin/env python3
"""
Simple Email Agent - Loads past 10 days emails and generates instant responses
No database, just Gmail API + OpenAI API
"""

import os
import time
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import openai
from dotenv import load_dotenv
from auth import GoogleAuth
from config import config

# Load environment variables
load_dotenv()

app = FastAPI(title="Simple Email Agent", version="1.0.0")

class SimpleEmailAgent:
    def __init__(self):
        self.auth = GoogleAuth()
        # Load OpenAI API key
        keys = config.load_encrypted_json('api_keys')
        self.openai_key = keys.get('openai_api_key')
        if self.openai_key:
            openai.api_key = self.openai_key

    def get_recent_emails(self, days: int = 10) -> List[Dict]:
        """Get emails from the past N days directly from Gmail API"""
        try:
            service = self.auth.get_gmail_service()
            
            # Calculate date filter
            since_date = datetime.now() - timedelta(days=days)
            date_str = since_date.strftime('%Y/%m/%d')
            
            print(f"📥 Fetching emails from past {days} days (since {date_str})...")
            
            # Search emails from past N days
            query = f'after:{date_str}'
            result = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=int(os.getenv('EMAIL_MAX_RESULTS', '20'))  # Configurable via environment
            ).execute()
            
            messages = result.get('messages', [])
            emails = []
            
            print(f"🔍 Found {len(messages)} emails, processing...")
            
            for i, message in enumerate(messages):
                try:
                    # Get full email details
                    email_detail = service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()
                    
                    # Extract email data
                    headers = email_detail['payload'].get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                    date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                    
                    # Get email body
                    body = self._extract_email_body(email_detail['payload'])
                    
                    email_data = {
                        'id': message['id'],
                        'subject': subject,
                        'sender': sender,
                        'date': date,
                        'body': body[:500] + '...' if len(body) > 500 else body,  # Truncate long emails
                        'snippet': email_detail.get('snippet', '')
                    }
                    
                    # Detect if this is a meeting invite
                    meeting_info = self.detect_meeting_invite(email_data)
                    email_data['meeting_info'] = meeting_info
                    
                    emails.append(email_data)
                    
                    if (i + 1) % 10 == 0:
                        print(f"   Processed {i + 1}/{len(messages)} emails...")
                        
                except Exception as e:
                    print(f"   ⚠️ Error processing email {i+1}: {e}")
                    continue
            
            print(f"✅ Successfully loaded {len(emails)} emails")
            return emails
            
        except Exception as e:
            print(f"❌ Error fetching emails: {e}")
            return []

    def _extract_email_body(self, payload):
        """Extract email body from Gmail API payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        import base64
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
        else:
            if payload['mimeType'] == 'text/plain':
                data = payload['body'].get('data', '')
                if data:
                    import base64
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        return body.strip()

    def generate_responses(self, email: Dict) -> List[Dict]:
        """Generate 5 different response options using OpenAI API"""
        if not self.openai_key:
            return [{
                'success': False,
                'error': 'OpenAI API key not configured',
                'response': 'Please configure OpenAI API key',
                'type': 'Error',
                'tone': 'neutral'
            }] * 5
        
        # Define 5 different response styles
        response_styles = [
            {
                'type': 'Professional',
                'tone': 'formal',
                'instruction': 'Generate a formal, professional response that acknowledges the email and provides a helpful, business-appropriate reply.'
            },
            {
                'type': 'Friendly',
                'tone': 'warm',
                'instruction': 'Generate a warm, friendly response that maintains professionalism while being approachable and personable.'
            },
            {
                'type': 'Quick Acknowledgment',
                'tone': 'brief',
                'instruction': 'Generate a brief, efficient response that quickly acknowledges the email and provides next steps if needed.'
            },
            {
                'type': 'Detailed',
                'tone': 'thorough',
                'instruction': 'Generate a comprehensive response that addresses all points in detail and provides thorough information.'
            },
            {
                'type': 'Action-Oriented',
                'tone': 'decisive',
                'instruction': 'Generate a response focused on action items, next steps, and clear decisions with specific timelines.'
            }
        ]
        
        responses = []
        
        for style in response_styles:
            try:
                prompt = f"""
                Generate a {style['tone']} email response for the following email:
                
                Subject: {email['subject']}
                From: {email['sender']}
                Body: {email['body']}
                
                Style: {style['instruction']}
                
                Keep the response 2-4 sentences and maintain the {style['tone']} tone throughout.
                """
                
                response = openai.chat.completions.create(
                    model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
                    messages=[
                        {"role": "system", "content": f"You are a helpful email assistant specializing in {style['tone']} responses."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=int(os.getenv('MAX_RESPONSE_TOKENS', '200')),
                    temperature=float(os.getenv('RESPONSE_TEMPERATURE', '0.8'))
                )
                
                responses.append({
                    'success': True,
                    'response': response.choices[0].message.content.strip(),
                    'type': style['type'],
                    'tone': style['tone'],
                    'model': os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
                })
                
            except Exception as e:
                responses.append({
                    'success': False,
                    'error': str(e),
                    'response': f'Error generating {style["type"]} response: {e}',
                    'type': style['type'],
                    'tone': style['tone']
                })
        
        return responses

    def detect_meeting_invite(self, email: Dict) -> Dict:
        """Detect if email is a meeting invite and extract meeting details"""
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        sender = email.get('sender', '').lower()
        
        # Meeting keywords
        meeting_keywords = [
            'meeting', 'call', 'zoom', 'teams', 'conference', 'appointment',
            'interview', 'schedule', 'calendar', 'invite', 'session',
            'discussion', 'review', 'standup', 'sync', 'catch up'
        ]
        
        # Check if it's a meeting invite
        is_meeting = any(keyword in subject or keyword in body for keyword in meeting_keywords)
        
        # Additional checks for calendar invites
        calendar_indicators = [
            'calendar', 'event', 'ics', 'when:', 'time:', 'date:', 'join',
            'location:', 'room:', 'agenda:', 'attendees:'
        ]
        
        has_calendar_info = any(indicator in body for indicator in calendar_indicators)
        
        if is_meeting or has_calendar_info:
            # Extract meeting details using regex
            meeting_details = self._extract_meeting_details(email)
            
            return {
                'is_meeting': True,
                'confidence': 0.9 if has_calendar_info else 0.7,
                'details': meeting_details
            }
        
        return {
            'is_meeting': False,
            'confidence': 0.0,
            'details': {}
        }

    def _extract_meeting_details(self, email: Dict) -> Dict:
        """Extract meeting details from email content"""
        subject = email.get('subject', '')
        body = email.get('body', '')
        content = f"{subject} {body}"
        
        # Extract potential meeting title
        title = subject.strip() if subject else "Meeting"
        
        # Extract date patterns
        date_patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b',
            r'\b((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+\w+\s+\d{1,2})\b'
        ]
        
        # Extract time patterns
        time_patterns = [
            r'\b(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))\b',
            r'\b(\d{1,2}\s*(?:AM|PM|am|pm))\b'
        ]
        
        extracted_date = None
        extracted_time = None
        
        for pattern in date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                extracted_date = match.group(1)
                break
                
        for pattern in time_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                extracted_time = match.group(1)
                break
        
        # Extract location/link
        location_patterns = [
            r'(?:zoom|teams|meet|location|room|address)[:.\s]+([^\n]+)',
            r'https?://[^\s]+(?:zoom|teams|meet)[^\s]*',
            r'join\s+(?:at|here)[:.\s]*([^\n]+)'
        ]
        
        location = None
        for pattern in location_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                break
        
        return {
            'title': title,
            'date': extracted_date,
            'time': extracted_time,
            'location': location,
            'description': body[:200] + '...' if len(body) > 200 else body
        }

    def create_calendar_event(self, meeting_details: Dict, email_id: str) -> Dict:
        """Create a Google Calendar event from meeting details"""
        try:
            # Get calendar service
            service = self.auth.get_calendar_service()
            
            # Prepare event data
            title = meeting_details.get('title', 'Meeting')
            description = meeting_details.get('description', '')
            location = meeting_details.get('location', '')
            
            # Default to 1 hour from now if no specific time
            start_time = datetime.now() + timedelta(hours=1)
            end_time = start_time + timedelta(hours=1)
            
            # Try to parse extracted date/time if available
            if meeting_details.get('date') and meeting_details.get('time'):
                try:
                    date_str = meeting_details['date']
                    time_str = meeting_details['time']
                    # This is a simple parser - could be enhanced
                    datetime_str = f"{date_str} {time_str}"
                    # For now, use default times - parsing can be enhanced later
                except:
                    pass
            
            event = {
                'summary': title,
                'location': location,
                'description': f"Created from email\n\n{description}",
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': os.getenv('CALENDAR_TIMEZONE', 'America/Los_Angeles'),
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': os.getenv('CALENDAR_TIMEZONE', 'America/Los_Angeles'),
                },
                'attendees': [],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }
            
            # Create the event
            created_event = service.events().insert(calendarId='primary', body=event).execute()
            
            return {
                'success': True,
                'event_id': created_event['id'],
                'event_link': created_event.get('htmlLink'),
                'message': f"Calendar event '{title}' created successfully!"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to create calendar event: {e}"
            }

# Initialize agent
agent = SimpleEmailAgent()

@app.get("/", response_class=HTMLResponse)
async def home():
    """Main page with email list and 5 response options"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Email Assistant</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 0; padding: 0; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
            .header { 
                background: rgba(255,255,255,0.95); 
                backdrop-filter: blur(10px);
                color: #333; 
                padding: 30px; 
                border-radius: 15px; 
                margin-bottom: 25px; 
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                text-align: center;
            }
            .header h1 { margin: 0 0 10px 0; font-size: 2.5em; color: #4a5568; }
            .header p { margin: 0 0 20px 0; color: #718096; font-size: 1.1em; }
            .refresh-btn { 
                background: linear-gradient(45deg, #4299e1, #3182ce); 
                color: white; 
                border: none; 
                padding: 15px 30px; 
                border-radius: 25px; 
                cursor: pointer; 
                font-size: 16px;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(66, 153, 225, 0.3);
            }
            .refresh-btn:hover { 
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(66, 153, 225, 0.4);
            }
            .email-card { 
                background: rgba(255,255,255,0.95); 
                backdrop-filter: blur(10px);
                margin: 20px 0; 
                border-radius: 15px; 
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                overflow: hidden;
                transition: transform 0.3s ease;
            }
            .email-card:hover { transform: translateY(-5px); }
            .email-header { 
                background: linear-gradient(45deg, #f7fafc, #edf2f7);
                padding: 20px; 
                border-bottom: 1px solid #e2e8f0; 
            }
            .subject { font-size: 1.3em; font-weight: 600; color: #2d3748; margin-bottom: 8px; }
            .sender { color: #4a5568; font-size: 0.9em; }
            .date { color: #718096; font-size: 0.8em; float: right; }
            .body { 
                padding: 20px; 
                color: #4a5568; 
                line-height: 1.6; 
                max-height: 120px;
                overflow-y: auto;
                border-bottom: 1px solid #e2e8f0;
            }
            .responses-section { padding: 20px; }
            .responses-header { 
                font-weight: 600; 
                color: #2d3748; 
                margin-bottom: 20px; 
                font-size: 1.1em;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .responses-grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                gap: 15px; 
            }
            .response-option { 
                background: #f7fafc; 
                border: 2px solid #e2e8f0;
                border-radius: 12px; 
                padding: 15px; 
                transition: all 0.3s ease;
                cursor: pointer;
            }
            .response-option:hover { 
                border-color: #4299e1; 
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(66, 153, 225, 0.15);
            }
            .response-type { 
                font-weight: 600; 
                color: #2d3748; 
                margin-bottom: 8px; 
                display: flex;
                align-items: center;
                gap: 6px;
            }
            .response-text { 
                color: #4a5568; 
                line-height: 1.5; 
                font-size: 0.9em;
            }
            .tone-badge {
                background: #e2e8f0;
                color: #4a5568;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 0.7em;
                font-weight: 500;
            }
            .loading { 
                text-align: center; 
                padding: 60px 20px; 
                color: white;
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
            }
            .loading h3 { font-size: 1.5em; margin-bottom: 10px; }
            .error { color: #e53e3e; background: #fed7d7; padding: 20px; border-radius: 10px; }
            .progress-bar {
                width: 100%;
                height: 4px;
                background: rgba(255,255,255,0.3);
                border-radius: 2px;
                overflow: hidden;
                margin-top: 15px;
            }
            .progress-fill {
                height: 100%;
                background: linear-gradient(45deg, #4299e1, #3182ce);
                border-radius: 2px;
                transition: width 0.3s ease;
            }
            
            /* Response type icons */
            .response-option[data-type="Professional"] .response-type:before { content: "💼 "; }
            .response-option[data-type="Friendly"] .response-type:before { content: "😊 "; }
            .response-option[data-type="Quick Acknowledgment"] .response-type:before { content: "⚡ "; }
            .response-option[data-type="Detailed"] .response-type:before { content: "📋 "; }
            .response-option[data-type="Action-Oriented"] .response-type:before { content: "🎯 "; }
            
            /* Calendar button styles */
            .calendar-section {
                background: linear-gradient(45deg, #48bb78, #38a169);
                margin: 15px 0;
                padding: 15px;
                border-radius: 10px;
                color: white;
            }
            .calendar-button {
                background: rgba(255,255,255,0.2);
                border: 2px solid rgba(255,255,255,0.3);
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s ease;
                font-weight: 600;
                display: inline-flex;
                align-items: center;
                gap: 8px;
            }
            .calendar-button:hover {
                background: rgba(255,255,255,0.3);
                border-color: rgba(255,255,255,0.5);
                transform: translateY(-1px);
            }
            .calendar-button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            .meeting-info {
                font-size: 0.9em;
                margin-top: 8px;
                opacity: 0.9;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 AI Email Assistant</h1>
                <p>Intelligent email responses with 5 tailored options for each message</p>
                <button class="refresh-btn" onclick="loadEmails()">🔄 Refresh & Generate Responses</button>
            </div>
            
            <div id="emails-container">
                <div class="loading">
                    <h3>🚀 Ready to Process Your Emails!</h3>
                    <p>Click the button above to fetch your recent emails and generate 5 AI responses for each message.</p>
                    <p style="font-size: 0.9em; opacity: 0.8;">This will process emails from the past 10 days.</p>
                </div>
            </div>
        </div>

        <script>
            let loadingInterval;
            
            async function loadEmails() {
                const container = document.getElementById('emails-container');
                container.innerHTML = `
                    <div class="loading">
                        <h3>⏳ Processing emails...</h3>
                        <p>This may take a moment as we generate 5 responses for each email...</p>
                        <div class="progress-bar">
                            <div class="progress-fill" id="progress-fill"></div>
                        </div>
                    </div>
                `;
                
                // Simulate progress
                let progress = 0;
                loadingInterval = setInterval(() => {
                    progress += Math.random() * 3;
                    if (progress > 90) progress = 90;
                    document.getElementById('progress-fill').style.width = progress + '%';
                }, 500);
                
                try {
                    const response = await fetch('/api/emails-with-responses');
                    const data = await response.json();
                    
                    clearInterval(loadingInterval);
                    document.getElementById('progress-fill').style.width = '100%';
                    
                    if (data.success) {
                        setTimeout(() => displayEmails(data.emails), 300);
                    } else {
                        container.innerHTML = `<div class="error"><h3>❌ Error</h3><p>${data.error}</p></div>`;
                    }
                } catch (error) {
                    clearInterval(loadingInterval);
                    container.innerHTML = `<div class="error"><h3>❌ Network Error</h3><p>${error.message}</p></div>`;
                }
            }
            
            function displayEmails(emails) {
                const container = document.getElementById('emails-container');
                
                if (emails.length === 0) {
                    container.innerHTML = '<div class="loading"><h3>📭 No emails found</h3><p>No emails from the past 10 days.</p></div>';
                    return;
                }
                
                let html = `<div style="color: white; text-align: center; margin-bottom: 20px; font-size: 1.2em;">
                    ✨ Successfully processed ${emails.length} emails with ${emails.length * 5} AI responses!
                </div>`;
                
                emails.forEach((email, index) => {
                    const clearDiv = '<div style="clear: both;"></div>';
                    html += `
                        <div class="email-card">
                            <div class="email-header">
                                <div class="subject">${email.subject}</div>
                                <div class="sender">From: ${email.sender}</div>
                                <div class="date">${email.date}</div>
                                ${clearDiv}
                            </div>
                            <div class="body">${email.body}</div>`;
                    
                    // Add calendar section if it's a meeting
                    if (email.meeting_info && email.meeting_info.is_meeting) {
                        const meetingDetails = email.meeting_info.details;
                        html += `
                            <div class="calendar-section">
                                <div style="display: flex; align-items: center; justify-content: space-between;">
                                    <div>
                                        <strong>📅 Meeting Detected!</strong>
                                        <div class="meeting-info">
                                            ${meetingDetails.title ? `Title: ${meetingDetails.title}` : ''}
                                            ${meetingDetails.date ? `<br>Date: ${meetingDetails.date}` : ''}
                                            ${meetingDetails.time ? `<br>Time: ${meetingDetails.time}` : ''}
                                            ${meetingDetails.location ? `<br>Location: ${meetingDetails.location}` : ''}
                                        </div>
                                    </div>
                                    <button class="calendar-button" onclick="createCalendarEvent('${email.id}', ${JSON.stringify(meetingDetails).replace(/"/g, '&quot;')})">
                                        📅 Add to Calendar
                                    </button>
                                </div>
                            </div>`;
                    }
                    
                    html += `
                            <div class="responses-section">
                                <div class="responses-header">
                                    🎯 AI Response Options
                                    <span class="tone-badge">5 styles available</span>
                                </div>
                                <div class="responses-grid">
                    `;
                    
                    if (email.ai_responses && email.ai_responses.length > 0) {
                        email.ai_responses.forEach(response => {
                            const statusClass = response.success ? '' : 'error';
                            html += `
                                <div class="response-option ${statusClass}" data-type="${response.type}">
                                    <div class="response-type">
                                        ${response.type}
                                        <span class="tone-badge">${response.tone}</span>
                                    </div>
                                    <div class="response-text">${response.response}</div>
                                </div>
                            `;
                        });
                    } else {
                        html += '<div class="error">No responses generated</div>';
                    }
                    
                    html += `
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                container.innerHTML = html;
            }
            
            // Calendar event creation function
            async function createCalendarEvent(emailId, meetingDetails) {
                const button = event.target;
                const originalText = button.innerHTML;
                
                try {
                    button.disabled = true;
                    button.innerHTML = '⏳ Creating...';
                    
                    const response = await fetch('/api/create-calendar-event', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            email_id: emailId,
                            meeting_details: meetingDetails
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        button.innerHTML = '✅ Added to Calendar!';
                        button.style.background = 'rgba(72, 187, 120, 0.8)';
                        
                        // Show success message
                        if (result.event_link) {
                            setTimeout(() => {
                                if (confirm('Calendar event created! Would you like to view it?')) {
                                    window.open(result.event_link, '_blank');
                                }
                            }, 500);
                        }
                    } else {
                        button.innerHTML = '❌ Failed';
                        button.style.background = 'rgba(255, 0, 0, 0.6)';
                        alert('Failed to create calendar event: ' + (result.error || result.message));
                        
                        setTimeout(() => {
                            button.innerHTML = originalText;
                            button.style.background = '';
                            button.disabled = false;
                        }, 3000);
                    }
                } catch (error) {
                    button.innerHTML = '❌ Error';
                    button.style.background = 'rgba(255, 0, 0, 0.6)';
                    alert('Network error: ' + error.message);
                    
                    setTimeout(() => {
                        button.innerHTML = originalText;
                        button.style.background = '';
                        button.disabled = false;
                    }, 3000);
                }
            }
            
            // Don't auto-load emails - wait for user to click button
            // loadEmails();
        </script>
    </body>
    </html>
    """

@app.get("/api/emails-with-responses")
async def get_emails_with_responses():
    """Get recent emails and generate responses for each"""
    try:
        print("🚀 Starting simple email agent...")
        
        # Get recent emails
        emails = agent.get_recent_emails(days=int(os.getenv('EMAIL_FETCH_DAYS', '10')))
        
        if not emails:
            return JSONResponse({
                'success': False,
                'error': 'No emails found or failed to fetch emails',
                'emails': []
            })
        
        print(f"💬 Generating responses for {len(emails)} emails...")
        
        # Generate 5 responses for each email
        for i, email in enumerate(emails):
            print(f"   Processing {i+1}/{len(emails)}: {email['subject'][:50]}...")
            
            responses_data = agent.generate_responses(email)
            email['ai_responses'] = responses_data
            email['response_success'] = all(r['success'] for r in responses_data)
            
            # Configurable delay for processing
            time.sleep(float(os.getenv('EMAIL_PROCESSING_DELAY_SECONDS', '0.2')))  # Respecting rate limits
        
        print("✅ All responses generated!")
        
        return JSONResponse({
            'success': True,
            'emails': emails,
            'total_count': len(emails)
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return JSONResponse({
            'success': False,
            'error': str(e),
            'emails': []
        })

@app.post("/api/create-calendar-event")
async def create_calendar_event_endpoint(request: dict):
    """Create a calendar event from email meeting details"""
    try:
        email_id = request.get('email_id')
        meeting_details = request.get('meeting_details')
        
        if not email_id or not meeting_details:
            return JSONResponse({
                'success': False,
                'error': 'Missing email_id or meeting_details'
            })
        
        result = agent.create_calendar_event(meeting_details, email_id)
        return JSONResponse(result)
        
    except Exception as e:
        return JSONResponse({
            'success': False,
            'error': str(e),
            'message': f'Failed to create calendar event: {e}'
        })

if __name__ == "__main__":
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', '8502'))
    log_level = os.getenv('DEV_LOG_LEVEL', 'info')
    
    print("🚀 Starting Simple Email Agent...")
    print(f"📧 Fetches past {os.getenv('EMAIL_FETCH_DAYS', '10')} days emails + generates AI responses")
    print(f"🌐 Web interface: http://{host}:{port}")
    
    uvicorn.run(app, host=host, port=port, log_level=log_level)