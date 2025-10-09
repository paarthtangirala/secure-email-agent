#!/usr/bin/env python3

"""
Simple demo script to show email response suggestions
"""

from response_generator import ResponseGenerator
from email_classifier import EmailClassifier
from config import config

def show_response_suggestions():
    """Show response suggestions for important emails"""

    print("💬 EMAIL RESPONSE SUGGESTIONS DEMO")
    print("=" * 60)

    # Initialize generator
    generator = ResponseGenerator()

    # Load processed emails
    processed_data = config.load_encrypted_json("processed_emails")

    if 'emails' not in processed_data:
        print("❌ No processed emails found. Run email processing first.")
        return

    # Find emails that need responses
    response_emails = []
    for email_id, data in processed_data['emails'].items():
        if data.get('classification', {}).get('requires_response'):
            response_emails.append((email_id, data))

    if not response_emails:
        print("📧 No emails requiring responses found.")
        return

    print(f"Found {len(response_emails)} emails that need responses:\n")

    for i, (email_id, email_data) in enumerate(response_emails[:3], 1):  # Show first 3
        print(f"📧 EMAIL {i}: {email_data['subject']}")
        print(f"   From: {email_data['sender']}")
        print(f"   Classification: {email_data['classification']['classification']}")

        # Create email data for response generation
        email_for_response = {
            'subject': email_data['subject'],
            'sender': email_data['sender'],
            'body': f"Email content for {email_data['subject'][:50]}...",
        }

        # Generate suggestions
        suggestions = generator.generate_response_suggestions(
            email_for_response,
            email_data['classification']
        )

        print(f"\n💡 RESPONSE SUGGESTIONS:")

        for j, suggestion in enumerate(suggestions, 1):
            print(f"\n   🔹 Option {j}: {suggestion['type'].replace('_', ' ').title()}")
            print(f"   📧 Subject: {suggestion['subject']}")
            print(f"   🎭 Tone: {suggestion['tone']}")
            print(f"   📝 Response:")
            # Format the response with proper indentation
            response_lines = suggestion['body'].split('\n')
            for line in response_lines:
                print(f"      {line}")

        print("\n" + "-" * 50)

        # Ask if user wants to see more
        if i < len(response_emails):
            continue_choice = input(f"\nShow next email? (y/n): ").strip().lower()
            if continue_choice != 'y':
                break

    print(f"\n✅ Demo complete! Total emails with responses: {len(response_emails)}")

def show_specific_email_responses():
    """Show responses for specific email types"""

    print("\n🎯 SPECIFIC EMAIL RESPONSE EXAMPLES")
    print("=" * 60)

    generator = ResponseGenerator()

    # Sample emails that commonly need responses
    sample_emails = [
        {
            'subject': 'A bill payment failed for Game Crate',
            'sender': 'Shopify Billing <billing@shopify.com>',
            'body': 'Your payment for Game Crate subscription has failed. Please update your payment method.',
            'classification': {
                'classification': 'important',
                'requires_response': True,
                'urgency_level': 'urgent'
            }
        },
        {
            'subject': 'Checking in, PAARTH, please review your BankAmeriDeals®',
            'sender': 'Bank of America <bankofamerica@emcom.bankofamerica.com>',
            'body': 'You have new BankAmeriDeals offers available. Review and activate them.',
            'classification': {
                'classification': 'important',
                'requires_response': True,
                'urgency_level': 'high'
            }
        },
        {
            'subject': 'Your credit card statement is available',
            'sender': 'Chase <no.reply.alerts@chase.com>',
            'body': 'Your credit card statement for September is now available.',
            'classification': {
                'classification': 'important',
                'requires_response': False,
                'urgency_level': 'normal'
            }
        }
    ]

    for i, email in enumerate(sample_emails, 1):
        print(f"\n📧 SAMPLE EMAIL {i}")
        print(f"Subject: {email['subject']}")
        print(f"From: {email['sender']}")
        print(f"Urgency: {email['classification']['urgency_level'].upper()}")

        suggestions = generator.generate_response_suggestions(email, email['classification'])

        print(f"\n💡 SUGGESTED RESPONSES:")

        for j, suggestion in enumerate(suggestions, 1):
            print(f"\n🔹 Response Option {j}: {suggestion['type'].replace('_', ' ').title()}")
            print(f"📧 Subject Line: {suggestion['subject']}")
            print(f"🎭 Tone: {suggestion['tone']}")
            print(f"\n📝 Email Body:")
            print("   " + suggestion['body'].replace('\n', '\n   '))

            if j < len(suggestions):
                print("\n   " + "─" * 40)

        print("\n" + "=" * 50)

if __name__ == "__main__":
    try:
        print("🤖 SECURE EMAIL AGENT - RESPONSE SUGGESTIONS")
        print("=" * 60)

        choice = input("\nChoose demo:\n1. Your actual emails\n2. Sample email responses\n\nEnter choice (1 or 2): ").strip()

        if choice == "1":
            show_response_suggestions()
        elif choice == "2":
            show_specific_email_responses()
        else:
            print("Invalid choice. Showing sample responses...")
            show_specific_email_responses()

    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted. Your email agent is ready for use!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure you've run email processing first with:")
        print("python main.py --process 24")