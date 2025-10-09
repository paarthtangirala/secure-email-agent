#!/usr/bin/env python3
"""
Simple working email dashboard - Command line interface
"""

from email_processor import EmailProcessor
from response_generator import ResponseGenerator
from config import config
import json

def main_menu():
    """Main menu for email dashboard"""

    print("\n🤖 SECURE EMAIL AGENT DASHBOARD")
    print("=" * 50)
    print("1. 📊 View Statistics")
    print("2. ⚡ Process New Emails")
    print("3. 📧 Show Important Emails")
    print("4. 💬 Get Response Suggestions")
    print("5. ⚙️  Settings")
    print("6. 🚪 Exit")
    print("=" * 50)

    while True:
        try:
            choice = input("\nEnter your choice (1-6): ").strip()

            if choice == "1":
                show_statistics()
            elif choice == "2":
                process_emails()
            elif choice == "3":
                show_important_emails()
            elif choice == "4":
                show_response_suggestions()
            elif choice == "5":
                show_settings()
            elif choice == "6":
                print("\n👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please enter 1-6.")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def show_statistics():
    """Show processing statistics"""
    print("\n📊 PROCESSING STATISTICS")
    print("-" * 30)

    try:
        processor = EmailProcessor()
        stats = processor.get_processing_stats()

        print(f"📧 Total Processed: {stats['total_processed']} emails")
        print(f"⭐ Important Emails: {stats['total_important']} emails")
        print(f"📅 Calendar Events: {stats['total_events_created']} events")
        print(f"💬 AI Responses: {stats['total_responses_generated']} responses")

        if stats['last_run']:
            print(f"🕒 Last Run: {stats['last_run']}")

        if stats['average_important_per_run'] > 0:
            print(f"📈 Avg Important/Run: {stats['average_important_per_run']:.1f}")

    except Exception as e:
        print(f"❌ Error loading statistics: {e}")

def process_emails():
    """Process new emails"""
    print("\n⚡ PROCESSING NEW EMAILS")
    print("-" * 30)

    try:
        hours = input("Hours back to process (default 24): ").strip()
        hours = int(hours) if hours.isdigit() else 24

        print(f"🔍 Processing emails from last {hours} hours...")

        processor = EmailProcessor()
        results = processor.process_new_emails(hours)

        if 'error' in results:
            print(f"❌ Error: {results['error']}")
            return

        print(f"\n✅ PROCESSING COMPLETE!")
        print(f"📧 Processed: {results['processed_count']} emails")
        print(f"⭐ Important: {len(results['important_emails'])} emails")
        print(f"📅 Calendar Events: {results['calendar_events_created']} events")
        print(f"💬 Response Suggestions: {len(results['response_suggestions'])} emails")

        if results.get('errors'):
            print(f"⚠️  Errors: {len(results['errors'])} emails failed")

    except Exception as e:
        print(f"❌ Error processing emails: {e}")

def show_important_emails():
    """Show important emails"""
    print("\n📧 IMPORTANT EMAILS")
    print("-" * 30)

    try:
        days = input("Days back to show (default 7): ").strip()
        days = int(days) if days.isdigit() else 7

        processor = EmailProcessor()
        emails = processor.get_important_emails(days)

        if not emails:
            print("📭 No important emails found.")
            return

        print(f"\nFound {len(emails)} important emails:\n")

        for i, email in enumerate(emails[:10], 1):  # Show top 10
            print(f"📧 {i}. {email['subject'][:60]}...")
            print(f"   From: {email['sender']}")
            print(f"   📊 {email['classification']['classification']}")
            print(f"   🎯 Confidence: {email['classification']['confidence']:.0%}")

            if email['classification'].get('urgency_level') == 'urgent':
                print(f"   🚨 URGENT")
            elif email['classification'].get('urgency_level') == 'high':
                print(f"   ⚡ High Priority")

            if email['classification'].get('requires_response'):
                print(f"   💬 Needs Response")

            print()

        if len(emails) > 10:
            print(f"... and {len(emails) - 10} more emails")

    except Exception as e:
        print(f"❌ Error loading emails: {e}")

def show_response_suggestions():
    """Show response suggestions for emails"""
    print("\n💬 EMAIL RESPONSE SUGGESTIONS")
    print("-" * 40)

    try:
        # Load processed emails
        processed_data = config.load_encrypted_json("processed_emails")

        if 'emails' not in processed_data:
            print("❌ No processed emails found. Process emails first.")
            return

        # Find emails needing responses
        response_emails = []
        for email_id, data in processed_data['emails'].items():
            if data.get('classification', {}).get('requires_response'):
                response_emails.append((email_id, data))

        if not response_emails:
            print("📭 No emails requiring responses found.")
            return

        print(f"Found {len(response_emails)} emails that need responses:\n")

        # Show first few emails with suggestions
        generator = ResponseGenerator()

        for i, (email_id, email_data) in enumerate(response_emails[:3], 1):
            print(f"📧 EMAIL {i}: {email_data['subject'][:50]}...")
            print(f"   From: {email_data['sender']}")
            print(f"   Priority: {email_data['classification'].get('urgency_level', 'normal').upper()}")

            # Generate suggestions
            email_for_response = {
                'subject': email_data['subject'],
                'sender': email_data['sender'],
                'body': f"Content of {email_data['subject'][:30]}...",
            }

            suggestions = generator.generate_response_suggestions(
                email_for_response, email_data['classification']
            )

            print(f"\n   💡 RESPONSE OPTIONS:")
            for j, suggestion in enumerate(suggestions, 1):
                print(f"\n   🔹 Option {j}: {suggestion['type'].replace('_', ' ').title()}")
                print(f"   📧 Subject: {suggestion['subject']}")
                print(f"   📝 Response:")
                # Show first few lines of response
                response_lines = suggestion['body'].split('\n')[:3]
                for line in response_lines:
                    print(f"      {line}")
                if len(suggestion['body'].split('\n')) > 3:
                    print("      ...")

            print("\n" + "─" * 40)

            if i < len(response_emails) and i < 3:
                continue_choice = input("\nShow next email? (y/n): ").strip().lower()
                if continue_choice != 'y':
                    break

        # Show enhanced suggestions for common emails
        print(f"\n🎯 QUICK REFERENCE - ENHANCED RESPONSES:")
        print("For Payment Issues: 'Hello, I will resolve this payment issue immediately...'")
        print("For Bank Offers: 'Thank you, I will review the offers within 24 hours...'")
        print("For Statements: 'Usually no response needed - just log in to review'")

    except Exception as e:
        print(f"❌ Error generating suggestions: {e}")

def show_settings():
    """Show current settings"""
    print("\n⚙️  CURRENT SETTINGS")
    print("-" * 25)

    try:
        # Check OpenAI status
        generator = ResponseGenerator()
        if generator.client:
            print("🤖 OpenAI: ✅ Configured (quota may be exceeded)")
        else:
            print("🤖 OpenAI: ❌ Not configured")

        # Check Google Auth
        from auth import GoogleAuth
        auth = GoogleAuth()
        print("🔐 Google Auth: ✅ Configured")

        # Check data encryption
        print("🔒 Data Encryption: ✅ Active")

        print("\n📋 Available Commands:")
        print("  python main.py --process 24   # Process new emails")
        print("  python main.py --important 7  # Show important emails")
        print("  python main.py --stats        # Show statistics")
        print("  python web_ui.py              # Start web interface")

    except Exception as e:
        print(f"❌ Error checking settings: {e}")

if __name__ == "__main__":
    try:
        main_menu()
    except Exception as e:
        print(f"❌ Application error: {e}")