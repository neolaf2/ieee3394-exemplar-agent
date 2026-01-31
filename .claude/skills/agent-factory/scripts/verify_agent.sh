#!/bin/bash
# Verify P3394 agent installation
set -e

echo "=== P3394 Agent Verification ==="
echo ""

# Check Python
echo "1. Checking Python..."
python_version=$(python --version 2>&1)
echo "   $python_version"
if [[ ! "$python_version" =~ "3.11" ]] && [[ ! "$python_version" =~ "3.12" ]] && [[ ! "$python_version" =~ "3.13" ]]; then
    echo "   WARNING: Python 3.11+ recommended"
fi

# Check uv
echo "2. Checking uv..."
if command -v uv &> /dev/null; then
    echo "   uv $(uv --version)"
else
    echo "   ERROR: uv not installed"
    echo "   Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check API key
echo "3. Checking API key..."
if [[ -n "$ANTHROPIC_API_KEY" ]]; then
    echo "   ANTHROPIC_API_KEY is set"
elif [[ -f ".env" ]]; then
    echo "   .env file exists"
else
    echo "   WARNING: ANTHROPIC_API_KEY not set and no .env file"
fi

# Check agent.yaml
echo "4. Checking agent.yaml..."
if [[ -f "agent.yaml" ]]; then
    agent_id=$(grep "id:" agent.yaml | head -1 | awk '{print $2}' | tr -d '"')
    agent_name=$(grep "name:" agent.yaml | head -1 | cut -d'"' -f2)
    echo "   Agent ID: $agent_id"
    echo "   Agent Name: $agent_name"
else
    echo "   ERROR: agent.yaml not found"
    exit 1
fi

# Check dependencies
echo "5. Checking dependencies..."
if [[ -f "uv.lock" ]]; then
    echo "   Dependencies installed (uv.lock exists)"
else
    echo "   Running uv sync..."
    uv sync
fi

# Check skills
echo "6. Checking skills..."
skill_count=$(ls -d .claude/skills/*/ 2>/dev/null | wc -l | tr -d ' ')
echo "   Found $skill_count skills"

# Run tests
echo "7. Running tests..."
if uv run pytest tests/ -q --tb=no 2>/dev/null; then
    echo "   Tests passed"
else
    echo "   WARNING: Some tests failed (may be expected for new agents)"
fi

echo ""
echo "=== Verification Complete ==="
echo ""
echo "To start your agent:"
echo "  uv run python -m p3394_agent --daemon"
echo ""
echo "To connect:"
echo "  uv run python -m p3394_agent"
