#!/bin/bash

# Test that all 4 new skills are installed and accessible

echo "======================================================================="
echo "Testing Installed Document Generation Skills"
echo "======================================================================="
echo ""

API_URL="http://localhost:8100/v1/messages"
API_KEY="test-key"

echo "Querying /listCapabilities?kind=composite..."
echo ""

response=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"model":"claude-sonnet-4-5-20250929","max_tokens":2048,"messages":[{"role":"user","content":"/listCapabilities?kind=composite"}]}')

# Extract the text content
text=$(echo "$response" | jq -r '.content[0].text' 2>/dev/null)

if [ -z "$text" ]; then
  echo "❌ Error: Could not get response from agent"
  echo "Raw response:"
  echo "$response"
  exit 1
fi

echo "Skills found:"
echo "============="
echo ""

# Check for each skill
for skill in "skill-creator" "pdf" "docx" "pptx"; do
  if echo "$text" | grep -q "$skill"; then
    echo "✓ $skill"
  else
    echo "✗ $skill (NOT FOUND)"
  fi
done

echo ""
echo "Full list of composite capabilities:"
echo "====================================="
echo "$text" | grep "^###" || echo "$text"
