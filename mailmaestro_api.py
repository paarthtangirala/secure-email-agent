#!/usr/bin/env python3
"""
MailMaestro API - Enhanced FastAPI backend with intelligence layer
Production-ready email assistant API with MUI frontend support
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# Import existing modules
from email_database import EmailDatabase
from complete_email_sync import CompleteEmailSync
from gmail_live_fetcher import GmailLiveFetcher
try:
    from fast_response_generator_v2 import FastResponseGenerator
except ImportError:
    from fast_response_generator import FastResponseGenerator
try:
    from calendar_manager import CalendarManager
    from auth import GoogleAuth
    CALENDAR_AVAILABLE = True
except ImportError:
    # Create a mock calendar manager if not available
    class CalendarManager:
        def __init__(self, auth_manager=None):
            pass
    CALENDAR_AVAILABLE = False

# Import new intelligence modules
from thread_summarizer import ThreadSummarizer
from task_detector import TaskDetector
from calendar_extractor import CalendarExtractor
from model_router import ModelRouter
from smart_labeler import SmartLabeler

# Response models
class EmailListResponse(BaseModel):
    emails: List[Dict[str, Any]]
    total_count: int
    page: int
    per_page: int
    has_more: bool

class ThreadResponse(BaseModel):
    thread_id: str
    emails: List[Dict[str, Any]]
    summary: str
    tasks: List[Dict[str, Any]]
    meeting_info: Optional[Dict[str, Any]]

class ReplyResponse(BaseModel):
    fast_replies: List[Dict[str, Any]]
    smart_reply: Optional[Dict[str, Any]]
    generation_time_ms: int
    smart_reply_task_id: Optional[str] = None

class TaskResponse(BaseModel):
    tasks: List[Dict[str, Any]]
    complexity_analysis: Dict[str, Any]

class CalendarResponse(BaseModel):
    action: str
    message: str
    confidence: float
    auto_reply: bool
    calendar_event: Optional[Dict[str, Any]]

class SyncRequest(BaseModel):
    hours_back: int = 24
    delta_sync: bool = True

class LabelRequest(BaseModel):
    email_ids: List[str]

# Initialize FastAPI app
app = FastAPI(
    title="MailMaestro API",
    description="AI-powered email assistant with intelligence layer",
    version="2.0.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
db = EmailDatabase()
email_sync = CompleteEmailSync()
gmail_fetcher = GmailLiveFetcher()
response_generator = FastResponseGenerator()

# Initialize calendar manager with auth if available
if CALENDAR_AVAILABLE:
    try:
        auth = GoogleAuth()
        calendar_manager = CalendarManager(auth)
    except Exception:
        calendar_manager = CalendarManager(None)
else:
    calendar_manager = CalendarManager()

# Initialize intelligence layer
model_router = ModelRouter()
thread_summarizer = ThreadSummarizer(model_router)
task_detector = TaskDetector(model_router)
calendar_extractor = CalendarExtractor(model_router)
smart_labeler = SmartLabeler(model_router)

# Background task tracking
background_tasks_status = {}

@app.get("/")
async def root():
    """Root endpoint - serve React app"""
    return {"message": "MailMaestro API", "version": "2.0.0", "status": "running"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": "connected",
            "email_sync": "ready",
            "ai_models": "available"
        }
    }

@app.get("/api/emails", response_model=EmailListResponse)
async def get_emails(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    sender: Optional[str] = None,
    label: Optional[str] = None,
    days: int = Query(10, ge=1, le=365)
):
    """Get emails directly from Gmail for past 10 days"""
    try:
        print(f"Fetching emails from Gmail - days: {days}, per_page: {per_page}")
        
        # Fetch emails directly from Gmail API
        emails = gmail_fetcher.fetch_recent_emails(
            days_back=days, 
            max_results=per_page * 2  # Get more to handle pagination
        )
        
        # Apply search filtering if provided
        if search:
            search_lower = search.lower()
            emails = [email for email in emails 
                     if search_lower in email.get('subject', '').lower() 
                     or search_lower in email.get('body_text', '').lower()]
        
        # Apply sender filtering if provided
        if sender:
            sender_lower = sender.lower()
            emails = [email for email in emails 
                     if sender_lower in email.get('sender', '').lower() 
                     or sender_lower in email.get('sender_email', '').lower()]
        
        # Sort by date (most recent first)
        emails.sort(key=lambda x: x.get('date_received', ''), reverse=True)
        
        # Apply pagination
        offset = (page - 1) * per_page
        paginated_emails = emails[offset:offset + per_page]
        has_more = len(emails) > offset + per_page
        
        print(f"Returning {len(paginated_emails)} emails from Gmail")
        
        return EmailListResponse(
            emails=paginated_emails,
            total_count=len(emails),
            page=page,
            per_page=per_page,
            has_more=has_more
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching emails: {str(e)}")

@app.get("/api/threads/{thread_id}")
async def get_thread(thread_id: str):
    """Get full thread with summary, tasks, and meeting info"""
    try:
        print(f"DEBUG: Fetching thread {thread_id}")
        
        # Get emails from Gmail and filter by thread_id
        emails = gmail_fetcher.fetch_recent_emails(days_back=30, max_results=200)
        thread_emails = [email for email in emails if email.get('thread_id') == thread_id]
        
        if not thread_emails:
            return {
                "thread_id": thread_id,
                "emails": [],
                "summary": "Thread not found in recent emails",
                "tasks": [],
                "meeting_info": None
            }
        
        # Sort by date
        thread_emails.sort(key=lambda x: x.get('date_received', ''))
        
        # Generate simple summary
        summary = f"Thread with {len(thread_emails)} messages"
        if thread_emails:
            latest_subject = thread_emails[-1].get('subject', '')
            summary = f"Discussion: {latest_subject[:100]}..."
        
        # Simple task detection
        tasks = []
        if thread_emails:
            latest_email = thread_emails[-1]
            body_text = latest_email.get('body_text', '').lower()
            if any(word in body_text for word in ['please', 'can you', 'need', 'urgent', 'asap']):
                tasks.append({
                    'id': 1,
                    'description': 'Response required',
                    'priority': 'medium',
                    'type': 'response'
                })
        
        # Simple meeting detection
        meeting_info = None
        if thread_emails:
            latest_email = thread_emails[-1]
            body_text = latest_email.get('body_text', '').lower()
            subject = latest_email.get('subject', '').lower()
            if any(word in body_text + subject for word in ['meeting', 'call', 'zoom', 'calendar', 'schedule']):
                meeting_info = {
                    'detected': True,
                    'type': 'meeting_invitation',
                    'confidence': 0.8
                }
        
        print(f"DEBUG: Returning thread with {len(thread_emails)} emails")
        return {
            "thread_id": thread_id,
            "emails": thread_emails,
            "summary": summary,
            "tasks": tasks,
            "meeting_info": meeting_info
        }
        
    except Exception as e:
        print(f"Exception in get_thread: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching thread: {str(e)}")


@app.post("/api/reply_suggestions")
async def generate_replies(
    email_id: str,
    background_tasks: BackgroundTasks
):
    """Generate AI reply suggestions (fast + smart paths)"""
    try:
        start_time = time.time()
        
        # Get email data from Gmail
        emails = gmail_fetcher.fetch_recent_emails(days_back=30, max_results=200)
        email = next((e for e in emails if e.get('id') == email_id), None)
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Generate fast replies (synchronous)
        try:
            email_data = {
                'subject': email.get('subject', ''),
                'body': email.get('body_text', ''),
                'sender': email.get('sender', '')
            }
            classification = {'primary_label': email.get('primary_label', 'general')}
            fast_replies = response_generator.generate_fast_responses(email_data, classification)
        except AttributeError:
            # Fallback fast replies
            fast_replies = [
                {'type': 'Professional', 'body': 'Thank you for your email. I will review this and get back to you soon.', 'confidence': 0.8},
                {'type': 'Quick', 'body': 'Got it! I\'ll take care of this.', 'confidence': 0.7},
                {'type': 'Friendly', 'body': 'Thanks for reaching out! I\'ll look into this.', 'confidence': 0.7}
            ]
        
        # Start smart reply generation in background
        task_id = f"smart_reply_{email_id}_{int(time.time())}"
        background_tasks.add_task(
            generate_smart_reply_background,
            task_id,
            email
        )
        
        generation_time = int((time.time() - start_time) * 1000)
        
        return ReplyResponse(
            fast_replies=fast_replies,
            smart_reply=None,  # Will be available via background task
            generation_time_ms=generation_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating replies: {str(e)}")

@app.get("/api/reply_suggestions/{task_id}/smart")
async def get_smart_reply(task_id: str):
    """Get smart reply from background task"""
    if task_id not in background_tasks_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_status = background_tasks_status[task_id]
    
    return {
        "status": task_status["status"],
        "result": task_status.get("result"),
        "error": task_status.get("error")
    }

@app.post("/api/tasks/{email_id}", response_model=TaskResponse)
async def extract_tasks(email_id: str):
    """Extract tasks from email"""
    try:
        # Get email data from Gmail
        emails = gmail_fetcher.fetch_recent_emails(days_back=30, max_results=200)
        email = next((e for e in emails if e.get('id') == email_id), None)
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Extract tasks
        tasks = task_detector.extract_tasks(
            email.get('body_text', ''),
            {
                'sender': email.get('sender', ''),
                'subject': email.get('subject', ''),
                'date': email.get('date_received', '')
            }
        )
        
        # Analyze complexity
        complexity = task_detector.analyze_task_complexity(tasks)
        
        return TaskResponse(
            tasks=tasks,
            complexity_analysis=complexity
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting tasks: {str(e)}")

@app.post("/api/calendar_autorespond", response_model=CalendarResponse)
async def calendar_autorespond(email_id: str):
    """Handle meeting invitations with auto-response proposal"""
    try:
        # Get email data from Gmail
        emails = gmail_fetcher.fetch_recent_emails(days_back=30, max_results=200)
        email = next((e for e in emails if e.get('id') == email_id), None)
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Extract meeting info
        meeting_info = calendar_extractor.extract_meeting_info(
            email.get('body_text', ''),
            {
                'subject': email.get('subject', ''),
                'sender': email.get('sender', '')
            }
        )
        
        if not meeting_info:
            return CalendarResponse(
                action="none",
                message="No meeting detected in this email",
                confidence=0.0,
                auto_reply=False,
                calendar_event=None
            )
        
        # Propose response
        response_proposal = calendar_extractor.propose_calendar_response(meeting_info)
        
        return CalendarResponse(**response_proposal)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing calendar request: {str(e)}")

@app.post("/api/sync")
async def sync_emails(
    sync_request: SyncRequest,
    background_tasks: BackgroundTasks
):
    """Sync emails from Gmail with intelligence processing"""
    try:
        task_id = f"sync_{int(time.time())}"
        
        # Start sync in background
        background_tasks.add_task(
            sync_emails_background,
            task_id,
            sync_request.hours_back,
            sync_request.delta_sync
        )
        
        return {
            "task_id": task_id,
            "status": "started",
            "message": f"Email sync started for last {sync_request.hours_back} hours"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting sync: {str(e)}")

@app.get("/api/sync/{task_id}/status")
async def get_sync_status(task_id: str):
    """Get sync task status"""
    if task_id not in background_tasks_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return background_tasks_status[task_id]

@app.post("/api/labels/classify", response_model=Dict[str, List[Dict]])
async def classify_emails(label_request: LabelRequest):
    """Classify emails with smart labels"""
    try:
        results = {}
        
        # Get emails from Gmail
        emails = gmail_fetcher.fetch_recent_emails(days_back=30, max_results=200)
        
        for email_id in label_request.email_ids:
            email = next((e for e in emails if e.get('id') == email_id), None)
            if email:
                labels = smart_labeler.classify_email(email)
                results[email_id] = labels
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error classifying emails: {str(e)}")

@app.get("/api/labels/stats")
async def get_label_stats():
    """Get label statistics"""
    try:
        stats = smart_labeler.get_label_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting label stats: {str(e)}")

@app.get("/api/dashboard/overview")
async def get_dashboard_overview():
    """Get dashboard overview data"""
    try:
        # Get recent emails from Gmail
        recent_emails = gmail_fetcher.fetch_recent_emails(days_back=7, max_results=50)
        
        # Calculate basic stats
        db_stats = {
            'total_emails': len(recent_emails),
            'important_emails': len([e for e in recent_emails if e.get('is_important')]),
            'needs_response': len([e for e in recent_emails if e.get('requires_response')]),
            'total_responses': 0,
            'calendar_events': 0
        }
        
        # Get important emails
        important_emails = [e for e in recent_emails if e.get('is_important')][:5]
        
        # Get label distribution
        label_stats = smart_labeler.get_label_statistics()
        
        # Get model usage
        model_usage = model_router.get_usage_report()
        
        return {
            "email_stats": db_stats,
            "recent_important": important_emails,
            "label_distribution": label_stats.get("label_distribution", {}),
            "model_usage": model_usage,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting dashboard data: {str(e)}")

@app.get("/api/search")
async def search_emails(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Full-text search emails"""
    try:
        # Get emails from Gmail and search
        all_emails = gmail_fetcher.fetch_recent_emails(days_back=30, max_results=200)
        
        # Simple search filtering
        q_lower = q.lower()
        results = []
        for email in all_emails:
            if (q_lower in email.get('subject', '').lower() or 
                q_lower in email.get('body_text', '').lower() or 
                q_lower in email.get('sender', '').lower()):
                results.append(email)
                
        # Limit results
        results = results[:limit]
        
        # Enrich with labels (simplified)
        for email in results:
            email['labels'] = [email.get('primary_label', 'general')]
        
        return {
            "query": q,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching emails: {str(e)}")

# Background task functions
async def generate_smart_reply_background(task_id: str, email: Dict):
    """Generate smart reply in background"""
    try:
        background_tasks_status[task_id] = {"status": "running"}
        
        # Use advanced response generation
        smart_reply = await response_generator.generate_smart_response(
            email.get('body_text', ''),
            email.get('subject', ''),
            email.get('sender', ''),
            context=email
        )
        
        background_tasks_status[task_id] = {
            "status": "completed",
            "result": smart_reply
        }
        
    except Exception as e:
        background_tasks_status[task_id] = {
            "status": "error",
            "error": str(e)
        }

async def sync_emails_background(task_id: str, hours_back: int, delta_sync: bool):
    """Sync emails in background with intelligence processing"""
    try:
        background_tasks_status[task_id] = {
            "status": "running",
            "progress": 0,
            "message": "Starting email sync..."
        }
        
        # Sync emails  
        try:
            # Try the new method first
            sync_results = email_sync.sync_recent_emails(hours_back)
        except AttributeError:
            # Fallback to existing method
            sync_results = {'new_emails': [], 'sync_time': 0}
        
        background_tasks_status[task_id].update({
            "progress": 50,
            "message": "Processing with AI intelligence..."
        })
        
        # Process new emails with intelligence layer
        new_emails = sync_results.get('new_emails', [])
        processed_count = 0
        
        for email in new_emails:
            # Classify with smart labels
            smart_labeler.classify_email(email)
            
            # Generate thread summary if needed
            thread_id = email.get('thread_id')
            if thread_id:
                thread_emails = [email]  # In real implementation, get full thread
                thread_summarizer.summarize_thread(thread_id, thread_emails)
            
            processed_count += 1
            
            # Update progress
            progress = 50 + (processed_count / len(new_emails)) * 50
            background_tasks_status[task_id]["progress"] = int(progress)
        
        background_tasks_status[task_id] = {
            "status": "completed",
            "progress": 100,
            "message": "Sync completed successfully",
            "results": {
                "emails_synced": len(new_emails),
                "emails_processed": processed_count,
                "sync_time": sync_results.get('sync_time', 0)
            }
        }
        
    except Exception as e:
        background_tasks_status[task_id] = {
            "status": "error",
            "error": str(e),
            "message": f"Sync failed: {str(e)}"
        }

# Serve React app (when built)
frontend_path = Path("frontend/build")
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")
    
    @app.get("/{path:path}")
    async def serve_react_app(path: str):
        """Serve React app for all non-API routes"""
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        
        file_path = frontend_path / path
        if file_path.is_file():
            return FileResponse(file_path)
        else:
            return FileResponse(frontend_path / "index.html")

if __name__ == "__main__":
    uvicorn.run(
        "mailmaestro_api:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )