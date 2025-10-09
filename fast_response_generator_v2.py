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
        self.regex_buckets = self._compile_regex_buckets()
        self.slot_patterns = self._compile_slot_patterns()
        self.response_templates = self._initialize_template_buckets()

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

    def _initialize_template_buckets(self) -> Dict:
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
                    'template': 'I can reschedule. I have availability {date} or next week at {time}. Let me know which works better.',
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
                    'template': 'Confirmed. Just to double-check - is this {time} on {date}?',
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
                    'template': 'I am available {date} at {time} or the following day. I can also do {date} if that works better.',
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
        }

    def extract_slots(self, text: str) -> Dict[str, str]:
        """Extract slots from email text with safe defaults"""
        slots = {
            'recipient_first': 'there',
            'date': 'soon',
            'time': 'at your convenience',
            'topic': 'this',
            'doc': 'the materials',
            'link': ''
        }

        # Extract first name from sender/recipient
        match = self.slot_patterns['recipient_first'].search(text)
        if match:
            slots['recipient_first'] = match.group(1)

        # Extract date
        match = self.slot_patterns['date'].search(text)
        if match:
            slots['date'] = match.group(1)

        # Extract time
        match = self.slot_patterns['time'].search(text)
        if match:
            slots['time'] = match.group(1)

        # Extract topic from subject/re: lines
        match = self.slot_patterns['topic'].search(text)
        if match:
            slots['topic'] = match.group(1).strip()

        # Extract document references
        match = self.slot_patterns['doc'].search(text)
        if match:
            slots['doc'] = match.group(1)

        return slots

    def detect_archetype(self, text: str) -> str:
        """Ultra-fast archetype detection using precompiled regex"""
        content = text.lower()

        # Score each bucket
        scores = {}
        for bucket_name, pattern in self.regex_buckets.items():
            matches = pattern.findall(content)
            scores[bucket_name] = len(matches)

        # Return highest scoring bucket, default to 'follow_up'
        if scores:
            best_match = max(scores.items(), key=lambda x: x[1])
            if best_match[1] > 0:
                return best_match[0]

        return 'follow_up'  # Safe default

    def fast_templates(self, email_text: str, tone: str = "professional") -> List[Dict]:
        """Generate 3 instant response options ≤100ms"""
        start_time = datetime.now()

        # Ultra-fast archetype detection
        archetype = self.detect_archetype(email_text)

        # Extract slots for templating
        slots = self.extract_slots(email_text)

        # Get template bucket
        templates = self.response_templates.get(archetype, self.response_templates['follow_up'])

        # Generate 3 variants
        responses = []
        for variant_type in ['confirm_short', 'clarify_one_thing', 'proactive_next_step']:
            template = templates[variant_type]

            # Fill slots in template with safe handling
            try:
                filled_body = template['template'].format(**slots)
            except KeyError:
                # Fallback if slot not found
                filled_body = template['template']

            response = {
                'title': template['title'],
                'body': filled_body,
                'follow_up_questions': template['follow_up_questions'],
                'archetype': archetype,
                'variant': variant_type,
                'tone': tone,
                'confidence': 0.9,  # High confidence for template matches
                'generation_time_ms': (datetime.now() - start_time).total_seconds() * 1000
            }
            responses.append(response)

        return responses

    # Legacy method for backward compatibility
    def generate_fast_responses(self, email_data: Dict, classification: Dict) -> List[Dict]:
        """Legacy compatibility method"""
        email_text = email_data.get('subject', '') + ' ' + email_data.get('body', '')
        return self.fast_templates(email_text)

    def get_smart_suggestions(self, email_data: Dict) -> Dict:
        """Legacy compatibility method"""
        return {
            'quick_actions': ['Review email', 'Prepare response', 'Check calendar'],
            'likely_response': 'confirm_short',
            'context_hints': ['Fast template response available']
        }

# Test the ultra-fast response generator
if __name__ == "__main__":
    generator = FastResponseGenerator()

    # Test with sample emails
    test_emails = [
        {
            'text': 'A bill payment failed for Game Crate. Please update your payment method.',
            'expected_archetype': 'payment'
        },
        {
            'text': 'Can we reschedule our meeting from Monday to Wednesday?',
            'expected_archetype': 'reschedule'
        },
        {
            'text': 'Thank you for your help with the project. Really appreciate it!',
            'expected_archetype': 'thank'
        }
    ]

    for test in test_emails:
        print(f"\n📧 Testing: {test['text'][:50]}...")
        start_time = datetime.now()

        responses = generator.fast_templates(test['text'])

        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        detected_archetype = generator.detect_archetype(test['text'])

        print(f"🎯 Detected archetype: {detected_archetype} (expected: {test['expected_archetype']})")
        print(f"⚡ Generation time: {duration_ms:.1f}ms")
        print(f"📝 Generated {len(responses)} response options:")

        for i, response in enumerate(responses, 1):
            print(f"  {i}. {response['title']} ({response['variant']})")
            print(f"     {response['body'][:60]}...")