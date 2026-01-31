---
name: agent-factory
description: Guided workflow for creating and deploying custom P3394-compliant agents in under 30 minutes. This skill should be used when a user wants to create their own agent, set up a new P3394 agent, customize an agent template, or deploy an agent. Works within Claude Code or any skill-capable agent.
version: 1.0.0
triggers:
  - "create an agent"
  - "set up a new agent"
  - "agent factory"
  - "build my own agent"
  - "customize agent"
  - "deploy agent"
---

# Agent Factory

Create and deploy your own P3394-compliant agent in 30 minutes or less.

## Overview

This skill guides you through the complete agent creation lifecycle:

1. **Clone** - Get the template from GitHub
2. **Configure** - Set identity, channels, and API keys
3. **Customize** - Add skills and business logic
4. **Verify** - Test the agent works correctly
5. **Deploy** - Run locally or in production

## Prerequisites Check

Before starting, verify these requirements:

```bash
# Check Python version (need 3.11+)
python --version

# Check uv is installed
uv --version

# Check git is installed
git --version
```

If uv is not installed:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Phase 1: Clone Template (2 minutes)

### Step 1.1: Create Project Directory

Ask the user where to create the agent:

```
Where should I create your agent project?
Examples:
- ./my-agent (current directory)
- ~/projects/my-agent
- /path/to/my-agent
```

### Step 1.2: Clone the Template

Execute:
```bash
git clone --branch v0.2.0 https://github.com/neolaf2/ieee3394-exemplar-agent.git <target-directory>
cd <target-directory>
```

### Step 1.3: Install Dependencies

```bash
uv sync
```

## Phase 2: Configure Identity (5 minutes)

### Step 2.1: Gather Agent Identity

Ask the user for:

1. **Agent ID** (kebab-case, e.g., "customer-support-bot")
2. **Agent Name** (display name, e.g., "Customer Support Assistant")
3. **Description** (one sentence about what the agent does)
4. **Version** (default: "0.1.0")

### Step 2.2: Update agent.yaml

Edit the agent.yaml file with the user's choices:

```yaml
agent:
  id: "<agent-id>"
  name: "<Agent Name>"
  version: "0.1.0"
  description: "<description>"
```

### Step 2.3: Configure API Key

Ask user for their Anthropic API key, then:

```bash
# Create .env file
echo "ANTHROPIC_API_KEY=<their-key>" > .env

# Add to .gitignore if not already
echo ".env" >> .gitignore
```

## Phase 3: Channel Selection (5 minutes)

### Step 3.1: Present Channel Options

```
Which channels do you want to enable?

1. CLI (Interactive terminal) - RECOMMENDED for development
2. Web (HTTP server with chat UI and API)
3. WhatsApp (Requires additional setup)
4. MCP Server (For integration with Claude Code)

Enter numbers separated by commas (e.g., "1,2"):
```

### Step 3.2: Configure Channels

Based on selection, update agent.yaml:

**CLI Channel:**
```yaml
channels:
  cli:
    enabled: true
    default: true
```

**Web Channel:**
```yaml
channels:
  web:
    enabled: true
    host: "0.0.0.0"
    port: 8000
```

**MCP Server:**
```yaml
channels:
  mcp:
    enabled: true
    transport: stdio
```

## Phase 4: Skill Selection (5 minutes)

### Step 4.1: Review Available Skills

Present the available skills:

| Skill | Description | Recommended |
|-------|-------------|-------------|
| echo | Simple echo for testing | Yes |
| help | Contextual help system | Yes |
| p3394-explainer | Explains P3394 concepts | For learning |
| site-generator | Generate static HTML | For websites |

### Step 4.2: Select Skills

Ask user which skills to enable (default: echo, help).

### Step 4.3: Update Skills Configuration

```yaml
skills:
  - name: "echo"
    enabled: true
  - name: "help"
    enabled: true
```

### Step 4.4: Create Custom Skill (Optional)

If user wants a custom skill:

```bash
mkdir -p .claude/skills/<skill-name>
```

Create `.claude/skills/<skill-name>/SKILL.md`:

```markdown
---
name: <skill-name>
description: <what the skill does>
triggers:
  - "<trigger phrase 1>"
  - "<trigger phrase 2>"
---

# <Skill Name>

<Instructions for what the skill should do>
```

## Phase 5: Customize System Prompt (3 minutes)

### Step 5.1: Gather Persona Information

Ask the user:
1. What personality should the agent have?
2. What domain expertise should it demonstrate?
3. Any specific instructions or constraints?

### Step 5.2: Update System Prompt

Edit agent.yaml llm section:

```yaml
llm:
  provider: "anthropic"
  model: "claude-sonnet-4-20250514"
  system_prompt: |
    You are {agent_name}, <persona description>.

    Your expertise includes:
    - <domain 1>
    - <domain 2>

    <any special instructions>
```

## Phase 6: Verification (5 minutes)

### Step 6.1: Run Tests

```bash
uv run pytest tests/ -v
```

### Step 6.2: Start Agent

```bash
# Terminal 1: Start daemon
uv run python -m p3394_agent --daemon

# Terminal 2: Connect client
uv run python -m p3394_agent
```

### Step 6.3: Test Commands

Guide user to test:

```
>>> /help
>>> /about
>>> /status
>>> /version
>>> Hello, what can you do?
```

### Step 6.4: Verify Custom Skills

If custom skills were created, test their triggers.

## Phase 7: Deployment Options (5 minutes)

### Option A: Local Development

Agent is already running. For persistent operation:

```bash
# Run in background
nohup uv run python -m p3394_agent --daemon > agent.log 2>&1 &
```

### Option B: Docker Deployment

```bash
# Build image
docker build -t <agent-id>:0.1.0 .

# Run container
docker run -d \
  --name <agent-id> \
  -p 8000:8000 \
  --env-file .env \
  <agent-id>:0.1.0
```

### Option C: Systemd Service (Linux)

Create `/etc/systemd/system/<agent-id>.service`:

```ini
[Unit]
Description=<Agent Name>
After=network.target

[Service]
Type=simple
User=<user>
WorkingDirectory=<project-path>
Environment=ANTHROPIC_API_KEY=<key>
ExecStart=/usr/bin/uv run python -m p3394_agent --daemon
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable <agent-id>
sudo systemctl start <agent-id>
```

## Completion Checklist

Before finishing, verify:

- [ ] Agent starts without errors
- [ ] `/help` command works
- [ ] `/about` shows custom identity
- [ ] Natural language queries work
- [ ] Custom skills trigger correctly (if any)
- [ ] Chosen deployment method is working

## Quick Reference

### Project Structure

```
<agent-directory>/
├── agent.yaml          # Main configuration
├── .env                # API keys (git-ignored)
├── .claude/
│   └── skills/         # Custom skills
│       └── <skill>/
│           └── SKILL.md
├── data/               # Runtime data
└── logs/               # Log files
```

### Common Commands

```bash
# Start daemon
uv run python -m p3394_agent --daemon

# Connect client
uv run python -m p3394_agent

# Run tests
uv run pytest

# Check logs
tail -f logs/agent.log
```

### Getting Help

- Documentation: [QUICKSTART.md](./QUICKSTART.md)
- Full guide: [INSTALLATION.md](./INSTALLATION.md)
- SDK guide: [docs/SDK_DEVELOPER_GUIDE.md](./docs/SDK_DEVELOPER_GUIDE.md)
- Issues: https://github.com/neolaf2/ieee3394-exemplar-agent/issues

## Time Budget

| Phase | Time | Cumulative |
|-------|------|------------|
| Clone Template | 2 min | 2 min |
| Configure Identity | 5 min | 7 min |
| Channel Selection | 5 min | 12 min |
| Skill Selection | 5 min | 17 min |
| System Prompt | 3 min | 20 min |
| Verification | 5 min | 25 min |
| Deployment | 5 min | 30 min |

Total: **30 minutes** to a working, deployed agent.
