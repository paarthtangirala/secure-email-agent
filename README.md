# 🔐 Secure Email Agent

An AI-powered email processing agent that automatically classifies emails, creates calendar events, and suggests responses while maintaining strong data encryption and privacy.

## ✨ Features

- **🔒 End-to-End Encryption**: All your data is encrypted locally using Fernet encryption
- **🤖 AI Email Classification**: Distinguishes between important personal emails and promotional content
- **📅 Smart Calendar Integration**: Automatically extracts meeting information and creates calendar events
- **💬 AI Response Suggestions**: Generates contextual email response suggestions
- **🌐 Web Interface**: Clean, modern web UI for managing your email agent
- **🛡️ Secure Storage**: API keys and sensitive data stored in encrypted format
- **📊 Analytics**: Track processing statistics and email trends

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the project
cd secure_email_agent

# Install dependencies
pip install -r requirements.txt
```

### 2. Google API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API and Google Calendar API
4. Create OAuth 2.0 credentials (Desktop Application)
5. Download the credentials JSON file
6. Save it as `encrypted_data/credentials.json` in the project directory

### 3. Initial Setup

```bash
# Run the setup process
python main.py --setup
```

This will:
- Authenticate with Google APIs
- Optionally set up OpenAI API key for AI responses
- Create encrypted storage for your data

### 4. Usage Options

#### Command Line Interface
```bash
# Process emails from last 24 hours
python main.py --process 24

# Show important emails from last 7 days
python main.py --important 7

# Show processing statistics
python main.py --stats

# Interactive mode
python main.py --interactive
```

#### Web Interface
```bash
# Start web server
python web_ui.py

# Then open http://localhost:8000 in your browser
```

## 🛠️ Configuration

### Email Classification
The system automatically learns to classify emails based on:
- **Important/Personal**: Emails from real people, interview invitations, meeting requests
- **Promotional**: Marketing emails, newsletters, automated messages
- **Requires Review**: Uncertain classifications that need human review

### Calendar Event Extraction
Automatically detects and extracts:
- Meeting times and dates
- Event locations (including video call links)
- Attendee information
- Event descriptions

### Response Suggestions
Generates appropriate responses for:
- Interview confirmations/questions
- Meeting acceptances/declines
- General professional correspondence
- Custom AI-powered responses (with OpenAI API)

## 🔧 Advanced Configuration

### Security Settings
- Encryption keys are stored securely using the system keyring
- All processed email data is encrypted at rest
- OAuth tokens are encrypted before storage
- No plain text storage of sensitive information

### Customization
Edit user preferences through the web interface or configuration files:
- Email signature
- Response tone preferences
- Auto-calendar event creation
- Classification confidence thresholds

## 📊 Data Privacy

- **Local Processing**: All email processing happens locally on your machine
- **Encrypted Storage**: All data is encrypted using industry-standard encryption
- **API Key Security**: Sensitive keys stored securely and never logged
- **No Cloud Storage**: Your email data never leaves your control
- **Audit Trail**: All processing activities are logged for your review

## 🔍 How It Works

1. **Email Retrieval**: Securely connects to Gmail using OAuth2
2. **Classification**: Uses ML and rule-based classification to identify important emails
3. **Calendar Processing**: Extracts meeting information using NLP techniques
4. **Response Generation**: Creates contextual response suggestions
5. **Secure Storage**: Encrypts and stores all data locally

## 🚨 Security Features

- **Zero Trust Architecture**: Assumes no external service is trustworthy
- **Local-First**: All processing happens on your machine
- **Encrypted Data**: AES-256 encryption for all stored data
- **Secure Key Management**: Uses system keyring when available
- **Audit Logging**: Track all agent activities
- **No Network Data**: Email content never transmitted to external servers (except OpenAI for AI responses if enabled)

## 📋 Requirements

- Python 3.8+
- Google account with Gmail and Calendar access
- Google Cloud project with APIs enabled
- Optional: OpenAI API key for enhanced AI responses

## 🆘 Troubleshooting

### Authentication Issues
- Ensure OAuth2 credentials are properly downloaded and placed in `encrypted_data/credentials.json`
- Check that Gmail and Calendar APIs are enabled in your Google Cloud project
- Verify OAuth consent screen is properly configured

### Permission Errors
- Make sure the application has the necessary OAuth scopes
- Re-run authentication if permissions change

### Processing Issues
- Check internet connectivity for API access
- Verify sufficient storage space for encrypted data
- Review error logs in the application output

## 🔄 Updates and Maintenance

- **Automatic Learning**: The classifier improves over time with your feedback
- **Data Backup**: Regularly backup your `encrypted_data` folder
- **Token Refresh**: OAuth tokens are automatically refreshed as needed
- **Security Updates**: Keep dependencies updated for security patches

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review error logs in the application
3. Ensure all setup steps were completed correctly

## ⚖️ Privacy Policy

This application:
- Does not collect or transmit your personal data
- Processes emails locally on your machine
- Uses encryption to protect your data at rest
- Only connects to Google APIs with your explicit OAuth consent
- Optionally uses OpenAI API only if you provide an API key and only for response generation

## 📝 License

This project is provided as-is for personal use. Ensure compliance with Google's API terms of service and OpenAI's usage policies when using their respective services.