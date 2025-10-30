#!/usr/bin/env python3
"""
MailMaestro API Key Setup Helper
Helps you configure your OpenAI API key and other credentials
"""

import os
import getpass
from pathlib import Path

def setup_openai_key():
    """Interactive setup for OpenAI API key"""
    print("🔑 MailMaestro API Key Setup")
    print("="*50)
    
    env_file = Path(".env")
    
    # Check if .env exists
    if env_file.exists():
        print("✅ Found existing .env file")
        with open(env_file) as f:
            content = f.read()
        
        if "OPENAI_API_KEY=" in content and not content.count("your-actual-api-key-here"):
            print("✅ OpenAI API key appears to be already configured")
            choice = input("Do you want to update it? (y/N): ").lower()
            if choice != 'y':
                print("✅ Keeping existing configuration")
                return
    
    print("\n📋 To get your OpenAI API key:")
    print("1. Go to: https://platform.openai.com/api-keys")
    print("2. Sign in to your OpenAI account")
    print("3. Click 'Create new secret key'")
    print("4. Copy the key (starts with 'sk-')")
    print()
    
    # Get API key securely
    api_key = getpass.getpass("🔐 Paste your OpenAI API key (input will be hidden): ")
    
    if not api_key.strip():
        print("❌ No API key provided. Exiting.")
        return
    
    if not api_key.startswith('sk-'):
        print("⚠️  Warning: OpenAI API keys usually start with 'sk-'")
        choice = input("Continue anyway? (y/N): ").lower()
        if choice != 'y':
            return
    
    # Read existing .env or create new
    env_content = ""
    if env_file.exists():
        with open(env_file) as f:
            env_content = f.read()
    
    # Update or add OpenAI key
    if "OPENAI_API_KEY=" in env_content:
        # Replace existing key
        lines = env_content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('OPENAI_API_KEY='):
                lines[i] = f"OPENAI_API_KEY={api_key}"
                break
        env_content = '\n'.join(lines)
    else:
        # Add new key
        if env_content and not env_content.endswith('\n'):
            env_content += '\n'
        env_content += f"OPENAI_API_KEY={api_key}\n"
    
    # Write updated .env file
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print("✅ OpenAI API key saved to .env file")
    
    # Test the key
    print("\n🧪 Testing API key...")
    try:
        os.environ['OPENAI_API_KEY'] = api_key
        from openai import OpenAI
        client = OpenAI()
        
        # Simple test call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        print("✅ API key is valid and working!")
        
    except Exception as e:
        print(f"❌ API key test failed: {str(e)}")
        print("Please check your API key and try again")
        return
    
    print("\n🚀 Setup complete! You can now run:")
    print("   python run_mailmaestro.py")

def check_current_setup():
    """Check current environment setup"""
    print("🔍 Current Environment Setup")
    print("="*40)
    
    # Check .env file
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file exists")
        with open(env_file) as f:
            content = f.read()
        
        if "OPENAI_API_KEY=" in content:
            if "your-actual-api-key-here" in content:
                print("⚠️  OpenAI API key needs to be set")
            else:
                print("✅ OpenAI API key configured")
        else:
            print("⚠️  No OpenAI API key in .env file")
    else:
        print("⚠️  No .env file found")
    
    # Check environment variable
    if os.getenv('OPENAI_API_KEY'):
        print("✅ OPENAI_API_KEY environment variable set")
    else:
        print("⚠️  OPENAI_API_KEY environment variable not set")
    
    print()

def main():
    """Main setup function"""
    print("🎯 MailMaestro Configuration Helper")
    print()
    
    while True:
        print("Choose an option:")
        print("1. Setup OpenAI API key")
        print("2. Check current setup")
        print("3. Exit")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            setup_openai_key()
        elif choice == '2':
            check_current_setup()
        elif choice == '3':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")
        
        print("\n" + "-"*50 + "\n")

if __name__ == "__main__":
    main()