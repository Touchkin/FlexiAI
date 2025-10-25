#!/usr/bin/env python3
"""Minimal test for Vertex AI with service account."""

import json
import os
import sys

# Set service account file
SERVICE_ACCOUNT_FILE = "dev-gemini-427512-71ac4bd1f35d.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(SERVICE_ACCOUNT_FILE)

# Read project ID
with open(SERVICE_ACCOUNT_FILE) as f:
    project_id = json.load(f)["project_id"]

print(f"Project: {project_id}")
print(f"Service Account File: {SERVICE_ACCOUNT_FILE}\n")

# Test FlexiAI
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, Message, ProviderConfig

config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="vertexai",
            api_key="not-used",
            model="gemini-2.0-flash",
            priority=1,
            config={
                "project": project_id,
                "location": "us-central1",
                "service_account_file": os.path.abspath(SERVICE_ACCOUNT_FILE),
            },
        )
    ]
)

print("Initializing client...")
client = FlexiAI(config)
print("✅ Client created\n")

print("Sending test request...")
response = client.chat_completion(
    messages=[Message(role="user", content="Say hello!")], max_tokens=50
)

print(f"✅ Response: {response.content}")
print(f"📊 Tokens: {response.usage.total_tokens}")
print(f"🔧 Provider: {response.provider}")
