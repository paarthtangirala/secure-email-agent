#!/usr/bin/env python3
"""
Simple script to securely configure OpenAI API key for refined responses
"""

import getpass
from config import config

def setup_openai_key():
    """Setup OpenAI API key securely"""
    print("🔑 OpenAI API Key Setup")
    print("=" * 30)
    print()
    print("To enable refined responses with OpenAI:")
    print("1. Get your API key from: https://platform.openai.com/api-keys")
    print("2. Enter it below (it will be encrypted and stored securely)")
    print()

    # Check if key already exists
    existing_keys = config.load_encrypted_json("api_keys")
    if existing_keys.get("openai_api_key"):
        print("✅ OpenAI API key is already configured!")
        overwrite = input("Do you want to update it? (y/N): ").lower()
        if overwrite != 'y':
            print("Keeping existing key.")
            return

    # Get new key
    print("Enter your OpenAI API key (starts with 'sk-'):")
    api_key = getpass.getpass("API Key: ").strip()

    if not api_key:
        print("❌ No API key provided. Exiting.")
        return

    if not api_key.startswith('sk-'):
        print("⚠️  Warning: OpenAI API keys usually start with 'sk-'")
        confirm = input("Continue anyway? (y/N): ").lower()
        if confirm != 'y':
            return

    # Save encrypted
    try:
        keys = config.load_encrypted_json("api_keys")
        keys["openai_api_key"] = api_key
        config.save_encrypted_json("api_keys", keys)

        print("✅ OpenAI API key configured successfully!")
        print("🚀 Restart your email agent to enable refined responses.")
        print()
        print("Your key is encrypted and stored securely in:")
        print(f"   {config.data_dir}/api_keys.enc")

    except Exception as e:
        print(f"❌ Error saving API key: {e}")

def remove_openai_key():
    """Remove OpenAI API key"""
    keys = config.load_encrypted_json("api_keys")
    if "openai_api_key" in keys:
        del keys["openai_api_key"]
        config.save_encrypted_json("api_keys", keys)
        print("✅ OpenAI API key removed.")
    else:
        print("❌ No OpenAI API key found.")

def check_openai_status():
    """Check OpenAI configuration status"""
    print("🔍 OpenAI Configuration Status")
    print("=" * 35)

    keys = config.load_encrypted_json("api_keys")
    api_key = keys.get("openai_api_key")

    if api_key:
        print("✅ OpenAI API key is configured")
        print(f"   Key length: {len(api_key)} characters")
        print(f"   Key preview: {api_key[:7]}...{api_key[-4:]}")
        print("🚀 Refined responses are enabled!")
    else:
        print("❌ OpenAI API key is NOT configured")
        print("   Only instant responses are available")
        print("   Run this script to add your API key")

if __name__ == "__main__":
    print("🤖 Email Agent - OpenAI Setup")
    print("=" * 35)
    print()
    print("1. Check current status")
    print("2. Setup/Update OpenAI API key")
    print("3. Remove OpenAI API key")
    print("4. Exit")
    print()

    choice = input("Choose option (1-4): ").strip()

    if choice == "1":
        check_openai_status()
    elif choice == "2":
        setup_openai_key()
    elif choice == "3":
        remove_openai_key()
    elif choice == "4":
        print("Goodbye!")
    else:
        print("Invalid choice.")