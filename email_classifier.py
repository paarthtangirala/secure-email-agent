import re
import json
from typing import Dict, List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import pickle
from config import config

class EmailClassifier:
    def __init__(self):
        self.classifier = None
        self.load_or_create_classifier()

        # Patterns for promotional/spam detection
        self.promotional_patterns = [
            r'\bunsubscribe\b', r'\bpromo\b', r'\bdeal\b', r'\bsale\b',
            r'\bdiscount\b', r'\boffer\b', r'\bfree\b', r'\bwin\b',
            r'\bclick here\b', r'\bbuy now\b', r'\blimited time\b',
            r'marketing@', r'noreply@', r'no-reply@', r'newsletter@'
        ]

        # Patterns for important personal emails
        self.important_patterns = [
            r'\binterview\b', r'\bmeeting\b', r'\bappointment\b',
            r'\bdeadline\b', r'\burgent\b', r'\bimportant\b',
            r'\bprofessor\b', r'\brecruiter\b', r'\bhr\b',
            r'\.edu$', r'from.*recruiter', r'job.*application'
        ]

    def load_or_create_classifier(self):
        """Load existing classifier or create a new one"""
        classifier_data = config.load_encrypted_json("email_classifier")

        if classifier_data and 'model' in classifier_data:
            try:
                # Decrypt and load the model
                model_bytes = config.decrypt_data(classifier_data['model'].encode('latin-1'))
                self.classifier = pickle.loads(model_bytes.encode('latin-1'))
                return
            except Exception as e:
                print(f"Failed to load classifier: {e}")

        # Create new classifier with basic training data
        self.create_default_classifier()

    def create_default_classifier(self):
        """Create a basic classifier with some default training data"""
        # Basic training data for email classification
        training_texts = [
            "Meeting tomorrow at 3pm in conference room",
            "Interview scheduled for next week",
            "Important project deadline approaching",
            "Professor office hours changed",
            "Job application status update",
            "Unsubscribe from our newsletter click here",
            "50% discount sale limited time offer",
            "Free gift with purchase buy now",
            "Marketing promotion special deal",
            "Newsletter weekly updates and offers"
        ]

        training_labels = [
            "important", "important", "important", "important", "important",
            "promotional", "promotional", "promotional", "promotional", "promotional"
        ]

        self.classifier = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=1000, stop_words='english')),
            ('nb', MultinomialNB())
        ])

        self.classifier.fit(training_texts, training_labels)
        self.save_classifier()

    def save_classifier(self):
        """Save the classifier in encrypted format"""
        try:
            model_bytes = pickle.dumps(self.classifier)
            encrypted_model = config.encrypt_data(model_bytes.decode('latin-1'))

            classifier_data = {
                'model': encrypted_model.decode('latin-1'),
                'version': '1.0'
            }

            config.save_encrypted_json("email_classifier", classifier_data)
        except Exception as e:
            print(f"Failed to save classifier: {e}")

    def classify_email(self, email_data: Dict) -> Dict:
        """Classify an email as important/personal vs promotional/spam"""

        # Extract text content
        subject = email_data.get('subject', '')
        sender = email_data.get('sender', '')
        body = email_data.get('body', '')

        combined_text = f"{subject} {sender} {body}".lower()

        # Rule-based classification first
        rule_based_score = self._rule_based_classify(combined_text, sender)

        # ML-based classification
        ml_prediction = "unknown"
        ml_confidence = 0.5

        if self.classifier:
            try:
                prediction = self.classifier.predict([combined_text])
                probabilities = self.classifier.predict_proba([combined_text])
                ml_prediction = prediction[0]
                ml_confidence = max(probabilities[0])
            except Exception as e:
                print(f"ML classification failed: {e}")

        # Combine rule-based and ML results
        final_classification = self._combine_classifications(
            rule_based_score, ml_prediction, ml_confidence
        )

        return {
            'classification': final_classification['type'],
            'confidence': final_classification['confidence'],
            'reasoning': final_classification['reasoning'],
            'requires_response': self._needs_response(combined_text),
            'urgency_level': self._assess_urgency(combined_text)
        }

    def _rule_based_classify(self, text: str, sender: str) -> Dict:
        """Rule-based classification using patterns"""
        promotional_score = 0
        important_score = 0

        # Check promotional patterns
        for pattern in self.promotional_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                promotional_score += 1

        # Check important patterns
        for pattern in self.important_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                important_score += 1

        # Domain-based scoring
        if re.search(r'\.edu$', sender):
            important_score += 2
        elif re.search(r'(noreply|no-reply|marketing)@', sender):
            promotional_score += 2

        if important_score > promotional_score:
            return {'type': 'important', 'score': important_score}
        elif promotional_score > important_score:
            return {'type': 'promotional', 'score': promotional_score}
        else:
            return {'type': 'uncertain', 'score': 0}

    def _combine_classifications(self, rule_result: Dict, ml_prediction: str, ml_confidence: float) -> Dict:
        """Combine rule-based and ML classifications"""

        if rule_result['type'] == 'important' and rule_result['score'] >= 2:
            return {
                'type': 'important',
                'confidence': 0.9,
                'reasoning': 'Strong rule-based indicators for important email'
            }
        elif rule_result['type'] == 'promotional' and rule_result['score'] >= 2:
            return {
                'type': 'promotional',
                'confidence': 0.9,
                'reasoning': 'Strong rule-based indicators for promotional email'
            }
        elif ml_confidence > 0.7:
            return {
                'type': ml_prediction,
                'confidence': ml_confidence,
                'reasoning': f'High confidence ML prediction: {ml_prediction}'
            }
        else:
            # Default to requiring human review for uncertain cases
            return {
                'type': 'requires_review',
                'confidence': 0.5,
                'reasoning': 'Uncertain classification, requires human review'
            }

    def _needs_response(self, text: str) -> bool:
        """Determine if email likely needs a response"""
        response_patterns = [
            r'\?', r'please respond', r'reply', r'confirm', r'rsvp',
            r'let me know', r'get back to', r'interview', r'meeting'
        ]

        for pattern in response_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _assess_urgency(self, text: str) -> str:
        """Assess the urgency level of the email"""
        urgent_patterns = [
            r'urgent', r'asap', r'immediate', r'deadline', r'today',
            r'emergency', r'critical', r'time sensitive'
        ]

        high_urgency_patterns = [
            r'tomorrow', r'this week', r'soon', r'priority'
        ]

        for pattern in urgent_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return 'urgent'

        for pattern in high_urgency_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return 'high'

        return 'normal'

    def improve_classifier(self, email_data: Dict, correct_classification: str):
        """Improve the classifier with user feedback"""
        text = f"{email_data.get('subject', '')} {email_data.get('body', '')}".lower()

        # This would typically involve retraining, but for simplicity,
        # we'll store feedback for future training
        feedback_data = config.load_encrypted_json("classifier_feedback")

        if 'feedback' not in feedback_data:
            feedback_data['feedback'] = []

        feedback_data['feedback'].append({
            'text': text,
            'correct_label': correct_classification,
            'timestamp': str(pd.Timestamp.now())
        })

        config.save_encrypted_json("classifier_feedback", feedback_data)

        # Retrain if we have enough feedback samples
        if len(feedback_data['feedback']) >= 10:
            self._retrain_classifier(feedback_data['feedback'])

    def _retrain_classifier(self, feedback_samples: List[Dict]):
        """Retrain classifier with user feedback"""
        try:
            texts = [sample['text'] for sample in feedback_samples[-50:]]  # Use last 50 samples
            labels = [sample['correct_label'] for sample in feedback_samples[-50:]]

            self.classifier.fit(texts, labels)
            self.save_classifier()

            print(f"Classifier retrained with {len(texts)} samples")
        except Exception as e:
            print(f"Failed to retrain classifier: {e}")