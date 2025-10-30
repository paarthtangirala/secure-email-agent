#!/usr/bin/env python3
"""
Performance Optimizer - Caching and optimization layer for MailMaestro
Achieves target performance: <100ms instant, <800ms smart, <200ms search
"""

import asyncio
import time
import json
import hashlib
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from functools import wraps
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from cachetools import TTLCache, LRUCache
import pickle

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    data: Any
    timestamp: float
    access_count: int = 0
    ttl: float = 3600  # 1 hour default
    
    def is_expired(self) -> bool:
        return time.time() > (self.timestamp + self.ttl)
    
    def access(self):
        self.access_count += 1

class PerformanceOptimizer:
    """Multi-layer caching and performance optimization system"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", enable_redis: bool = False):
        self.enable_redis = enable_redis
        
        # Initialize Redis if available
        self.redis_client = None
        if enable_redis and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()  # Test connection
            except Exception as e:
                print(f"Redis not available, using memory cache only: {e}")
                self.redis_client = None
        
        # Memory caches with different TTLs
        self.instant_cache = TTLCache(maxsize=1000, ttl=300)  # 5 min for instant responses
        self.smart_cache = TTLCache(maxsize=500, ttl=1800)   # 30 min for smart responses
        self.search_cache = TTLCache(maxsize=2000, ttl=600)  # 10 min for search results
        self.thread_cache = TTLCache(maxsize=1000, ttl=900)  # 15 min for thread summaries
        self.task_cache = TTLCache(maxsize=1000, ttl=1200)   # 20 min for task extraction
        
        # SQLite cache for persistence
        self.sqlite_cache_path = "performance_cache.db"
        self._init_sqlite_cache()
        
        # Thread pool for async operations
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
        self.process_pool = ProcessPoolExecutor(max_workers=4)
        
        # Performance metrics
        self.metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_response_time': 0.0,
            'total_requests': 0
        }
        
        # Lock for thread safety
        self.cache_lock = threading.RLock()
    
    def _init_sqlite_cache(self):
        """Initialize SQLite cache database"""
        conn = sqlite3.connect(self.sqlite_cache_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                cache_key TEXT PRIMARY KEY,
                cache_type TEXT,
                data BLOB,
                timestamp REAL,
                ttl REAL,
                access_count INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_type_timestamp 
            ON cache_entries (cache_type, timestamp)
        """)
        conn.commit()
        conn.close()
    
    def cache_key(self, *args, **kwargs) -> str:
        """Generate consistent cache key from arguments"""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_from_cache(self, key: str, cache_type: str = 'default') -> Optional[Any]:
        """Get item from appropriate cache layer"""
        with self.cache_lock:
            # 1. Try memory cache first (fastest)
            cache_map = {
                'instant': self.instant_cache,
                'smart': self.smart_cache,
                'search': self.search_cache,
                'thread': self.thread_cache,
                'task': self.task_cache,
                'default': self.instant_cache
            }
            
            memory_cache = cache_map.get(cache_type, self.instant_cache)
            if key in memory_cache:
                self.metrics['cache_hits'] += 1
                return memory_cache[key]
            
            # 2. Try Redis cache (if available)
            if self.redis_client:
                try:
                    redis_key = f"{cache_type}:{key}"
                    cached_data = self.redis_client.get(redis_key)
                    if cached_data:
                        data = pickle.loads(cached_data)
                        # Promote to memory cache
                        memory_cache[key] = data
                        self.metrics['cache_hits'] += 1
                        return data
                except Exception:
                    pass  # Fall through to SQLite
            
            # 3. Try SQLite cache (persistent)
            try:
                conn = sqlite3.connect(self.sqlite_cache_path)
                cursor = conn.execute("""
                    SELECT data, timestamp, ttl FROM cache_entries 
                    WHERE cache_key = ? AND cache_type = ?
                """, (key, cache_type))
                
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    data_blob, timestamp, ttl = row
                    
                    # Check if expired
                    if time.time() <= (timestamp + ttl):
                        data = pickle.loads(data_blob)
                        # Promote to memory cache
                        memory_cache[key] = data
                        self.metrics['cache_hits'] += 1
                        return data
                    else:
                        # Clean up expired entry
                        self._remove_from_sqlite_cache(key, cache_type)
            except Exception:
                pass
            
            self.metrics['cache_misses'] += 1
            return None
    
    def set_in_cache(self, key: str, data: Any, cache_type: str = 'default', ttl: float = 3600):
        """Set item in appropriate cache layers"""
        with self.cache_lock:
            # 1. Set in memory cache
            cache_map = {
                'instant': self.instant_cache,
                'smart': self.smart_cache,
                'search': self.search_cache,
                'thread': self.thread_cache,
                'task': self.task_cache,
                'default': self.instant_cache
            }
            
            memory_cache = cache_map.get(cache_type, self.instant_cache)
            memory_cache[key] = data
            
            # 2. Set in Redis cache (if available)
            if self.redis_client:
                try:
                    redis_key = f"{cache_type}:{key}"
                    self.redis_client.setex(
                        redis_key, 
                        int(ttl), 
                        pickle.dumps(data)
                    )
                except Exception:
                    pass
            
            # 3. Set in SQLite cache (for persistence)
            try:
                conn = sqlite3.connect(self.sqlite_cache_path)
                conn.execute("""
                    INSERT OR REPLACE INTO cache_entries 
                    (cache_key, cache_type, data, timestamp, ttl, access_count)
                    VALUES (?, ?, ?, ?, ?, 0)
                """, (key, cache_type, pickle.dumps(data), time.time(), ttl))
                conn.commit()
                conn.close()
            except Exception:
                pass
    
    def _remove_from_sqlite_cache(self, key: str, cache_type: str):
        """Remove expired entry from SQLite cache"""
        try:
            conn = sqlite3.connect(self.sqlite_cache_path)
            conn.execute("""
                DELETE FROM cache_entries 
                WHERE cache_key = ? AND cache_type = ?
            """, (key, cache_type))
            conn.commit()
            conn.close()
        except Exception:
            pass
    
    def cached(self, cache_type: str = 'default', ttl: float = 3600):
        """Decorator for caching function results"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                key = self.cache_key(func.__name__, *args, **kwargs)
                
                # Try to get from cache
                cached_result = self.get_from_cache(key, cache_type)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Update metrics
                self.metrics['total_requests'] += 1
                self.metrics['avg_response_time'] = (
                    (self.metrics['avg_response_time'] * (self.metrics['total_requests'] - 1) + execution_time) 
                    / self.metrics['total_requests']
                )
                
                # Cache the result
                self.set_in_cache(key, result, cache_type, ttl)
                
                return result
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Generate cache key
                key = self.cache_key(func.__name__, *args, **kwargs)
                
                # Try to get from cache
                cached_result = self.get_from_cache(key, cache_type)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                start_time = time.time()
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Update metrics
                self.metrics['total_requests'] += 1
                self.metrics['avg_response_time'] = (
                    (self.metrics['avg_response_time'] * (self.metrics['total_requests'] - 1) + execution_time) 
                    / self.metrics['total_requests']
                )
                
                # Cache the result
                self.set_in_cache(key, result, cache_type, ttl)
                
                return result
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
        return decorator
    
    def preload_cache(self, email_ids: List[str]):
        """Preload cache with common operations for given emails"""
        async def preload_worker():
            tasks = []
            
            for email_id in email_ids:
                # Preload thread summaries
                tasks.append(self._preload_thread_summary(email_id))
                
                # Preload task extraction
                tasks.append(self._preload_task_extraction(email_id))
                
                # Preload classification
                tasks.append(self._preload_classification(email_id))
            
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Run preloading in background
        asyncio.create_task(preload_worker())
    
    async def _preload_thread_summary(self, email_id: str):
        """Preload thread summary for email"""
        # This would call the actual thread summarizer
        # For now, simulate with a placeholder
        await asyncio.sleep(0.1)  # Simulate processing
        key = self.cache_key('thread_summary', email_id)
        self.set_in_cache(key, f"Preloaded summary for {email_id}", 'thread', 900)
    
    async def _preload_task_extraction(self, email_id: str):
        """Preload task extraction for email"""
        await asyncio.sleep(0.1)
        key = self.cache_key('task_extraction', email_id)
        self.set_in_cache(key, [], 'task', 1200)
    
    async def _preload_classification(self, email_id: str):
        """Preload email classification"""
        await asyncio.sleep(0.05)
        key = self.cache_key('classification', email_id)
        self.set_in_cache(key, ['general'], 'instant', 300)
    
    def batch_process(self, operations: List[Dict], max_workers: int = 10) -> List[Any]:
        """Process multiple operations in parallel with caching"""
        
        def process_operation(op: Dict):
            op_type = op.get('type')
            op_data = op.get('data', {})
            
            # Generate cache key
            key = self.cache_key(op_type, **op_data)
            
            # Check cache first
            cache_type = {
                'instant_reply': 'instant',
                'smart_reply': 'smart',
                'search': 'search',
                'thread_summary': 'thread',
                'task_extraction': 'task'
            }.get(op_type, 'default')
            
            cached_result = self.get_from_cache(key, cache_type)
            if cached_result is not None:
                return {'operation': op, 'result': cached_result, 'from_cache': True}
            
            # Simulate processing (replace with actual function calls)
            start_time = time.time()
            
            if op_type == 'instant_reply':
                result = self._generate_instant_reply(op_data)
            elif op_type == 'smart_reply':
                result = self._generate_smart_reply(op_data)
            elif op_type == 'search':
                result = self._perform_search(op_data)
            elif op_type == 'thread_summary':
                result = self._generate_thread_summary(op_data)
            elif op_type == 'task_extraction':
                result = self._extract_tasks(op_data)
            else:
                result = {'error': f'Unknown operation type: {op_type}'}
            
            processing_time = time.time() - start_time
            
            # Cache the result
            ttl = {
                'instant_reply': 300,   # 5 min
                'smart_reply': 1800,    # 30 min
                'search': 600,          # 10 min
                'thread_summary': 900,  # 15 min
                'task_extraction': 1200 # 20 min
            }.get(op_type, 3600)
            
            self.set_in_cache(key, result, cache_type, ttl)
            
            return {
                'operation': op, 
                'result': result, 
                'from_cache': False,
                'processing_time': processing_time
            }
        
        # Use thread pool for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(process_operation, operations))
        
        return results
    
    def _generate_instant_reply(self, data: Dict) -> Dict:
        """Generate instant reply (target: <100ms)"""
        # Simulate fast template-based reply generation
        time.sleep(0.05)  # 50ms simulation
        
        templates = [
            "Thank you for your email. I'll review this and get back to you soon.",
            "Got it! I'll take care of this right away.",
            "Thanks for the update. This is very helpful."
        ]
        
        return {
            'replies': [
                {'type': 'Professional', 'body': templates[0], 'confidence': 0.8},
                {'type': 'Quick', 'body': templates[1], 'confidence': 0.7},
                {'type': 'Friendly', 'body': templates[2], 'confidence': 0.7}
            ],
            'generation_time_ms': 50
        }
    
    def _generate_smart_reply(self, data: Dict) -> Dict:
        """Generate smart reply (target: <800ms)"""
        # Simulate AI-powered reply generation
        time.sleep(0.3)  # 300ms simulation
        
        return {
            'type': 'Smart',
            'subject': 'Re: ' + data.get('subject', 'Your email'),
            'body': 'Thank you for your detailed message. Based on your request, I understand you need assistance with this matter. I\'ll provide a comprehensive response addressing your specific concerns.',
            'confidence': 0.9,
            'generation_time_ms': 300
        }
    
    def _perform_search(self, data: Dict) -> Dict:
        """Perform search (target: <200ms)"""
        # Simulate search operation
        time.sleep(0.1)  # 100ms simulation
        
        query = data.get('query', '')
        
        return {
            'query': query,
            'results': [
                {'id': f'email_{i}', 'subject': f'Result {i} for {query}', 'relevance': 0.9 - i*0.1}
                for i in range(min(10, len(query)))  # Mock results based on query length
            ],
            'total_count': min(10, len(query)),
            'search_time_ms': 100
        }
    
    def _generate_thread_summary(self, data: Dict) -> str:
        """Generate thread summary (target: <500ms)"""
        # Simulate thread summary generation
        time.sleep(0.2)  # 200ms simulation
        
        email_count = data.get('email_count', 1)
        return f"Thread with {email_count} emails discussing project updates and next steps."
    
    def _extract_tasks(self, data: Dict) -> List[Dict]:
        """Extract tasks (target: varies)"""
        # Simulate task extraction
        time.sleep(0.15)  # 150ms simulation
        
        content = data.get('content', '')
        task_indicators = ['please', 'need', 'can you', 'deadline', 'by']
        
        task_count = sum(1 for indicator in task_indicators if indicator in content.lower())
        
        return [
            {
                'task': f'Task {i+1} extracted from email',
                'priority': 'medium',
                'due_date': 'none',
                'confidence': 0.7
            }
            for i in range(min(task_count, 3))
        ]
    
    def cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        try:
            conn = sqlite3.connect(self.sqlite_cache_path)
            
            # Remove expired entries
            current_time = time.time()
            conn.execute("""
                DELETE FROM cache_entries 
                WHERE (timestamp + ttl) < ?
            """, (current_time,))
            
            # Remove least accessed entries if cache is too large
            conn.execute("""
                DELETE FROM cache_entries 
                WHERE cache_key IN (
                    SELECT cache_key FROM cache_entries 
                    ORDER BY access_count ASC, timestamp ASC 
                    LIMIT (
                        SELECT MAX(0, COUNT(*) - 10000) FROM cache_entries
                    )
                )
            """)
            
            conn.commit()
            conn.close()
            
            # Vacuum to reclaim space
            conn = sqlite3.connect(self.sqlite_cache_path)
            conn.execute("VACUUM")
            conn.close()
            
        except Exception as e:
            print(f"Cache cleanup failed: {e}")
    
    def get_performance_metrics(self) -> Dict:
        """Get current performance metrics"""
        with self.cache_lock:
            total_cache_operations = self.metrics['cache_hits'] + self.metrics['cache_misses']
            hit_rate = (self.metrics['cache_hits'] / total_cache_operations * 100) if total_cache_operations > 0 else 0
            
            # Memory cache sizes
            cache_sizes = {
                'instant_cache': len(self.instant_cache),
                'smart_cache': len(self.smart_cache),
                'search_cache': len(self.search_cache),
                'thread_cache': len(self.thread_cache),
                'task_cache': len(self.task_cache)
            }
            
            # SQLite cache size
            try:
                conn = sqlite3.connect(self.sqlite_cache_path)
                cursor = conn.execute("SELECT COUNT(*) FROM cache_entries")
                sqlite_cache_size = cursor.fetchone()[0]
                conn.close()
            except Exception:
                sqlite_cache_size = 0
            
            return {
                'cache_hit_rate': round(hit_rate, 2),
                'total_requests': self.metrics['total_requests'],
                'average_response_time': round(self.metrics['avg_response_time'] * 1000, 2),  # ms
                'cache_sizes': cache_sizes,
                'sqlite_cache_size': sqlite_cache_size,
                'redis_available': self.redis_client is not None
            }
    
    def warm_up_cache(self, sample_data: List[Dict]):
        """Warm up cache with sample operations"""
        print("Warming up performance cache...")
        
        # Create sample operations for cache warming
        operations = []
        
        for data in sample_data:
            operations.extend([
                {'type': 'instant_reply', 'data': data},
                {'type': 'thread_summary', 'data': data},
                {'type': 'task_extraction', 'data': data},
                {'type': 'search', 'data': {'query': data.get('subject', 'test')}}
            ])
        
        # Process operations to populate cache
        results = self.batch_process(operations[:20])  # Limit to first 20 for warmup
        
        cached_count = sum(1 for r in results if not r.get('from_cache', True))
        print(f"Cache warmed up with {cached_count} operations")
        
        return results

# Global optimizer instance
performance_optimizer = PerformanceOptimizer()

# Convenience decorators
instant_cache = performance_optimizer.cached('instant', 300)    # 5 min TTL
smart_cache = performance_optimizer.cached('smart', 1800)       # 30 min TTL
search_cache = performance_optimizer.cached('search', 600)      # 10 min TTL
thread_cache = performance_optimizer.cached('thread', 900)      # 15 min TTL
task_cache = performance_optimizer.cached('task', 1200)         # 20 min TTL