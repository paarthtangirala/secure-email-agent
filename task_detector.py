#!/usr/bin/env python3
"""
Task Detector - Extract structured tasks from email content
Part of MailMaestro-level intelligence layer
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from openai import OpenAI
from config import config

class TaskDetector:
    """Extract and structure tasks from email content"""
    
    def __init__(self, model_router=None):
        self.client = OpenAI()
        self.model_router = model_router
        
        # Task patterns for fast detection
        self.task_patterns = [
            r"(?:can you|could you|please|need you to|would you)\s+(.{10,100})",
            r"(?:action items?|tasks?|todo|to-do)[\s:]\s*(.{10,200})",
            r"(?:by|before|due)\s+(\w+day|\d{1,2}[/-]\d{1,2})",
            r"(?:deadline|due date|target date)[\s:]+(.{5,50})",
            r"(?:complete|finish|deliver|submit)\s+(.{10,100})",
        ]
        
        # Date patterns
        self.date_patterns = [
            r"(?:by|before|due)\s+(\w+day)",  # by Friday
            r"(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)",  # 12/25 or 12/25/24
            r"(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}",
            r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}",
            r"(?:next|this)\s+(?:week|month|monday|tuesday|wednesday|thursday|friday)",
            r"(?:tomorrow|today|asap|urgent)"
        ]
    
    def extract_tasks(self, email_text: str, email_metadata: Dict = None) -> List[Dict]:
        """
        Extract structured tasks from email content
        
        Args:
            email_text: Email body text
            email_metadata: Sender, subject, date info
            
        Returns:
            List of task dicts with structure:
            [{"task": str, "due_date": str, "owner": str, "priority": str, "confidence": float}]
        """
        try:
            # Quick pattern-based detection first
            pattern_tasks = self._extract_pattern_tasks(email_text)
            
            # Use LLM for comprehensive extraction
            llm_tasks = self._extract_llm_tasks(email_text, email_metadata)
            
            # Merge and deduplicate
            all_tasks = self._merge_tasks(pattern_tasks, llm_tasks)
            
            return all_tasks
            
        except Exception as e:
            print(f"Error extracting tasks: {e}")
            return []
    
    def _extract_pattern_tasks(self, email_text: str) -> List[Dict]:
        """Fast pattern-based task extraction"""
        tasks = []
        text_lower = email_text.lower()
        
        for pattern in self.task_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                task_text = match.group(1).strip()
                
                # Extract potential date
                due_date = self._extract_date_from_text(task_text)
                
                # Determine priority
                priority = self._determine_priority(task_text)
                
                tasks.append({
                    "task": task_text,
                    "due_date": due_date,
                    "owner": "me",  # Default assumption
                    "priority": priority,
                    "confidence": 0.7,
                    "source": "pattern"
                })
        
        return tasks
    
    def _extract_llm_tasks(self, email_text: str, email_metadata: Dict = None) -> List[Dict]:
        """LLM-powered task extraction"""
        try:
            # Choose model
            model = "gpt-4o-mini"
            if self.model_router:
                model = self.model_router.choose_model("tasks")
            
            # Build context
            sender = email_metadata.get('sender', 'Unknown') if email_metadata else 'Unknown'
            subject = email_metadata.get('subject', '') if email_metadata else ''
            
            prompt = f"""Extract action items/tasks from this email. Return ONLY valid JSON array.

Email from: {sender}
Subject: {subject}

Email content:
{email_text[:2000]}

Extract tasks in this exact format:
[
  {{
    "task": "specific action to take",
    "due_date": "YYYY-MM-DD or relative like 'this friday'",
    "owner": "me" or "sender" or "team",
    "priority": "low" or "medium" or "high" or "urgent",
    "confidence": 0.8
  }}
]

Rules:
- Only include actionable items requiring work
- Be specific about what needs to be done
- If no clear due date, use "none"
- Return empty array [] if no tasks found
- Must be valid JSON"""

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert at extracting actionable tasks from emails. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Clean JSON response (remove markdown code blocks)
            if response_text.startswith("```json"):
                response_text = response_text[7:]  # Remove ```json
            if response_text.startswith("```"):
                response_text = response_text[3:]   # Remove ```
            if response_text.endswith("```"):
                response_text = response_text[:-3]  # Remove ending ```
            response_text = response_text.strip()
            
            # Parse JSON response
            try:
                tasks = json.loads(response_text)
                if isinstance(tasks, list):
                    # Add source and normalize
                    for task in tasks:
                        task["source"] = "llm"
                        task["confidence"] = task.get("confidence", 0.8)
                    return tasks
            except json.JSONDecodeError:
                print(f"Invalid JSON from LLM: {response_text}")
            
            return []
            
        except Exception as e:
            print(f"LLM task extraction failed: {e}")
            return []
    
    def _extract_date_from_text(self, text: str) -> str:
        """Extract due date from text"""
        text_lower = text.lower()
        
        # Check for specific patterns
        for pattern in self.date_patterns:
            match = re.search(pattern, text_lower)
            if match:
                date_str = match.group()
                return self._parse_relative_date(date_str)
        
        return "none"
    
    def _parse_relative_date(self, date_str: str) -> str:
        """Convert relative dates to ISO format"""
        today = datetime.now()
        date_str = date_str.lower().strip()
        
        # Handle common relative dates
        if "today" in date_str:
            return today.strftime("%Y-%m-%d")
        elif "tomorrow" in date_str:
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "friday" in date_str:
            days_ahead = 4 - today.weekday()  # Friday is weekday 4
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        elif "monday" in date_str:
            days_ahead = 0 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        elif "next week" in date_str:
            return (today + timedelta(days=7)).strftime("%Y-%m-%d")
        elif "asap" in date_str or "urgent" in date_str:
            return today.strftime("%Y-%m-%d")
        
        # Try to parse specific dates (MM/DD format)
        date_match = re.search(r"(\d{1,2})[/-](\d{1,2})", date_str)
        if date_match:
            month, day = int(date_match.group(1)), int(date_match.group(2))
            try:
                # Assume current year
                year = today.year
                parsed_date = datetime(year, month, day)
                # If date is in the past, assume next year
                if parsed_date < today:
                    parsed_date = datetime(year + 1, month, day)
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                pass
        
        return date_str  # Return as-is if can't parse
    
    def _determine_priority(self, task_text: str) -> str:
        """Determine task priority from text content"""
        text_lower = task_text.lower()
        
        # Urgent indicators
        if any(word in text_lower for word in ["urgent", "asap", "immediately", "critical"]):
            return "urgent"
        
        # High priority indicators
        if any(word in text_lower for word in ["important", "priority", "deadline", "due"]):
            return "high"
        
        # Low priority indicators
        if any(word in text_lower for word in ["when you can", "no rush", "whenever"]):
            return "low"
        
        return "medium"  # Default
    
    def _merge_tasks(self, pattern_tasks: List[Dict], llm_tasks: List[Dict]) -> List[Dict]:
        """Merge and deduplicate tasks from different sources"""
        all_tasks = []
        
        # Add LLM tasks first (higher quality)
        for task in llm_tasks:
            all_tasks.append(task)
        
        # Add pattern tasks that don't overlap
        for pattern_task in pattern_tasks:
            is_duplicate = False
            for existing_task in all_tasks:
                # Simple similarity check
                if self._tasks_similar(pattern_task["task"], existing_task["task"]):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                all_tasks.append(pattern_task)
        
        # Sort by priority
        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        all_tasks.sort(key=lambda x: priority_order.get(x.get("priority", "medium"), 2))
        
        return all_tasks[:10]  # Limit to top 10 tasks
    
    def _tasks_similar(self, task1: str, task2: str) -> bool:
        """Check if two tasks are similar enough to be duplicates"""
        # Simple word overlap check
        words1 = set(task1.lower().split())
        words2 = set(task2.lower().split())
        
        overlap = len(words1.intersection(words2))
        min_length = min(len(words1), len(words2))
        
        return overlap / min_length > 0.6 if min_length > 0 else False

    def analyze_task_complexity(self, tasks: List[Dict]) -> Dict:
        """Analyze the complexity and workload of extracted tasks"""
        if not tasks:
            return {"total_tasks": 0, "complexity": "none"}
        
        total_tasks = len(tasks)
        urgent_count = sum(1 for t in tasks if t.get("priority") == "urgent")
        high_count = sum(1 for t in tasks if t.get("priority") == "high")
        
        complexity = "low"
        if urgent_count > 0 or high_count > 2:
            complexity = "high"
        elif high_count > 0 or total_tasks > 5:
            complexity = "medium"
        
        return {
            "total_tasks": total_tasks,
            "urgent_count": urgent_count,
            "high_priority_count": high_count,
            "complexity": complexity,
            "estimated_hours": total_tasks * 0.5  # Rough estimate
        }