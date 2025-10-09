#!/usr/bin/env python3
"""
Perplexity-Style Email Agent - Multi-step reasoning with structured workflow
Mimics Perplexity's approach to handling complex requests step-by-step
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class AgentStep:
    step_number: int
    description: str
    status: str  # "pending", "in_progress", "completed", "failed"
    result: Optional[Dict] = None
    timestamp: Optional[datetime] = None

class PerplexityStyleEmailAgent:
    """
    Multi-step email agent that breaks down complex tasks into clear steps,
    just like Perplexity's browser agent approach
    """

    def __init__(self):
        self.current_workflow = []

    def process_request(self, user_request: str, email_context: Dict) -> List[AgentStep]:
        """
        Main entry point - processes user request step by step like Perplexity
        """
        print(f"🤖 Processing: {user_request}")

        # Step 1: Parse and understand the request
        workflow = self._plan_workflow(user_request, email_context)

        # Step 2: Execute each step sequentially
        for step in workflow:
            self._execute_step(step, email_context)

        return workflow

    def _plan_workflow(self, request: str, context: Dict) -> List[AgentStep]:
        """
        Plan the workflow steps needed to fulfill the request
        Similar to how Perplexity breaks down complex queries
        """
        workflow = []

        # Analyze what the user is asking for
        if "calendar" in request.lower() or "meeting" in request.lower():
            workflow.extend([
                AgentStep(1, "Parse email content for meeting details", "pending"),
                AgentStep(2, "Extract date, time, and attendees", "pending"),
                AgentStep(3, "Authenticate with Google Calendar", "pending"),
                AgentStep(4, "Create calendar event", "pending"),
                AgentStep(5, "Send confirmation to user", "pending")
            ])

        elif "respond" in request.lower() or "reply" in request.lower():
            workflow.extend([
                AgentStep(1, "Analyze email sentiment and intent", "pending"),
                AgentStep(2, "Generate appropriate response options", "pending"),
                AgentStep(3, "Present responses to user for selection", "pending")
            ])

        elif "extract" in request.lower() or "information" in request.lower():
            workflow.extend([
                AgentStep(1, "Identify key information in email", "pending"),
                AgentStep(2, "Structure extracted data", "pending"),
                AgentStep(3, "Present formatted results", "pending")
            ])

        self.current_workflow = workflow
        return workflow

    def _execute_step(self, step: AgentStep, context: Dict):
        """Execute a single workflow step with progress tracking"""
        step.status = "in_progress"
        step.timestamp = datetime.now()

        print(f"📋 Step {step.step_number}: {step.description}")

        try:
            # Route to appropriate handler based on step content
            if "meeting details" in step.description:
                step.result = self._parse_meeting_details(context)
            elif "extract date" in step.description:
                step.result = self._extract_temporal_info(context)
            elif "authenticate" in step.description:
                step.result = self._handle_authentication()
            elif "create calendar" in step.description:
                step.result = self._create_calendar_event(context)
            elif "analyze email" in step.description:
                step.result = self._analyze_email_intent(context)
            elif "generate response" in step.description:
                step.result = self._generate_responses(context)
            else:
                step.result = {"message": "Step completed"}

            step.status = "completed"
            print(f"✅ Step {step.step_number} completed")

        except Exception as e:
            step.status = "failed"
            step.result = {"error": str(e)}
            print(f"❌ Step {step.step_number} failed: {e}")

    def _parse_meeting_details(self, context: Dict) -> Dict:
        """Parse meeting information from email - Step 1 of calendar workflow"""
        email_text = f"{context.get('subject', '')} {context.get('body', '')}"

        # Use existing calendar detector logic
        from calendar_detector import CalendarDetector
        detector = CalendarDetector()

        if detector.is_meeting_invitation(context.get('subject', ''), context.get('body', '')):
            details = detector.extract_meeting_details(context.get('subject', ''), context.get('body', ''))
            return {
                "is_meeting": True,
                "details": details,
                "confidence": 0.95
            }

        return {"is_meeting": False, "reason": "No meeting indicators found"}

    def _extract_temporal_info(self, context: Dict) -> Dict:
        """Extract dates, times, durations - Step 2 of calendar workflow"""
        from calendar_detector import CalendarDetector
        detector = CalendarDetector()

        content = f"{context.get('subject', '')} {context.get('body', '')}"

        return {
            "date": detector.extract_date(content),
            "time": detector.extract_time(content),
            "duration": detector.extract_duration(content),
            "location": detector.extract_location(content)
        }

    def _handle_authentication(self) -> Dict:
        """Handle Google API authentication - Step 3 of calendar workflow"""
        try:
            from auth import GoogleAuth
            auth = GoogleAuth()
            creds = auth.get_credentials()

            if creds:
                return {"authenticated": True, "service": "google_calendar"}
            else:
                return {"authenticated": False, "error": "No valid credentials"}

        except Exception as e:
            return {"authenticated": False, "error": str(e)}

    def _create_calendar_event(self, context: Dict) -> Dict:
        """Create the actual calendar event - Step 4 of calendar workflow"""
        from calendar_detector import CalendarDetector
        detector = CalendarDetector()

        result = detector.process_email(context)
        return result or {"created": False, "error": "Event creation failed"}

    def _analyze_email_intent(self, context: Dict) -> Dict:
        """Analyze email for response generation - Step 1 of response workflow"""
        from instant_response_system import InstantResponseSystem
        system = InstantResponseSystem()

        subject = context.get('subject', '')
        body = context.get('body_text', context.get('body', ''))

        email_type = system.detect_email_type(subject, body)

        return {
            "email_type": email_type,
            "sentiment": "neutral",  # Could add sentiment analysis
            "urgency": "normal",     # Could add urgency detection
            "requires_response": True
        }

    def _generate_responses(self, context: Dict) -> Dict:
        """Generate response options - Step 2 of response workflow"""
        from instant_response_system import InstantResponseSystem
        system = InstantResponseSystem()

        responses = system.generate_instant_responses(context)

        return {
            "responses_generated": len(responses),
            "options": responses,
            "generation_time_ms": responses[0].get('generation_time_ms', 0) if responses else 0
        }

def demo_perplexity_style_workflow():
    """Demo showing Perplexity-style step-by-step processing"""
    agent = PerplexityStyleEmailAgent()

    # Example: Process a meeting invitation
    sample_email = {
        "subject": "Team Meeting Tomorrow at 2 PM",
        "body": "Hi team, let's have our weekly sync tomorrow at 2:00 PM in the conference room.",
        "sender": "john@company.com"
    }

    print("🚀 PERPLEXITY-STYLE EMAIL AGENT DEMO")
    print("=" * 50)

    workflow = agent.process_request("Create a calendar event from this email", sample_email)

    print("\n📊 WORKFLOW SUMMARY:")
    for step in workflow:
        status_emoji = {"completed": "✅", "failed": "❌", "pending": "⏳"}
        print(f"{status_emoji.get(step.status, '❓')} Step {step.step_number}: {step.description}")
        if step.result:
            print(f"   Result: {json.dumps(step.result, indent=2)[:100]}...")

if __name__ == "__main__":
    demo_perplexity_style_workflow()