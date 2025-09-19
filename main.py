#!/usr/bin/env python3

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from email_processor import EmailProcessor
from response_generator import ResponseGenerator
from calendar_manager import CalendarManager
from auth import GoogleAuth
from config import config

class SecureEmailAgent:
    def __init__(self):
        self.processor = EmailProcessor()
        self.response_generator = ResponseGenerator()

    def run_email_processing(self, hours_back: int = 24):
        """Run email processing for the specified time period"""
        print(f"🔍 Processing emails from the last {hours_back} hours...")

        try:
            results = self.processor.process_new_emails(hours_back)

            if 'error' in results:
                print(f"❌ Error: {results['error']}")
                return False

            # Display results
            print(f"\n📊 Processing Results:")
            print(f"   Processed: {results['processed_count']} emails")
            print(f"   Important: {len(results['important_emails'])} emails")
            print(f"   Calendar events created: {results['calendar_events_created']}")
            print(f"   Response suggestions: {len(results['response_suggestions'])}")

            if results.get('errors'):
                print(f"   Errors: {len(results['errors'])} emails failed")

            # Show important emails
            if results['important_emails']:
                print(f"\n📧 Important Emails:")
                for i, email in enumerate(results['important_emails'][:5], 1):
                    print(f"   {i}. {email['subject'][:60]}...")
                    print(f"      From: {email['sender']}")
                    print(f"      Classification: {email['classification']['classification']}")

                    if email.get('calendar_event_created'):
                        print(f"      ✅ Calendar event created")

                    if email.get('response_suggestions'):
                        print(f"      💬 {len(email['response_suggestions'])} response suggestions")

                    print()

            return True

        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False

    def show_important_emails(self, days_back: int = 7):
        """Show important emails from the specified period"""
        print(f"📧 Important emails from the last {days_back} days:")

        try:
            emails = self.processor.get_important_emails(days_back)

            if not emails:
                print("   No important emails found.")
                return

            for i, email in enumerate(emails, 1):
                print(f"\n{i}. {email['subject']}")
                print(f"   From: {email['sender']}")
                print(f"   Classification: {email['classification']['classification']}")
                print(f"   Confidence: {email['classification']['confidence']:.2f}")

                if email['classification'].get('requires_response'):
                    print(f"   🔔 Requires response")

                urgency = email['classification'].get('urgency_level', 'normal')
                if urgency == 'urgent':
                    print(f"   🚨 URGENT")
                elif urgency == 'high':
                    print(f"   ⚡ High priority")

        except Exception as e:
            print(f"❌ Error retrieving emails: {e}")

    def show_stats(self):
        """Show processing statistics"""
        print("📊 Processing Statistics:")

        try:
            stats = self.processor.get_processing_stats()

            print(f"   Total processed: {stats['total_processed']} emails")
            print(f"   Total important: {stats['total_important']} emails")
            print(f"   Calendar events created: {stats['total_events_created']}")
            print(f"   Response suggestions: {stats['total_responses_generated']}")

            if stats['last_run']:
                last_run = datetime.fromisoformat(stats['last_run'])
                print(f"   Last run: {last_run.strftime('%Y-%m-%d %H:%M:%S')}")

            if stats['average_important_per_run'] > 0:
                print(f"   Avg important per run: {stats['average_important_per_run']:.1f}")

        except Exception as e:
            print(f"❌ Error retrieving statistics: {e}")

    def setup_authentication(self):
        """Setup Google authentication"""
        print("🔐 Setting up Google authentication...")

        try:
            auth = GoogleAuth()
            if auth.authenticate():
                print("✅ Authentication successful!")
                return True
            else:
                print("❌ Authentication failed!")
                return False

        except Exception as e:
            print(f"❌ Authentication error: {e}")
            print("\nMake sure you have:")
            print("1. Downloaded OAuth2 credentials from Google Cloud Console")
            print(f"2. Saved them as: {config.credentials_file}")
            print("3. Enabled Gmail and Calendar APIs in your project")
            return False

    def setup_openai(self):
        """Setup OpenAI API key"""
        print("🤖 Setting up OpenAI for AI responses...")

        api_key = input("Enter your OpenAI API key (or press Enter to skip): ").strip()

        if api_key:
            self.response_generator.set_openai_key(api_key)
            print("✅ OpenAI API key saved securely!")
        else:
            print("⏭️ Skipping OpenAI setup - only template responses will be available")

    def interactive_mode(self):
        """Run in interactive mode"""
        print("🤖 Secure Email Agent - Interactive Mode")
        print("Type 'help' for available commands, 'quit' to exit")

        while True:
            try:
                command = input("\n> ").strip().lower()

                if command == 'quit' or command == 'exit':
                    break
                elif command == 'help':
                    self.show_help()
                elif command == 'process':
                    hours = input("Hours back to process (default 24): ").strip()
                    hours = int(hours) if hours.isdigit() else 24
                    self.run_email_processing(hours)
                elif command == 'important':
                    days = input("Days back to show (default 7): ").strip()
                    days = int(days) if days.isdigit() else 7
                    self.show_important_emails(days)
                elif command == 'stats':
                    self.show_stats()
                elif command == 'auth':
                    self.setup_authentication()
                elif command == 'openai':
                    self.setup_openai()
                else:
                    print("Unknown command. Type 'help' for available commands.")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")

    def show_help(self):
        """Show help information"""
        print("\n📖 Available Commands:")
        print("   process  - Process new emails")
        print("   important - Show important emails")
        print("   stats    - Show processing statistics")
        print("   auth     - Setup Google authentication")
        print("   openai   - Setup OpenAI API key")
        print("   help     - Show this help")
        print("   quit     - Exit the program")

def main():
    parser = argparse.ArgumentParser(description='Secure Email Agent')
    parser.add_argument('--process', type=int, metavar='HOURS',
                      help='Process emails from the last N hours')
    parser.add_argument('--important', type=int, metavar='DAYS',
                      help='Show important emails from the last N days')
    parser.add_argument('--stats', action='store_true',
                      help='Show processing statistics')
    parser.add_argument('--setup', action='store_true',
                      help='Run initial setup')
    parser.add_argument('--interactive', action='store_true',
                      help='Run in interactive mode')

    args = parser.parse_args()

    # Create agent
    agent = SecureEmailAgent()

    # Check if credentials exist
    if not config.credentials_file.exists() and not args.setup:
        print("⚠️  No Google credentials found!")
        print("Run with --setup to configure authentication")
        return

    if args.setup:
        print("🚀 Setting up Secure Email Agent...")
        if agent.setup_authentication():
            agent.setup_openai()
            print("\n✅ Setup complete! You can now run the agent.")
        return

    if args.process:
        agent.run_email_processing(args.process)
    elif args.important:
        agent.show_important_emails(args.important)
    elif args.stats:
        agent.show_stats()
    elif args.interactive:
        agent.interactive_mode()
    else:
        # Default: process last 24 hours
        agent.run_email_processing(24)

if __name__ == '__main__':
    main()