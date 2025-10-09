#!/usr/bin/env python3

"""
Demo mode for Secure Email Agent
Shows all functionality without requiring OAuth authentication
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List

# Sample email data for demonstration
SAMPLE_EMAILS = [
    {
        "id": "email_001",
        "subject": "Interview Invitation - Software Engineer Position",
        "sender": "recruiter@techcorp.com",
        "date": "2025-01-19 10:30:00",
        "body": """Dear Candidate,

We are pleased to invite you for an interview for the Software Engineer position at TechCorp.

Interview Details:
- Date: Monday, January 22, 2025
- Time: 2:00 PM PST
- Duration: 1 hour
- Location: Zoom Meeting (link will be provided)

Please confirm your availability for this time slot.

Best regards,
Sarah Johnson
Technical Recruiter
TechCorp Inc."""
    },
    {
        "id": "email_002",
        "subject": "Team Meeting - Project Alpha Review",
        "sender": "manager@company.com",
        "date": "2025-01-19 09:15:00",
        "body": """Hi Team,

We need to schedule our weekly Project Alpha review meeting.

Proposed time: Wednesday, January 24, 2025 at 3:30 PM
Duration: 45 minutes
Agenda:
- Sprint review
- Blockers discussion
- Next week planning

Please let me know if this time works for everyone.

Thanks,
Mike"""
    },
    {
        "id": "email_003",
        "subject": "50% OFF Sale - Limited Time Offer!",
        "sender": "marketing@deals.com",
        "date": "2025-01-19 08:00:00",
        "body": """🎉 HUGE SALE ALERT! 🎉

Get 50% OFF on all products! Limited time offer expires soon!

✅ Free shipping
✅ Money-back guarantee
✅ Premium quality products

Click here to shop now: [SHOP NOW]

Unsubscribe from future emails: [UNSUBSCRIBE]

This offer expires January 25, 2025"""
    },
    {
        "id": "email_004",
        "subject": "Urgent: Server Maintenance Window",
        "sender": "devops@mycompany.com",
        "date": "2025-01-19 11:45:00",
        "body": """URGENT: Scheduled Maintenance

We have a critical server maintenance window scheduled:

Date: Tomorrow (January 20, 2025)
Time: 2:00 AM - 4:00 AM EST
Expected downtime: 2 hours
Systems affected: Production database, API services

Please ensure all critical operations are completed before the maintenance window.

Contact me immediately if you have concerns.

Best,
DevOps Team"""
    },
    {
        "id": "email_005",
        "subject": "Coffee Chat Invitation",
        "sender": "colleague@work.com",
        "date": "2025-01-19 14:20:00",
        "body": """Hey!

Hope you're doing well! Would you like to grab coffee sometime this week?

I'm free:
- Tuesday afternoon after 3pm
- Thursday morning before 11am
- Friday anytime

Let me know what works for you!

Cheers,
Alex"""
    }
]

class EmailAgentDemo:
    def __init__(self):
        # Import the actual agent components
        from email_classifier import EmailClassifier
        from response_generator import ResponseGenerator
        from calendar_manager import CalendarManager
        from auth import GoogleAuth

        self.classifier = EmailClassifier()
        self.response_generator = ResponseGenerator()

        print("🤖 Secure Email Agent - DEMO MODE")
        print("=" * 50)
        print("This demo shows the agent's capabilities using sample emails")
        print("No OAuth authentication required!")
        print()

    def run_demo(self):
        """Run the complete demo"""
        print("📧 Processing sample emails...\n")

        results = {
            'processed_count': 0,
            'important_emails': [],
            'promotional_emails': [],
            'calendar_events': [],
            'response_suggestions': []
        }

        for email in SAMPLE_EMAILS:
            result = self._process_demo_email(email)
            results['processed_count'] += 1

            if result['classification']['classification'] == 'important':
                results['important_emails'].append(result)
            elif result['classification']['classification'] == 'promotional':
                results['promotional_emails'].append(result)

            if result.get('calendar_events'):
                results['calendar_events'].extend(result['calendar_events'])

            if result.get('response_suggestions'):
                results['response_suggestions'].extend(result['response_suggestions'])

        self._display_results(results)

    def _process_demo_email(self, email_data: Dict) -> Dict:
        """Process a single demo email"""
        print(f"📬 Processing: {email_data['subject'][:50]}...")

        # Classify the email
        classification = self.classifier.classify_email(email_data)

        result = {
            'email_id': email_data['id'],
            'subject': email_data['subject'],
            'sender': email_data['sender'],
            'classification': classification,
            'processed_at': datetime.now().isoformat()
        }

        # Extract calendar events if important
        if classification['classification'] == 'important':
            calendar_events = self._extract_demo_calendar_events(email_data)
            if calendar_events:
                result['calendar_events'] = calendar_events

        # Generate response suggestions for important emails
        if classification.get('requires_response') and classification['classification'] == 'important':
            suggestions = self.response_generator.generate_response_suggestions(
                email_data, classification
            )
            result['response_suggestions'] = suggestions

        return result

    def _extract_demo_calendar_events(self, email_data: Dict) -> List[Dict]:
        """Extract calendar events from demo emails"""
        events = []

        # Simple pattern matching for demo
        body = email_data['body'].lower()
        subject = email_data['subject'].lower()

        # Look for meeting/interview patterns
        if any(word in body or word in subject for word in ['interview', 'meeting', 'call']):
            # Extract basic event info (simplified for demo)
            if 'monday, january 22, 2025' in body and '2:00 pm' in body:
                events.append({
                    'summary': 'Software Engineer Interview - TechCorp',
                    'start': '2025-01-22T14:00:00',
                    'end': '2025-01-22T15:00:00',
                    'location': 'Zoom Meeting',
                    'confidence': 0.9
                })
            elif 'wednesday, january 24, 2025' in body and '3:30 pm' in body:
                events.append({
                    'summary': 'Project Alpha Review Meeting',
                    'start': '2025-01-24T15:30:00',
                    'end': '2025-01-24T16:15:00',
                    'location': 'Conference Room',
                    'confidence': 0.85
                })

        return events

    def _display_results(self, results: Dict):
        """Display the demo results"""
        print("\n" + "="*60)
        print("📊 PROCESSING RESULTS")
        print("="*60)

        print(f"📧 Total emails processed: {results['processed_count']}")
        print(f"⭐ Important emails: {len(results['important_emails'])}")
        print(f"🛒 Promotional emails: {len(results['promotional_emails'])}")
        print(f"📅 Calendar events extracted: {len(results['calendar_events'])}")
        print(f"💬 Response suggestions generated: {len(results['response_suggestions'])}")

        # Show important emails
        if results['important_emails']:
            print("\n" + "="*60)
            print("⭐ IMPORTANT EMAILS")
            print("="*60)

            for i, email in enumerate(results['important_emails'], 1):
                print(f"\n{i}. {email['subject']}")
                print(f"   From: {email['sender']}")
                print(f"   Classification: {email['classification']['classification']}")
                print(f"   Confidence: {email['classification']['confidence']:.2f}")
                print(f"   Reasoning: {email['classification']['reasoning']}")

                if email['classification'].get('requires_response'):
                    print("   🔔 Requires response")

                urgency = email['classification'].get('urgency_level', 'normal')
                if urgency == 'urgent':
                    print("   🚨 URGENT")
                elif urgency == 'high':
                    print("   ⚡ High priority")

        # Show calendar events
        if results['calendar_events']:
            print("\n" + "="*60)
            print("📅 CALENDAR EVENTS EXTRACTED")
            print("="*60)

            for i, event in enumerate(results['calendar_events'], 1):
                print(f"\n{i}. {event['summary']}")
                print(f"   Start: {event['start']}")
                print(f"   End: {event['end']}")
                print(f"   Location: {event['location']}")
                print(f"   Confidence: {event['confidence']:.1%}")

        # Show response suggestions
        if results['response_suggestions']:
            print("\n" + "="*60)
            print("💬 RESPONSE SUGGESTIONS")
            print("="*60)

            for i, suggestion in enumerate(results['response_suggestions'][:3], 1):
                print(f"\n{i}. {suggestion['type'].title()} Response")
                print(f"   Subject: {suggestion['subject']}")
                print(f"   Confidence: {suggestion['confidence']:.1%}")
                print(f"   Reasoning: {suggestion['reasoning']}")
                print("   Body preview:")
                print(f"   {suggestion['body'][:100]}...")

        # Show promotional emails (filtered out)
        if results['promotional_emails']:
            print("\n" + "="*60)
            print("🛒 PROMOTIONAL EMAILS (FILTERED)")
            print("="*60)

            for email in results['promotional_emails']:
                print(f"• {email['subject']} (from {email['sender']})")
                print(f"  Confidence: {email['classification']['confidence']:.1%}")

        print("\n" + "="*60)
        print("✅ DEMO COMPLETE")
        print("="*60)
        print("This demonstrates the core functionality of your Secure Email Agent:")
        print("• Email classification (important vs promotional)")
        print("• Calendar event extraction from meeting emails")
        print("• Automated response suggestions")
        print("• Priority and urgency assessment")
        print("• Secure, encrypted data handling")
        print("\nTo use with real emails, complete the OAuth setup!")

def main():
    """Run the demo"""
    try:
        demo = EmailAgentDemo()
        demo.run_demo()
    except Exception as e:
        print(f"Demo error: {e}")
        print("Note: Some features may require all dependencies to be installed")

if __name__ == '__main__':
    main()