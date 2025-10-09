#!/usr/bin/env python3
"""
Complete Gmail Sync - Gets ALL emails from Gmail without time or read/unread restrictions
"""

import time
from typing import Dict, List
from email_processor import EmailProcessor
from email_database import EmailDatabase
from auth import GoogleAuth
from email_classifier import EmailClassifier
from datetime import datetime

class CompleteEmailSync:
    """Complete Gmail synchronization - gets every single email"""

    def __init__(self):
        self.auth = GoogleAuth()
        self.db = EmailDatabase()
        self.classifier = EmailClassifier()
        self.processor = EmailProcessor()

    def sync_all_emails(self, progress_callback=None) -> Dict:
        """Sync ALL emails from Gmail - complete history"""
        try:
            service = self.auth.get_gmail_service()

            print("🔄 Starting complete Gmail sync - this will get ALL your emails...")
            start_time = time.time()

            # Get ALL email IDs without any filters
            all_email_ids = []
            page_token = None
            batch_count = 0

            while True:
                batch_count += 1
                print(f"📥 Fetching email batch {batch_count}...")

                # Get emails without any query restrictions - this gets EVERYTHING
                result = service.users().messages().list(
                    userId='me',
                    maxResults=500,  # Max per request
                    pageToken=page_token
                ).execute()

                messages = result.get('messages', [])
                if not messages:
                    break

                # Extract just the IDs
                batch_ids = [msg['id'] for msg in messages]
                all_email_ids.extend(batch_ids)

                print(f"✅ Got {len(batch_ids)} emails (Total so far: {len(all_email_ids)})")

                # Progress callback
                if progress_callback:
                    progress_callback(len(all_email_ids), batch_count)

                # Check for next page
                page_token = result.get('nextPageToken')
                if not page_token:
                    break

                # Small delay to be nice to Gmail API
                time.sleep(0.1)

            print(f"📧 Found {len(all_email_ids)} total emails in your Gmail!")

            # Now process each email and store in database
            processed_count = 0
            important_count = 0
            errors = []

            for i, email_id in enumerate(all_email_ids):
                try:
                    if i % 50 == 0:  # Progress update every 50 emails
                        print(f"⚡ Processing email {i+1}/{len(all_email_ids)} ({(i+1)/len(all_email_ids)*100:.1f}%)")

                    # Get full email data
                    email_data = self.processor._get_email_data(service, email_id)

                    if email_data:
                        # Classify email
                        classification = self.classifier.classify_email(email_data)
                        email_data['classification'] = classification

                        # Store in database
                        if self.db.store_email(email_data):
                            processed_count += 1

                            if classification.get('classification') == 'important':
                                important_count += 1

                    # Small delay every 10 emails to avoid rate limits
                    if i % 10 == 0:
                        time.sleep(0.05)

                except Exception as e:
                    print(f"❌ Error processing email {email_id}: {e}")
                    errors.append(str(e))
                    continue

            # Optimize database after sync
            print("🔧 Optimizing database for maximum performance...")
            self.db.optimize_database()

            end_time = time.time()
            duration = end_time - start_time

            print(f"✅ COMPLETE SYNC FINISHED!")
            print(f"📊 Processed: {processed_count}/{len(all_email_ids)} emails")
            print(f"⭐ Important: {important_count} emails")
            print(f"⏱️  Duration: {duration/60:.1f} minutes")
            print(f"⚡ Speed: {processed_count/duration:.1f} emails/second")

            return {
                'success': True,
                'total_found': len(all_email_ids),
                'processed_count': processed_count,
                'important_count': important_count,
                'errors': len(errors),
                'duration_minutes': duration/60,
                'emails_per_second': processed_count/duration if duration > 0 else 0
            }

        except Exception as e:
            print(f"❌ Complete sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_found': 0,
                'processed_count': 0,
                'important_count': 0
            }
        finally:
            self.db.close()

    def get_sync_progress(self) -> Dict:
        """Get current sync progress from database"""
        try:
            stats = self.db.get_statistics()
            return {
                'total_emails': stats.get('total_emails', 0),
                'important_emails': stats.get('important_emails', 0),
                'date_range': stats.get('date_range', {}),
                'top_senders': stats.get('top_senders', [])[:5]  # Top 5 senders
            }
        except Exception as e:
            return {'error': str(e)}

if __name__ == "__main__":
    # Test the complete sync
    syncer = CompleteEmailSync()

    def progress_update(total_found, batch_count):
        print(f"🔍 Discovery progress: {total_found} emails found (batch {batch_count})")

    result = syncer.sync_all_emails(progress_callback=progress_update)
    print(f"🎉 Sync result: {result}")