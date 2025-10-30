#!/usr/bin/env python3
"""
Thread Summarizer - Generate concise 2-3 line summaries for email threads
Part of MailMaestro-level intelligence layer
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from openai import OpenAI
from config import config
import sqlite3

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, that's okay

class ThreadSummarizer:
    """Generate and cache thread summaries with LLM intelligence"""
    
    def __init__(self, model_router=None):
        self.client = OpenAI()
        self.model_router = model_router
        self.cache_db = "secure_emails.db"
        
    def summarize_thread(self, thread_id: str, emails: List[Dict], 
                        max_chars: int = 300) -> str:
        """
        Generate concise thread summary
        
        Args:
            thread_id: Gmail thread ID
            emails: List of email dicts with subject, body, sender, date
            max_chars: Maximum characters for summary
            
        Returns:
            String summary (2-3 lines, ≤300 chars)
        """
        try:
            # Check cache first
            cached = self._get_cached_summary(thread_id, emails)
            if cached:
                return cached
                
            # Generate new summary
            summary = self._generate_summary(emails, max_chars)
            
            # Cache the result
            self._cache_summary(thread_id, emails, summary)
            
            return summary
            
        except Exception as e:
            print(f"Error summarizing thread: {e}")
            return self._fallback_summary(emails)
    
    def _generate_summary(self, emails: List[Dict], max_chars: int) -> str:
        """Generate summary using LLM"""
        try:
            # Sort emails by date
            sorted_emails = sorted(emails, key=lambda x: x.get('date', ''))
            
            # Build context from thread
            context = self._build_thread_context(sorted_emails)
            
            # Choose model
            model = "gpt-4o-mini"
            if self.model_router:
                model = self.model_router.choose_model("summarize")
            
            # Create prompt
            prompt = f"""Summarize this email thread in exactly 2-3 lines (max {max_chars} chars).
Focus on the main topic and current status/ask.

Thread context:
{context}

Format:
Line 1: Main topic/subject
Line 2: Current status or outstanding ask
Line 3: (optional) Next action if clear

Keep it concise and actionable."""

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert email summarizer. Generate concise, actionable thread summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Ensure it's within character limit
            if len(summary) > max_chars:
                lines = summary.split('\n')
                summary = '\n'.join(lines[:2])  # Take first 2 lines
                if len(summary) > max_chars:
                    summary = summary[:max_chars-3] + "..."
                    
            return summary
            
        except Exception as e:
            print(f"LLM summarization failed: {e}")
            return self._fallback_summary(emails)
    
    def _build_thread_context(self, emails: List[Dict]) -> str:
        """Build context string from email thread"""
        context_parts = []
        
        for i, email in enumerate(emails[-3:]):  # Last 3 emails
            sender = email.get('sender', 'Unknown')
            subject = email.get('subject', 'No subject')
            body = email.get('body', '')[:500]  # First 500 chars
            
            context_parts.append(f"Email {i+1} from {sender}:")
            context_parts.append(f"Subject: {subject}")
            context_parts.append(f"Content: {body}...")
            context_parts.append("")
            
        return '\n'.join(context_parts)
    
    def _fallback_summary(self, emails: List[Dict]) -> str:
        """Generate basic summary without LLM"""
        if not emails:
            return "Empty conversation"
            
        latest = emails[-1]
        subject = latest.get('subject', 'Email conversation')
        
        # Clean subject
        clean_subject = subject.replace('Re:', '').replace('Fwd:', '').strip()
        
        # Detect intent from body
        body = latest.get('body', '').lower()
        intent = "Discussion ongoing"
        
        if any(word in body for word in ['can you', 'could you', 'please help']):
            intent = "Action requested"
        elif any(word in body for word in ['meeting', 'schedule', 'calendar']):
            intent = "Meeting coordination"
        elif any(word in body for word in ['?', 'question']):
            intent = "Question pending"
        elif any(word in body for word in ['confirm', 'confirmation']):
            intent = "Confirmation needed"
            
        return f"Topic: {clean_subject[:100]}\nStatus: {intent}"
    
    def _get_cached_summary(self, thread_id: str, emails: List[Dict]) -> Optional[str]:
        """Get cached summary if still valid"""
        try:
            conn = sqlite3.connect(self.cache_db)
            
            # Generate hash of email content for cache validation
            content_hash = self._hash_thread_content(emails)
            
            cursor = conn.execute("""
                SELECT summary_text FROM thread_summary_cache 
                WHERE thread_id = ? AND content_hash = ?
                AND updated_at > datetime('now', '-1 hour')
            """, (thread_id, content_hash))
            
            row = cursor.fetchone()
            conn.close()
            
            return row[0] if row else None
            
        except Exception:
            return None
    
    def _cache_summary(self, thread_id: str, emails: List[Dict], summary: str):
        """Cache the generated summary"""
        try:
            conn = sqlite3.connect(self.cache_db)
            
            # Create summary cache table if needed
            conn.execute("""
                CREATE TABLE IF NOT EXISTS thread_summary_cache (
                    thread_id TEXT,
                    content_hash TEXT,
                    summary_text TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (thread_id, content_hash)
                )
            """)
            
            content_hash = self._hash_thread_content(emails)
            
            conn.execute("""
                INSERT OR REPLACE INTO thread_summary_cache 
                (thread_id, content_hash, summary_text, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (thread_id, content_hash, summary))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Failed to cache summary: {e}")
    
    def _hash_thread_content(self, emails: List[Dict]) -> str:
        """Generate hash of thread content for cache validation"""
        content = ""
        for email in emails:
            content += email.get('id', '') + email.get('subject', '') + email.get('date', '')
        return hashlib.md5(content.encode()).hexdigest()

    def batch_summarize_threads(self, threads: Dict[str, List[Dict]]) -> Dict[str, str]:
        """Batch process multiple threads for efficiency"""
        summaries = {}
        
        for thread_id, emails in threads.items():
            try:
                summary = self.summarize_thread(thread_id, emails)
                summaries[thread_id] = summary
            except Exception as e:
                print(f"Failed to summarize thread {thread_id}: {e}")
                summaries[thread_id] = "Failed to summarize"
                
        return summaries