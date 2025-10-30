#!/usr/bin/env python3
"""
Privacy Guard - PII redaction and privacy protection for email content
Part of MailMaestro security layer
"""

import re
import hashlib
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from cryptography.fernet import Fernet

# Optional AI dependencies with graceful fallback
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PIIDetection:
    """Detected PII information"""
    text: str
    type: str
    start: int
    end: int
    confidence: float
    replacement: str

class PrivacyGuard:
    """Comprehensive PII detection and redaction system"""
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        self.encryption_key = encryption_key or Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
        
        # Load NLP models for advanced PII detection (optional)
        self.nlp = None
        self.ner_pipeline = None
        
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
                self.nlp = None
        
        if TRANSFORMERS_AVAILABLE:
            try:
                self.ner_pipeline = pipeline("ner", 
                                           model="dslim/bert-base-NER",
                                           aggregation_strategy="simple")
            except Exception as e:
                logger.warning(f"Could not load transformers NER pipeline: {e}")
                self.ner_pipeline = None
        
        # PII patterns for regex-based detection
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            'ssn': r'\b(?:\d{3}-?\d{2}-?\d{4})\b',
            'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'date_of_birth': r'\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12][0-9]|3[01])[/-](?:19|20)\d{2}\b',
            'address': r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Place|Pl)\b',
        }
        
        # Sensitive keywords that might indicate PII context
        self.sensitive_keywords = [
            'password', 'pin', 'secret', 'confidential', 'private',
            'ssn', 'social security', 'drivers license', 'passport',
            'bank account', 'routing number', 'credit card', 'cvv',
            'medical record', 'diagnosis', 'prescription'
        ]
        
        # Common names for enhanced detection
        self.common_names = self._load_common_names()
        
    def _load_common_names(self) -> set:
        """Load common first and last names for name detection"""
        # This would typically load from a file or API
        # For demo purposes, using a small subset
        return {
            'john', 'jane', 'michael', 'sarah', 'david', 'jennifer', 
            'robert', 'lisa', 'william', 'ashley', 'james', 'jessica',
            'smith', 'johnson', 'williams', 'brown', 'jones', 'garcia',
            'miller', 'davis', 'rodriguez', 'martinez', 'hernandez'
        }
    
    def detect_pii(self, text: str, confidence_threshold: float = 0.8) -> List[PIIDetection]:
        """
        Comprehensive PII detection using multiple methods
        
        Args:
            text: Input text to analyze
            confidence_threshold: Minimum confidence for detection
            
        Returns:
            List of PIIDetection objects
        """
        detections = []
        
        # 1. Regex-based detection
        regex_detections = self._detect_pii_regex(text)
        detections.extend(regex_detections)
        
        # 2. NLP-based detection
        if self.nlp:
            nlp_detections = self._detect_pii_nlp(text)
            detections.extend(nlp_detections)
        
        # 3. Transformer-based NER detection
        if self.ner_pipeline:
            ner_detections = self._detect_pii_ner(text)
            detections.extend(ner_detections)
        
        # 4. Context-based detection
        context_detections = self._detect_pii_context(text)
        detections.extend(context_detections)
        
        # Filter by confidence and deduplicate
        filtered_detections = self._filter_and_deduplicate(
            detections, confidence_threshold
        )
        
        return filtered_detections
    
    def _detect_pii_regex(self, text: str) -> List[PIIDetection]:
        """Regex-based PII detection"""
        detections = []
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                replacement = self._generate_replacement(pii_type, match.group())
                
                detection = PIIDetection(
                    text=match.group(),
                    type=pii_type,
                    start=match.start(),
                    end=match.end(),
                    confidence=0.9,  # High confidence for regex matches
                    replacement=replacement
                )
                detections.append(detection)
        
        return detections
    
    def _detect_pii_nlp(self, text: str) -> List[PIIDetection]:
        """spaCy NLP-based PII detection"""
        if not self.nlp:
            return []
        
        detections = []
        doc = self.nlp(text)
        
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'GPE', 'MONEY', 'DATE']:
                # Additional validation for person names
                if ent.label_ == 'PERSON':
                    confidence = self._validate_person_name(ent.text)
                else:
                    confidence = 0.7
                
                replacement = self._generate_replacement(ent.label_.lower(), ent.text)
                
                detection = PIIDetection(
                    text=ent.text,
                    type=ent.label_.lower(),
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=confidence,
                    replacement=replacement
                )
                detections.append(detection)
        
        return detections
    
    def _detect_pii_ner(self, text: str) -> List[PIIDetection]:
        """Transformer-based NER detection"""
        if not self.ner_pipeline:
            return []
        
        detections = []
        
        try:
            entities = self.ner_pipeline(text)
            
            for entity in entities:
                # Map entity labels to our PII types
                pii_type = self._map_ner_label(entity['entity_group'])
                
                if pii_type:
                    replacement = self._generate_replacement(pii_type, entity['word'])
                    
                    detection = PIIDetection(
                        text=entity['word'],
                        type=pii_type,
                        start=entity['start'],
                        end=entity['end'],
                        confidence=entity['score'],
                        replacement=replacement
                    )
                    detections.append(detection)
        
        except Exception as e:
            logger.warning(f"NER detection failed: {e}")
        
        return detections
    
    def _detect_pii_context(self, text: str) -> List[PIIDetection]:
        """Context-based PII detection using keyword analysis"""
        detections = []
        text_lower = text.lower()
        
        # Look for sensitive contexts
        for keyword in self.sensitive_keywords:
            if keyword in text_lower:
                # Look for potential PII near the keyword
                keyword_pos = text_lower.find(keyword)
                context_start = max(0, keyword_pos - 50)
                context_end = min(len(text), keyword_pos + len(keyword) + 50)
                context = text[context_start:context_end]
                
                # Look for patterns in this context
                potential_pii = self._extract_context_pii(context, context_start)
                detections.extend(potential_pii)
        
        return detections
    
    def _extract_context_pii(self, context: str, offset: int) -> List[PIIDetection]:
        """Extract PII from sensitive context"""
        detections = []
        
        # Look for quoted strings or values after colons
        patterns = [
            r':\s*"([^"]+)"',  # "value" after colon
            r':\s*([A-Za-z0-9@._-]+)',  # value after colon
            r'"([^"]*(?:password|pin|secret)[^"]*)"'  # quoted sensitive text
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, context, re.IGNORECASE)
            
            for match in matches:
                value = match.group(1)
                
                # Skip if too short or looks like common words
                if len(value) < 3 or value.lower() in ['the', 'and', 'for', 'are']:
                    continue
                
                replacement = self._generate_replacement('sensitive_data', value)
                
                detection = PIIDetection(
                    text=value,
                    type='sensitive_data',
                    start=offset + match.start(1),
                    end=offset + match.end(1),
                    confidence=0.6,
                    replacement=replacement
                )
                detections.append(detection)
        
        return detections
    
    def _validate_person_name(self, name: str) -> float:
        """Validate if detected name is likely a real person name"""
        name_parts = name.lower().split()
        
        # Check against common names
        common_count = sum(1 for part in name_parts if part in self.common_names)
        
        # Basic heuristics
        if len(name_parts) >= 2 and common_count > 0:
            return 0.8
        elif common_count > 0:
            return 0.6
        elif len(name_parts) >= 2 and all(part.isalpha() for part in name_parts):
            return 0.5
        else:
            return 0.3
    
    def _map_ner_label(self, label: str) -> Optional[str]:
        """Map NER labels to our PII types"""
        mapping = {
            'PER': 'person',
            'PERSON': 'person',
            'ORG': 'organization',
            'LOC': 'location',
            'MISC': 'miscellaneous'
        }
        return mapping.get(label.upper())
    
    def _generate_replacement(self, pii_type: str, original_text: str) -> str:
        """Generate appropriate replacement text for PII"""
        replacements = {
            'email': '[EMAIL_REDACTED]',
            'phone': '[PHONE_REDACTED]',
            'ssn': '[SSN_REDACTED]',
            'credit_card': '[CARD_REDACTED]',
            'person': '[NAME_REDACTED]',
            'address': '[ADDRESS_REDACTED]',
            'organization': '[ORG_REDACTED]',
            'date_of_birth': '[DOB_REDACTED]',
            'sensitive_data': '[SENSITIVE_REDACTED]'
        }
        
        # Create a hash-based consistent replacement for some types
        if pii_type in ['person', 'email', 'organization']:
            hash_suffix = hashlib.md5(original_text.encode()).hexdigest()[:4].upper()
            base_replacement = replacements.get(pii_type, '[REDACTED]')
            return f"{base_replacement}_{hash_suffix}"
        
        return replacements.get(pii_type, '[REDACTED]')
    
    def _filter_and_deduplicate(self, detections: List[PIIDetection], 
                               threshold: float) -> List[PIIDetection]:
        """Filter by confidence and remove overlapping detections"""
        # Filter by confidence
        filtered = [d for d in detections if d.confidence >= threshold]
        
        # Sort by confidence (highest first)
        filtered.sort(key=lambda x: x.confidence, reverse=True)
        
        # Remove overlapping detections (keep highest confidence)
        non_overlapping = []
        
        for detection in filtered:
            overlaps = any(
                (detection.start < existing.end and detection.end > existing.start)
                for existing in non_overlapping
            )
            
            if not overlaps:
                non_overlapping.append(detection)
        
        return non_overlapping
    
    def redact_pii(self, text: str, detections: List[PIIDetection] = None) -> Tuple[str, List[PIIDetection]]:
        """
        Redact PII from text
        
        Args:
            text: Original text
            detections: Pre-computed detections (optional)
            
        Returns:
            Tuple of (redacted_text, detections_used)
        """
        if detections is None:
            detections = self.detect_pii(text)
        
        # Sort detections by start position (reverse order for replacement)
        detections_sorted = sorted(detections, key=lambda x: x.start, reverse=True)
        
        redacted_text = text
        
        for detection in detections_sorted:
            redacted_text = (
                redacted_text[:detection.start] +
                detection.replacement +
                redacted_text[detection.end:]
            )
        
        return redacted_text, detections
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
    
    def analyze_privacy_risk(self, text: str) -> Dict:
        """Analyze privacy risk of text content"""
        detections = self.detect_pii(text)
        
        # Calculate risk score
        risk_weights = {
            'ssn': 10,
            'credit_card': 9,
            'email': 5,
            'phone': 6,
            'person': 4,
            'address': 6,
            'sensitive_data': 8
        }
        
        total_risk = sum(
            risk_weights.get(d.type, 3) * d.confidence 
            for d in detections
        )
        
        # Normalize to 0-100 scale
        risk_score = min(100, int(total_risk * 2))
        
        # Categorize risk level
        if risk_score >= 80:
            risk_level = 'HIGH'
        elif risk_score >= 50:
            risk_level = 'MEDIUM'
        elif risk_score >= 20:
            risk_level = 'LOW'
        else:
            risk_level = 'MINIMAL'
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'pii_count': len(detections),
            'pii_types': list(set(d.type for d in detections)),
            'detections': detections,
            'recommendation': self._get_privacy_recommendation(risk_level, detections)
        }
    
    def _get_privacy_recommendation(self, risk_level: str, detections: List[PIIDetection]) -> str:
        """Get privacy protection recommendation"""
        if risk_level == 'HIGH':
            return "High privacy risk detected. Consider redacting PII before sending to external APIs."
        elif risk_level == 'MEDIUM':
            return "Moderate privacy risk. Review detected PII and consider redaction if sharing externally."
        elif risk_level == 'LOW':
            return "Low privacy risk detected. Basic precautions recommended."
        else:
            return "Minimal privacy risk. Standard processing can proceed."

    def create_privacy_report(self, email_data: Dict) -> Dict:
        """Create comprehensive privacy report for email"""
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        
        # Analyze each component
        subject_analysis = self.analyze_privacy_risk(subject)
        body_analysis = self.analyze_privacy_risk(body)
        
        # Combined analysis
        total_detections = subject_analysis['pii_count'] + body_analysis['pii_count']
        max_risk = max(subject_analysis['risk_score'], body_analysis['risk_score'])
        
        all_types = set(subject_analysis['pii_types'] + body_analysis['pii_types'])
        
        return {
            'email_id': email_data.get('id'),
            'timestamp': email_data.get('date_received'),
            'overall_risk_score': max_risk,
            'total_pii_detected': total_detections,
            'pii_types_found': list(all_types),
            'subject_analysis': subject_analysis,
            'body_analysis': body_analysis,
            'processing_safe': max_risk < 70,  # Safe threshold for external API calls
            'redaction_recommended': max_risk >= 50
        }