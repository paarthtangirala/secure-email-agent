#!/usr/bin/env python3
"""
World-class email database system with SQLite and full-text search
Optimized for handling millions of emails with lightning-fast search
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from config import config

class EmailDatabase:
    """High-performance SQLite database for email storage and search"""

    def __init__(self, db_path: str = "secure_emails.db"):
        self.db_path = db_path
        self.connection = None
        self._initialize_database()

    def _get_connection(self):
        """Get database connection with optimizations"""
        if not self.connection:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Enable dict-like access

            # Performance optimizations
            self.connection.execute("PRAGMA journal_mode=WAL")  # Write-ahead logging
            self.connection.execute("PRAGMA synchronous=NORMAL")  # Balance safety/speed
            self.connection.execute("PRAGMA cache_size=10000")  # Large cache
            self.connection.execute("PRAGMA temp_store=memory")  # Use memory for temp storage

        return self.connection

    def _initialize_database(self):
        """Create database tables with indexes for world-class performance"""
        conn = self._get_connection()

        # Main emails table with all metadata
        conn.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id TEXT PRIMARY KEY,
                thread_id TEXT,
                subject TEXT,
                sender TEXT,
                sender_email TEXT,
                recipients TEXT,
                date_received TEXT,
                date_parsed DATETIME,
                body_text TEXT,
                body_html TEXT,
                labels TEXT,
                message_id TEXT,
                in_reply_to TEXT,
                email_references TEXT,
                attachments_count INTEGER DEFAULT 0,
                is_important BOOLEAN DEFAULT 0,
                is_unread BOOLEAN DEFAULT 1,
                classification TEXT,
                confidence REAL,
                urgency_level TEXT,
                requires_response BOOLEAN DEFAULT 0,
                sentiment REAL,
                language TEXT,
                word_count INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Full-text search table for lightning-fast text search
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS emails_fts USING fts5(
                id,
                subject,
                sender,
                body_text,
                content='emails',
                content_rowid='rowid',
                tokenize='porter'
            )
        """)

        # AI responses table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT,
                response_type TEXT,
                subject TEXT,
                body TEXT,
                tone TEXT,
                confidence REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        """)

        # Calendar events extracted from emails
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT,
                title TEXT,
                start_time TEXT,
                end_time TEXT,
                location TEXT,
                description TEXT,
                event_type TEXT,
                confidence REAL,
                google_event_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        """)

        # Attachments table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT,
                filename TEXT,
                file_type TEXT,
                file_size INTEGER,
                attachment_id TEXT,
                is_downloaded BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        """)

        # Thread summary cache for minimal context
        conn.execute("""
            CREATE TABLE IF NOT EXISTS thread_summaries (
                thread_id TEXT,
                last_message_id TEXT,
                summary_line1 TEXT,
                summary_line2 TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (thread_id, last_message_id)
            )
        """)

        # Performance indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_date ON emails (date_received DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails (sender_email)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_thread ON emails (thread_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_important ON emails (is_important)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_classification ON emails (classification)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_urgency ON emails (urgency_level)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_responses_email ON email_responses (email_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_email ON email_events (email_id)")

        # Triggers to keep FTS table in sync
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS emails_fts_insert AFTER INSERT ON emails
            BEGIN
                INSERT INTO emails_fts(id, subject, sender, body_text)
                VALUES (new.id, new.subject, new.sender, new.body_text);
            END
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS emails_fts_update AFTER UPDATE ON emails
            BEGIN
                UPDATE emails_fts SET
                    subject = new.subject,
                    sender = new.sender,
                    body_text = new.body_text
                WHERE id = new.id;
            END
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS emails_fts_delete AFTER DELETE ON emails
            BEGIN
                DELETE FROM emails_fts WHERE id = old.id;
            END
        """)

        conn.commit()

    def store_email(self, email_data: Dict) -> bool:
        """Store email with full metadata and classification"""
        try:
            conn = self._get_connection()

            # Extract sender email from full sender string
            sender_email = self._extract_email(email_data.get('sender', ''))

            # Prepare email record
            email_record = {
                'id': email_data.get('id'),
                'thread_id': email_data.get('thread_id'),
                'subject': email_data.get('subject', ''),
                'sender': email_data.get('sender', ''),
                'sender_email': sender_email,
                'recipients': json.dumps(email_data.get('recipients', [])),
                'date_received': email_data.get('date', ''),
                'date_parsed': datetime.now().isoformat(),
                'body_text': email_data.get('body', ''),
                'body_html': email_data.get('html_body', ''),
                'labels': json.dumps(email_data.get('labels', [])),
                'message_id': email_data.get('message_id', ''),
                'in_reply_to': email_data.get('in_reply_to', ''),
                'email_references': email_data.get('references', ''),
                'attachments_count': len(email_data.get('attachments', [])),
                'word_count': len(email_data.get('body', '').split())
            }

            # Add classification data if available
            classification = email_data.get('classification', {})
            if classification:
                email_record.update({
                    'is_important': 1 if classification.get('classification') == 'important' else 0,
                    'classification': classification.get('classification', ''),
                    'confidence': classification.get('confidence', 0.0),
                    'urgency_level': classification.get('urgency_level', 'normal'),
                    'requires_response': 1 if classification.get('requires_response', False) else 0,
                    'sentiment': classification.get('sentiment', 0.0),
                    'language': classification.get('language', 'en')
                })

            # Use INSERT OR REPLACE to handle duplicates
            placeholders = ', '.join(['?' for _ in email_record.keys()])
            columns = ', '.join(email_record.keys())

            conn.execute(f"""
                INSERT OR REPLACE INTO emails ({columns})
                VALUES ({placeholders})
            """, list(email_record.values()))

            conn.commit()
            return True

        except Exception as e:
            print(f"Error storing email: {e}")
            return False

    def store_responses(self, email_id: str, responses: List[Dict]) -> bool:
        """Store AI-generated responses for an email"""
        try:
            conn = self._get_connection()

            # Clear existing responses
            conn.execute("DELETE FROM email_responses WHERE email_id = ?", (email_id,))

            # Insert new responses
            for response in responses:
                conn.execute("""
                    INSERT INTO email_responses (email_id, response_type, subject, body, tone, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    email_id,
                    response.get('type', ''),
                    response.get('subject', ''),
                    response.get('body', ''),
                    response.get('tone', ''),
                    response.get('confidence', 0.8)
                ))

            conn.commit()
            return True

        except Exception as e:
            print(f"Error storing responses: {e}")
            return False

    def search_emails(self, query: str = "", sender: str = "",
                     days: int = 30, limit: int = 50) -> List[Dict]:
        """Ultra-fast full-text search with filters"""
        try:
            conn = self._get_connection()

            if query:
                # Use FTS for text search
                sql = """
                    SELECT e.*, rank
                    FROM emails_fts
                    JOIN emails e ON emails_fts.id = e.id
                    WHERE emails_fts MATCH ?
                """
                params = [query]

                if sender:
                    sql += " AND e.sender_email LIKE ?"
                    params.append(f"%{sender}%")

            elif sender:
                # Direct search by sender
                sql = """
                    SELECT *, 1.0 as rank
                    FROM emails
                    WHERE sender_email LIKE ?
                """
                params = [f"%{sender}%"]

            else:
                # Recent emails
                sql = """
                    SELECT *, 1.0 as rank
                    FROM emails
                    WHERE 1=1
                """
                params = []

            # Add date filter
            if days:
                sql += " AND date_received >= datetime('now', '-{} days')".format(days)

            sql += " ORDER BY date_received DESC, rank DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            results = []

            for row in cursor.fetchall():
                email = dict(row)
                # Convert JSON fields back to objects
                email['labels'] = json.loads(email.get('labels', '[]'))
                email['recipients'] = json.loads(email.get('recipients', '[]'))
                results.append(email)

            return results

        except Exception as e:
            print(f"Error searching emails: {e}")
            return []

    def get_email_by_id(self, email_id: str) -> Optional[Dict]:
        """Get single email with all related data"""
        try:
            conn = self._get_connection()

            # Get email
            cursor = conn.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
            row = cursor.fetchone()

            if not row:
                return None

            email = dict(row)
            email['labels'] = json.loads(email.get('labels', '[]'))
            email['recipients'] = json.loads(email.get('recipients', '[]'))

            # Get responses
            cursor = conn.execute("""
                SELECT * FROM email_responses WHERE email_id = ?
                ORDER BY created_at DESC
            """, (email_id,))
            email['responses'] = [dict(row) for row in cursor.fetchall()]

            # Get events
            cursor = conn.execute("""
                SELECT * FROM email_events WHERE email_id = ?
                ORDER BY start_time
            """, (email_id,))
            email['events'] = [dict(row) for row in cursor.fetchall()]

            return email

        except Exception as e:
            print(f"Error getting email: {e}")
            return None

    def get_statistics(self) -> Dict:
        """Get comprehensive database statistics"""
        try:
            conn = self._get_connection()

            stats = {}

            # Email counts
            cursor = conn.execute("SELECT COUNT(*) FROM emails")
            stats['total_emails'] = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM emails WHERE is_important = 1")
            stats['important_emails'] = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM emails WHERE requires_response = 1")
            stats['needs_response'] = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM email_responses")
            stats['total_responses'] = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM email_events")
            stats['calendar_events'] = cursor.fetchone()[0]

            # Date ranges
            cursor = conn.execute("""
                SELECT MIN(date_received), MAX(date_received) FROM emails
            """)
            date_range = cursor.fetchone()
            stats['date_range'] = {
                'earliest': date_range[0],
                'latest': date_range[1]
            }

            # Top senders
            cursor = conn.execute("""
                SELECT sender_email, COUNT(*) as count
                FROM emails
                WHERE sender_email IS NOT NULL AND sender_email != ''
                GROUP BY sender_email
                ORDER BY count DESC
                LIMIT 10
            """)
            stats['top_senders'] = [{'sender': row[0], 'count': row[1]}
                                  for row in cursor.fetchall()]

            return stats

        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}

    def optimize_database(self):
        """Optimize database for maximum performance"""
        try:
            conn = self._get_connection()

            # Update statistics
            conn.execute("ANALYZE")

            # Optimize FTS index
            conn.execute("INSERT INTO emails_fts(emails_fts) VALUES('optimize')")

            # Vacuum if needed
            conn.execute("PRAGMA optimize")

            conn.commit()
            print("✅ Database optimized successfully")

        except Exception as e:
            print(f"Error optimizing database: {e}")

    def _extract_email(self, sender_string: str) -> str:
        """Extract email address from sender string"""
        import re
        email_pattern = r'<([^>]+)>|([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        match = re.search(email_pattern, sender_string)
        if match:
            return match.group(1) or match.group(2)
        return sender_string

    def get_latest_email_excerpt(self, message_id: str, limit_chars: int = 2000) -> str:
        """Get excerpt of latest email for Smart-Path context"""
        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT subject, body_text
                FROM emails
                WHERE id = ?
            """, (message_id,))

            row = cursor.fetchone()
            if not row:
                return ""

            subject = row[0] or ""
            body = row[1] or ""
            full_text = f"Subject: {subject}\n\n{body}"

            # Truncate to limit while preserving word boundaries
            if len(full_text) <= limit_chars:
                return full_text

            truncated = full_text[:limit_chars]
            last_space = truncated.rfind(' ')
            if last_space > limit_chars * 0.8:  # Don't cut too much
                truncated = truncated[:last_space]

            return truncated + "..."

        except Exception as e:
            print(f"Error getting email excerpt: {e}")
            return ""

    def get_thread_summary_cached(self, message_id: str, max_chars: int = 280) -> str:
        """Get cached thread summary or generate if missing"""
        try:
            conn = self._get_connection()

            # Get thread_id for this message
            cursor = conn.execute("SELECT thread_id FROM emails WHERE id = ?", (message_id,))
            row = cursor.fetchone()
            if not row:
                return "Email conversation"

            thread_id = row[0]

            # Try to get cached summary
            cursor = conn.execute("""
                SELECT summary_line1, summary_line2
                FROM thread_summaries
                WHERE thread_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
            """, (thread_id,))

            row = cursor.fetchone()
            if row and row[0]:
                line1 = row[0] or ""
                line2 = row[1] or ""
                return f"{line1}\n{line2}".strip()

            # Generate new summary if not cached
            return self._generate_thread_summary(thread_id, message_id, max_chars)

        except Exception as e:
            print(f"Error getting thread summary: {e}")
            return "Email conversation"

    def _generate_thread_summary(self, thread_id: str, latest_message_id: str, max_chars: int) -> str:
        """Generate 2-line thread summary and cache it"""
        try:
            conn = self._get_connection()

            # Get latest few emails in thread
            cursor = conn.execute("""
                SELECT subject, body_text, sender, date_received
                FROM emails
                WHERE thread_id = ?
                ORDER BY date_received DESC
                LIMIT 3
            """, (thread_id,))

            emails = cursor.fetchall()
            if not emails:
                return "Email conversation"

            # Extract key info for summary
            latest = emails[0]
            subject = latest[0] or "Email"
            body = latest[1] or ""

            # Simple summary generation (could be enhanced with NLP)
            # Line 1: Topic + latest intent
            topic = subject.replace("Re:", "").replace("Fwd:", "").strip()[:50]

            # Line 2: Outstanding ask (basic pattern matching)
            ask = ""
            if any(word in body.lower() for word in ['can you', 'could you', 'please', 'need', 'require']):
                ask = "Action requested"
            elif any(word in body.lower() for word in ['confirm', 'schedule', 'meeting']):
                ask = "Confirmation needed"
            elif any(word in body.lower() for word in ['question', '?']):
                ask = "Question pending"
            else:
                ask = "Discussion ongoing"

            line1 = f"Topic: {topic}"[:140]
            line2 = f"Status: {ask}"[:140]

            # Cache the summary
            conn.execute("""
                INSERT OR REPLACE INTO thread_summaries
                (thread_id, last_message_id, summary_line1, summary_line2, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (thread_id, latest_message_id, line1, line2))

            conn.commit()

            return f"{line1}\n{line2}"

        except Exception as e:
            print(f"Error generating thread summary: {e}")
            return "Email conversation"

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None