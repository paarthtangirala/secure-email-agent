import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import config

class GoogleAuthConsole:
    def __init__(self):
        self.gmail_service = None
        self.calendar_service = None

    def authenticate(self):
        """Authenticate with Google APIs using console-based OAuth2"""
        # Load existing credentials
        creds = None
        token_data = config.load_encrypted_json("token")

        if token_data:
            creds = Credentials.from_authorized_user_info(
                token_data,
                config.gmail_scopes + config.calendar_scopes
            )

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("🔄 Refreshing expired token...")
                    creds.refresh(Request())
                    print("✅ Token refreshed successfully")
                except Exception as e:
                    print(f"❌ Token refresh failed: {e}")
                    creds = None

            if not creds:
                if not config.credentials_file.exists():
                    raise FileNotFoundError(
                        f"Please download your OAuth2 credentials JSON file "
                        f"and save it as {config.credentials_file}"
                    )

                print("🔐 Starting OAuth authentication...")
                print("💡 Using console-based authentication (no browser required)")

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(config.credentials_file),
                    config.gmail_scopes + config.calendar_scopes
                )

                print("\n📋 Please follow these steps:")
                print("1. Copy the URL that will be displayed below")
                print("2. Open it in your web browser")
                print("3. Complete the authorization process")
                print("4. Copy the authorization code from the browser")
                print("5. Paste it back here when prompted")
                print("\nPress Enter to continue...")
                input()

                try:
                    creds = flow.run_console()
                    print("✅ Console OAuth successful!")
                except Exception as e:
                    print(f"❌ Console OAuth failed: {e}")
                    print("\nTroubleshooting tips:")
                    print("1. Make sure you copied the entire URL")
                    print("2. Ensure you're logged into the correct Google account")
                    print("3. Check that the authorization code is complete")
                    print("4. Verify the redirect URI includes: urn:ietf:wg:oauth:2.0:oob")
                    raise

            # Save the credentials for the next run (encrypted)
            config.save_encrypted_json("token", json.loads(creds.to_json()))
            print("💾 Credentials saved securely")

        # Build services
        try:
            print("🔗 Building Gmail service...")
            self.gmail_service = build('gmail', 'v1', credentials=creds)
            print("🔗 Building Calendar service...")
            self.calendar_service = build('calendar', 'v3', credentials=creds)
            print("✅ Services created successfully")
        except Exception as e:
            print(f"❌ Failed to build services: {e}")
            raise

        return True

    def get_gmail_service(self):
        if not self.gmail_service:
            self.authenticate()
        return self.gmail_service

    def get_calendar_service(self):
        if not self.calendar_service:
            self.authenticate()
        return self.calendar_service