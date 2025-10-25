"""
Minimal Vertex AI API Key Test
Replace YOUR_API_KEY and YOUR_PROJECT_ID with your actual values.
"""

from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, Message, ProviderConfig, UnifiedRequest

# Configure with YOUR credentials
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="vertexai",
            api_key="YOUR_API_KEY",  # ← Replace with your API key
            model="gemini-2.0-flash",
            priority=1,
            config={
                "project": "YOUR_PROJECT_ID",  # ← Replace with your project ID
                "location": "us-central1",  # ← Optional: change if needed
            },
        )
    ]
)

# Test it
client = FlexiAI(config)
response = client.chat_completion(
    UnifiedRequest(messages=[Message(role="user", content="Say hello!")], max_tokens=50)
)

print(f"✅ Response: {response.content}")
print(f"📊 Tokens used: {response.usage.total_tokens}")
