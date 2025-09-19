import os
from cryptography.fernet import Fernet
from pathlib import Path
import keyring
import json

class SecureConfig:
    def __init__(self):
        self.app_name = "SecureEmailAgent"
        self.base_dir = Path(__file__).parent
        self.data_dir = self.base_dir / "encrypted_data"
        self.data_dir.mkdir(exist_ok=True)

        # Generate or load encryption key
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)

        # OAuth scopes
        self.gmail_scopes = ['https://www.googleapis.com/auth/gmail.readonly']
        self.calendar_scopes = ['https://www.googleapis.com/auth/calendar']

        # API credentials paths
        self.credentials_file = self.data_dir / "credentials.json"
        self.token_file = self.data_dir / "token.json"

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
            key_file = self.data_dir / ".key"
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