import re
import json
import openai
from typing import Dict, List, Optional
from datetime import datetime
from config import config

class ResponseGenerator:
    def __init__(self):
        # Initialize OpenAI client (you'll need to set your API key)
        self.client = None
        self._setup_openai()

        # Response templates for common scenarios
        self.templates = {
            'interview_confirmation': {
                'subject': 'Re: {original_subject}',
                'tone': 'professional',
                'template': '''Thank you for the interview invitation. I am available at the proposed time and look forward to our discussion.

Best regards,
[Your name]'''
            },
            'meeting_acceptance': {
                'subject': 'Re: {original_subject}',
                'tone': 'professional',
                'template': '''Thank you for the meeting invitation. I confirm my attendance.

Please let me know if you need anything from me in preparation.

Best regards,
[Your name]'''
            },
            'polite_decline': {
                'subject': 'Re: {original_subject}',
                'tone': 'polite',
                'template': '''Thank you for your message. Unfortunately, I won't be able to {action} at this time.

I appreciate your understanding.

Best regards,
[Your name]'''
            },
            'request_more_info': {
                'subject': 'Re: {original_subject}',
                'tone': 'professional',
                'template': '''Thank you for your email. Could you please provide more information about {topic}?

I look forward to hearing from you.

Best regards,
[Your name]'''
            }
        }

        # Response patterns for different email types
        self.response_patterns = {
            'interview': ['interview', 'candidate', 'position', 'role', 'hiring'],
            'meeting': ['meeting', 'discussion', 'call', 'conference'],
            'appointment': ['appointment', 'schedule', 'available'],
            'request': ['request', 'need', 'please', 'could you'],
            'information': ['information', 'details', 'clarification']
        }

    def _setup_openai(self):
        """Setup OpenAI client with API key"""
        try:
            # Try to load API key from encrypted storage
            api_settings = config.load_encrypted_json("api_settings")

            if 'openai_api_key' in api_settings:
                openai.api_key = api_settings['openai_api_key']
                self.client = openai.OpenAI(api_key=api_settings['openai_api_key'])
            else:
                print("OpenAI API key not found. AI responses will be template-based only.")
        except Exception as e:
            print(f"Failed to setup OpenAI: {e}")

    def set_openai_key(self, api_key: str):
        """Set OpenAI API key securely"""
        api_settings = config.load_encrypted_json("api_settings")
        api_settings['openai_api_key'] = api_key
        config.save_encrypted_json("api_settings", api_settings)

        openai.api_key = api_key
        self.client = openai.OpenAI(api_key=api_key)

    def generate_response_suggestions(self, email_data: Dict, classification: Dict) -> List[Dict]:
        """Generate response suggestions for an email"""
        suggestions = []

        # Only generate responses for important/personal emails that need responses
        if classification['classification'] != 'important' or not classification.get('requires_response', False):
            return suggestions

        # Get email context
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        sender = email_data.get('sender', '')

        # Determine response type
        response_type = self._determine_response_type(subject, body)

        # Generate template-based responses
        template_responses = self._generate_template_responses(email_data, response_type)
        suggestions.extend(template_responses)

        # Generate AI-powered responses if available
        if self.client:
            ai_responses = self._generate_ai_responses(email_data, classification)
            suggestions.extend(ai_responses)

        # Rank and return top suggestions
        return self._rank_suggestions(suggestions, email_data)

    def _determine_response_type(self, subject: str, body: str) -> str:
        """Determine the type of response needed"""
        combined_text = f"{subject} {body}".lower()

        # Check for specific patterns
        for response_type, patterns in self.response_patterns.items():
            for pattern in patterns:
                if pattern in combined_text:
                    return response_type

        return 'general'

    def _generate_template_responses(self, email_data: Dict, response_type: str) -> List[Dict]:
        """Generate template-based response suggestions"""
        suggestions = []
        subject = email_data.get('subject', '')
        body = email_data.get('body', '').lower()

        # Interview-related responses
        if response_type == 'interview' or 'interview' in body:
            # Acceptance
            suggestions.append({
                'type': 'acceptance',
                'subject': f"Re: {subject}",
                'body': self.templates['interview_confirmation']['template'],
                'tone': 'professional',
                'confidence': 0.8,
                'reasoning': 'Standard interview confirmation response'
            })

            # Request for more details
            suggestions.append({
                'type': 'request_info',
                'subject': f"Re: {subject}",
                'body': '''Thank you for the interview invitation. Could you please provide:

- The interview format (in-person, video call, phone)
- Duration of the interview
- Any materials I should prepare

I look forward to hearing from you.

Best regards,
[Your name]''',
                'tone': 'professional',
                'confidence': 0.7,
                'reasoning': 'Requests additional interview details'
            })

        # Meeting-related responses
        elif response_type == 'meeting' or any(word in body for word in ['meeting', 'call', 'discussion']):
            suggestions.append({
                'type': 'acceptance',
                'subject': f"Re: {subject}",
                'body': self.templates['meeting_acceptance']['template'],
                'tone': 'professional',
                'confidence': 0.8,
                'reasoning': 'Standard meeting acceptance response'
            })

            # Alternative time suggestion
            if 'available' in body or 'schedule' in body:
                suggestions.append({
                    'type': 'alternative',
                    'subject': f"Re: {subject}",
                    'body': '''Thank you for reaching out. The proposed time doesn't work for me, but I'm available:

- [Alternative time slot 1]
- [Alternative time slot 2]
- [Alternative time slot 3]

Please let me know what works best for you.

Best regards,
[Your name]''',
                    'tone': 'professional',
                    'confidence': 0.6,
                    'reasoning': 'Suggests alternative meeting times'
                })

        # General professional response
        else:
            suggestions.append({
                'type': 'acknowledgment',
                'subject': f"Re: {subject}",
                'body': '''Thank you for your email. I have received your message and will review it carefully.

I will get back to you shortly with a detailed response.

Best regards,
[Your name]''',
                'tone': 'professional',
                'confidence': 0.6,
                'reasoning': 'General acknowledgment response'
            })

        return suggestions

    def _generate_ai_responses(self, email_data: Dict, classification: Dict) -> List[Dict]:
        """Generate AI-powered response suggestions"""
        suggestions = []

        if not self.client:
            return suggestions

        try:
            # Prepare context for AI
            context = self._prepare_ai_context(email_data, classification)

            # Generate response using OpenAI
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a professional email assistant. Generate appropriate email response suggestions based on the context provided. Consider the tone, urgency, and type of email when crafting responses.

Provide 2-3 different response options with varying tones (professional, friendly, brief). Each response should be appropriate for the context and sender relationship."""
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                max_tokens=1000,
                temperature=0.7
            )

            ai_content = response.choices[0].message.content

            # Parse AI response into suggestions
            ai_suggestions = self._parse_ai_response(ai_content, email_data)
            suggestions.extend(ai_suggestions)

        except Exception as e:
            print(f"Error generating AI responses: {e}")

        return suggestions

    def _prepare_ai_context(self, email_data: Dict, classification: Dict) -> str:
        """Prepare context for AI response generation"""
        context = f"""
Email Details:
- Subject: {email_data.get('subject', '')}
- From: {email_data.get('sender', '')}
- Classification: {classification['classification']}
- Urgency: {classification.get('urgency_level', 'normal')}
- Requires Response: {classification.get('requires_response', False)}

Email Content:
{email_data.get('body', '')[:1000]}

Please generate appropriate response suggestions considering:
1. The professional relationship with the sender
2. The urgency and context of the email
3. Appropriate tone and formality level
4. Any action items or requests mentioned

Generate 2-3 response options with different approaches (e.g., accepting, requesting more information, politely declining).
"""
        return context

    def _parse_ai_response(self, ai_content: str, email_data: Dict) -> List[Dict]:
        """Parse AI-generated response into structured suggestions"""
        suggestions = []

        # Split the AI response into individual suggestions
        # This is a simplified parser - you might want more sophisticated parsing
        response_sections = re.split(r'(?:Option \d+|Response \d+|Suggestion \d+):', ai_content)

        for i, section in enumerate(response_sections[1:], 1):  # Skip first empty section
            if section.strip():
                suggestions.append({
                    'type': 'ai_generated',
                    'subject': f"Re: {email_data.get('subject', '')}",
                    'body': section.strip(),
                    'tone': 'ai_determined',
                    'confidence': 0.7,
                    'reasoning': f'AI-generated response option {i}'
                })

        return suggestions

    def _rank_suggestions(self, suggestions: List[Dict], email_data: Dict) -> List[Dict]:
        """Rank suggestions by relevance and appropriateness"""
        # Simple ranking based on confidence scores and email context
        ranked = sorted(suggestions, key=lambda x: x.get('confidence', 0.5), reverse=True)

        # Add ranking information
        for i, suggestion in enumerate(ranked):
            suggestion['rank'] = i + 1

        return ranked[:5]  # Return top 5 suggestions

    def customize_response(self, suggestion: Dict, user_preferences: Dict) -> Dict:
        """Customize a response suggestion based on user preferences"""
        customized = suggestion.copy()

        # Apply user's signature if available
        if 'signature' in user_preferences:
            customized['body'] = customized['body'].replace('[Your name]', user_preferences['signature'])

        # Adjust tone if user has preferences
        if 'preferred_tone' in user_preferences:
            tone = user_preferences['preferred_tone']
            if tone == 'casual' and 'Best regards' in customized['body']:
                customized['body'] = customized['body'].replace('Best regards,', 'Thanks,')
            elif tone == 'formal' and 'Thanks,' in customized['body']:
                customized['body'] = customized['body'].replace('Thanks,', 'Best regards,')

        return customized

    def save_response_feedback(self, suggestion: Dict, was_used: bool, user_rating: Optional[int] = None):
        """Save feedback on response suggestions for improvement"""
        feedback_data = config.load_encrypted_json("response_feedback")

        if 'feedback' not in feedback_data:
            feedback_data['feedback'] = []

        feedback_entry = {
            'timestamp': datetime.now().isoformat(),
            'suggestion_type': suggestion.get('type'),
            'was_used': was_used,
            'user_rating': user_rating,
            'confidence': suggestion.get('confidence'),
            'reasoning': suggestion.get('reasoning')
        }

        feedback_data['feedback'].append(feedback_entry)
        config.save_encrypted_json("response_feedback", feedback_data)

    def get_user_preferences(self) -> Dict:
        """Load user preferences for response generation"""
        return config.load_encrypted_json("user_preferences")

    def save_user_preferences(self, preferences: Dict):
        """Save user preferences for response generation"""
        config.save_encrypted_json("user_preferences", preferences)