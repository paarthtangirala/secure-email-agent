import os
from cryptography.fernet import Fernet
from pathlib import Path
import keyring
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SecureConfig:
    def __init__(self):
        self.app_name = os.getenv('APP_NAME', 'SecureEmailAgent')
        self.base_dir = Path(__file__).parent
        self.data_dir = self.base_dir / os.getenv('ENCRYPTED_DATA_DIR', 'encrypted_data')
        self.data_dir.mkdir(exist_ok=True)

        # Generate or load encryption key
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)

        # OAuth scopes - minimal permissions
        self.gmail_scopes = [os.getenv('GMAIL_SCOPES', 'https://www.googleapis.com/auth/gmail.readonly')]
        self.calendar_scopes = [os.getenv('CALENDAR_SCOPES', 'https://www.googleapis.com/auth/calendar.events')]

        # API credentials paths
        credentials_path = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        self.credentials_file = self.base_dir / credentials_path if not os.path.isabs(credentials_path) else Path(credentials_path)
        self.token_file = self.data_dir / "token.json"

        # Fast-Path → Smart-Path Configuration
        self.DEFAULT_TONE = os.getenv('DEFAULT_TONE', 'professional')
        self.SIGNATURE = os.getenv('SIGNATURE', '— Your Assistant')
        self.BUSINESS_HOURS = os.getenv('BUSINESS_HOURS', '09:00-17:00')
        self.MEETING_DEFAULT_DURATION_MIN = int(os.getenv('MEETING_DEFAULT_DURATION_MINUTES', '30'))
        self.AUTO_CC = os.getenv('AUTO_CC', '').split(',') if os.getenv('AUTO_CC') else []
        self.AUTO_BCC = os.getenv('AUTO_BCC', '').split(',') if os.getenv('AUTO_BCC') else []
        self.OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

        # Circuit breaker settings
        self.OPENAI_TIMEOUT_SECONDS = float(os.getenv('OPENAI_TIMEOUT_SECONDS', '5.0'))
        self.OPENAI_MAX_LATENCY_MS = int(os.getenv('OPENAI_MAX_LATENCY_MS', '800'))
        self.CIRCUIT_BREAKER_WINDOW = int(os.getenv('CIRCUIT_BREAKER_WINDOW', '10'))  # Number of calls to track

        # Privacy settings
        self.LOG_EMAIL_BODIES = os.getenv('LOG_EMAIL_BODIES', 'false').lower() == 'true'  # Never log raw email content
        self.DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

        # Performance targets
        self.FAST_PATH_TARGET_MS = int(os.getenv('FAST_PATH_TARGET_MS', '100'))
        self.SMART_PATH_TARGET_MS = int(os.getenv('SMART_PATH_TARGET_MS', '900'))

    def _get_or_create_encryption_key(self):
        """Get encryption key from secure storage or create new one"""
        try:
            key_str = keyring.get_password(self.app_name, "encryption_key")
            if key_str:
                return key_str.encode()
            else:
                # Generate new key
                key = Fernet.generate_key()
                keyring.set_password(self.app_name, "encryption_key", key.decode())
                return key
        except Exception as e:
            print(f"Warning: Could not access keyring, using file-based key storage: {e}")
            key_file = self.data_dir / os.getenv('KEY_FILE_NAME', '.key')
            if key_file.exists():
                return key_file.read_bytes()
            else:
                key = Fernet.generate_key()
                key_file.write_bytes(key)
                key_file.chmod(0o600)  # Read/write for owner only
                return key

    def encrypt_data(self, data: str) -> bytes:
        """Encrypt sensitive data"""
        return self.cipher.encrypt(data.encode())

    def decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypt sensitive data"""
        return self.cipher.decrypt(encrypted_data).decode()

    def save_encrypted_json(self, filename: str, data: dict):
        """Save JSON data in encrypted format"""
        json_str = json.dumps(data)
        encrypted_data = self.encrypt_data(json_str)
        filepath = self.data_dir / f"{filename}.enc"
        filepath.write_bytes(encrypted_data)

    def load_encrypted_json(self, filename: str) -> dict:
        """Load and decrypt JSON data"""
        filepath = self.data_dir / f"{filename}.enc"
        if not filepath.exists():
            return {}
        encrypted_data = filepath.read_bytes()
        json_str = self.decrypt_data(encrypted_data)
        return json.loads(json_str)

config = SecureConfig()