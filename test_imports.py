#!/usr/bin/env python3

"""
Test script to identify which import is causing the application to hang.
"""

import sys
import time

def test_import(module_name, import_statement):
    """Test a single import and measure time"""
    print(f"Testing: {module_name}...", end=" ", flush=True)
    start_time = time.time()

    try:
        exec(import_statement)
        end_time = time.time()
        print(f"✅ OK ({end_time - start_time:.2f}s)")
        return True
    except Exception as e:
        end_time = time.time()
        print(f"❌ FAILED ({end_time - start_time:.2f}s): {e}")
        return False

def main():
    print("🔍 Testing imports to identify hanging issue...\n")

    # Test basic imports first
    basic_imports = [
        ("argparse", "import argparse"),
        ("json", "import json"),
        ("sys", "import sys"),
        ("datetime", "from datetime import datetime"),
        ("pathlib", "from pathlib import Path"),
    ]

    print("📦 Basic Python imports:")
    for name, stmt in basic_imports:
        test_import(name, stmt)

    print("\n📦 Google API imports:")
    google_imports = [
        ("google.auth.transport.requests", "from google.auth.transport.requests import Request"),
        ("google.oauth2.credentials", "from google.oauth2.credentials import Credentials"),
        ("google_auth_oauthlib.flow", "from google_auth_oauthlib.flow import InstalledAppFlow"),
        ("googleapiclient.discovery", "from googleapiclient.discovery import build"),
        ("googleapiclient.errors", "from googleapiclient.errors import HttpError"),
    ]

    for name, stmt in google_imports:
        test_import(name, stmt)

    print("\n📦 ML/Data Science imports:")
    ml_imports = [
        ("sklearn.feature_extraction.text", "from sklearn.feature_extraction.text import TfidfVectorizer"),
        ("sklearn.naive_bayes", "from sklearn.naive_bayes import MultinomialNB"),
        ("sklearn.pipeline", "from sklearn.pipeline import Pipeline"),
        ("pickle", "import pickle"),
        ("nltk", "import nltk"),
        ("pandas", "import pandas"),
        ("numpy", "import numpy"),
    ]

    for name, stmt in ml_imports:
        test_import(name, stmt)

    print("\n📦 Other dependencies:")
    other_imports = [
        ("cryptography", "from cryptography.fernet import Fernet"),
        ("keyring", "import keyring"),
        ("openai", "import openai"),
        ("fastapi", "import fastapi"),
        ("uvicorn", "import uvicorn"),
        ("transformers", "import transformers"),
        ("torch", "import torch"),
    ]

    for name, stmt in other_imports:
        test_import(name, stmt)

    print("\n📦 Project modules:")
    project_imports = [
        ("config", "from config import config"),
    ]

    for name, stmt in project_imports:
        test_import(name, stmt)

    # Test the problematic module imports one by one
    print("\n📦 Project modules (step by step):")

    # Test config first since everything depends on it
    if test_import("config creation", "from config import config"):

        # Test each module that depends on config
        modules_to_test = [
            ("auth", "from auth import GoogleAuth"),
            ("email_classifier", "from email_classifier import EmailClassifier"),
            ("email_processor", "from email_processor import EmailProcessor"),
            ("response_generator", "from response_generator import ResponseGenerator"),
            ("calendar_manager", "from calendar_manager import CalendarManager"),
        ]

        for name, stmt in modules_to_test:
            test_import(name, stmt)

    print("\n✅ Import test completed!")

if __name__ == '__main__':
    main()