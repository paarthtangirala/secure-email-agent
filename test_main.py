#!/usr/bin/env python3

"""
Test the main application flow step by step to identify hanging issues.
"""

import sys
import time

def test_step(step_name, func):
    """Test a single step and measure time"""
    print(f"Testing: {step_name}...", end=" ", flush=True)
    start_time = time.time()

    try:
        result = func()
        end_time = time.time()
        print(f"✅ OK ({end_time - start_time:.2f}s)")
        return result
    except Exception as e:
        end_time = time.time()
        print(f"❌ FAILED ({end_time - start_time:.2f}s): {e}")
        return None

def main():
    print("🔍 Testing main application flow...\n")

    # Test step by step
    print("📦 Step 1: Import main modules")
    modules = test_step("Main imports", lambda: {
        'EmailProcessor': __import__('email_processor').EmailProcessor,
        'ResponseGenerator': __import__('response_generator').ResponseGenerator,
        'CalendarManager': __import__('calendar_manager').CalendarManager,
        'GoogleAuth': __import__('auth').GoogleAuth,
        'config': __import__('config').config
    })

    if not modules:
        return

    print("\n📦 Step 2: Create agent components")
    auth = test_step("GoogleAuth creation", lambda: modules['GoogleAuth']())
    processor = test_step("EmailProcessor creation", lambda: modules['EmailProcessor']())
    response_gen = test_step("ResponseGenerator creation", lambda: modules['ResponseGenerator']())

    if not all([auth, processor, response_gen]):
        return

    print("\n📦 Step 3: Test configuration access")
    test_step("Check credentials file", lambda: modules['config'].credentials_file.exists())
    test_step("Load encrypted JSON", lambda: modules['config'].load_encrypted_json("test"))

    print("\n📦 Step 4: Test authentication setup (without actual OAuth)")
    test_step("GoogleAuth initialization", lambda: modules['GoogleAuth']())

    # The issue might be in the specific authentication call
    print("\n📦 Step 5: Test the problematic authentication call")
    auth_instance = modules['GoogleAuth']()

    # Let's see if the issue is in loading existing credentials
    test_step("Load existing token", lambda: modules['config'].load_encrypted_json("token"))

    print("\n✅ Main application flow test completed!")

if __name__ == '__main__':
    main()