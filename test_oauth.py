#!/usr/bin/env python3

"""
Standalone OAuth test script to debug Google authentication issues.
This script will help identify and fix OAuth configuration problems.
"""

import json
import os
import sys
from pathlib import Path

def test_oauth():
    """Test OAuth authentication with minimal dependencies"""
    print("🔍 Testing OAuth authentication...")

    # Check if credentials file exists
    creds_file = Path("encrypted_data/credentials.json")
    if not creds_file.exists():
        print("❌ Credentials file not found at encrypted_data/credentials.json")
        return False

    # Load and validate credentials file
    try:
        with open(creds_file, 'r') as f:
            creds_data = json.load(f)

        print("✅ Credentials file loaded successfully")

        # Check structure
        if 'installed' not in creds_data:
            print("❌ Invalid credentials file structure - missing 'installed' key")
            return False

        installed = creds_data['installed']
        required_keys = ['client_id', 'client_secret', 'auth_uri', 'token_uri', 'redirect_uris']

        for key in required_keys:
            if key not in installed:
                print(f"❌ Missing required key in credentials: {key}")
                return False

        print("✅ Credentials file structure is valid")
        print(f"📋 Client ID: {installed['client_id']}")
        print(f"📋 Project ID: {installed.get('project_id', 'Not specified')}")
        print(f"📋 Redirect URIs: {installed['redirect_uris']}")

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in credentials file: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading credentials file: {e}")
        return False

    # Test Google API imports
    try:
        print("\n🔍 Testing Google API imports...")
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        print("✅ All Google API imports successful")
    except ImportError as e:
        print(f"❌ Google API import failed: {e}")
        print("💡 Try: pip install google-api-python-client google-auth-oauthlib")
        return False

    # Test OAuth flow creation
    try:
        print("\n🔍 Testing OAuth flow creation...")
        scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/calendar'
        ]

        flow = InstalledAppFlow.from_client_secrets_file(
            str(creds_file), scopes
        )
        print("✅ OAuth flow created successfully")

        # Check redirect URIs compatibility
        redirect_uris = installed['redirect_uris']
        compatible_uris = []

        # Check for local server compatibility
        for uri in redirect_uris:
            if uri.startswith('http://localhost'):
                compatible_uris.append(('local_server', uri))
            elif uri == 'urn:ietf:wg:oauth:2.0:oob':
                compatible_uris.append(('console', uri))

        print(f"📋 Compatible OAuth methods: {len(compatible_uris)}")
        for method, uri in compatible_uris:
            print(f"   - {method}: {uri}")

        if not compatible_uris:
            print("⚠️  No compatible redirect URIs found!")
            print("💡 Add these to your Google Cloud Console OAuth client:")
            print("   - http://localhost:8080/")
            print("   - urn:ietf:wg:oauth:2.0:oob")
            return False

    except Exception as e:
        print(f"❌ OAuth flow creation failed: {e}")
        return False

    # Test a quick OAuth attempt (console mode if available)
    try:
        print("\n🔍 Testing console-based OAuth (safe, no browser)...")
        if 'urn:ietf:wg:oauth:2.0:oob' in redirect_uris:
            print("✅ Console OAuth available")
            print("💡 You can use console-based authentication as a fallback")
        else:
            print("⚠️  Console OAuth not available - need to add urn:ietf:wg:oauth:2.0:oob")

    except Exception as e:
        print(f"❌ Error testing console OAuth: {e}")

    print("\n📋 OAuth Test Summary:")
    print("✅ Credentials file exists and is valid")
    print("✅ Google API libraries are installed")
    print("✅ OAuth flow can be created")

    if 'http://localhost:8080/' in redirect_uris or 'http://localhost' in redirect_uris:
        print("✅ Local server OAuth should work")
    else:
        print("⚠️  Local server OAuth may fail - check redirect URIs")

    if 'urn:ietf:wg:oauth:2.0:oob' in redirect_uris:
        print("✅ Console OAuth available as fallback")
    else:
        print("⚠️  Console OAuth not available")

    print("\n🔧 Next steps:")
    print("1. Ensure these redirect URIs are configured in Google Cloud Console:")
    print("   - http://localhost:8080/")
    print("   - http://localhost")
    print("   - urn:ietf:wg:oauth:2.0:oob")
    print("2. Try running the application again")

    return True

if __name__ == '__main__':
    success = test_oauth()
    sys.exit(0 if success else 1)