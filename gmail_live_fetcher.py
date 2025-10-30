#!/usr/bin/env python3
"""
Gmail Live Fetcher - Direct Gmail API access for recent emails
Fetches emails from past 10 days without database storage
"""

import base64
import email
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from auth import GoogleAuth

class GmailLiveFetcher:
    """Fetch emails directly from Gmail API for past 10 days"""
    
    def __init__(self):
        self.auth = GoogleAuth()
        self.service = None
        
    def _get_service(self):
        """Get Gmail service with authentication"""
        if not self.service:
            try:
                self.service = self.auth.get_gmail_service()
            except Exception as e:
                print(f"Gmail authentication failed: {e}")
                return None
        return self.service
    
    def fetch_recent_emails(self, days_back: int = 10, max_results: int = 50) -> List[Dict]:
        """
        Fetch emails from Gmail for the past N days
        
        Args:
            days_back: Number of days to look back
            max_results: Maximum number of emails to fetch
            
        Returns:
            List of email dictionaries with id, subject, sender, date, body, etc.
        """
        try:
            service = self._get_service()
            if not service:
                return []
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Gmail API query for recent emails
            query = f'after:{start_date.strftime("%Y/%m/%d")}'
            
            print(f"Fetching emails from Gmail for past {days_back} days...")
            
            # Get message list
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            print(f"Found {len(messages)} recent emails")
            
            emails = []
            for i, message in enumerate(messages):
                try:
                    email_data = self._fetch_email_details(service, message['id'])
                    if email_data:
                        emails.append(email_data)
                        
                    # Progress update
                    if (i + 1) % 10 == 0:
                        print(f"Processed {i + 1}/{len(messages)} emails...")
                        
                except Exception as e:
                    print(f"Error fetching email {message['id']}: {e}")
                    continue
            
            print(f"Successfully fetched {len(emails)} emails from Gmail")
            return emails
            
        except Exception as e:
            print(f"Error fetching emails from Gmail: {e}")
            return []
    
    def _fetch_email_details(self, service, message_id: str) -> Optional[Dict]:
        """Fetch detailed email information"""
        try:
            message = service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = message['payload'].get('headers', [])
            header_dict = {h['name'].lower(): h['value'] for h in headers}
            
            # Extract body
            body_text = self._extract_body(message['payload'])
            
            # Parse date
            date_received = header_dict.get('date', '')
            
            # Create email dictionary
            email_data = {
                'id': message_id,
                'thread_id': message.get('threadId', message_id),
                'subject': header_dict.get('subject', 'No Subject'),
                'sender': header_dict.get('from', 'Unknown Sender'),
                'sender_email': self._extract_email_from_sender(header_dict.get('from', '')),
                'recipients': [header_dict.get('to', '')],
                'date_received': date_received,
                'body_text': body_text[:5000],  # Limit body size
                'body_html': '',
                'labels': [],
                'primary_label': 'inbox',
                'is_important': False,
                'is_unread': 'UNREAD' in message.get('labelIds', []),
                'attachments_count': len(message['payload'].get('parts', [])) - 1 if message['payload'].get('parts') else 0,
                'classification': 'general',
                'confidence': 1.0,
                'urgency_level': 'medium',
                'requires_response': False
            }
            
            return email_data
            
        except Exception as e:
            print(f"Error extracting email details: {e}")
            return None
    
    def _extract_body(self, payload) -> str:
        """Extract email body text from payload"""
        body = ""
        
        try:
            # If it's a simple text email
            if payload.get('body', {}).get('data'):
                body = base64.urlsafe_b64decode(
                    payload['body']['data']
                ).decode('utf-8', errors='ignore')
            
            # If it's a multipart email
            elif payload.get('parts'):
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        if part.get('body', {}).get('data'):
                            part_body = base64.urlsafe_b64decode(
                                part['body']['data']
                            ).decode('utf-8', errors='ignore')
                            body += part_body
                    elif part.get('parts'):  # Nested parts
                        for nested_part in part['parts']:
                            if (nested_part.get('mimeType') == 'text/plain' and 
                                nested_part.get('body', {}).get('data')):
                                nested_body = base64.urlsafe_b64decode(
                                    nested_part['body']['data']
                                ).decode('utf-8', errors='ignore')
                                body += nested_body
            
            return body.strip()
            
        except Exception as e:
            print(f"Error extracting body: {e}")
            return ""
    
    def _extract_email_from_sender(self, sender_str: str) -> str:
        """Extract email address from sender string"""
        try:
            if '<' in sender_str and '>' in sender_str:
                return sender_str.split('<')[1].split('>')[0]
            elif '@' in sender_str:
                return sender_str.strip()
            else:
                return sender_str
        except:
            return sender_str
    
    def test_connection(self) -> bool:
        """Test Gmail API connection"""
        try:
            service = self._get_service()
            if service:
                # Try a simple API call
                results = service.users().labels().list(userId='me').execute()
                labels = results.get('labels', [])
                print(f"✅ Gmail connection successful - found {len(labels)} labels")
                return True
            else:
                print("❌ Failed to get Gmail service")
                return False
        except Exception as e:
            print(f"❌ Gmail connection test failed: {e}")
            return False