#!/usr/bin/env python3

"""
Test the fixed OAuth authentication
"""

import sys

def main():
    print("🔍 Testing fixed OAuth authentication...\n")

    try:
        # Test imports
        from config import config
        from auth import GoogleAuth

        print("✅ Modules imported successfully")

        # Test auth creation
        auth = GoogleAuth()
        print("✅ GoogleAuth instance created")

        # Check credentials file
        if not config.credentials_file.exists():
            print("❌ No credentials file found")
            return False

        print("✅ Credentials file exists")

        # Test flow creation (without actual authentication)
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_secrets_file(
            str(config.credentials_file),
            config.gmail_scopes + config.calendar_scopes
        )

        print("✅ OAuth flow created successfully")

        # Test URL generation (this should work)
        auth_url, _ = flow.authorization_url(prompt='consent')
        print("✅ Authorization URL generated successfully")
        print(f"📋 URL starts with: {auth_url[:50]}...")

        print("\n✅ All OAuth components are working!")
        print("🔧 The authentication is ready to use.")
        print("💡 Run 'python main.py --setup' in your terminal to complete setup.")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)