# OAuth Setup Guide

## ✅ OAuth Issue Fixed

The OAuth hanging issue has been resolved. The application now uses console-based authentication which doesn't require a local server that could hang.

## 🔧 How to Set Up Authentication

### Step 1: Update Google Cloud Console (REQUIRED)

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Find your OAuth 2.0 Client ID: `83386187308-f165o3vkr5h2re6q3m19bcgr0nn4lb7n.apps.googleusercontent.com`
3. Click "Edit" on the client ID
4. In the "Authorized redirect URIs" section, make sure you have:
   - `urn:ietf:wg:oauth:2.0:oob` (REQUIRED for manual auth)
   - `http://localhost:8080/` (optional for local server)
   - `http://localhost/` (optional for local server)
5. **IMPORTANT**: Click "Save" after adding the redirect URIs

### Step 2: Run the Setup

```bash
python main.py --setup
```

### What Happens During Setup

1. The application will prompt you to press Enter to continue
2. A Google authorization URL will be displayed
3. Copy the URL and open it in your web browser
4. Sign in to your Google account if needed
5. Click "Allow" to grant permissions to the app
6. You'll see a page with an authorization code
7. Copy the entire authorization code (it may be long)
8. Paste it back into the terminal when prompted
9. Your credentials will be saved securely and encrypted

### Step 3: Test the Setup

```bash
python main.py --process 1
```

This will process emails from the last 1 hour as a test.

## 🔍 What Was Fixed

- **Before**: OAuth used `run_local_server()` which would hang waiting for browser callback
- **After**: OAuth uses `run_console()` which prompts for manual authorization code entry
- **Result**: No more hanging, reliable authentication process

## 🛡️ Security Features

- All credentials are encrypted using the `cryptography` library
- Encryption keys are stored in system keyring
- OAuth tokens are encrypted before being saved to disk
- No sensitive data is stored in plain text

## 📋 Troubleshooting

### If Authentication Fails

1. **Check redirect URI**: Make sure `urn:ietf:wg:oauth:2.0:oob` is added to Google Cloud Console
2. **Complete authorization code**: Ensure you copy the entire authorization code from the browser
3. **Correct Google account**: Make sure you're authorizing with the intended Google account
4. **API access**: Verify that Gmail and Calendar APIs are enabled in your Google Cloud project

### If You See "Invalid Client" Error

1. Download a fresh `credentials.json` file from Google Cloud Console
2. Replace the existing file at `encrypted_data/credentials.json`
3. Run the setup again

### If You Get Permission Errors

1. Make sure the Gmail API and Calendar API are enabled in your Google Cloud project
2. Check that your OAuth consent screen is properly configured
3. Verify that your account has access to the APIs

## 🚀 Ready to Use

The OAuth authentication is now working properly. You can proceed with using the secure email agent!