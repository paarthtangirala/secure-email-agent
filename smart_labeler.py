#!/usr/bin/env python3
"""
Smart Labeler - Multi-label email classifier for intelligent inbox organization
Part of MailMaestro-level intelligence layer
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Set, Optional
from openai import OpenAI
import sqlite3
from config import config

class SmartLabeler:
    """Multi-label email classifier with pattern recognition and ML"""
    
    def __init__(self, model_router=None):
        self.client = OpenAI()
        self.model_router = model_router
        self.db_path = "secure_emails.db"
        
        # Predefined label categories
        self.label_categories = {
            "meeting": {
                "keywords": ["meeting", "call", "zoom", "teams", "schedule", "appointment", "sync"],
                "patterns": [r"meeting", r"let's schedule", r"calendar invite", r"zoom link"],
                "priority": "high"
            },
            "billing": {
                "keywords": ["invoice", "payment", "bill", "receipt", "charge", "subscription", "refund"],
                "patterns": [r"\$\d+", r"invoice #", r"payment due", r"billing"],
                "priority": "high"
            },
            "follow_up": {
                "keywords": ["follow up", "checking in", "reminder", "following up", "just following"],
                "patterns": [r"following up", r"checking on", r"any update"],
                "priority": "medium"
            },
            "offer": {
                "keywords": ["offer", "proposal", "opportunity", "partnership", "collaboration", "deal"],
                "patterns": [r"we'd like to", r"interested in", r"proposal", r"partnership"],
                "priority": "high"
            },
            "support": {
                "keywords": ["help", "issue", "problem", "bug", "error", "trouble", "assistance"],
                "patterns": [r"having trouble", r"need help", r"issue with", r"error"],
                "priority": "high"
            },
            "newsletter": {
                "keywords": ["newsletter", "update", "announcement", "unsubscribe", "weekly"],
                "patterns": [r"newsletter", r"unsubscribe", r"weekly update"],
                "priority": "low"
            },
            "urgent": {
                "keywords": ["urgent", "asap", "immediately", "critical", "emergency", "deadline"],
                "patterns": [r"urgent", r"asap", r"immediate", r"critical"],
                "priority": "urgent"
            },
            "social": {
                "keywords": ["congrats", "congratulations", "birthday", "holiday", "welcome"],
                "patterns": [r"congratulations", r"happy birthday", r"welcome"],
                "priority": "low"
            },
            "travel": {
                "keywords": ["flight", "hotel", "travel", "trip", "itinerary", "booking"],
                "patterns": [r"flight", r"booking confirmation", r"itinerary"],
                "priority": "medium"
            },
            "general": {
                "keywords": [],
                "patterns": [],
                "priority": "medium"
            }
        }
        
        self._initialize_label_storage()
    
    def _initialize_label_storage(self):
        """Initialize database table for storing email labels"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS email_labels (
                    email_id TEXT,
                    label TEXT,
                    confidence REAL,
                    source TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (email_id, label)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_email_labels_email 
                ON email_labels (email_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_email_labels_label 
                ON email_labels (label)
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error initializing label storage: {e}")
    
    def classify_email(self, email_data: Dict) -> List[Dict]:
        """
        Classify email with multiple labels
        
        Args:
            email_data: Dict with id, subject, body, sender, etc.
            
        Returns:
            List of label dicts: [{"label": str, "confidence": float, "source": str}]
        """
        try:
            email_id = email_data.get('id')
            subject = email_data.get('subject', '')
            body = email_data.get('body', '')
            sender = email_data.get('sender', '')
            
            # Combine text for analysis
            full_text = f"{subject} {body}".lower()
            
            # Pattern-based classification (fast)
            pattern_labels = self._classify_by_patterns(full_text, sender)
            
            # LLM-based classification (comprehensive)
            llm_labels = self._classify_by_llm(email_data)
            
            # Merge and rank labels
            final_labels = self._merge_classifications(pattern_labels, llm_labels)
            
            # Store labels in database
            self._store_labels(email_id, final_labels)
            
            return final_labels
            
        except Exception as e:
            print(f"Error classifying email: {e}")
            return [{"label": "general", "confidence": 0.5, "source": "fallback"}]
    
    def _classify_by_patterns(self, text: str, sender: str) -> List[Dict]:
        """Fast pattern-based classification"""
        labels = []
        
        for label_name, config in self.label_categories.items():
            if label_name == "general":
                continue
                
            confidence = 0.0
            
            # Check keywords
            keyword_matches = sum(1 for keyword in config["keywords"] if keyword in text)
            if keyword_matches > 0:
                confidence += min(keyword_matches * 0.3, 0.7)
            
            # Check patterns
            pattern_matches = sum(1 for pattern in config["patterns"] 
                                if re.search(pattern, text, re.IGNORECASE))
            if pattern_matches > 0:
                confidence += min(pattern_matches * 0.4, 0.8)
            
            # Sender-based adjustments
            confidence = self._adjust_for_sender(confidence, label_name, sender)
            
            if confidence >= 0.3:
                labels.append({
                    "label": label_name,
                    "confidence": min(confidence, 1.0),
                    "source": "pattern"
                })
        
        return labels
    
    def _classify_by_llm(self, email_data: Dict) -> List[Dict]:
        """LLM-based comprehensive classification"""
        try:
            subject = email_data.get('subject', '')
            body = email_data.get('body', '')[:2000]  # Limit for cost
            sender = email_data.get('sender', '')
            
            # Choose model
            model = "gpt-4o-mini"
            if self.model_router:
                model = self.model_router.choose_model("classify")
            
            # Available labels
            label_names = [name for name in self.label_categories.keys() if name != "general"]
            
            prompt = f"""Classify this email with appropriate labels. Return ONLY valid JSON array.

From: {sender}
Subject: {subject}

Body:
{body}

Available labels: {', '.join(label_names)}

Classify with confidence scores. Return format:
[
  {{"label": "meeting", "confidence": 0.9}},
  {{"label": "urgent", "confidence": 0.7}}
]

Rules:
- Only use labels from the available list
- Confidence: 0.0-1.0 (only include if >= 0.5)
- Multiple labels are allowed
- Return empty array [] if no strong matches
- Must be valid JSON"""

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert email classifier. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.2
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Clean JSON response (remove markdown code blocks)
            if response_text.startswith("```json"):
                response_text = response_text[7:]  # Remove ```json
            if response_text.startswith("```"):
                response_text = response_text[3:]   # Remove ```
            if response_text.endswith("```"):
                response_text = response_text[:-3]  # Remove ending ```
            response_text = response_text.strip()
            
            try:
                labels = json.loads(response_text)
                if isinstance(labels, list):
                    # Add source
                    for label in labels:
                        label["source"] = "llm"
                    return labels
            except json.JSONDecodeError:
                print(f"Invalid JSON from LLM: {response_text}")
                
            return []
            
        except Exception as e:
            print(f"LLM classification failed: {e}")
            return []
    
    def _adjust_for_sender(self, base_confidence: float, label: str, sender: str) -> float:
        """Adjust confidence based on sender patterns"""
        sender_lower = sender.lower()
        
        # Newsletter detection
        if label == "newsletter":
            newsletter_indicators = ["newsletter", "noreply", "marketing", "updates", "news"]
            if any(indicator in sender_lower for indicator in newsletter_indicators):
                return min(base_confidence + 0.3, 1.0)
        
        # Billing detection
        if label == "billing":
            billing_senders = ["billing", "invoice", "accounting", "payments", "finance"]
            if any(word in sender_lower for word in billing_senders):
                return min(base_confidence + 0.4, 1.0)
        
        # Support detection
        if label == "support":
            support_indicators = ["support", "help", "noreply", "customer"]
            if any(indicator in sender_lower for indicator in support_indicators):
                return min(base_confidence + 0.2, 1.0)
        
        return base_confidence
    
    def _merge_classifications(self, pattern_labels: List[Dict], 
                             llm_labels: List[Dict]) -> List[Dict]:
        """Merge pattern and LLM classifications"""
        merged = {}
        
        # Start with LLM labels (higher quality)
        for label_data in llm_labels:
            label = label_data["label"]
            merged[label] = label_data
        
        # Add pattern labels that don't conflict
        for label_data in pattern_labels:
            label = label_data["label"]
            if label not in merged:
                merged[label] = label_data
            else:
                # Take higher confidence
                if label_data["confidence"] > merged[label]["confidence"]:
                    # Keep LLM source but update confidence
                    merged[label]["confidence"] = max(
                        merged[label]["confidence"], 
                        label_data["confidence"]
                    )
                    merged[label]["source"] = "hybrid"
        
        # Convert back to list and sort by confidence
        result = list(merged.values())
        result.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Add general label if no strong labels
        if not result or max(label["confidence"] for label in result) < 0.5:
            result.append({"label": "general", "confidence": 0.6, "source": "fallback"})
        
        return result[:5]  # Limit to top 5 labels
    
    def _store_labels(self, email_id: str, labels: List[Dict]):
        """Store labels in database"""
        if not email_id or not labels:
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Clear existing labels for this email
            conn.execute("DELETE FROM email_labels WHERE email_id = ?", (email_id,))
            
            # Insert new labels
            for label_data in labels:
                conn.execute("""
                    INSERT INTO email_labels (email_id, label, confidence, source)
                    VALUES (?, ?, ?, ?)
                """, (
                    email_id,
                    label_data["label"],
                    label_data["confidence"],
                    label_data["source"]
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error storing labels: {e}")
    
    def get_email_labels(self, email_id: str) -> List[Dict]:
        """Get stored labels for an email"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("""
                SELECT label, confidence, source, created_at
                FROM email_labels
                WHERE email_id = ?
                ORDER BY confidence DESC
            """, (email_id,))
            
            labels = []
            for row in cursor.fetchall():
                labels.append({
                    "label": row[0],
                    "confidence": row[1],
                    "source": row[2],
                    "created_at": row[3]
                })
            
            conn.close()
            return labels
            
        except Exception as e:
            print(f"Error getting labels: {e}")
            return []
    
    def get_emails_by_label(self, label: str, limit: int = 50) -> List[str]:
        """Get email IDs with specific label"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("""
                SELECT email_id, confidence
                FROM email_labels
                WHERE label = ?
                ORDER BY confidence DESC, created_at DESC
                LIMIT ?
            """, (label, limit))
            
            email_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            return email_ids
            
        except Exception as e:
            print(f"Error getting emails by label: {e}")
            return []
    
    def get_label_statistics(self) -> Dict:
        """Get statistics about label usage"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Label counts
            cursor = conn.execute("""
                SELECT label, COUNT(*) as count, AVG(confidence) as avg_confidence
                FROM email_labels
                GROUP BY label
                ORDER BY count DESC
            """)
            
            label_stats = {}
            for row in cursor.fetchall():
                label_stats[row[0]] = {
                    "count": row[1],
                    "avg_confidence": round(row[2], 2)
                }
            
            # Total emails labeled
            cursor = conn.execute("SELECT COUNT(DISTINCT email_id) FROM email_labels")
            total_labeled = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "total_emails_labeled": total_labeled,
                "label_distribution": label_stats,
                "most_common_label": max(label_stats.items(), key=lambda x: x[1]["count"])[0] if label_stats else None
            }
            
        except Exception as e:
            print(f"Error getting label statistics: {e}")
            return {}

    def batch_classify_emails(self, emails: List[Dict]) -> Dict[str, List[Dict]]:
        """Classify multiple emails efficiently"""
        results = {}
        
        for email in emails:
            email_id = email.get('id')
            if email_id:
                labels = self.classify_email(email)
                results[email_id] = labels
        
        return results
    
    def suggest_custom_labels(self, emails: List[Dict]) -> List[str]:
        """Suggest custom labels based on email patterns"""
        # Analyze frequent terms not covered by existing labels
        all_text = []
        for email in emails:
            text = f"{email.get('subject', '')} {email.get('body', '')}"
            all_text.append(text.lower())
        
        # Simple frequency analysis (could be enhanced with NLP)
        combined_text = ' '.join(all_text)
        words = re.findall(r'\b\w{4,}\b', combined_text)
        
        # Filter out common words and existing labels
        common_words = {'that', 'with', 'have', 'this', 'will', 'from', 'they', 'been', 'your'}
        existing_labels = set(self.label_categories.keys())
        
        word_freq = {}
        for word in words:
            if word not in common_words and word not in existing_labels:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return top frequent terms as label suggestions
        suggestions = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        return [word for word, freq in suggestions if freq >= 3]