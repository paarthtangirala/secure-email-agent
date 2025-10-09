#!/usr/bin/env python3
"""
RAG-Enhanced Secure Email Agent with Cryostat-Style Retrieval
===========================================================

This is the enhanced version of ultimate_web_ui_v2.py with integrated
RAG (Retrieval-Augmented Generation) capabilities for grounded smart responses.

New Features:
- Knowledge-grounded Smart-Path responses
- Citation support with source references
- Retrieval performance optimization
- Enhanced prompt engineering with evidence
- UI updates for citation display
"""

# Import everything from the base version
import sys
import os
sys.path.append(os.path.dirname(__file__))

# Import all base functionality
from ultimate_web_ui_v2 import *

# Import RAG components
try:
    from retrieval import get_retriever, format_results_for_llm
    from knowledge_indexer import get_indexer
    RAG_AVAILABLE = True
    print("🧠 RAG components loaded successfully")
except ImportError as e:
    print(f"⚠️ RAG components not available: {e}")
    RAG_AVAILABLE = False

# Enhanced OpenAI prompt for grounded responses
GROUNDED_SYSTEM_PROMPT = """You are a grounded email assistant that provides accurate, evidence-based responses.

CRITICAL RULES:
1. Use ONLY the provided EVIDENCE to answer questions
2. If information is missing from evidence, ask ONE specific question
3. Include bracketed citations [1], [2], [3] when using evidence
4. Be concise (40-120 words per response)
5. Output valid JSON matching the exact schema
6. Never make up information not in the evidence

Your responses should be professional, helpful, and clearly cite sources."""

def create_grounded_prompt(email_data: dict, evidence: list, tone: str = "professional") -> dict:
    """Create enhanced prompt with retrieved evidence for grounded responses."""

    # Create thread summary (max 280 chars)
    subject = email_data.get('subject', '')[:100]
    sender = email_data.get('sender', '')[:50]
    thread_summary = f"Email from {sender}: {subject}"
    if len(thread_summary) > 280:
        thread_summary = thread_summary[:277] + "..."

    # Create latest email content (max 2000 chars)
    body = email_data.get('body_text', '')
    if len(body) > 2000:
        body = body[:1997] + "..."

    latest_email = f"Subject: {subject}\nFrom: {sender}\n\n{body}"

    # Prepare evidence with proper IDs
    formatted_evidence = []
    for i, item in enumerate(evidence[:3], 1):  # Max 3 pieces of evidence
        formatted_evidence.append({
            "id": i,
            "text": item.get("text", ""),
            "source": item.get("source", "Unknown")
        })

    # Create the prompt payload
    prompt_data = {
        "task": "Generate 3 short grounded email replies using ONLY the provided evidence.",
        "thread_summary": thread_summary,
        "latest_email": latest_email,
        "evidence": formatted_evidence,
        "tone": tone,
        "signature": "— Paarth"
    }

    return prompt_data

@app.get("/api/reply-suggestions")
async def reply_suggestions_rag(message_id: str, tone: str = "professional"):
    """Enhanced Fast-Path → Smart-Path reply generation with RAG"""
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

        # Prepare base response
        response_data = {
            "fast": fast_responses,
            "smart": None,
            "evidence": [],  # New field for evidence/citations
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
            "rag_available": RAG_AVAILABLE,
            "generation_time_ms": (time.time() - start_time) * 1000
        }

        # Launch Enhanced Smart-Path with RAG if available
        if not circuit_breaker_open and has_openai and RAG_AVAILABLE:
            async def generate_grounded_smart_responses():
                try:
                    smart_start = time.time()

                    # Step 1: Retrieve relevant evidence
                    retrieval_start = time.time()
                    retriever = get_retriever()

                    # Create retrieval query from email content
                    query_content = f"{email_data.get('subject', '')} {email_data.get('body_text', '')}"

                    # Retrieve evidence (target <150ms)
                    retrieved_results = retriever.retrieve(
                        query=query_content,
                        k=3,  # Get top 3 most relevant pieces
                        chunk_type=None  # Let router decide
                    )

                    retrieval_time = (time.time() - retrieval_start) * 1000
                    print(f"🔍 Retrieved {len(retrieved_results)} pieces of evidence in {retrieval_time:.1f}ms")

                    # Format evidence for LLM
                    formatted_evidence = format_results_for_llm(retrieved_results)

                    # Step 2: Generate grounded response if we have evidence
                    if formatted_evidence:
                        # Create enhanced prompt with evidence
                        prompt_data = create_grounded_prompt(email_data, formatted_evidence, tone)

                        # Make OpenAI API call with grounded prompt and timeout
                        client = openai.OpenAI(
                            api_key=openai_key,
                            timeout=15.0  # 15 second timeout
                        )

                        completion = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "system", "content": GROUNDED_SYSTEM_PROMPT},
                                {"role": "user", "content": json.dumps(prompt_data, indent=2)}
                            ],
                            response_format={"type": "json_object"},
                            temperature=0.7,
                            max_tokens=600,  # Reduced for faster responses
                            timeout=15.0
                        )

                        # Parse response
                        smart_response_text = completion.choices[0].message.content
                        smart_response = json.loads(smart_response_text)

                        # Enhance responses with generation metadata
                        smart_time = (time.time() - smart_start) * 1000

                        if isinstance(smart_response.get('responses'), list):
                            for i, response in enumerate(smart_response['responses']):
                                response.update({
                                    'id': f'smart_grounded_{i+1}',
                                    'generation_time_ms': smart_time,
                                    'method': 'grounded_gpt',
                                    'evidence_count': len(formatted_evidence),
                                    'retrieval_time_ms': retrieval_time
                                })

                        # Update global response with smart results and evidence
                        response_data["smart"] = smart_response.get('responses', [])
                        response_data["evidence"] = formatted_evidence

                        print(f"🤖 Generated {len(response_data['smart'])} grounded responses in {smart_time:.1f}ms")

                    else:
                        # Fall back to non-grounded response if no evidence
                        print("🔍 No relevant evidence found, falling back to standard response")
                        # Could implement fallback to original smart response here

                except openai.AuthenticationError:
                    print("❌ OpenAI Authentication failed")
                    smart_state.circuit_breaker.record_failure()
                except openai.RateLimitError:
                    print("⚠️ OpenAI Rate limit exceeded")
                    smart_state.circuit_breaker.record_failure()
                except openai.APITimeoutError:
                    print("⏱️ OpenAI request timed out (>15s)")
                    smart_state.circuit_breaker.record_failure()
                except openai.APIConnectionError:
                    print("🌐 OpenAI connection error")
                    smart_state.circuit_breaker.record_failure()
                except Exception as e:
                    print(f"❌ Smart response generation failed: {e}")
                    smart_state.circuit_breaker.record_failure()

            # Execute the enhanced smart response generation
            asyncio.create_task(generate_grounded_smart_responses())

        return response_data

    except Exception as e:
        print(f"Reply suggestions error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Add new endpoint for RAG-specific operations
@app.get("/api/rag/stats")
async def rag_stats():
    """Get RAG system statistics and health."""
    if not RAG_AVAILABLE:
        return {"available": False, "error": "RAG components not loaded"}

    try:
        # Get indexer stats
        indexer = get_indexer()
        index_stats = indexer.get_index_stats()

        # Get retriever performance stats
        retriever = get_retriever()
        retrieval_stats = retriever.get_performance_stats()

        return {
            "available": True,
            "indexing": index_stats,
            "retrieval": retrieval_stats,
            "status": "healthy" if retrieval_stats.get("average_time_ms", 999) < 200 else "slow"
        }
    except Exception as e:
        return {"available": True, "error": str(e), "status": "error"}

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

@app.post("/api/rag/reindex")
async def trigger_reindex(limit: int = 1000):
    """Trigger manual re-indexing of recent emails."""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG not available")

    try:
        indexer = get_indexer()

        # Run indexing in background
        def run_indexing():
            stats = indexer.batch_index_emails(limit=limit)
            print(f"📚 Manual re-indexing complete: {stats}")
            return stats

        # Start background task
        asyncio.create_task(asyncio.to_thread(run_indexing))

        return {
            "status": "started",
            "message": f"Re-indexing started for up to {limit} recent emails",
            "estimated_time_seconds": limit * 0.1  # Rough estimate
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Re-indexing failed: {e}")

@app.get("/api/rag/search")
async def rag_search(q: str, k: int = 5, chunk_type: str = None):
    """Direct RAG search endpoint for testing."""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG not available")

    try:
        retriever = get_retriever()
        results = retriever.retrieve(
            query=q,
            k=k,
            chunk_type=chunk_type
        )

        # Format results for API response
        formatted_results = []
        for result in results:
            formatted_results.append({
                "text": result.text,
                "source_title": result.source_title,
                "source_type": result.source_type,
                "relevance_score": result.relevance_score,
                "chunk_type": result.chunk_type,
                "citation_id": result.citation_id
            })

        return {
            "query": q,
            "results": formatted_results,
            "count": len(formatted_results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

# Enhanced HTML template with citation support
def get_enhanced_html_template():
    """Get the enhanced HTML template with RAG citation support."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🤖 RAG-Enhanced Email Agent</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }

            .container {
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }

            .header {
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }

            .header h1 {
                margin: 0;
                font-size: 2.5rem;
                font-weight: 700;
            }

            .subtitle {
                margin: 10px 0 0 0;
                opacity: 0.9;
                font-size: 1.1rem;
            }

            .controls-bar {
                padding: 20px;
                background: #ffffff;
                border-bottom: 1px solid #e2e8f0;
                display: flex;
                gap: 15px;
                align-items: center;
            }

            .search-container {
                flex: 1;
                display: flex;
                gap: 10px;
            }

            .search-input {
                flex: 1;
                padding: 12px 20px;
                border: 2px solid #e2e8f0;
                border-radius: 25px;
                font-size: 16px;
                transition: all 0.2s;
            }

            .search-input:focus {
                outline: none;
                border-color: #3b82f6;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
            }

            .btn {
                padding: 12px 24px;
                border: none;
                border-radius: 25px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                font-size: 14px;
                white-space: nowrap;
            }

            .btn-primary {
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
            }

            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }

            .btn-secondary {
                background: white;
                color: #667eea;
                border: 2px solid #667eea;
            }

            .btn-secondary:hover {
                background: #f0f4ff;
                transform: translateY(-2px);
            }

            .btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none !important;
            }

            .stats-bar {
                display: flex;
                justify-content: space-around;
                padding: 20px;
                background: #f8fafc;
                border-bottom: 1px solid #e2e8f0;
            }

            .stat-item {
                text-align: center;
            }

            .stat-value {
                font-size: 2rem;
                font-weight: bold;
                color: #4f46e5;
                margin: 0;
            }

            .stat-label {
                color: #64748b;
                margin: 5px 0 0 0;
                font-size: 0.9rem;
            }

            .main-content {
                display: flex;
                height: 600px;
            }

            .email-list {
                width: 400px;
                border-right: 1px solid #e2e8f0;
                overflow-y: auto;
                background: #fafafa;
            }

            .email-item {
                padding: 15px;
                border-bottom: 1px solid #e2e8f0;
                cursor: pointer;
                transition: all 0.2s;
            }

            .email-item:hover {
                background: #f1f5f9;
            }

            .email-item.selected {
                background: #dbeafe;
                border-left: 4px solid #3b82f6;
            }

            .email-subject {
                font-weight: 600;
                margin-bottom: 5px;
                color: #1e293b;
            }

            .email-meta {
                font-size: 0.9rem;
                color: #64748b;
                display: flex;
                justify-content: space-between;
            }

            .email-detail {
                flex: 1;
                padding: 30px;
                overflow-y: auto;
            }

            .email-header {
                border-bottom: 2px solid #e2e8f0;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }

            .email-title {
                font-size: 1.5rem;
                font-weight: bold;
                margin-bottom: 10px;
                color: #1e293b;
            }

            .email-info {
                color: #64748b;
                line-height: 1.6;
            }

            .email-body {
                background: #f8fafc;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 30px;
                line-height: 1.6;
                white-space: pre-wrap;
                border-left: 4px solid #3b82f6;
            }

            .response-section {
                margin-top: 30px;
            }

            .section-title {
                font-size: 1.3rem;
                font-weight: bold;
                margin-bottom: 20px;
                color: #1e293b;
                display: flex;
                align-items: center;
                gap: 10px;
            }

            .response-tabs {
                display: flex;
                margin-bottom: 20px;
                border-bottom: 2px solid #e2e8f0;
            }

            .tab {
                padding: 12px 24px;
                cursor: pointer;
                border: none;
                background: none;
                font-size: 1rem;
                font-weight: 600;
                color: #64748b;
                transition: all 0.2s;
                border-bottom: 3px solid transparent;
            }

            .tab.active {
                color: #3b82f6;
                border-bottom-color: #3b82f6;
            }

            .tab:hover {
                color: #3b82f6;
                background: #f1f5f9;
            }

            .tab-content {
                display: none;
            }

            .tab-content.active {
                display: block;
            }

            .response-card {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 15px;
                transition: all 0.2s;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }

            .response-card:hover {
                box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                transform: translateY(-2px);
            }

            .response-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }

            .response-title {
                font-weight: 600;
                color: #1e293b;
                font-size: 1.1rem;
            }

            .response-meta {
                font-size: 0.8rem;
                color: #64748b;
                display: flex;
                gap: 15px;
            }

            .response-body {
                color: #374151;
                line-height: 1.6;
                font-size: 1rem;
            }

            .citation {
                display: inline-block;
                background: #dbeafe;
                color: #1d4ed8;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 0.8rem;
                font-weight: 600;
                margin: 0 2px;
                cursor: pointer;
                transition: all 0.2s;
            }

            .citation:hover {
                background: #bfdbfe;
                transform: scale(1.1);
            }

            .evidence-section {
                margin-top: 20px;
                padding: 20px;
                background: #f8fafc;
                border-radius: 10px;
                border-left: 4px solid #059669;
            }

            .evidence-title {
                font-weight: 600;
                color: #059669;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .evidence-item {
                background: white;
                padding: 15px;
                margin-bottom: 10px;
                border-radius: 8px;
                border-left: 3px solid #10b981;
            }

            .evidence-source {
                font-size: 0.9rem;
                color: #059669;
                font-weight: 600;
                margin-bottom: 5px;
            }

            .evidence-text {
                color: #374151;
                line-height: 1.5;
            }

            .loading {
                text-align: center;
                padding: 40px;
                color: #64748b;
            }

            .loading-spinner {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid #e2e8f0;
                border-radius: 50%;
                border-top-color: #3b82f6;
                animation: spin 1s ease-in-out infinite;
                margin-right: 10px;
            }

            @keyframes spin {
                to { transform: rotate(360deg); }
            }

            .error {
                background: #fef2f2;
                border: 1px solid #fecaca;
                color: #dc2626;
                padding: 15px;
                border-radius: 8px;
                margin: 10px 0;
            }

            .rag-status {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 0.9rem;
                color: #059669;
                font-weight: 600;
            }

            .rag-badge {
                background: #d1fae5;
                color: #059669;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.8rem;
                font-weight: 600;
            }

            .copy-button {
                background: #3b82f6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 0.9rem;
                transition: all 0.2s;
            }

            .copy-button:hover {
                background: #2563eb;
                transform: translateY(-1px);
            }

            .toast {
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: #10b981;
                color: white;
                padding: 15px 20px;
                border-radius: 8px;
                font-weight: 600;
                opacity: 0;
                transform: translateY(100px);
                transition: all 0.3s;
                z-index: 1000;
            }

            .toast.show {
                opacity: 1;
                transform: translateY(0);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 RAG-Enhanced Email Agent</h1>
                <p class="subtitle">Intelligent responses powered by retrieval-augmented generation</p>
            </div>

            <div class="controls-bar">
                <div class="search-container">
                    <input type="text" id="searchInput" class="search-input" placeholder="🔍 Search your emails instantly...">
                    <button class="btn btn-primary" onclick="performSearch()">Search</button>
                </div>
                <button class="btn btn-secondary" onclick="syncEmails()">🔄 Sync Emails</button>
                <button class="btn btn-secondary" onclick="loadRecentEmails()">📥 Load Recent</button>
            </div>

            <div class="stats-bar">
                <div class="stat-item">
                    <div class="stat-value" id="totalEmails">0</div>
                    <div class="stat-label">Total Emails</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="ragStatus">🧠</div>
                    <div class="stat-label">RAG Status</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="avgResponseTime">0ms</div>
                    <div class="stat-label">Avg Response Time</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="evidenceCount">0</div>
                    <div class="stat-label">Evidence Sources</div>
                </div>
            </div>

            <div class="main-content">
                <div class="email-list" id="emailList">
                    <div class="loading">
                        <div class="loading-spinner"></div>
                        Loading emails...
                    </div>
                </div>

                <div class="email-detail" id="emailDetail">
                    <div style="text-align: center; padding: 100px 20px; color: #64748b;">
                        <h2>📧 Select an email to get started</h2>
                        <p>Choose an email from the list to see AI-powered response suggestions with citations.</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="toast" id="toast"></div>

        <script>
            let currentEmailId = null;
            let allEmails = [];
            let currentEvidence = [];

            // Load initial data
            loadStats();
            loadEmails();

            async function loadStats() {
                try {
                    const [statsResponse, ragResponse] = await Promise.all([
                        fetch('/api/stats'),
                        fetch('/api/rag/stats').catch(() => ({json: () => ({available: false})}))
                    ]);

                    const stats = await statsResponse.json();
                    const ragStats = await ragResponse.json();

                    document.getElementById('totalEmails').textContent = stats.total_emails?.toLocaleString() || '0';

                    // Update RAG status
                    const ragStatusEl = document.getElementById('ragStatus');
                    const evidenceCountEl = document.getElementById('evidenceCount');

                    if (ragStats.available) {
                        ragStatusEl.textContent = ragStats.status === 'healthy' ? '✅' : '⚠️';
                        evidenceCountEl.textContent = ragStats.indexing?.total_fine_chunks?.toLocaleString() || '0';
                        document.getElementById('avgResponseTime').textContent =
                            (ragStats.retrieval?.average_time_ms || 0).toFixed(0) + 'ms';
                    } else {
                        ragStatusEl.textContent = '❌';
                        evidenceCountEl.textContent = 'N/A';
                    }
                } catch (error) {
                    console.error('Failed to load stats:', error);
                }
            }

            async function loadEmails(query = '', days = 7, limit = 30) {
                try {
                    const listEl = document.getElementById('emailList');
                    listEl.innerHTML = '<div class="loading"><div class="loading-spinner"></div>Loading emails...</div>';

                    const params = new URLSearchParams({ days, limit });
                    if (query) params.append('query', query);

                    const response = await fetch(`/api/search-emails?${params}`);
                    const data = await response.json();
                    allEmails = data.results || [];
                    renderEmailList();
                } catch (error) {
                    console.error('Failed to load emails:', error);
                    document.getElementById('emailList').innerHTML =
                        '<div class="error">Failed to load emails</div>';
                }
            }

            async function performSearch() {
                const query = document.getElementById('searchInput').value.trim();
                if (query) {
                    await loadEmails(query, 30, 50);
                } else {
                    await loadEmails('', 7, 30);
                }
            }

            async function loadRecentEmails() {
                document.getElementById('searchInput').value = '';
                await loadEmails('', 7, 30);
            }

            async function syncEmails() {
                try {
                    const btn = event.target;
                    btn.disabled = true;
                    btn.innerHTML = '⏳ Syncing...';

                    showToast('🔄 Starting email sync...');

                    const response = await fetch('/api/sync-all-emails', { method: 'POST' });
                    const result = await response.json();

                    if (result.success) {
                        showToast(`✅ Sync completed! Processed ${result.processed_count || 'some'} emails`);
                        await loadStats();
                        await loadRecentEmails();
                    } else {
                        showToast('❌ Sync failed: ' + result.error);
                    }
                } catch (error) {
                    console.error('Sync error:', error);
                    showToast('❌ Sync failed');
                } finally {
                    const btn = event.target;
                    btn.disabled = false;
                    btn.innerHTML = '🔄 Sync Emails';
                }
            }

            // Add Enter key support for search
            document.addEventListener('DOMContentLoaded', () => {
                const searchInput = document.getElementById('searchInput');
                if (searchInput) {
                    searchInput.addEventListener('keypress', (e) => {
                        if (e.key === 'Enter') {
                            performSearch();
                        }
                    });
                }
            });

            function renderEmailList() {
                const listEl = document.getElementById('emailList');
                if (allEmails.length === 0) {
                    listEl.innerHTML = '<div class="loading">No emails found</div>';
                    return;
                }

                listEl.innerHTML = allEmails.map(email => `
                    <div class="email-item" onclick="selectEmail('${email.id}')" data-id="${email.id}">
                        <div class="email-subject">${escapeHtml(email.subject || 'No Subject')}</div>
                        <div class="email-meta">
                            <span>${escapeHtml(email.sender || 'Unknown')}</span>
                            <span>${new Date(email.date_received).toLocaleDateString()}</span>
                        </div>
                    </div>
                `).join('');
            }

            async function selectEmail(emailId) {
                currentEmailId = emailId;

                // Update UI selection
                document.querySelectorAll('.email-item').forEach(item => {
                    item.classList.toggle('selected', item.dataset.id === emailId);
                });

                // Find email data
                const email = allEmails.find(e => e.id === emailId);
                if (!email) return;

                // Show email details
                showEmailDetail(email);

                // Load responses
                await loadResponses(emailId);
            }

            function showEmailDetail(email) {
                const detailEl = document.getElementById('emailDetail');
                detailEl.innerHTML = `
                    <div class="email-header">
                        <div class="email-title">${escapeHtml(email.subject || 'No Subject')}</div>
                        <div class="email-info">
                            <strong>From:</strong> ${escapeHtml(email.sender || 'Unknown')}<br>
                            <strong>Date:</strong> ${new Date(email.date_received).toLocaleString()}<br>
                            <strong>Classification:</strong> ${escapeHtml(email.classification || 'Unknown')}
                        </div>
                    </div>

                    <div class="email-body">
                        ${escapeHtml(email.body_text || 'No content available')}
                    </div>

                    <div class="response-section">
                        <div class="section-title">
                            ⚡ AI Response Options
                            <div class="rag-badge">RAG-Enhanced</div>
                        </div>

                        <div class="response-tabs">
                            <button class="tab active" onclick="switchTab('instant')">
                                🚀 Instant (3)
                            </button>
                            <button class="tab" onclick="switchTab('grounded')" id="groundedTab">
                                🧠 Grounded (Loading...)
                            </button>
                        </div>

                        <div class="tab-content active" id="instantContent">
                            <div class="loading">
                                <div class="loading-spinner"></div>
                                Generating instant responses...
                            </div>
                        </div>

                        <div class="tab-content" id="groundedContent">
                            <div class="loading">
                                <div class="loading-spinner"></div>
                                🧠 Generating grounded responses with evidence...
                            </div>
                        </div>

                        <div class="evidence-section" id="evidenceSection" style="display: none;">
                            <div class="evidence-title">
                                📚 Evidence Sources
                                <span class="rag-status">Retrieved from knowledge base</span>
                            </div>
                            <div id="evidenceItems"></div>
                        </div>
                    </div>
                `;
            }

            async function loadResponses(emailId) {
                try {
                    const response = await fetch(`/api/reply-suggestions?message_id=${emailId}&tone=professional`);
                    const data = await response.json();

                    // Show instant responses immediately
                    if (data.fast && data.fast.length > 0) {
                        renderInstantResponses(data.fast);
                    }

                    // Show grounded responses when available
                    if (data.smart && data.smart.length > 0) {
                        renderGroundedResponses(data.smart);
                        document.getElementById('groundedTab').textContent =
                            `🧠 Grounded (${data.smart.length})`;
                    }

                    // Show evidence if available
                    if (data.evidence && data.evidence.length > 0) {
                        currentEvidence = data.evidence;
                        renderEvidence(data.evidence);
                    }

                    // Update tab status
                    if (!data.openai_available) {
                        document.getElementById('groundedTab').textContent = '🔑 Grounded (Setup Required)';
                        document.getElementById('groundedContent').innerHTML = `
                            <div style="text-align: center; padding: 30px; color: #666;">
                                <h3>🔑 OpenAI Not Configured</h3>
                                <p>To enable grounded responses with citations, add your OpenAI API key.</p>
                                <p><strong>The instant responses above work perfectly without OpenAI!</strong></p>
                            </div>
                        `;
                    } else if (!data.rag_available) {
                        document.getElementById('groundedTab').textContent = '📚 Grounded (RAG N/A)';
                        document.getElementById('groundedContent').innerHTML = `
                            <div style="text-align: center; padding: 30px; color: #666;">
                                <h3>📚 RAG Components Not Available</h3>
                                <p>Knowledge indexing and retrieval components need to be installed.</p>
                                <p>Install: <code>pip install chromadb sentence-transformers PyPDF2</code></p>
                            </div>
                        `;
                    }

                } catch (error) {
                    console.error('Failed to load responses:', error);
                    document.getElementById('instantContent').innerHTML =
                        '<div class="error">Failed to load responses</div>';
                }
            }

            function renderInstantResponses(responses) {
                const content = responses.map(response => `
                    <div class="response-card">
                        <div class="response-header">
                            <div class="response-title">${escapeHtml(response.title)}</div>
                            <div class="response-meta">
                                <span>⚡ ${response.generation_time_ms?.toFixed(1)}ms</span>
                                <span>📊 ${response.confidence}% confidence</span>
                                <button class="copy-button" onclick="copyResponse('${escapeHtml(response.body)}')">
                                    📋 Copy
                                </button>
                            </div>
                        </div>
                        <div class="response-body">${escapeHtml(response.body)}</div>
                    </div>
                `).join('');

                document.getElementById('instantContent').innerHTML = content;
            }

            function renderGroundedResponses(responses) {
                const content = responses.map(response => `
                    <div class="response-card">
                        <div class="response-header">
                            <div class="response-title">${escapeHtml(response.title || 'Grounded Response')}</div>
                            <div class="response-meta">
                                <span>🧠 ${response.generation_time_ms?.toFixed(1)}ms</span>
                                <span>📚 ${response.evidence_count || 0} sources</span>
                                <button class="copy-button" onclick="copyResponse('${escapeHtml(response.body)}')">
                                    📋 Copy
                                </button>
                            </div>
                        </div>
                        <div class="response-body">${addCitationHighlights(escapeHtml(response.body))}</div>
                    </div>
                `).join('');

                document.getElementById('groundedContent').innerHTML = content;
            }

            function renderEvidence(evidence) {
                const evidenceItems = evidence.map(item => `
                    <div class="evidence-item" id="evidence-${item.id}">
                        <div class="evidence-source">[${item.id}] ${escapeHtml(item.source)}</div>
                        <div class="evidence-text">${escapeHtml(item.text)}</div>
                    </div>
                `).join('');

                document.getElementById('evidenceItems').innerHTML = evidenceItems;
                document.getElementById('evidenceSection').style.display = 'block';
            }

            function addCitationHighlights(text) {
                // Convert citation markers like [1], [2], [3] to clickable elements
                return text.replace(/\\[(\\d+)\\]/g,
                    '<span class="citation" onclick="highlightEvidence($1)">[$1]</span>');
            }

            function highlightEvidence(citationId) {
                // Highlight the corresponding evidence item
                document.querySelectorAll('.evidence-item').forEach(item => {
                    item.style.background = 'white';
                });

                const evidenceItem = document.getElementById(`evidence-${citationId}`);
                if (evidenceItem) {
                    evidenceItem.style.background = '#fef3c7';
                    evidenceItem.scrollIntoView({ behavior: 'smooth', block: 'center' });

                    // Reset highlight after 3 seconds
                    setTimeout(() => {
                        evidenceItem.style.background = 'white';
                    }, 3000);
                }
            }

            function switchTab(tabName) {
                // Update tab buttons
                document.querySelectorAll('.tab').forEach(tab => {
                    tab.classList.remove('active');
                });
                event.target.classList.add('active');

                // Update tab content
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                document.getElementById(tabName + 'Content').classList.add('active');
            }

            function copyResponse(text) {
                navigator.clipboard.writeText(text).then(() => {
                    showToast('Response copied to clipboard!');
                }).catch(err => {
                    console.error('Failed to copy:', err);
                    showToast('Failed to copy response');
                });
            }

            function showToast(message) {
                const toast = document.getElementById('toast');
                toast.textContent = message;
                toast.classList.add('show');
                setTimeout(() => {
                    toast.classList.remove('show');
                }, 3000);
            }

            function escapeHtml(text) {
                if (!text) return '';
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            // Auto-refresh stats every 30 seconds
            setInterval(loadStats, 30000);
        </script>
    </body>
    </html>
    """

# Replace the main route with enhanced version
@app.get("/")
async def enhanced_root():
    """Enhanced root endpoint with RAG support."""
    return HTMLResponse(content=get_enhanced_html_template())

if __name__ == "__main__":
    # Initialize RAG components if available
    if RAG_AVAILABLE:
        print("🚀 Starting RAG-Enhanced Email Agent...")
        print("📚 Initializing knowledge indexer...")
        indexer = get_indexer()
        print("🔍 Initializing retrieval system...")
        retriever = get_retriever()
        print("✅ RAG components ready!")
    else:
        print("⚠️ Starting without RAG (install: pip install chromadb sentence-transformers PyPDF2)")

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8600, log_level="info")