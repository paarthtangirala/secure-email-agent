import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import config

class GoogleAuth:
    def __init__(self):
        self.gmail_service = None
        self.calendar_service = None

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
                creds = flow.run_local_server(port=0)

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