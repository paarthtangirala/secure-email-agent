#!/usr/bin/env python3
"""
Fast Response Generator 2.0 - Ultra-fast template engine with precompiled regex archetypes
Provides instant responses ≤100ms with slot-filling and smart archetype detection
"""

import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import string

class FastResponseGenerator:
    """Template Engine 2.0: Ultra-fast response generator with archetype detection"""

    def __init__(self):
        self.response_templates = self._initialize_templates()
        self.regex_buckets = self._compile_regex_buckets()
        self.slot_patterns = self._compile_slot_patterns()

    def _compile_regex_buckets(self) -> Dict[str, re.Pattern]:
        """Precompile regex patterns for ultra-fast archetype detection"""
        return {
            'reschedule': re.compile(r'\b(reschedule|postpone|delay|move|shift|change.*time|different.*time)\b', re.IGNORECASE),
            'confirm': re.compile(r'\b(confirm|confirmation|verify|affirm|acknowledge|yes.*correct)\b', re.IGNORECASE),
            'availability': re.compile(r'\b(available|availability|free|busy|schedule|calendar|time.*work)\b', re.IGNORECASE),
            'deadline': re.compile(r'\b(deadline|due.*date|urgent|asap|rush|priority|time.*sensitive)\b', re.IGNORECASE),
            'invoice': re.compile(r'\b(invoice|bill|payment.*due|amount.*owed|balance|charges)\b', re.IGNORECASE),
            'payment': re.compile(r'\b(payment.*failed|declined|billing.*issue|update.*payment|card.*expired)\b', re.IGNORECASE),
            'refund': re.compile(r'\b(refund|return|money.*back|reimburs|credit)\b', re.IGNORECASE),
            'bank': re.compile(r'\b(bank.*deal|offer|cashback|reward|statement|account.*summary)\b', re.IGNORECASE),
            'statement': re.compile(r'\b(statement.*available|monthly.*statement|billing.*statement|account.*activity)\b', re.IGNORECASE),
            'offer': re.compile(r'\b(special.*offer|deal|discount|promo|sale|limited.*time)\b', re.IGNORECASE),
            'scope': re.compile(r'\b(scope|requirements|specification|details|deliverable)\b', re.IGNORECASE),
            'deliverables': re.compile(r'\b(deliver|completion|finished|ready|done|complete)\b', re.IGNORECASE),
            'follow_up': re.compile(r'\b(follow.*up|checking.*in|touching.*base|update|progress)\b', re.IGNORECASE),
            'thank': re.compile(r'\b(thank|appreciate|grateful|thanks)\b', re.IGNORECASE),
            'intro': re.compile(r'\b(introduction|introduce|meet|connect|new.*team|joining)\b', re.IGNORECASE),
            'application': re.compile(r'\b(application|apply|position|role|job|opportunity)\b', re.IGNORECASE),
            'interview': re.compile(r'\b(interview|meeting.*discuss|talk|call.*schedule)\b', re.IGNORECASE),
        }

    def _compile_slot_patterns(self) -> Dict[str, re.Pattern]:
        """Compile patterns for slot extraction with safe defaults"""
        return {
            'recipient_first': re.compile(r'\b([A-Z][a-z]+)(?:\s|,|$)', re.MULTILINE),
            'date': re.compile(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+day\s*\d{1,2}|\w+\s+\d{1,2}(?:st|nd|rd|th)?)', re.IGNORECASE),
            'time': re.compile(r'\b(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?|\d{1,2}\s*(?:AM|PM|am|pm))', re.IGNORECASE),
            'topic': re.compile(r'(?:re:|subject:|regarding:)\s*([^\n\r]{1,50})', re.IGNORECASE),
            'doc': re.compile(r'\b(document|file|report|proposal|contract)s?\b', re.IGNORECASE),
            'link': re.compile(r'(https?://[^\s]+)', re.IGNORECASE),
        }

    def _initialize_templates(self) -> Dict:
        """Initialize ultra-fast template buckets with 3 variants each"""
        return {
            'payment': {
                'confirm_short': {
                    'title': 'Quick Payment Fix',
                    'template': 'Thank you for the alert. I will update my payment method immediately.',
                    'follow_up_questions': []
                },
                'clarify_one_thing': {
                    'title': 'Payment Issue - Need Details',
                    'template': 'I received the payment notification. Which specific payment method failed so I can update the correct one?',
                    'follow_up_questions': ['Which payment method needs updating?']
                },
                'proactive_next_step': {
                    'title': 'Payment Resolution Plan',
                    'template': 'I will update my payment information now and confirm once the payment processes successfully. You should see the update within the next hour.',
                    'follow_up_questions': []
                }
            },
            'reschedule': {
                'confirm_short': {
                    'title': 'Reschedule Confirmed',
                    'template': 'Yes, I can reschedule. Please send the new time that works best.',
                    'follow_up_questions': []
                },
                'clarify_one_thing': {
                    'title': 'Reschedule - Need Timeframe',
                    'template': 'I can definitely reschedule. What timeframe are you thinking?',
                    'follow_up_questions': ['What dates/times work for you?']
                },
                'proactive_next_step': {
                    'title': 'Reschedule Options',
                    'template': 'I can reschedule. I have availability {date} or {date} at {time}. Let me know which works better.',
                    'follow_up_questions': []
                }
            },
            'confirm': {
                'confirm_short': {
                    'title': 'Confirmed',
                    'template': 'Confirmed. See you then.',
                    'follow_up_questions': []
                },
                'clarify_one_thing': {
                    'title': 'Confirmation - Quick Check',
                    'template': 'Confirmed. Just to double-check - is this {time} {date}?',
                    'follow_up_questions': ['Time and date correct?']
                },
                'proactive_next_step': {
                    'title': 'Confirmed with Prep',
                    'template': 'Confirmed. I will prepare {doc} beforehand and send any questions if they come up.',
                    'follow_up_questions': []
                }
            },
            'availability': {
                'confirm_short': {
                    'title': 'Available',
                    'template': 'Yes, I am available during that time.',
                    'follow_up_questions': []
                },
                'clarify_one_thing': {
                    'title': 'Availability Check',
                    'template': 'I am generally available then. How long should I block out?',
                    'follow_up_questions': ['What is the expected duration?']
                },
                'proactive_next_step': {
                    'title': 'Availability with Options',
                    'template': 'I am available {date} at {time} or {time}. I can also do {date} if that works better.',
                    'follow_up_questions': []
                }
            },
            'interview': {
                'confirm_short': {
                    'title': 'Interview Confirmed',
                    'template': 'Thank you for the interview opportunity. I confirm my attendance.',
                    'follow_up_questions': []
                },
                'clarify_one_thing': {
                    'title': 'Interview - Format Question',
                    'template': 'Thank you for the interview invitation. Will this be in-person or virtual?',
                    'follow_up_questions': ['What is the interview format?']
                },
                'proactive_next_step': {
                    'title': 'Interview Preparation',
                    'template': 'I confirm the interview and will prepare thoroughly. I will also send my updated portfolio beforehand.',
                    'follow_up_questions': []
                }
            },
            'bank': {
                'confirm_short': {
                    'title': 'Will Review',
                    'template': 'Thank you for the notification. I will review the offers.',
                    'follow_up_questions': []
                },
                'clarify_one_thing': {
                    'title': 'Bank Offers - Quick Question',
                    'template': 'Thanks for the update. Are there any time-sensitive offers I should prioritize?',
                    'follow_up_questions': ['Any urgent offers to activate?']
                },
                'proactive_next_step': {
                    'title': 'Bank Offers Review',
                    'template': 'I will review the offers today and activate the relevant cashback deals. I will reply if I have questions.',
                    'follow_up_questions': []
                }
            },
            'follow_up': {
                'confirm_short': {
                    'title': 'Thanks for Following Up',
                    'template': 'Thank you for checking in. Everything is progressing well.',
                    'follow_up_questions': []
                },
                'clarify_one_thing': {
                    'title': 'Follow-up Status',
                    'template': 'Thanks for following up. Which specific item did you want an update on?',
                    'follow_up_questions': ['Which project/item needs an update?']
                },
                'proactive_next_step': {
                    'title': 'Status Update',
                    'template': 'Good timing for a follow-up. I will send a detailed status update by end of day.',
                    'follow_up_questions': []
                }
            },
            'thank': {
                'confirm_short': {
                    'title': 'You are Welcome',
                    'template': 'You are very welcome. Happy to help.',
                    'follow_up_questions': []
                },
                'clarify_one_thing': {
                    'title': 'Thanks - Anything Else?',
                    'template': 'You are welcome! Is there anything else I can help with?',
                    'follow_up_questions': ['Need help with anything else?']
                },
                'proactive_next_step': {
                    'title': 'Thanks and Next',
                    'template': 'You are welcome! I will keep you updated as things progress.',
                    'follow_up_questions': []
                }
            }
        },
            'bank_offers': {
                'high': [
                    {
                        'type': 'interested_review',
                        'subject': 'Re: {original_subject} - Will Review Offers',
                        'tone': 'professional',
                        'body': '''Thank you for the BankAmeriDeals notification.

I will review the available offers within the next 24 hours and activate any that are relevant.

I appreciate you keeping me informed about these opportunities.

Best regards'''
                    },
                    {
                        'type': 'quick_acknowledge',
                        'subject': 'Re: {original_subject} - Checking Now',
                        'tone': 'casual',
                        'body': '''Thanks for the update on the new deals!

I'll check them out today and activate the ones I can use.

Appreciate the notification.'''
                    },
                    {
                        'type': 'detailed_request',
                        'subject': 'Re: {original_subject} - Request for Summary',
                        'tone': 'formal',
                        'body': '''Thank you for the BankAmeriDeals update.

Could you please provide a summary of the most valuable offers currently available?

I'm particularly interested in cashback deals for everyday purchases.

Thank you for your assistance.

Best regards'''
                    }
                ]
            },
            'meeting_invitation': {
                'urgent': [
                    {
                        'type': 'accept_enthusiastic',
                        'subject': 'Re: {original_subject} - Confirmed!',
                        'tone': 'enthusiastic',
                        'body': '''Thank you for the meeting invitation!

I confirm my attendance and look forward to our discussion.

Please let me know if you need anything from me in preparation.

Best regards'''
                    },
                    {
                        'type': 'accept_professional',
                        'subject': 'Re: {original_subject} - Meeting Confirmed',
                        'tone': 'professional',
                        'body': '''I confirm my availability for the scheduled meeting.

I will join at the specified time and location.

Please send any agenda items or preparation materials if available.

Best regards'''
                    },
                    {
                        'type': 'tentative_questions',
                        'subject': 'Re: {original_subject} - Questions About Meeting',
                        'tone': 'professional',
                        'body': '''Thank you for the meeting invitation.

Could you please confirm:
- The expected duration of the meeting
- Main topics to be discussed
- Any materials I should prepare

I look forward to our conversation.

Best regards'''
                    }
                ]
            },
            'statement_notification': {
                'normal': [
                    {
                        'type': 'acknowledge_review',
                        'subject': 'Re: {original_subject} - Will Review',
                        'tone': 'professional',
                        'body': '''Thank you for the statement notification.

I will review the statement and contact you if I have any questions.

Best regards'''
                    },
                    {
                        'type': 'no_response_needed',
                        'subject': 'Re: {original_subject}',
                        'tone': 'minimal',
                        'body': '''Received. Thank you.'''
                    },
                    {
                        'type': 'automatic_payment',
                        'subject': 'Re: {original_subject} - Automatic Payment Confirmed',
                        'tone': 'professional',
                        'body': '''Thank you for the statement notification.

My automatic payment is set up and will process on the due date.

Please confirm if any action is needed on my part.

Best regards'''
                    }
                ]
            },
            'general': {
                'normal': [
                    {
                        'type': 'acknowledge',
                        'subject': 'Re: {original_subject}',
                        'tone': 'professional',
                        'body': '''Thank you for your email.

I will review this and get back to you shortly.

Best regards'''
                    },
                    {
                        'type': 'quick_thanks',
                        'subject': 'Re: {original_subject}',
                        'tone': 'casual',
                        'body': '''Thanks for the email!

I'll take a look and respond soon.

Best'''
                    },
                    {
                        'type': 'detailed_response',
                        'subject': 'Re: {original_subject} - Response',
                        'tone': 'formal',
                        'body': '''Thank you for reaching out.

I have received your message and will provide a detailed response within 24 hours.

Please let me know if this matter is urgent and requires immediate attention.

Best regards'''
                    }
                ]
            }
        }

    def generate_fast_responses(self, email_data: Dict, classification: Dict) -> List[Dict]:
        """Generate multiple response options instantly based on email content"""

        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        sender = email_data.get('sender', '').lower()
        urgency = classification.get('urgency_level', 'normal')

        # Intelligent email type detection
        email_type = self._detect_email_type(subject, body, sender)

        # Get templates for this email type and urgency
        templates = self._get_templates_for_type(email_type, urgency)

        # Generate responses from templates
        responses = []
        for template in templates:
            response = {
                'type': template['type'],
                'subject': template['subject'].format(
                    original_subject=email_data.get('subject', 'Your Email')
                ),
                'tone': template['tone'],
                'body': template['body'],
                'confidence': self._calculate_confidence(email_type, template),
                'urgency': urgency,
                'generated_at': datetime.now().isoformat()
            }
            responses.append(response)

        return responses

    def _detect_email_type(self, subject: str, body: str, sender: str) -> str:
        """Intelligent email type detection based on content patterns"""

        content = f"{subject} {body}".lower()

        # Payment-related patterns
        if any(keyword in content for keyword in [
            'payment failed', 'bill payment', 'payment failure', 'declined',
            'payment method', 'billing', 'payment unsuccessful'
        ]):
            return 'payment_failed'

        # Bank offers and deals
        if any(keyword in content for keyword in [
            'bankamerideals', 'bank deal', 'offers', 'cashback', 'rewards',
            'activate', 'deals available', 'special offer'
        ]) and any(bank in sender for bank in ['bank', 'chase', 'wells', 'citi']):
            return 'bank_offers'

        # Meeting invitations
        if any(keyword in content for keyword in [
            'meeting', 'interview', 'call', 'zoom', 'appointment',
            'schedule', 'calendar invite', 'meeting request'
        ]):
            return 'meeting_invitation'

        # Statement notifications
        if any(keyword in content for keyword in [
            'statement', 'monthly statement', 'billing statement',
            'account summary', 'balance', 'statement available'
        ]):
            return 'statement_notification'

        # Default to general
        return 'general'

    def _get_templates_for_type(self, email_type: str, urgency: str) -> List[Dict]:
        """Get appropriate templates based on email type and urgency"""

        if email_type in self.response_templates:
            # Try to get templates for specific urgency level
            if urgency in self.response_templates[email_type]:
                return self.response_templates[email_type][urgency]

            # Fallback to any available urgency level for this type
            for level in ['urgent', 'high', 'normal']:
                if level in self.response_templates[email_type]:
                    return self.response_templates[email_type][level]

        # Fallback to general templates
        return self.response_templates['general']['normal']

    def _calculate_confidence(self, email_type: str, template: Dict) -> float:
        """Calculate confidence score for the response"""

        # Base confidence based on email type match
        base_confidence = 0.9 if email_type != 'general' else 0.7

        # Adjust based on template type
        template_type = template.get('type', '')
        if 'immediate' in template_type or 'urgent' in template_type:
            return min(base_confidence + 0.05, 0.95)
        elif 'professional' in template_type:
            return base_confidence
        else:
            return max(base_confidence - 0.1, 0.6)

    def get_smart_suggestions(self, email_data: Dict) -> Dict:
        """Get smart suggestions including likely actions"""

        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()

        suggestions = {
            'quick_actions': [],
            'likely_response': None,
            'context_hints': []
        }

        # Quick action suggestions
        if 'payment' in f"{subject} {body}":
            suggestions['quick_actions'].append("Update payment method")
            suggestions['quick_actions'].append("Check account balance")
            suggestions['likely_response'] = 'immediate_action'

        if 'meeting' in f"{subject} {body}":
            suggestions['quick_actions'].append("Add to calendar")
            suggestions['quick_actions'].append("Check availability")
            suggestions['likely_response'] = 'accept_professional'

        if 'deal' in f"{subject} {body}" or 'offer' in f"{subject} {body}":
            suggestions['quick_actions'].append("Review offers")
            suggestions['quick_actions'].append("Activate relevant deals")
            suggestions['likely_response'] = 'interested_review'

        # Context hints
        if 'urgent' in f"{subject} {body}":
            suggestions['context_hints'].append("This email appears urgent")

        if any(bank in email_data.get('sender', '').lower() for bank in ['bank', 'chase', 'wells']):
            suggestions['context_hints'].append("Banking/financial email")

        return suggestions

# Test the fast response generator
if __name__ == "__main__":
    generator = FastResponseGenerator()

    # Test with sample emails
    test_emails = [
        {
            'subject': 'A bill payment failed for Game Crate',
            'sender': 'Shopify Billing <billing@shopify.com>',
            'body': 'Your payment for Game Crate subscription has failed. Please update your payment method.'
        },
        {
            'subject': 'Checking in, PAARTH, please review your BankAmeriDeals®',
            'sender': 'Bank of America <bankofamerica@emcom.bankofamerica.com>',
            'body': 'You have new BankAmeriDeals offers available. Review and activate them.'
        }
    ]

    for email in test_emails:
        print(f"\n📧 Testing: {email['subject']}")
        classification = {'urgency_level': 'urgent'}
        responses = generator.generate_fast_responses(email, classification)

        for i, response in enumerate(responses, 1):
            print(f"\n🔹 Option {i}: {response['type']}")
            print(f"Subject: {response['subject']}")
            print(f"Tone: {response['tone']}")
            print(f"Body: {response['body'][:100]}...")