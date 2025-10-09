#!/usr/bin/env python3
"""
Robust test script for the instant email agent
Tests all major functionality with proper error handling
"""

import os
import requests
import json
import time
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api_endpoint(url: str, description: str) -> Dict:
    """Test an API endpoint with proper error handling"""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=10)
        response_time = (time.time() - start_time) * 1000

        if response.status_code == 200:
            try:
                data = response.json()
                return {
                    "success": True,
                    "data": data,
                    "response_time_ms": response_time,
                    "status_code": response.status_code
                }
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"JSON decode error: {e}",
                    "raw_response": response.text[:200],
                    "response_time_ms": response_time,
                    "status_code": response.status_code
                }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "raw_response": response.text[:200],
                "response_time_ms": response_time,
                "status_code": response.status_code
            }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Request error: {e}",
            "response_time_ms": None,
            "status_code": None
        }

def run_instant_agent_tests():
    """Run comprehensive tests on the instant email agent"""
    host = os.getenv('TEST_HOST', '127.0.0.1')
    port = os.getenv('TEST_PORT', '8502')
    base_url = f"http://{host}:{port}"

    print("🧪 INSTANT EMAIL AGENT - COMPREHENSIVE TESTING")
    print("=" * 55)
    print()

    tests = [
        {
            "name": "API Status",
            "url": f"{base_url}/api/stats",
            "check_fields": ["total_emails", "smart_path_status"]
        },
        {
            "name": "Email Search",
            "url": f"{base_url}/api/search-emails?limit=5",
            "check_fields": ["results", "success"]
        },
        {
            "name": "Instant Response Generation",
            "url": f"{base_url}/api/reply-suggestions?message_id={os.getenv('TEST_EMAIL_ID', '192736c46228737a')}&tone=professional",
            "check_fields": ["fast", "generation_time_ms"]
        }
    ]

    results = {}

    for test in tests:
        print(f"🔍 Testing: {test['name']}")
        result = test_api_endpoint(test['url'], test['name'])
        results[test['name']] = result

        if result['success']:
            print(f"   ✅ SUCCESS - {result['response_time_ms']:.1f}ms")

            # Check specific fields
            for field in test['check_fields']:
                if field in result['data']:
                    value = result['data'][field]
                    if field == 'fast' and isinstance(value, list):
                        print(f"   📊 {field}: {len(value)} responses")
                        if value:
                            print(f"       First response: \"{value[0].get('title', 'No title')}\"")
                            print(f"       Generation time: {value[0].get('generation_time_ms', 'unknown')}ms")
                    elif field == 'results' and isinstance(value, list):
                        print(f"   📊 {field}: {len(value)} emails found")
                    elif field == 'total_emails':
                        print(f"   📊 {field}: {value:,}")
                    else:
                        print(f"   📊 {field}: {value}")
                else:
                    print(f"   ⚠️  Missing field: {field}")
        else:
            print(f"   ❌ FAILED - {result['error']}")
            if result.get('raw_response'):
                print(f"   📝 Response preview: {result['raw_response']}")

        print()

    # Summary
    print("📋 TEST SUMMARY")
    print("=" * 20)
    successful_tests = sum(1 for r in results.values() if r['success'])
    total_tests = len(results)

    print(f"✅ Successful: {successful_tests}/{total_tests}")
    print(f"❌ Failed: {total_tests - successful_tests}/{total_tests}")

    if successful_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Your instant email agent is working perfectly!")
        print("\n🌐 Open http://127.0.0.1:8502 in your browser to use it!")
    else:
        print(f"\n⚠️  {total_tests - successful_tests} test(s) failed. Check the details above.")

    return results

def test_instant_response_performance():
    """Test response generation performance multiple times"""
    print("\n⚡ PERFORMANCE TESTING - Instant Response Generation")
    print("=" * 55)

    host = os.getenv('TEST_HOST', '127.0.0.1')
    port = os.getenv('TEST_PORT', '8502')
    email_id = os.getenv('TEST_EMAIL_ID', '192736c46228737a')
    url = f"http://{host}:{port}/api/reply-suggestions?message_id={email_id}&tone=professional"

    times = []
    for i in range(5):
        result = test_api_endpoint(url, f"Performance Test {i+1}")
        if result['success']:
            times.append(result['response_time_ms'])
            fast_responses = result['data'].get('fast', [])
            if fast_responses:
                gen_time = fast_responses[0].get('generation_time_ms', 0)
                print(f"   Test {i+1}: {result['response_time_ms']:.1f}ms total, {gen_time:.1f}ms generation")
        else:
            print(f"   Test {i+1}: FAILED - {result['error']}")

    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print(f"\n📊 Performance Summary:")
        print(f"   Average: {avg_time:.1f}ms")
        print(f"   Fastest: {min_time:.1f}ms")
        print(f"   Slowest: {max_time:.1f}ms")

        if avg_time < 50:
            print("   🚀 EXCELLENT - Ultra-fast performance!")
        elif avg_time < 100:
            print("   ✅ GOOD - Fast performance")
        else:
            print("   ⚠️  SLOW - Performance could be improved")

if __name__ == "__main__":
    # Run main tests
    run_instant_agent_tests()

    # Run performance tests
    test_instant_response_performance()