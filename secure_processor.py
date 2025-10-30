#!/usr/bin/env python3
"""
Secure Processor - Enhanced security wrapper for AI processing
Integrates with privacy_guard for PII protection
"""

import json
import time
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from cryptography.fernet import Fernet

from privacy_guard import PrivacyGuard, PIIDetection
from thread_summarizer import ThreadSummarizer
from task_detector import TaskDetector
from calendar_extractor import CalendarExtractor
from smart_labeler import SmartLabeler

@dataclass
class SecurityContext:
    """Security context for processing operations"""
    allow_external_apis: bool = True
    require_pii_redaction: bool = True
    max_risk_score: int = 70
    encrypt_results: bool = False
    audit_log: bool = True

@dataclass
class ProcessingResult:
    """Secure processing result with privacy metadata"""
    result: Any
    privacy_analysis: Dict
    security_context: SecurityContext
    processing_time: float
    redacted_content: Optional[str] = None
    audit_id: str = None

class SecureProcessor:
    """Secure wrapper for AI processing with privacy protection"""
    
    def __init__(self, privacy_guard: PrivacyGuard = None):
        self.privacy_guard = privacy_guard or PrivacyGuard()
        self.audit_log = []
        
        # Initialize AI components
        self.thread_summarizer = ThreadSummarizer()
        self.task_detector = TaskDetector()
        self.calendar_extractor = CalendarExtractor()
        self.smart_labeler = SmartLabeler()
        
    def process_email_securely(self, email_data: Dict, 
                              security_context: SecurityContext = None) -> ProcessingResult:
        """
        Process email with comprehensive security and privacy protection
        
        Args:
            email_data: Email data dictionary
            security_context: Security requirements and constraints
            
        Returns:
            ProcessingResult with security metadata
        """
        start_time = time.time()
        context = security_context or SecurityContext()
        
        # Generate audit ID
        audit_id = f"proc_{int(time.time())}_{hash(email_data.get('id', ''))}"
        
        try:
            # 1. Privacy Analysis
            privacy_report = self.privacy_guard.create_privacy_report(email_data)
            
            # 2. Security Decision
            can_process = self._evaluate_security_clearance(privacy_report, context)
            
            if not can_process:
                return self._create_blocked_result(privacy_report, context, audit_id)
            
            # 3. Prepare Content for Processing
            processed_content = self._prepare_content_for_processing(
                email_data, privacy_report, context
            )
            
            # 4. Perform AI Processing
            ai_results = self._perform_ai_processing(processed_content, context)
            
            # 5. Secure Results
            final_result = self._secure_results(ai_results, context)
            
            # 6. Create Processing Result
            processing_time = time.time() - start_time
            
            result = ProcessingResult(
                result=final_result,
                privacy_analysis=privacy_report,
                security_context=context,
                processing_time=processing_time,
                redacted_content=processed_content.get('redacted_body'),
                audit_id=audit_id
            )
            
            # 7. Audit Logging
            if context.audit_log:
                self._log_processing_event(result)
            
            return result
            
        except Exception as e:
            # Log security exception
            self._log_security_exception(email_data, e, audit_id)
            raise
    
    def _evaluate_security_clearance(self, privacy_report: Dict, 
                                   context: SecurityContext) -> bool:
        """Evaluate if processing should proceed based on security context"""
        
        # Check risk score threshold
        if privacy_report['overall_risk_score'] > context.max_risk_score:
            return False
        
        # Check for specific high-risk PII types
        high_risk_types = {'ssn', 'credit_card', 'sensitive_data'}
        if any(pii_type in high_risk_types for pii_type in privacy_report['pii_types_found']):
            if context.require_pii_redaction and not context.allow_external_apis:
                return False
        
        return True
    
    def _prepare_content_for_processing(self, email_data: Dict, 
                                      privacy_report: Dict, 
                                      context: SecurityContext) -> Dict:
        """Prepare email content for secure AI processing"""
        
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        
        processed_content = {
            'original_subject': subject,
            'original_body': body,
            'subject': subject,
            'body': body,
            'redacted_subject': None,
            'redacted_body': None,
        }
        
        # Apply PII redaction if required
        if (context.require_pii_redaction and 
            privacy_report['overall_risk_score'] >= 50):
            
            # Redact subject
            if privacy_report['subject_analysis']['pii_count'] > 0:
                redacted_subject, _ = self.privacy_guard.redact_pii(
                    subject, privacy_report['subject_analysis']['detections']
                )
                processed_content['subject'] = redacted_subject
                processed_content['redacted_subject'] = redacted_subject
            
            # Redact body
            if privacy_report['body_analysis']['pii_count'] > 0:
                redacted_body, _ = self.privacy_guard.redact_pii(
                    body, privacy_report['body_analysis']['detections']
                )
                processed_content['body'] = redacted_body
                processed_content['redacted_body'] = redacted_body
        
        return processed_content
    
    def _perform_ai_processing(self, content: Dict, 
                             context: SecurityContext) -> Dict:
        """Perform AI processing with security constraints"""
        
        results = {}
        
        # Thread summarization
        try:
            if context.allow_external_apis:
                # Use full content for better results
                summary = self.thread_summarizer.summarize_thread(
                    'temp_thread', [{'body': content['body'], 'subject': content['subject']}]
                )
                results['summary'] = summary
            else:
                # Use local-only processing
                results['summary'] = "Summary unavailable (external API disabled)"
        except Exception as e:
            results['summary'] = f"Summary generation failed: {str(e)}"
        
        # Task detection
        try:
            tasks = self.task_detector.extract_tasks(
                content['body'],
                {'subject': content['subject'], 'sender': 'secure_processing'}
            )
            results['tasks'] = tasks
        except Exception as e:
            results['tasks'] = []
        
        # Calendar extraction
        try:
            meeting_info = self.calendar_extractor.extract_meeting_info(
                content['body'],
                {'subject': content['subject']}
            )
            results['meeting_info'] = meeting_info
        except Exception as e:
            results['meeting_info'] = None
        
        # Smart labeling
        try:
            labels = self.smart_labeler.classify_email({
                'id': 'temp_email',
                'subject': content['subject'],
                'body': content['body'],
                'sender': 'secure_processing'
            })
            results['labels'] = labels
        except Exception as e:
            results['labels'] = []
        
        return results
    
    def _secure_results(self, results: Dict, context: SecurityContext) -> Dict:
        """Apply additional security measures to results"""
        
        secured_results = results.copy()
        
        # Encrypt sensitive results if required
        if context.encrypt_results:
            for key, value in secured_results.items():
                if isinstance(value, (str, dict, list)):
                    try:
                        json_str = json.dumps(value) if not isinstance(value, str) else value
                        encrypted_value = self.privacy_guard.encrypt_sensitive_data(json_str)
                        secured_results[f"{key}_encrypted"] = encrypted_value
                        # Remove original if encryption successful
                        del secured_results[key]
                    except Exception:
                        # Keep original if encryption fails
                        pass
        
        # Add security metadata
        secured_results['_security'] = {
            'processed_securely': True,
            'encryption_applied': context.encrypt_results,
            'pii_redacted': context.require_pii_redaction,
            'external_apis_used': context.allow_external_apis,
            'timestamp': time.time()
        }
        
        return secured_results
    
    def _create_blocked_result(self, privacy_report: Dict, 
                             context: SecurityContext, 
                             audit_id: str) -> ProcessingResult:
        """Create result for blocked processing due to security constraints"""
        
        blocked_result = {
            'status': 'blocked',
            'reason': 'Security constraints prevent processing',
            'risk_score': privacy_report['overall_risk_score'],
            'max_allowed_risk': context.max_risk_score,
            'pii_types_detected': privacy_report['pii_types_found'],
            'recommendation': privacy_report.get('recommendation', 'Manual review required')
        }
        
        return ProcessingResult(
            result=blocked_result,
            privacy_analysis=privacy_report,
            security_context=context,
            processing_time=0.0,
            audit_id=audit_id
        )
    
    def _log_processing_event(self, result: ProcessingResult):
        """Log processing event for audit trail"""
        
        log_entry = {
            'audit_id': result.audit_id,
            'timestamp': time.time(),
            'risk_score': result.privacy_analysis['overall_risk_score'],
            'pii_detected': result.privacy_analysis['total_pii_detected'],
            'processing_time': result.processing_time,
            'external_apis_used': result.security_context.allow_external_apis,
            'pii_redacted': result.security_context.require_pii_redaction,
            'status': 'completed' if 'status' not in result.result else result.result['status']
        }
        
        self.audit_log.append(log_entry)
        
        # Keep only last 1000 entries
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
    
    def _log_security_exception(self, email_data: Dict, exception: Exception, audit_id: str):
        """Log security-related exceptions"""
        
        log_entry = {
            'audit_id': audit_id,
            'timestamp': time.time(),
            'event_type': 'security_exception',
            'exception': str(exception),
            'email_id': email_data.get('id'),
            'sender': email_data.get('sender', 'unknown')
        }
        
        self.audit_log.append(log_entry)
    
    def get_security_report(self, hours_back: int = 24) -> Dict:
        """Generate security processing report"""
        
        current_time = time.time()
        cutoff_time = current_time - (hours_back * 3600)
        
        # Filter recent events
        recent_events = [
            event for event in self.audit_log 
            if event['timestamp'] >= cutoff_time
        ]
        
        if not recent_events:
            return {
                'period_hours': hours_back,
                'total_processing_events': 0,
                'summary': 'No processing events in the specified period'
            }
        
        # Calculate statistics
        total_events = len(recent_events)
        completed_events = [e for e in recent_events if e.get('status') == 'completed']
        blocked_events = [e for e in recent_events if e.get('status') == 'blocked']
        exception_events = [e for e in recent_events if e.get('event_type') == 'security_exception']
        
        # Risk score statistics
        risk_scores = [e['risk_score'] for e in recent_events if 'risk_score' in e]
        avg_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        
        # PII detection statistics
        total_pii_detected = sum(e.get('pii_detected', 0) for e in recent_events)
        
        # Processing time statistics
        processing_times = [e.get('processing_time', 0) for e in completed_events]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        return {
            'period_hours': hours_back,
            'total_processing_events': total_events,
            'completed_successfully': len(completed_events),
            'blocked_by_security': len(blocked_events),
            'security_exceptions': len(exception_events),
            'average_risk_score': round(avg_risk_score, 2),
            'total_pii_detected': total_pii_detected,
            'average_processing_time': round(avg_processing_time, 3),
            'external_api_usage': sum(1 for e in recent_events if e.get('external_apis_used')),
            'pii_redaction_applied': sum(1 for e in recent_events if e.get('pii_redacted')),
            'recommendations': self._generate_security_recommendations(recent_events)
        }
    
    def _generate_security_recommendations(self, events: List[Dict]) -> List[str]:
        """Generate security recommendations based on processing patterns"""
        
        recommendations = []
        
        if not events:
            return recommendations
        
        # High risk score pattern
        high_risk_events = [e for e in events if e.get('risk_score', 0) > 70]
        if len(high_risk_events) > len(events) * 0.2:  # More than 20% high-risk
            recommendations.append(
                "Consider implementing stricter PII redaction policies for high-risk emails"
            )
        
        # Frequent blocking
        blocked_events = [e for e in events if e.get('status') == 'blocked']
        if len(blocked_events) > len(events) * 0.1:  # More than 10% blocked
            recommendations.append(
                "Review security thresholds as frequent blocking may impact functionality"
            )
        
        # Exception rate
        exception_events = [e for e in events if e.get('event_type') == 'security_exception']
        if len(exception_events) > 0:
            recommendations.append(
                "Investigate security exceptions to identify potential system vulnerabilities"
            )
        
        # PII detection rate
        pii_events = [e for e in events if e.get('pii_detected', 0) > 0]
        if len(pii_events) > len(events) * 0.5:  # More than 50% contain PII
            recommendations.append(
                "High PII detection rate - consider user training on email security practices"
            )
        
        return recommendations
    
    async def process_email_batch_securely(self, emails: List[Dict], 
                                         security_context: SecurityContext = None) -> List[ProcessingResult]:
        """Process multiple emails securely with concurrency control"""
        
        context = security_context or SecurityContext()
        
        # Limit concurrency for security
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent processes
        
        async def process_single_email(email_data):
            async with semaphore:
                return self.process_email_securely(email_data, context)
        
        # Create tasks for all emails
        tasks = [process_single_email(email) for email in emails]
        
        # Execute with concurrency control
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create error result
                error_result = ProcessingResult(
                    result={'status': 'error', 'error': str(result)},
                    privacy_analysis={'error': 'Processing failed'},
                    security_context=context,
                    processing_time=0.0,
                    audit_id=f"error_{int(time.time())}_{i}"
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        return processed_results