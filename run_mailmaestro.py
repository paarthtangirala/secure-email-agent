#!/usr/bin/env python3
"""
MailMaestro Launcher - Production-ready startup script
Integrates all components and provides health checks
"""

import asyncio
import sys
import os
import time
import signal
import subprocess
from pathlib import Path
from typing import Dict, Any
import uvicorn
import webbrowser
from concurrent.futures import ThreadPoolExecutor

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import all components
from mailmaestro_api import app
from performance_optimizer import performance_optimizer
from privacy_guard import PrivacyGuard
from secure_processor import SecureProcessor
from email_database import EmailDatabase
from complete_email_sync import CompleteEmailSync

class MailMaestroLauncher:
    """Production launcher for MailMaestro system"""
    
    def __init__(self):
        self.processes = {}
        self.shutdown_event = asyncio.Event()
        
        # Component initialization
        self.db = EmailDatabase()
        self.privacy_guard = PrivacyGuard()
        self.secure_processor = SecureProcessor(self.privacy_guard)
        
        # Configuration
        self.config = {
            'api_host': '127.0.0.1',
            'api_port': 8000,
            'frontend_port': 3000,
            'auto_open_browser': True,
            'development_mode': True,
            'enable_performance_monitoring': True
        }
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if all required dependencies are available"""
        checks = {}
        
        # Check Python packages
        required_packages = [
            'fastapi', 'uvicorn', 'openai', 'google.auth',
            'cryptography', 'pandas', 'sqlalchemy'
        ]
        
        for package in required_packages:
            try:
                __import__(package)
                checks[f'python_{package}'] = True
            except ImportError:
                checks[f'python_{package}'] = False
        
        # Check optional packages
        optional_packages = [
            'spacy', 'transformers', 'redis', 'chromadb'
        ]
        
        for package in optional_packages:
            try:
                __import__(package)
                checks[f'optional_{package}'] = True
            except ImportError:
                checks[f'optional_{package}'] = False
        
        # Check database
        try:
            self.db.get_statistics()
            checks['database'] = True
        except Exception:
            checks['database'] = False
        
        # Check performance cache
        try:
            performance_optimizer.get_performance_metrics()
            checks['performance_cache'] = True
        except Exception:
            checks['performance_cache'] = False
        
        return checks
    
    def warm_up_system(self):
        """Warm up caches and initialize components"""
        print("🚀 Warming up MailMaestro system...")
        
        try:
            # Initialize performance cache
            sample_data = [
                {'subject': 'Test Email 1', 'content': 'This is a test email for cache warming.'},
                {'subject': 'Meeting Request', 'content': 'Let\'s schedule a meeting for next week.'},
                {'subject': 'Project Update', 'content': 'Please review the attached project documentation.'},
            ]
            
            performance_optimizer.warm_up_cache(sample_data)
            
            # Test AI components
            print("🧠 Testing AI components...")
            
            # Test privacy guard
            test_text = "Contact John Doe at john.doe@example.com for more information."
            privacy_analysis = self.privacy_guard.analyze_privacy_risk(test_text)
            print(f"   Privacy Guard: {len(privacy_analysis['detections'])} PII items detected")
            
            # Test secure processor
            test_email = {
                'id': 'test_email',
                'subject': 'Test Subject',
                'body': 'Test email body',
                'sender': 'test@example.com'
            }
            
            # Quick security test
            result = self.secure_processor.process_email_securely(test_email)
            print(f"   Secure Processor: Risk score {result.privacy_analysis['overall_risk_score']}")
            
            print("✅ System warm-up completed")
            
        except Exception as e:
            print(f"⚠️  Warm-up encountered issues: {e}")
    
    def start_backend(self):
        """Start the FastAPI backend server"""
        print(f"🔧 Starting MailMaestro API server on {self.config['api_host']}:{self.config['api_port']}")
        
        # Configure uvicorn
        config = uvicorn.Config(
            app=app,
            host=self.config['api_host'],
            port=self.config['api_port'],
            reload=self.config['development_mode'],
            log_level="info" if self.config['development_mode'] else "warning",
            access_log=self.config['development_mode']
        )
        
        server = uvicorn.Server(config)
        return server
    
    def start_frontend(self):
        """Start the React frontend development server"""
        frontend_path = Path(__file__).parent / 'frontend'
        
        if not frontend_path.exists():
            print("⚠️  Frontend directory not found. Backend-only mode.")
            return None
        
        print(f"🎨 Starting React frontend on port {self.config['frontend_port']}")
        
        try:
            # Check if npm install is needed
            node_modules = frontend_path / 'node_modules'
            if not node_modules.exists():
                print("📦 Installing frontend dependencies...")
                subprocess.run(['npm', 'install'], cwd=frontend_path, check=True)
            
            # Start development server
            process = subprocess.Popen(
                ['npm', 'start'],
                cwd=frontend_path,
                env={**os.environ, 'PORT': str(self.config['frontend_port'])},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            return process
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to start frontend: {e}")
            return None
        except FileNotFoundError:
            print("⚠️  npm not found. Install Node.js to use the frontend.")
            return None
    
    def open_browser(self):
        """Open browser to the application"""
        if self.config['auto_open_browser']:
            time.sleep(3)  # Wait for servers to start
            
            frontend_url = f"http://localhost:{self.config['frontend_port']}"
            api_url = f"http://{self.config['api_host']}:{self.config['api_port']}"
            
            try:
                # Try frontend first
                webbrowser.open(frontend_url)
                print(f"🌐 Opened browser to {frontend_url}")
            except Exception:
                try:
                    # Fallback to API docs
                    webbrowser.open(f"{api_url}/docs")
                    print(f"🌐 Opened browser to {api_url}/docs")
                except Exception:
                    print("🌐 Could not open browser automatically")
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        def signal_handler(signum, frame):
            print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def monitor_performance(self):
        """Monitor system performance"""
        if not self.config['enable_performance_monitoring']:
            return
        
        async def performance_monitor():
            while not self.shutdown_event.is_set():
                try:
                    await asyncio.sleep(30)  # Check every 30 seconds
                    
                    metrics = performance_optimizer.get_performance_metrics()
                    
                    # Log performance metrics
                    if metrics['total_requests'] > 0:
                        print(f"📊 Performance: {metrics['cache_hit_rate']}% cache hit rate, "
                              f"{metrics['average_response_time']}ms avg response time")
                    
                    # Cleanup expired cache entries periodically
                    if metrics['total_requests'] % 100 == 0:
                        performance_optimizer.cleanup_expired_cache()
                
                except Exception as e:
                    print(f"Performance monitoring error: {e}")
        
        return asyncio.create_task(performance_monitor())
    
    async def run(self):
        """Main run method"""
        print("🎯 MailMaestro - AI Email Assistant")
        print("=" * 50)
        
        # Check dependencies
        print("🔍 Checking system dependencies...")
        deps = self.check_dependencies()
        
        critical_deps = ['python_fastapi', 'python_uvicorn', 'database']
        missing_critical = [dep for dep in critical_deps if not deps.get(dep, False)]
        
        if missing_critical:
            print(f"❌ Critical dependencies missing: {missing_critical}")
            print("Please run: pip install -r requirements_mailmaestro.txt")
            return False
        
        print("✅ Core dependencies satisfied")
        
        # Warn about missing optional dependencies
        optional_missing = [dep for dep, available in deps.items() 
                          if dep.startswith('optional_') and not available]
        if optional_missing:
            print(f"⚠️  Optional features disabled (missing: {optional_missing})")
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        # Warm up system
        self.warm_up_system()
        
        # Start backend server
        server = self.start_backend()
        
        # Start frontend (if available)
        frontend_process = self.start_frontend()
        if frontend_process:
            self.processes['frontend'] = frontend_process
        
        # Start performance monitoring
        perf_monitor = self.monitor_performance()
        
        # Open browser
        browser_task = asyncio.create_task(
            asyncio.to_thread(self.open_browser)
        )
        
        print("\n🚀 MailMaestro is running!")
        print(f"   📡 API Server: http://{self.config['api_host']}:{self.config['api_port']}")
        print(f"   📊 API Docs: http://{self.config['api_host']}:{self.config['api_port']}/docs")
        
        if frontend_process:
            print(f"   🎨 Frontend: http://localhost:{self.config['frontend_port']}")
        
        print("\n💡 Features Available:")
        print("   • AI-powered email classification and labeling")
        print("   • Thread summarization with context")
        print("   • Task extraction and management")
        print("   • Smart reply generation (5+ styles)")
        print("   • Calendar integration and meeting detection")
        print("   • Privacy-first PII detection and redaction")
        print("   • High-performance caching and optimization")
        
        print("\n🛑 Press Ctrl+C to stop")
        
        try:
            # Run the server
            await server.serve()
        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested")
        finally:
            # Cleanup
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown"""
        print("🔄 Shutting down MailMaestro...")
        
        self.shutdown_event.set()
        
        # Stop frontend process
        if 'frontend' in self.processes:
            try:
                self.processes['frontend'].terminate()
                self.processes['frontend'].wait(timeout=5)
                print("✅ Frontend stopped")
            except Exception as e:
                print(f"⚠️  Frontend shutdown issue: {e}")
        
        # Final performance report
        try:
            metrics = performance_optimizer.get_performance_metrics()
            if metrics['total_requests'] > 0:
                print(f"📊 Final stats: {metrics['total_requests']} requests, "
                      f"{metrics['cache_hit_rate']}% cache hit rate")
        except Exception:
            pass
        
        print("👋 MailMaestro shutdown complete")

def main():
    """Main entry point"""
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    # Create and run launcher
    launcher = MailMaestroLauncher()
    
    try:
        asyncio.run(launcher.run())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()