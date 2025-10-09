# Environment Configuration Guide

This guide helps you set up the environment variables for the AI Email Assistant.

## Quick Setup

1. **Copy the template file:**
   ```bash
   cp .env.template .env
   ```

2. **Edit the .env file with your actual values:**
   ```bash
   nano .env  # or use your preferred editor
   ```

3. **Required variables to update:**
   - `OPENAI_API_KEY`: Your OpenAI API key from https://platform.openai.com/api-keys
   - `GOOGLE_CREDENTIALS_FILE`: Path to your Google OAuth credentials JSON file

## Environment Variables Reference

### Core Configuration
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `HOST`: Server host (default: 127.0.0.1)
- `PORT`: Server port (default: 8502)
- `GOOGLE_CREDENTIALS_FILE`: Path to Google OAuth credentials

### Email Processing
- `EMAIL_FETCH_DAYS`: Number of days to fetch emails (default: 10)
- `EMAIL_MAX_RESULTS`: Maximum emails to process (default: 20)
- `EMAIL_PROCESSING_DELAY_SECONDS`: Delay between API calls (default: 0.2)

### AI Response Configuration
- `OPENAI_MODEL`: OpenAI model to use (default: gpt-3.5-turbo)
- `MAX_RESPONSE_TOKENS`: Maximum tokens per response (default: 200)
- `RESPONSE_TEMPERATURE`: Response creativity level (default: 0.8)
- `DEFAULT_TONE`: Default response tone (default: professional)

### Google OAuth Settings
- `OAUTH_TIMEOUT_SECONDS`: OAuth timeout (default: 120)
- `OAUTH_REDIRECT_PORT`: OAuth redirect port (default: 8080)
- `OAUTH_REDIRECT_HOST`: OAuth redirect host (default: localhost)

### Security Settings
- `APP_NAME`: Application name for secure storage (default: SecureEmailAgent)
- `DEBUG_MODE`: Enable debug mode (default: false)
- `LOG_EMAIL_BODIES`: Log email content (default: false - recommended)

## Google Cloud Console Setup

Make sure your OAuth redirect URIs include:
- `http://localhost:8080/`
- `http://127.0.0.1:8080/`

Or use your custom `OAUTH_REDIRECT_HOST` and `OAUTH_REDIRECT_PORT` values.

## Security Notes

1. **Never commit .env files** - They contain sensitive information
2. **Keep .env.template updated** - When adding new variables
3. **Use strong API keys** - Rotate them regularly
4. **Limit API scopes** - Only request necessary permissions

## Testing Your Setup

After configuring your .env file:

```bash
# Install dependencies
pip install -r requirements.txt

# Test the configuration
python simple_email_agent.py

# Run tests
python test_instant_agent.py
```

## Troubleshooting

### Common Issues

**"OpenAI API key not found"**
- Check your `OPENAI_API_KEY` in .env
- Ensure no extra spaces or quotes

**"Google credentials not found"**
- Verify `GOOGLE_CREDENTIALS_FILE` path
- Check file permissions

**"Port already in use"**
- Change `PORT` in .env
- Update OAuth redirect URIs accordingly

**"OAuth authentication failed"**
- Verify `OAUTH_REDIRECT_PORT` and `OAUTH_REDIRECT_HOST`
- Check Google Cloud Console redirect URI configuration

### Getting Help

1. Check the main README.md for detailed setup instructions
2. Verify all required dependencies are installed
3. Ensure your .env file matches the .env.template structure
4. Check that sensitive files are properly excluded by .gitignore