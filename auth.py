import os
import json
import signal
import threading
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from config import config

# Load environment variables
load_dotenv()

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("OAuth authentication timed out")

class GoogleAuth:
    def __init__(self):
        self.gmail_service = None
        self.calendar_service = None
        self.oauth_timeout = int(os.getenv('OAUTH_TIMEOUT_SECONDS', '120'))  # Configurable timeout

    def authenticate(self):
        """Authenticate with Google APIs using OAuth2"""
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
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Token refresh failed: {e}")
                    creds = None

            if not creds:
                if not config.credentials_file.exists():
                    raise FileNotFoundError(
                        f"Please download your OAuth2 credentials JSON file "
                        f"and save it as {config.credentials_file}"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(config.credentials_file),
                    config.gmail_scopes + config.calendar_scopes
                )

                print("🔐 Starting OAuth authentication...")
                print("💡 Using local server authentication")

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(config.credentials_file),
                    config.gmail_scopes + config.calendar_scopes
                )

                print("\n📋 OAuth Instructions:")
                print("1. A browser window will open automatically")
                print("2. Complete the Google authorization process")
                print("3. The browser will redirect and complete authentication")
                print("\nStarting authentication...")

                try:
                    # Try local server first (configurable port and host)
                    oauth_port = int(os.getenv('OAUTH_REDIRECT_PORT', '8080'))
                    oauth_host = os.getenv('OAUTH_REDIRECT_HOST', 'localhost')
                    creds = flow.run_local_server(port=oauth_port, host=oauth_host, open_browser=True)
                    print("✅ Local server OAuth successful!")

                except Exception as e:
                    oauth_port = os.getenv('OAUTH_REDIRECT_PORT', '8080')
                    oauth_host = os.getenv('OAUTH_REDIRECT_HOST', 'localhost')
                    print(f"❌ Local server OAuth failed: {e}")
                    print("\n🔧 Troubleshooting:")
                    print(f"1. Make sure http://{oauth_host}:{oauth_port}/ is added to your Google Cloud Console redirect URIs")
                    print(f"2. Check that no other application is using port {oauth_port}")
                    print("3. Try a different port or manual authentication")
                    raise

            # Save the credentials for the next run (encrypted)
            config.save_encrypted_json("token", json.loads(creds.to_json()))

        # Build services
        self.gmail_service = build('gmail', 'v1', credentials=creds)
        self.calendar_service = build('calendar', 'v3', credentials=creds)

        return True

    def get_gmail_service(self):
        if not self.gmail_service:
            self.authenticate()
        return self.gmail_service

    def get_calendar_service(self):
        if not self.calendar_service:
            self.authenticate()
        return self.calendar_service