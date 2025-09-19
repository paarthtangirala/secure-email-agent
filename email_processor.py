import base64
import json
import email
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from googleapiclient.errors import HttpError
from auth import GoogleAuth
from email_classifier import EmailClassifier
from calendar_manager import CalendarManager
from response_generator import ResponseGenerator
from config import config

class EmailProcessor:
    def __init__(self):
        self.auth = GoogleAuth()
        self.classifier = EmailClassifier()
        self.calendar_manager = CalendarManager(self.auth)
        self.response_generator = ResponseGenerator()

        # Processing settings
        self.max_emails_per_run = 50
        self.processed_emails_cache = set()

    def process_new_emails(self, hours_back: int = 24) -> Dict:
        """Process new emails from the last specified hours"""
        try:
            # Get Gmail service
            service = self.auth.get_gmail_service()

            # Calculate time threshold
            since_time = datetime.now() - timedelta(hours=hours_back)
            query = f'is:unread after:{since_time.strftime("%Y/%m/%d")}'

            # Get emails
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=self.max_emails_per_run
            ).execute()

            messages = results.get('messages', [])

            if not messages:
                return {
                    'processed_count': 0,
                    'important_emails': [],
                    'calendar_events_created': 0,
                    'response_suggestions': []
                }

            # Process each email
            processing_results = {
                'processed_count': 0,
                'important_emails': [],
                'calendar_events_created': 0,
                'response_suggestions': [],
                'errors': []
            }

            for message in messages:
                try:
                    result = self._process_single_email(service, message['id'])
                    if result:
                        processing_results['processed_count'] += 1

                        if result.get('is_important'):
                            processing_results['important_emails'].append(result)

                        if result.get('calendar_event_created'):
                            processing_results['calendar_events_created'] += 1

                        if result.get('response_suggestions'):
                            processing_results['response_suggestions'].extend(
                                result['response_suggestions']
                            )

                except Exception as e:
                    processing_results['errors'].append({
                        'email_id': message['id'],
                        'error': str(e)
                    })

            # Save processing summary
            self._save_processing_summary(processing_results)

            return processing_results

        except HttpError as error:
            print(f'An error occurred processing emails: {error}')
            return {'error': str(error)}

    def _process_single_email(self, service, email_id: str) -> Optional[Dict]:
        """Process a single email"""
        try:
            # Skip if already processed
            if email_id in self.processed_emails_cache:
                return None

            # Get email details
            email_data = self._get_email_data(service, email_id)
            if not email_data:
                return None

            # Classify email
            classification = self.classifier.classify_email(email_data)

            # Skip promotional emails unless they need review
            if classification['classification'] == 'promotional':
                self.processed_emails_cache.add(email_id)
                return None

            result = {
                'email_id': email_id,
                'subject': email_data['subject'],
                'sender': email_data['sender'],
                'classification': classification,
                'is_important': classification['classification'] in ['important', 'requires_review'],
                'processed_at': datetime.now().isoformat()
            }

            # Extract calendar events if important
            if classification['classification'] == 'important':
                calendar_events = self.calendar_manager.extract_calendar_events(email_data)

                if calendar_events:
                    result['potential_events'] = calendar_events

                    # Auto-create high-confidence events if enabled
                    for event in calendar_events:
                        if event.get('confidence', 0) > 0.8:
                            # Check for conflicts first
                            conflicts = self.calendar_manager.check_conflicts(event)

                            if not conflicts:
                                event_id = self.calendar_manager.create_calendar_event(event)
                                if event_id:
                                    result['calendar_event_created'] = True
                                    result['created_event_id'] = event_id

            # Generate response suggestions for important emails
            if classification.get('requires_response') and classification['classification'] == 'important':
                suggestions = self.response_generator.generate_response_suggestions(
                    email_data, classification
                )
                result['response_suggestions'] = suggestions

            # Save processed email data
            self._save_processed_email_data(email_id, email_data, result)

            self.processed_emails_cache.add(email_id)
            return result

        except Exception as e:
            print(f"Error processing email {email_id}: {e}")
            return None

    def _get_email_data(self, service, email_id: str) -> Optional[Dict]:
        """Extract email data from Gmail API response"""
        try:
            # Get email message
            message = service.users().messages().get(
                userId='me',
                id=email_id,
                format='full'
            ).execute()

            # Extract headers
            headers = {h['name']: h['value'] for h in message['payload']['headers']}

            # Extract body
            body = self._extract_email_body(message['payload'])

            email_data = {
                'id': email_id,
                'subject': headers.get('Subject', ''),
                'sender': headers.get('From', ''),
                'date': headers.get('Date', ''),
                'body': body,
                'thread_id': message.get('threadId', ''),
                'labels': message.get('labelIds', [])
            }

            return email_data

        except Exception as e:
            print(f"Error extracting email data: {e}")
            return None

    def _extract_email_body(self, payload) -> str:
        """Extract email body from payload"""
        body = ""

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body += base64.urlsafe_b64decode(data).decode('utf-8')
                elif part['mimeType'] == 'text/html':
                    data = part['body']['data']
                    # You might want to use a library to convert HTML to text
                    html_body = base64.urlsafe_b64decode(data).decode('utf-8')
                    # Basic HTML tag removal (you should use a proper HTML parser)
                    import re
                    body += re.sub('<[^<]+?>', '', html_body)
        else:
            if payload['mimeType'] == 'text/plain':
                data = payload['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')

        return body

    def _save_processed_email_data(self, email_id: str, email_data: Dict, result: Dict):
        """Save processed email data securely"""
        processed_data = config.load_encrypted_json("processed_emails")

        if 'emails' not in processed_data:
            processed_data['emails'] = {}

        processed_data['emails'][email_id] = {
            'subject': email_data['subject'],
            'sender': email_data['sender'],
            'classification': result['classification'],
            'processed_at': result['processed_at'],
            'has_calendar_event': result.get('calendar_event_created', False),
            'has_responses': bool(result.get('response_suggestions'))
        }

        config.save_encrypted_json("processed_emails", processed_data)

    def _save_processing_summary(self, results: Dict):
        """Save processing summary for reporting"""
        summaries = config.load_encrypted_json("processing_summaries")

        if 'summaries' not in summaries:
            summaries['summaries'] = []

        summary = {
            'timestamp': datetime.now().isoformat(),
            'processed_count': results['processed_count'],
            'important_count': len(results['important_emails']),
            'events_created': results['calendar_events_created'],
            'responses_generated': len(results['response_suggestions']),
            'errors': len(results.get('errors', []))
        }

        summaries['summaries'].append(summary)

        # Keep only last 100 summaries
        if len(summaries['summaries']) > 100:
            summaries['summaries'] = summaries['summaries'][-100:]

        config.save_encrypted_json("processing_summaries", summaries)

    def get_important_emails(self, days_back: int = 7) -> List[Dict]:
        """Get important emails from the last specified days"""
        processed_data = config.load_encrypted_json("processed_emails")

        if 'emails' not in processed_data:
            return []

        cutoff_date = datetime.now() - timedelta(days=days_back)
        important_emails = []

        for email_id, data in processed_data['emails'].items():
            try:
                processed_at = datetime.fromisoformat(data['processed_at'])
                if (processed_at > cutoff_date and
                    data['classification']['classification'] in ['important', 'requires_review']):
                    important_emails.append({
                        'id': email_id,
                        'subject': data['subject'],
                        'sender': data['sender'],
                        'classification': data['classification'],
                        'processed_at': data['processed_at']
                    })
            except:
                continue

        return sorted(important_emails, key=lambda x: x['processed_at'], reverse=True)

    def get_response_suggestions_for_email(self, email_id: str) -> List[Dict]:
        """Get response suggestions for a specific email"""
        # This would typically involve loading the email data and regenerating suggestions
        # For now, we'll return cached suggestions if available
        processed_data = config.load_encrypted_json("processed_emails")

        if email_id in processed_data.get('emails', {}):
            # In a full implementation, you'd regenerate or load cached suggestions
            return []

        return []

    def mark_email_as_handled(self, email_id: str, action_taken: str):
        """Mark an email as handled with the action taken"""
        processed_data = config.load_encrypted_json("processed_emails")

        if email_id in processed_data.get('emails', {}):
            processed_data['emails'][email_id]['handled'] = True
            processed_data['emails'][email_id]['action_taken'] = action_taken
            processed_data['emails'][email_id]['handled_at'] = datetime.now().isoformat()

            config.save_encrypted_json("processed_emails", processed_data)

    def get_processing_stats(self) -> Dict:
        """Get processing statistics"""
        summaries = config.load_encrypted_json("processing_summaries")

        if 'summaries' not in summaries or not summaries['summaries']:
            return {
                'total_processed': 0,
                'total_important': 0,
                'total_events_created': 0,
                'total_responses_generated': 0,
                'last_run': None
            }

        recent_summaries = summaries['summaries'][-30:]  # Last 30 runs

        stats = {
            'total_processed': sum(s['processed_count'] for s in recent_summaries),
            'total_important': sum(s['important_count'] for s in recent_summaries),
            'total_events_created': sum(s['events_created'] for s in recent_summaries),
            'total_responses_generated': sum(s['responses_generated'] for s in recent_summaries),
            'last_run': recent_summaries[-1]['timestamp'] if recent_summaries else None,
            'average_important_per_run': sum(s['important_count'] for s in recent_summaries) / len(recent_summaries) if recent_summaries else 0
        }

        return stats