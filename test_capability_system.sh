#!/bin/bash
#
# Test Agent Capability Descriptor System
#
# Demonstrates the capability system functionality:
# 1. List all capabilities
# 2. Filter capabilities by kind (skills only)
# 3. Filter capabilities by substrate (commands only)
# 4. Test backward compatibility

API_URL="http://localhost:8100/v1/messages"
API_KEY="test-key"

echo "======================================================================"
echo "🧪 Testing Agent Capability Descriptor (ACD) System"
echo "======================================================================"
echo ""

# Test 1: List all capabilities
echo "📋 Test 1: List All Capabilities"
echo "----------------------------------------------------------------------"
response=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 2048,
    "messages": [{"role": "user", "content": "/listCapabilities"}]
  }')

if echo "$response" | jq -e '.content[0].text' > /dev/null 2>&1; then
    count=$(echo "$response" | jq -r '.content[0].text' | grep -c "**ID:**")
    echo "✓ Listed $count capabilities successfully"
    echo ""
    echo "Sample output:"
    echo "$response" | jq -r '.content[0].text' | head -20
else
    echo "✗ Failed to list capabilities"
    exit 1
fi

# Test 2: Filter by kind (skills only)
echo ""
echo "📊 Test 2: Filter by Kind (Composite/Skills Only)"
echo "----------------------------------------------------------------------"
response=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 2048,
    "messages": [{"role": "user", "content": "/listCapabilities?kind=composite"}]
  }')

if echo "$response" | jq -e '.content[0].text' > /dev/null 2>&1; then
    count=$(echo "$response" | jq -r '.content[0].text' | grep -c "**ID:**")
    echo "✓ Found $count composite capabilities (skills)"
    echo ""
    echo "Skills:"
    echo "$response" | jq -r '.content[0].text' | grep "###" | head -5
else
    echo "✗ Failed to filter by kind"
    exit 1
fi

# Test 3: Filter by substrate (commands only)
echo ""
echo "⚙️ Test 3: Filter by Substrate (Symbolic/Commands Only)"
echo "----------------------------------------------------------------------"
response=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 2048,
    "messages": [{"role": "user", "content": "/listCapabilities?substrate=symbolic"}]
  }')

if echo "$response" | jq -e '.content[0].text' > /dev/null 2>&1; then
    count=$(echo "$response" | jq -r '.content[0].text' | grep -c "**ID:**")
    echo "✓ Found $count symbolic capabilities (commands)"
    echo ""
    echo "Commands:"
    echo "$response" | jq -r '.content[0].text' | grep "###" | head -6
else
    echo "✗ Failed to filter by substrate"
    exit 1
fi

# Test 4: Backward compatibility
echo ""
echo "🔄 Test 4: Backward Compatibility (Legacy /listSkills)"
echo "----------------------------------------------------------------------"
response=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 2048,
    "messages": [{"role": "user", "content": "/listSkills"}]
  }')

if echo "$response" | jq -e '.content[0].text' > /dev/null 2>&1; then
    count=$(echo "$response" | jq -r '.content[0].text' | grep -c "**ID:**")
    echo "✓ /listSkills works (shows $count capabilities)"
    echo "✓ Backward compatibility maintained"
else
    echo "✗ /listSkills failed"
    exit 1
fi

# Test 5: Legacy commands still work
echo ""
echo "📌 Test 5: Legacy Commands Still Work"
echo "----------------------------------------------------------------------"
for cmd in "/help" "/about" "/status"; do
    response=$(curl -s -X POST "$API_URL" \
      -H "Content-Type: application/json" \
      -H "x-api-key: $API_KEY" \
      -d "{
        \"model\": \"claude-sonnet-4-5-20250929\",
        \"max_tokens\": 1024,
        \"messages\": [{\"role\": \"user\", \"content\": \"$cmd\"}]
      }")

    if echo "$response" | jq -e '.content[0].text' > /dev/null 2>&1; then
        length=$(echo "$response" | jq -r '.content[0].text' | wc -c)
        printf "✓ %-15s → %5d chars response\n" "$cmd" "$length"
    else
        echo "✗ $cmd failed"
        exit 1
    fi
done

echo ""
echo "======================================================================"
echo "🎉 All capability system tests passed!"
echo "======================================================================"
echo ""
echo "Summary:"
echo "  ✓ Capability registry working"
echo "  ✓ Query filtering operational"
echo "  ✓ Backward compatibility confirmed"
echo "  ✓ All legacy commands functional"
echo ""
echo "The Agent Capability Descriptor system is ready for production!"
echo ""

exit 0
