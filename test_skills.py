#!/usr/bin/env python3
import requests
import json

# Test /listCapabilities
response = requests.post(
    "http://localhost:8100/v1/messages",
    headers={
        "Content-Type": "application/json",
        "x-api-key": "test-key"
    },
    json={
        "model": "claude-sonnet-4-5-20250929",
        "max_tokens": 1024,
        "messages": [{
            "role": "user",
            "content": "/listCapabilities?kind=composite"
        }]
    }
)

if response.ok:
    data = response.json()
    print(data["content"][0]["text"])
else:
    print(f"Error: {response.status_code}")
    print(response.text)
