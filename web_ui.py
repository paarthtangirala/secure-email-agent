#!/usr/bin/env python3

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
from datetime import datetime

from email_processor import EmailProcessor
from response_generator import ResponseGenerator
from calendar_manager import CalendarManager
from auth import GoogleAuth
from config import config

# Pydantic models for API requests/responses
class EmailProcessingRequest(BaseModel):
    hours_back: int = 24

class ResponseGenerationRequest(BaseModel):
    email_id: str

class UserPreferencesModel(BaseModel):
    signature: Optional[str] = None
    preferred_tone: Optional[str] = "professional"
    auto_create_events: bool = False
    confidence_threshold: float = 0.8

class SetupRequest(BaseModel):
    openai_api_key: Optional[str] = None

# FastAPI app
app = FastAPI(title="Secure Email Agent", version="1.0.0")

# Global instances
processor = EmailProcessor()
response_generator = ResponseGenerator()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main web interface"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Secure Email Agent</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .content {
                padding: 30px;
            }
            .card {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                border-left: 4px solid #667eea;
            }
            .button {
                background: #667eea;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                margin: 5px;
            }
            .button:hover {
                background: #5a6fd8;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }
            .stat-card {
                background: white;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 20px;
                text-align: center;
            }
            .stat-number {
                font-size: 32px;
                font-weight: bold;
                color: #667eea;
            }
            .stat-label {
                color: #6c757d;
                margin-top: 5px;
            }
            .email-list {
                max-height: 400px;
                overflow-y: auto;
                border: 1px solid #e9ecef;
                border-radius: 8px;
            }
            .email-item {
                padding: 15px;
                border-bottom: 1px solid #e9ecef;
                cursor: pointer;
            }
            .email-item:hover {
                background-color: #f8f9fa;
            }
            .email-subject {
                font-weight: bold;
                margin-bottom: 5px;
            }
            .email-meta {
                color: #6c757d;
                font-size: 12px;
            }
            .loading {
                text-align: center;
                padding: 20px;
                color: #6c757d;
            }
            .error {
                color: #dc3545;
                background: #f8d7da;
                border: 1px solid #f5c6cb;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }
            .success {
                color: #155724;
                background: #d4edda;
                border: 1px solid #c3e6cb;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }
            .modal {
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.5);
            }
            .modal-content {
                background-color: white;
                margin: 15% auto;
                padding: 30px;
                border-radius: 10px;
                width: 80%;
                max-width: 600px;
            }
            .close {
                color: #aaa;
                float: right;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
            }
            .close:hover {
                color: black;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 Secure Email Agent</h1>
                <p>AI-powered email processing with end-to-end encryption</p>
            </div>

            <div class="content">
                <!-- Stats Section -->
                <div class="card">
                    <h2>📊 Statistics</h2>
                    <div class="stats-grid" id="stats-grid">
                        <div class="loading">Loading statistics...</div>
                    </div>
                </div>

                <!-- Actions Section -->
                <div class="card">
                    <h2>⚡ Actions</h2>
                    <button class="button" onclick="processEmails()">Process New Emails</button>
                    <button class="button" onclick="showImportantEmails()">Show Important Emails</button>
                    <button class="button" onclick="openSettings()">Settings</button>
                    <button class="button" onclick="refreshData()">Refresh</button>
                </div>

                <!-- Important Emails Section -->
                <div class="card">
                    <h2>📧 Important Emails</h2>
                    <div class="email-list" id="email-list">
                        <div class="loading">Click "Show Important Emails" to load...</div>
                    </div>
                </div>

                <!-- Status Section -->
                <div id="status-area"></div>
            </div>
        </div>

        <!-- Settings Modal -->
        <div id="settingsModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeSettings()">&times;</span>
                <h2>⚙️ Settings</h2>
                <form id="settingsForm">
                    <div style="margin-bottom: 15px;">
                        <label>Email Signature:</label><br>
                        <input type="text" id="signature" style="width: 100%; padding: 8px; margin-top: 5px;" placeholder="Your Name">
                    </div>
                    <div style="margin-bottom: 15px;">
                        <label>Preferred Tone:</label><br>
                        <select id="tone" style="width: 100%; padding: 8px; margin-top: 5px;">
                            <option value="professional">Professional</option>
                            <option value="casual">Casual</option>
                            <option value="formal">Formal</option>
                        </select>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <label>
                            <input type="checkbox" id="autoCreateEvents"> Auto-create calendar events
                        </label>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <label>OpenAI API Key (for AI responses):</label><br>
                        <input type="password" id="openaiKey" style="width: 100%; padding: 8px; margin-top: 5px;" placeholder="sk-...">
                    </div>
                    <button type="button" class="button" onclick="saveSettings()">Save Settings</button>
                </form>
            </div>
        </div>

        <script>
            // Global state
            let currentEmails = [];

            // Load initial data
            document.addEventListener('DOMContentLoaded', function() {
                loadStats();
            });

            // API Functions
            async function apiCall(endpoint, method = 'GET', data = null) {
                try {
                    const options = {
                        method: method,
                        headers: {
                            'Content-Type': 'application/json',
                        },
                    };

                    if (data) {
                        options.body = JSON.stringify(data);
                    }

                    const response = await fetch(endpoint, options);
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return await response.json();
                } catch (error) {
                    showError('API Error: ' + error.message);
                    throw error;
                }
            }

            // Load statistics
            async function loadStats() {
                try {
                    const stats = await apiCall('/api/stats');
                    displayStats(stats);
                } catch (error) {
                    document.getElementById('stats-grid').innerHTML = '<div class="error">Failed to load statistics</div>';
                }
            }

            // Display statistics
            function displayStats(stats) {
                const statsGrid = document.getElementById('stats-grid');
                statsGrid.innerHTML = `
                    <div class="stat-card">
                        <div class="stat-number">${stats.total_processed || 0}</div>
                        <div class="stat-label">Emails Processed</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${stats.total_important || 0}</div>
                        <div class="stat-label">Important Emails</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${stats.total_events_created || 0}</div>
                        <div class="stat-label">Calendar Events</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${stats.total_responses_generated || 0}</div>
                        <div class="stat-label">AI Responses</div>
                    </div>
                `;
            }

            // Process emails
            async function processEmails() {
                showStatus('Processing emails...', 'loading');
                try {
                    const hours = parseInt(prompt('Hours back to process (default 24):') || '24');
                    const result = await apiCall('/api/process', 'POST', { hours_back: hours });
                    showStatus(`Successfully processed ${result.processed_count} emails. Found ${result.important_emails?.length || 0} important emails.`, 'success');
                    loadStats();
                } catch (error) {
                    showStatus('Failed to process emails', 'error');
                }
            }

            // Show important emails
            async function showImportantEmails() {
                const emailList = document.getElementById('email-list');
                emailList.innerHTML = '<div class="loading">Loading important emails...</div>';

                try {
                    const days = parseInt(prompt('Days back to show (default 7):') || '7');
                    const emails = await apiCall(`/api/important?days=${days}`);
                    currentEmails = emails;
                    displayEmails(emails);
                } catch (error) {
                    emailList.innerHTML = '<div class="error">Failed to load emails</div>';
                }
            }

            // Display emails
            function displayEmails(emails) {
                const emailList = document.getElementById('email-list');

                if (emails.length === 0) {
                    emailList.innerHTML = '<div class="loading">No important emails found</div>';
                    return;
                }

                emailList.innerHTML = emails.map(email => `
                    <div class="email-item" onclick="showEmailDetails('${email.id}')">
                        <div class="email-subject">${escapeHtml(email.subject)}</div>
                        <div class="email-meta">
                            From: ${escapeHtml(email.sender)} |
                            ${email.classification.classification}
                            (${Math.round(email.classification.confidence * 100)}% confidence)
                            ${email.classification.urgency_level === 'urgent' ? ' | 🚨 URGENT' : ''}
                            ${email.classification.requires_response ? ' | 💬 Needs Response' : ''}
                        </div>
                    </div>
                `).join('');
            }

            // Show email details (placeholder)
            function showEmailDetails(emailId) {
                alert(`Email details for ID: ${emailId}\\n\\nThis would show:\\n- Full email content\\n- Response suggestions\\n- Calendar event options`);
            }

            // Settings functions
            function openSettings() {
                document.getElementById('settingsModal').style.display = 'block';
                loadSettings();
            }

            function closeSettings() {
                document.getElementById('settingsModal').style.display = 'none';
            }

            async function loadSettings() {
                try {
                    const prefs = await apiCall('/api/preferences');
                    document.getElementById('signature').value = prefs.signature || '';
                    document.getElementById('tone').value = prefs.preferred_tone || 'professional';
                    document.getElementById('autoCreateEvents').checked = prefs.auto_create_events || false;
                } catch (error) {
                    // Settings might not exist yet
                }
            }

            async function saveSettings() {
                try {
                    const settings = {
                        signature: document.getElementById('signature').value,
                        preferred_tone: document.getElementById('tone').value,
                        auto_create_events: document.getElementById('autoCreateEvents').checked,
                    };

                    const openaiKey = document.getElementById('openaiKey').value;
                    if (openaiKey.trim()) {
                        await apiCall('/api/setup', 'POST', { openai_api_key: openaiKey });
                    }

                    await apiCall('/api/preferences', 'POST', settings);
                    showStatus('Settings saved successfully!', 'success');
                    closeSettings();
                } catch (error) {
                    showStatus('Failed to save settings', 'error');
                }
            }

            // Refresh data
            function refreshData() {
                loadStats();
                if (currentEmails.length > 0) {
                    showImportantEmails();
                }
            }

            // Utility functions
            function showStatus(message, type) {
                const statusArea = document.getElementById('status-area');
                const className = type === 'error' ? 'error' : type === 'success' ? 'success' : 'loading';
                statusArea.innerHTML = `<div class="${className}">${message}</div>`;

                if (type === 'success') {
                    setTimeout(() => {
                        statusArea.innerHTML = '';
                    }, 5000);
                }
            }

            function showError(message) {
                showStatus(message, 'error');
            }

            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            // Close modal when clicking outside
            window.onclick = function(event) {
                const modal = document.getElementById('settingsModal');
                if (event.target === modal) {
                    modal.style.display = 'none';
                }
            }
        </script>
    </body>
    </html>
    """

@app.get("/api/stats")
async def get_stats():
    """Get processing statistics"""
    try:
        return processor.get_processing_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process")
async def process_emails(request: EmailProcessingRequest, background_tasks: BackgroundTasks):
    """Process new emails"""
    try:
        # Run processing in background for better responsiveness
        result = processor.process_new_emails(request.hours_back)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/important")
async def get_important_emails(days: int = 7):
    """Get important emails"""
    try:
        return processor.get_important_emails(days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/preferences")
async def get_user_preferences():
    """Get user preferences"""
    try:
        return response_generator.get_user_preferences()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/preferences")
async def save_user_preferences(preferences: UserPreferencesModel):
    """Save user preferences"""
    try:
        response_generator.save_user_preferences(preferences.dict())
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/setup")
async def setup_api_keys(request: SetupRequest):
    """Setup API keys"""
    try:
        if request.openai_api_key:
            response_generator.set_openai_key(request.openai_api_key)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/responses/{email_id}")
async def get_response_suggestions(email_id: str):
    """Get response suggestions for an email"""
    try:
        return processor.get_response_suggestions_for_email(email_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def run_web_ui(host="127.0.0.1", port=8000):
    """Run the web UI server"""
    import uvicorn
    print(f"🌐 Starting Secure Email Agent Web UI at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run_web_ui()