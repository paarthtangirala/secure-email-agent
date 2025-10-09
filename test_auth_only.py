#!/usr/bin/env python3

"""
Test OAuth authentication in isolation.
"""

import sys
import signal
from pathlib import Path

def timeout_handler(signum, frame):
    print("❌ Authentication timed out!")
    sys.exit(1)

def main():
    print("🔍 Testing OAuth authentication in isolation...\n")

    # Set timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(60)  # 60 second timeout

    try:
        # Import required modules
        from config import config
        from auth import GoogleAuth

        print("✅ Modules imported successfully")

        # Create auth instance
        auth = GoogleAuth()
        print("✅ GoogleAuth instance created")

        # Check if credentials exist
        if not config.credentials_file.exists():
            print("❌ No credentials file found")
            return False

        print("✅ Credentials file exists")

        # Try authentication
        print("🔐 Starting authentication...")
        print("   (This may open a browser or prompt for input)")

        result = auth.authenticate()

        if result:
            print("✅ Authentication successful!")

            # Test services
            gmail_service = auth.get_gmail_service()
            calendar_service = auth.get_calendar_service()

            print("✅ Gmail service created")
            print("✅ Calendar service created")

            # Test a simple API call
            try:
                profile = gmail_service.users().getProfile(userId='me').execute()
                print(f"✅ Gmail API test successful - Email: {profile.get('emailAddress')}")
            except Exception as e:
                print(f"⚠️  Gmail API test failed: {e}")

            return True
        else:
            print("❌ Authentication failed")
            return False

    except Exception as e:
        print(f"❌ Error during authentication: {e}")
        return False
    finally:
        signal.alarm(0)  # Cancel timeout

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)