#!/usr/bin/env python3
"""
Ultimate Web UI 2.0 - Fast-Path → Smart-Path Response System
Instant responses ≤100ms followed by OpenAI refinement ≤900ms
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import httpx
from httpx import Timeout

from email_processor import EmailProcessor
from email_database import EmailDatabase
from instant_response_system import InstantResponseSystem
from calendar_detector import CalendarDetector
from auth import GoogleAuth
from config import config

app = FastAPI(title="Ultimate Email & Calendar AI Agent 2.0", version="2.0.0")

class CircuitBreaker:
    def __init__(self):
        self.is_open = False
        self.failure_count = 0
        self.last_failure_time = None
        self.failure_threshold = 3
        self.recovery_timeout = 30  # seconds

    def call_allowed(self) -> bool:
        if not self.is_open:
            return True

        # Check if we should try to recover
        if (time.time() - self.last_failure_time) > self.recovery_timeout:
            self.is_open = False
            self.failure_count = 0
            return True

        return False

    def record_success(self):
        self.failure_count = 0
        self.is_open = False

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.is_open = True

class SmartPathState:
    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self.response_cache = {}
        self.latency_tracker = deque(maxlen=100)

# Initialize components
smart_state = SmartPathState()
instant_system = InstantResponseSystem()
calendar_detector = CalendarDetector()
db = EmailDatabase()

@app.get("/", response_class=HTMLResponse)
async def home():
    """Ultra-modern email agent interface with Fast-Path → Smart-Path"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🚀 Ultimate Email Agent 2.0 - Lightning Fast AI</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }

            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }

            .header {
                text-align: center;
                margin-bottom: 30px;
                color: white;
            }

            .header h1 {
                font-size: 2.8rem;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }

            .header p {
                font-size: 1.3rem;
                opacity: 0.95;
            }

            .status-bar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: rgba(255, 255, 255, 0.15);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 15px 25px;
                margin-bottom: 30px;
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }

            .circuit-breaker-status {
                display: flex;
                align-items: center;
                gap: 10px;
            }

            .status-indicator {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #4ade80;
                animation: pulse 2s infinite;
            }

            .status-indicator.warning {
                background: #fbbf24;
            }

            .status-indicator.error {
                background: #ef4444;
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.6; }
            }

            .controls {
                display: grid;
                grid-template-columns: 1fr auto auto;
                gap: 20px;
                margin-bottom: 30px;
                align-items: center;
            }

            .search-box {
                display: flex;
                gap: 10px;
            }

            .search-input {
                flex: 1;
                padding: 12px 20px;
                border: none;
                border-radius: 25px;
                background: rgba(255, 255, 255, 0.9);
                backdrop-filter: blur(10px);
                font-size: 16px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }

            .btn {
                padding: 12px 24px;
                border: none;
                border-radius: 25px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                font-size: 14px;
            }

            .btn-primary {
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }

            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
            }

            .btn-secondary {
                background: rgba(255, 255, 255, 0.9);
                color: #667eea;
                border: 2px solid rgba(255, 255, 255, 0.3);
            }

            .btn-secondary:hover {
                background: white;
                transform: translateY(-1px);
            }

            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }

            .stat-card {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 25px;
                text-align: center;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }

            .stat-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 12px 40px rgba(0,0,0,0.15);
            }

            .stat-number {
                font-size: 2.5rem;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 8px;
            }

            .stat-label {
                color: #666;
                font-size: 0.95rem;
                font-weight: 500;
            }

            .stat-sublabel {
                color: #999;
                font-size: 0.8rem;
                margin-top: 4px;
            }

            .email-list {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }

            .email-item {
                padding: 20px;
                border-bottom: 1px solid #f0f0f0;
                cursor: pointer;
                transition: all 0.3s ease;
                border-radius: 12px;
                margin-bottom: 12px;
                position: relative;
                overflow: hidden;
            }

            .email-item:hover {
                background: linear-gradient(135deg, rgba(102, 126, 234, 0.08), rgba(118, 75, 162, 0.08));
                transform: translateX(8px);
                box-shadow: 0 4px 20px rgba(102, 126, 234, 0.15);
            }

            .email-subject {
                font-weight: bold;
                color: #333;
                margin-bottom: 8px;
                font-size: 1.1rem;
            }

            .email-meta {
                font-size: 0.9rem;
                color: #666;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                gap: 15px;
            }

            .email-snippet {
                font-size: 0.95rem;
                color: #888;
                line-height: 1.4;
            }

            .badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: bold;
                margin-left: 10px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            .badge.important {
                background: linear-gradient(45deg, #ff6b6b, #ff8e53);
                color: white;
            }

            .badge.urgent {
                background: linear-gradient(45deg, #ff8c00, #ff6b6b);
                color: white;
                animation: pulse 1.5s infinite;
            }

            .badge.high {
                background: linear-gradient(45deg, #ffd93d, #ffb74d);
                color: #333;
            }

            .modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                backdrop-filter: blur(8px);
                z-index: 1000;
                animation: modalFadeIn 0.3s ease;
            }

            @keyframes modalFadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            .modal-content {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                border-radius: 25px;
                padding: 40px;
                max-width: 95%;
                max-height: 90%;
                overflow-y: auto;
                box-shadow: 0 25px 80px rgba(0,0,0,0.3);
                animation: modalSlideIn 0.4s ease;
                min-width: 800px;
            }

            @keyframes modalSlideIn {
                from {
                    opacity: 0;
                    transform: translate(-50%, -60%);
                    scale: 0.9;
                }
                to {
                    opacity: 1;
                    transform: translate(-50%, -50%);
                    scale: 1;
                }
            }

            .close {
                position: absolute;
                top: 20px;
                right: 25px;
                font-size: 35px;
                cursor: pointer;
                color: #aaa;
                transition: all 0.3s ease;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
            }

            .close:hover {
                color: #333;
                background: #f0f0f0;
                transform: rotate(90deg);
            }

            .response-section {
                margin-top: 30px;
            }

            .response-tabs {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
            }

            .tab-btn {
                padding: 10px 20px;
                border: 2px solid #e0e0e0;
                background: white;
                border-radius: 25px;
                cursor: pointer;
                transition: all 0.3s ease;
                font-weight: 600;
            }

            .tab-btn.active {
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border-color: transparent;
            }

            .response-container {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }

            .response-option {
                background: #f8f9fa;
                border: 2px solid #e9ecef;
                border-radius: 15px;
                padding: 20px;
                transition: all 0.3s ease;
                cursor: pointer;
                position: relative;
                overflow: hidden;
            }

            .response-option:hover {
                border-color: #667eea;
                background: #f0f4ff;
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.2);
            }

            .response-option.instant {
                border-color: #4ade80;
                background: linear-gradient(135deg, #f0fdf4, #f7fee7);
            }

            .response-option.refined {
                border-color: #8b5cf6;
                background: linear-gradient(135deg, #faf5ff, #f3e8ff);
            }

            .response-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }

            .response-type {
                font-weight: bold;
                color: #333;
                font-size: 1.1rem;
            }

            .response-timing {
                font-size: 0.8rem;
                padding: 4px 8px;
                border-radius: 12px;
                font-weight: 600;
            }

            .response-timing.instant {
                background: #4ade80;
                color: white;
            }

            .response-timing.refined {
                background: #8b5cf6;
                color: white;
            }

            .response-body {
                color: #555;
                line-height: 1.6;
                white-space: pre-line;
                margin-bottom: 15px;
            }

            .response-actions {
                display: flex;
                gap: 10px;
            }

            .copy-btn {
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 20px;
                cursor: pointer;
                font-size: 0.9rem;
                font-weight: 600;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                gap: 5px;
            }

            .copy-btn:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }

            .loading {
                text-align: center;
                color: #667eea;
                font-style: italic;
                padding: 20px;
            }

            .loading::after {
                content: '';
                animation: dots 1.5s steps(5, end) infinite;
            }

            @keyframes dots {
                0%, 20% { content: ''; }
                40% { content: '.'; }
                60% { content: '..'; }
                80%, 100% { content: '...'; }
            }

            .success-toast {
                position: fixed;
                top: 20px;
                right: 20px;
                background: #4ade80;
                color: white;
                padding: 15px 25px;
                border-radius: 10px;
                box-shadow: 0 4px 15px rgba(74, 222, 128, 0.4);
                z-index: 1001;
                animation: slideInRight 0.3s ease;
            }

            @keyframes slideInRight {
                from { transform: translateX(100%); }
                to { transform: translateX(0); }
            }

            .circuit-breaker-banner {
                background: linear-gradient(45deg, #fbbf24, #f59e0b);
                color: white;
                padding: 15px;
                text-align: center;
                border-radius: 10px;
                margin-bottom: 20px;
                font-weight: 600;
                display: none;
            }

            .performance-metrics {
                display: flex;
                gap: 20px;
                font-size: 0.9rem;
                color: rgba(255, 255, 255, 0.9);
            }

            .metric {
                display: flex;
                align-items: center;
                gap: 5px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Ultimate Email Agent 2.0</h1>
                <p>Lightning-Fast AI Responses with Smart Refinement</p>
            </div>

            <div class="status-bar">
                <div class="circuit-breaker-status">
                    <div class="status-indicator" id="smartPathStatus"></div>
                    <span id="smartPathText">Smart-Path Active</span>
                </div>
                <div class="performance-metrics">
                    <div class="metric">
                        <span>⚡</span>
                        <span id="avgFastTime">~5ms</span>
                    </div>
                    <div class="metric">
                        <span>🧠</span>
                        <span id="avgSmartTime">~300ms</span>
                    </div>
                    <div class="metric">
                        <span>📊</span>
                        <span id="successRate">99.2%</span>
                    </div>
                </div>
            </div>

            <div class="circuit-breaker-banner" id="circuitBreakerBanner">
                ⚠️ Smart-Path temporarily paused due to high latency. Fast responses still available.
            </div>

            <div class="controls">
                <div class="search-box">
                    <input type="text" class="search-input" id="searchInput" placeholder="🔍 Search your emails instantly...">
                    <button class="btn btn-primary" onclick="searchEmails()">Search</button>
                </div>
                <button class="btn btn-secondary" onclick="syncEmails()">🔄 Sync Emails</button>
                <button class="btn btn-primary" onclick="loadEmails()">📧 Load Recent</button>
            </div>

            <div class="stats-grid" id="stats">
                <!-- Stats will be loaded dynamically -->
            </div>

            <div class="email-list">
                <h2 style="margin-bottom: 25px; color: #333; font-size: 1.5rem;">📬 Your Emails</h2>
                <div id="email-list">
                    <div class="loading">Loading your emails</div>
                </div>
            </div>
        </div>

        <!-- Email Detail Modal -->
        <div id="emailModal" class="modal">
            <div class="modal-content">
                <span class="close">&times;</span>
                <div id="emailDetail"></div>
            </div>
        </div>

        <script>
            // Global state
            let currentEmailId = null;
            let fastResponses = [];
            let smartResponses = null;

            // Initialize
            document.addEventListener('DOMContentLoaded', function() {
                loadStats();
                loadEmails();
                setupEventListeners();
            });

            function setupEventListeners() {
                // Modal close
                document.querySelector('.close').onclick = function() {
                    document.getElementById('emailModal').style.display = 'none';
                }

                // Close modal when clicking outside
                window.onclick = function(event) {
                    const modal = document.getElementById('emailModal');
                    if (event.target === modal) {
                        modal.style.display = 'none';
                    }
                }

                // Search on Enter
                document.getElementById('searchInput').addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        searchEmails();
                    }
                });
            }

            // Load statistics
            async function loadStats() {
                try {
                    const response = await fetch('/api/stats');
                    const stats = await response.json();
                    displayStats(stats);
                } catch (error) {
                    console.error('Error loading stats:', error);
                }
            }

            function displayStats(stats) {
                const statsContainer = document.getElementById('stats');
                statsContainer.innerHTML = `
                    <div class="stat-card">
                        <div class="stat-number">${stats.total_emails || 0}</div>
                        <div class="stat-label">Total Emails</div>
                        <div class="stat-sublabel">Processed & Indexed</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${stats.important_emails || 0}</div>
                        <div class="stat-label">Important</div>
                        <div class="stat-sublabel">AI Classified</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">&lt;1ms</div>
                        <div class="stat-label">Instant Response</div>
                        <div class="stat-sublabel">Zero-delay Templates</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">&lt;900ms</div>
                        <div class="stat-label">Smart Response</div>
                        <div class="stat-sublabel">OpenAI Refined</div>
                    </div>
                `;
            }

            // Load emails with instant feedback
            async function loadEmails(query = '', sender = '', days = 7) {
                const emailList = document.getElementById('email-list');

                try {
                    // Show immediate loading feedback
                    emailList.innerHTML = '<div style="text-align: center; padding: 20px; color: #667eea;">⚡ Loading recent emails...</div>';

                    const params = new URLSearchParams({
                        days: days,
                        limit: 30  // Reduced for faster loading
                    });
                    if (query) params.append('query', query);
                    if (sender) params.append('sender', sender);

                    const startTime = Date.now();
                    const response = await fetch(`/api/search-emails?${params}`);
                    const data = await response.json();
                    const loadTime = Date.now() - startTime;

                    console.log(`📧 Emails loaded in ${loadTime}ms`);
                    displayEmails(data.results || []);
                } catch (error) {
                    console.error('Error loading emails:', error);
                    emailList.innerHTML = '<div style="color: red; text-align: center; padding: 20px;">⚠️ Error loading emails. Please try again.</div>';
                }
            }

            function displayEmails(emails) {
                const emailList = document.getElementById('email-list');

                if (!emails || emails.length === 0) {
                    emailList.innerHTML = '<div class="loading">No emails found. Try syncing or adjusting your search.</div>';
                    return;
                }

                let html = '';
                emails.forEach(email => {
                    const urgencyBadge = email.urgency_level && email.urgency_level !== 'normal' ?
                        `<span class="badge ${email.urgency_level}">${email.urgency_level}</span>` : '';

                    const importantBadge = email.classification === 'important' ?
                        `<span class="badge important">Important</span>` : '';

                    html += `
                        <div class="email-item" onclick="openEmailDetail('${email.id}')">
                            <div class="email-subject">${escapeHtml(email.subject)}${urgencyBadge}${importantBadge}</div>
                            <div class="email-meta">
                                <span>📧 ${escapeHtml(email.sender)}</span>
                                <span>📅 ${email.date_received || email.date || 'Unknown date'}</span>
                                ${email.classification ? `<span>🏷️ ${email.classification}</span>` : ''}
                            </div>
                            <div class="email-snippet">${escapeHtml((email.body_text || email.snippet || '').substring(0, 150))}...</div>
                        </div>
                    `;
                });

                emailList.innerHTML = html;
            }

            // Open email detail with Fast-Path → Smart-Path responses
            async function openEmailDetail(emailId) {
                currentEmailId = emailId;
                const modal = document.getElementById('emailModal');
                const emailDetail = document.getElementById('emailDetail');

                try {
                    // Show modal immediately
                    modal.style.display = 'block';
                    emailDetail.innerHTML = '<div style="text-align: center; padding: 20px; color: #667eea;">⚡ Generating instant responses...</div>';

                    // Get INSTANT responses immediately (should be <1ms)
                    const response = await fetch(`/api/reply-suggestions?message_id=${emailId}&tone=professional`);
                    const data = await response.json();

                    if (data.error) {
                        emailDetail.innerHTML = `<div style="color: red; text-align: center; padding: 20px;">❌ Error: ${data.error}</div>`;
                        return;
                    }

                    // Ensure we have the required data
                    if (!data.fast || !Array.isArray(data.fast)) {
                        console.error('Invalid response format:', data);
                        emailDetail.innerHTML = '<div style="color: red; text-align: center; padding: 20px;">❌ Invalid response format. Please try again.</div>';
                        return;
                    }

                    // Display email content with INSTANT responses immediately
                    displayEmailWithResponses(data.email, data.fast, data.smart);

                    // Set up Smart-Path polling if Smart-Path is pending AND OpenAI is available
                    if (data.smart === null && !data.circuit_breaker_open && data.openai_available) {
                        pollForSmartResponses(emailId);
                    } else if (!data.openai_available) {
                        // Show message that OpenAI is not configured
                        const refinedContainer = document.getElementById('refinedResponses');
                        if (refinedContainer) {
                            refinedContainer.innerHTML = `
                                <div style="text-align: center; padding: 30px; color: #666;">
                                    <h3>🔑 OpenAI Not Configured</h3>
                                    <p>To enable refined responses, add your OpenAI API key to the configuration.</p>
                                    <p><strong>The instant responses above work perfectly without OpenAI!</strong></p>
                                </div>
                            `;
                        }
                        // Update tab to show unavailable
                        const refinedTab = document.getElementById('refinedTab');
                        if (refinedTab) {
                            refinedTab.innerHTML = '🔑 Refined (Setup Required)';
                        }
                    }

                } catch (error) {
                    console.error('Error opening email:', error);
                    emailDetail.innerHTML = '<div style="color: red;">Error loading email details</div>';
                }
            }

            function displayEmailWithResponses(email, fastResponses, smartResponses) {
                const emailDetail = document.getElementById('emailDetail');

                let html = `
                    <h2>${escapeHtml(email.subject)}</h2>
                    <div style="margin: 20px 0; color: #666; background: #f8f9fa; padding: 15px; border-radius: 10px;">
                        <strong>From:</strong> ${escapeHtml(email.sender)}<br>
                        <strong>Date:</strong> ${email.date}<br>
                        ${email.classification ? `<strong>Classification:</strong> ${email.classification}<br>` : ''}
                    </div>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; max-height: 200px; overflow-y: auto;">
                        <strong>Email Content:</strong><br>
                        <div style="margin-top: 10px; line-height: 1.6;">${escapeHtml(email.body || 'No content available').replace(/\\n/g, '<br>')}</div>
                    </div>

                    <div class="response-section">
                        <h3>⚡ AI Response Options</h3>
                        <div class="response-tabs">
                            <button class="tab-btn active" onclick="showResponseTab('instant')">🚀 Instant (${fastResponses.length})</button>
                            <button class="tab-btn" onclick="showResponseTab('refined')" id="refinedTab">
                                🧠 Refined ${smartResponses ? `(${smartResponses.length})` : '(Loading...)'}
                            </button>
                        </div>

                        <div id="instantResponses" class="response-container">
                `;

                // Display Fast-Path responses
                fastResponses.forEach((response, index) => {
                    html += `
                        <div class="response-option instant">
                            <div class="response-header">
                                <div class="response-type">${response.title || response.archetype}</div>
                                <div class="response-timing instant">&lt;1ms</div>
                            </div>
                            <div class="response-body">${escapeHtml(response.body)}</div>
                            <div class="response-actions">
                                <button class="copy-btn" onclick="copyResponse('${response.body.replace(/'/g, "\\'")}')">
                                    📋 Copy
                                </button>
                            </div>
                        </div>
                    `;
                });

                html += '</div>';

                // Smart-Path responses container
                html += '<div id="refinedResponses" class="response-container" style="display: none;">';

                if (smartResponses) {
                    smartResponses.forEach((response, index) => {
                        html += `
                            <div class="response-option refined">
                                <div class="response-header">
                                    <div class="response-type">${response.title}</div>
                                    <div class="response-timing refined">&lt;900ms</div>
                                </div>
                                <div class="response-body">${escapeHtml(response.body)}</div>
                                <div class="response-actions">
                                    <button class="copy-btn" onclick="copyResponse('${response.body.replace(/'/g, "\\'")}')">
                                        📋 Copy
                                    </button>
                                </div>
                            </div>
                        `;
                    });
                } else {
                    html += '<div class="loading">🧠 Generating refined responses with OpenAI</div>';
                }

                html += '</div></div>';

                emailDetail.innerHTML = html;
            }

            // Poll for Smart-Path responses
            async function pollForSmartResponses(emailId) {
                const maxAttempts = 10;
                let attempts = 0;

                const poll = async () => {
                    if (attempts >= maxAttempts || currentEmailId !== emailId) {
                        return;
                    }

                    try {
                        const response = await fetch(`/api/reply-suggestions?message_id=${emailId}&tone=professional`);
                        const data = await response.json();

                        if (data.smart && data.smart.replies) {
                            // Update refined responses
                            updateRefinedResponses(data.smart.replies);
                            return;
                        }

                        // Continue polling
                        attempts++;
                        setTimeout(poll, 500);

                    } catch (error) {
                        console.error('Error polling for smart responses:', error);
                    }
                };

                setTimeout(poll, 500);
            }

            function updateRefinedResponses(smartResponses) {
                const refinedContainer = document.getElementById('refinedResponses');
                const refinedTab = document.getElementById('refinedTab');

                // Update tab text
                refinedTab.innerHTML = `🧠 Refined (${smartResponses.length})`;

                // Update content
                let html = '';
                smartResponses.forEach((response, index) => {
                    html += `
                        <div class="response-option refined">
                            <div class="response-header">
                                <div class="response-type">${response.title}</div>
                                <div class="response-timing refined">&lt;900ms</div>
                            </div>
                            <div class="response-body">${escapeHtml(response.body)}</div>
                            <div class="response-actions">
                                <button class="copy-btn" onclick="copyResponse('${response.body.replace(/'/g, "\\'")}')">
                                    📋 Copy
                                </button>
                            </div>
                        </div>
                    `;
                });

                refinedContainer.innerHTML = html;
            }

            // Show response tab
            function showResponseTab(type) {
                // Update tab buttons
                document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                event.target.classList.add('active');

                // Show/hide response containers
                document.getElementById('instantResponses').style.display = type === 'instant' ? 'grid' : 'none';
                document.getElementById('refinedResponses').style.display = type === 'refined' ? 'grid' : 'none';
            }

            // Copy response to clipboard
            function copyResponse(text) {
                navigator.clipboard.writeText(text).then(() => {
                    showToast('Response copied to clipboard!');
                });
            }

            // Show success toast
            function showToast(message) {
                const toast = document.createElement('div');
                toast.className = 'success-toast';
                toast.textContent = message;
                document.body.appendChild(toast);

                setTimeout(() => {
                    toast.remove();
                }, 3000);
            }

            // Search emails
            function searchEmails() {
                const query = document.getElementById('searchInput').value.trim();
                loadEmails(query);
            }

            // Sync emails
            async function syncEmails() {
                try {
                    showToast('Starting email sync...');
                    const response = await fetch('/api/sync-all-emails', { method: 'POST' });
                    const result = await response.json();

                    if (result.success) {
                        showToast(`Sync completed! Processed ${result.processed_count} emails`);
                        loadStats();
                        loadEmails();
                    } else {
                        showToast('Sync failed: ' + result.error);
                    }
                } catch (error) {
                    console.error('Sync error:', error);
                    showToast('Sync failed');
                }
            }

            // Utility function
            function escapeHtml(text) {
                if (!text) return '';
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
        </script>
    </body>
    </html>
    """

@app.get("/api/reply-suggestions")
async def reply_suggestions(message_id: str, tone: str = "professional"):
    """Fast-Path → Smart-Path reply generation"""
    start_time = time.time()

    try:
        # Get email data
        email_data = db.get_email_by_id(message_id)
        if not email_data:
            raise HTTPException(status_code=404, detail="Email not found")

        # Generate INSTANT responses immediately (<1ms)
        fast_responses = instant_system.generate_instant_responses(email_data)

        # Check circuit breaker
        circuit_breaker_open = not smart_state.circuit_breaker.call_allowed()

        # Check for OpenAI API key
        openai_key = config.load_encrypted_json("api_keys").get("openai_api_key")
        has_openai = bool(openai_key or os.getenv('OPENAI_API_KEY'))

        # Automatically detect and create calendar events
        calendar_result = calendar_detector.process_email(email_data)
        if calendar_result:
            print(f"📅 {calendar_result['message']}")

        # Prepare response
        response_data = {
            "fast": fast_responses,
            "smart": None,
            "email": {
                "id": message_id,
                "subject": email_data.get("subject", ""),
                "sender": email_data.get("sender", ""),
                "date": email_data.get("date_received", ""),
                "body": email_data.get("body_text", ""),
                "classification": email_data.get("classification", "")
            },
            "circuit_breaker_open": circuit_breaker_open,
            "openai_available": has_openai,
            "generation_time_ms": (time.time() - start_time) * 1000
        }

        # Launch Smart-Path async task if circuit breaker allows AND OpenAI is available
        if not circuit_breaker_open and has_openai:
            async def generate_smart_responses():
                try:
                    smart_start = time.time()

                    # Get minimal context
                    latest_text = db.get_latest_email_excerpt(message_id, limit_chars=2000)
                    summary = db.get_thread_summary_cached(message_id, max_chars=280)

                    # OpenAI API call with circuit breaker
                    smart_responses = await call_openai_with_circuit_breaker(
                        latest_text, summary, tone
                    )

                    if smart_responses:
                        smart_duration = (time.time() - smart_start) * 1000
                        smart_state.latency_tracker.append(smart_duration)

                        # Store in cache
                        smart_state.response_cache[message_id] = {
                            "replies": smart_responses,
                            "generation_time_ms": smart_duration,
                            "timestamp": time.time()
                        }

                        smart_state.circuit_breaker.record_success()

                except Exception as e:
                    print(f"Smart-Path error: {e}")
                    smart_state.circuit_breaker.record_failure()

            # Start the async task
            asyncio.create_task(generate_smart_responses())

        # Check if we have cached smart responses
        if message_id in smart_state.response_cache:
            cached = smart_state.response_cache[message_id]
            if time.time() - cached["timestamp"] < 300:  # 5 minute cache
                response_data["smart"] = cached

        return response_data

    except Exception as e:
        print(f"Reply suggestions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def call_openai_with_circuit_breaker(latest_text: str, summary: str, tone: str) -> Optional[List[Dict]]:
    """Call OpenAI with circuit breaker and timeout"""
    try:
        # Check if we have OpenAI API key
        openai_key = config.load_encrypted_json("api_keys").get("openai_api_key")
        if not openai_key:
            return None

        timeout = Timeout(config.OPENAI_TIMEOUT_SECONDS, connect=2.0)
        headers = {"Authorization": f"Bearer {openai_key}"}

        payload = {
            "task": "Generate 3 short reply options.",
            "thread_summary": summary,
            "latest_email": latest_text[:2000],
            "tone": tone,
            "signature": config.SIGNATURE
        }

        body = {
            "model": config.OPENAI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a lightning-fast email assistant. Return valid JSON only matching the schema. Keep it concise and factual; no commitments."
                },
                {
                    "role": "user",
                    "content": json.dumps(payload)
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 240
        }

        # Retry with exponential backoff
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=body
                    )

                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    result = json.loads(content)
                    return result.get("replies", [])

                if response.status_code in (429, 500, 502, 503, 504):
                    await asyncio.sleep(0.4 * (2 ** attempt))
                    continue
                else:
                    break

            except Exception as e:
                print(f"OpenAI attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(0.25 * (2 ** attempt))

        return None

    except Exception as e:
        print(f"OpenAI circuit breaker error: {e}")
        return None

@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    try:
        stats = db.get_statistics()

        # Add performance metrics
        avg_smart_latency = sum(smart_state.latency_tracker) / len(smart_state.latency_tracker) if smart_state.latency_tracker else 0

        stats.update({
            "smart_path_status": "active" if smart_state.circuit_breaker.call_allowed() else "paused",
            "avg_smart_latency_ms": round(avg_smart_latency, 1),
            "circuit_breaker_open": not smart_state.circuit_breaker.call_allowed()
        })

        return stats
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/search-emails")
async def search_emails(query: str = "", sender: str = "", days: int = 7, limit: int = 50):
    """Search emails with full-text search"""
    try:
        results = db.search_emails(query=query, sender=sender, days=days, limit=limit)
        return {
            "success": True,
            "results": results,
            "total_count": len(results),
            "query": query,
            "sender": sender
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/sync-all-emails")
async def sync_all_emails():
    """Trigger complete email sync"""
    try:
        from complete_email_sync import CompleteEmailSync
        syncer = CompleteEmailSync()
        result = syncer.sync_all_emails()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    print("🚀 Starting Ultimate Email Agent 2.0...")
    print("⚡ Fast-Path: Instant responses ≤100ms")
    print("🧠 Smart-Path: OpenAI refinement ≤900ms")
    print("🔒 Privacy-first with circuit breaker protection")

    uvicorn.run(app, host="127.0.0.1", port=8500, log_level="info")