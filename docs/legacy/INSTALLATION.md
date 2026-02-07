# P3394 Agent Installation Guide

Complete installation guide for the P3394 Agent Starter Kit.

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
  - [Method 1: Git Clone (Recommended)](#method-1-git-clone-recommended)
  - [Method 2: UV Dependency](#method-2-uv-dependency)
  - [Method 3: Docker](#method-3-docker)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| Python | 3.11 or higher |
| Memory | 512 MB RAM |
| Disk | 100 MB free space |
| Network | Internet access for API calls |

### Required Tools

| Tool | Purpose | Installation |
|------|---------|--------------|
| [uv](https://github.com/astral-sh/uv) | Package management | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| git | Version control | System package manager |

### Optional Tools

| Tool | Purpose | When Needed |
|------|---------|-------------|
| Docker | Containerized deployment | Production deployments |
| Node.js 18+ | WhatsApp bridge | WhatsApp channel |
| PostgreSQL | Production database | Supabase backend |

### API Keys

| Key | Purpose | Get From |
|-----|---------|----------|
| `ANTHROPIC_API_KEY` | Claude API access (required) | [console.anthropic.com](https://console.anthropic.com) |
| `SUPABASE_URL` | Database backend (optional) | [supabase.com](https://supabase.com) |
| `SUPABASE_KEY` | Database auth (optional) | Supabase dashboard |

---

## Installation Methods

### Method 1: Git Clone (Recommended)

Best for: Development, customization, full control

```bash
# 1. Clone the repository
git clone --branch v0.2.0 https://github.com/neolaf2/ieee3394-exemplar-agent.git my-agent
cd my-agent

# 2. Install dependencies
uv sync

# 3. Set API key
export ANTHROPIC_API_KEY='your-api-key-here'

# 4. Verify installation
uv run python -m p3394_agent --version

# 5. Run the agent
uv run python -m p3394_agent --daemon
```

#### Clone Options

```bash
# Latest stable release
git clone --branch v0.2.0 https://github.com/neolaf2/ieee3394-exemplar-agent.git

# Latest development
git clone https://github.com/neolaf2/ieee3394-exemplar-agent.git

# Specific commit
git clone https://github.com/neolaf2/ieee3394-exemplar-agent.git
git checkout abc123
```

### Method 2: UV Dependency

Best for: Using as a library in your own project

```bash
# 1. Create new project
mkdir my-agent && cd my-agent
uv init

# 2. Add as dependency
uv add git+https://github.com/neolaf2/ieee3394-exemplar-agent.git@v0.2.0

# 3. Create your agent entry point
cat > main.py << 'EOF'
import asyncio
from p3394_agent.server import create_server

async def main():
    server = await create_server()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
EOF

# 4. Create minimal config
cat > agent.yaml << 'EOF'
agent:
  id: "my-agent"
  name: "My Agent"
  version: "0.1.0"
channels:
  cli:
    enabled: true
EOF

# 5. Run
export ANTHROPIC_API_KEY='your-key'
uv run python main.py
```

### Method 3: Docker

Best for: Production deployments, isolated environments

```bash
# 1. Clone repository
git clone --branch v0.2.0 https://github.com/neolaf2/ieee3394-exemplar-agent.git
cd ieee3394-exemplar-agent

# 2. Build image
docker build -t p3394-agent:0.2.0 .

# 3. Run container
docker run -d \
  --name my-agent \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY='your-key' \
  -v $(pwd)/agent.yaml:/app/agent.yaml:ro \
  -v $(pwd)/data:/app/data \
  p3394-agent:0.2.0
```

#### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./agent.yaml:/app/agent.yaml:ro
      - ./data:/app/data
      - ./.claude/skills:/app/.claude/skills:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Run:
```bash
docker-compose up -d
```

---

## Configuration

### Configuration File: agent.yaml

The main configuration file controls all agent behavior.

```yaml
# =============================================================================
# AGENT IDENTITY
# =============================================================================
agent:
  id: "my-agent"                    # Unique identifier (kebab-case)
  name: "My Custom Agent"           # Display name
  version: "0.1.0"                  # Semantic version
  description: "My P3394 agent"     # Brief description

# =============================================================================
# CHANNELS
# =============================================================================
channels:
  # CLI Channel (interactive terminal)
  cli:
    enabled: true
    default: true                   # Default channel for messages
    socket_path: "/tmp/p3394-agent.sock"

  # Web Channel (HTTP server)
  web:
    enabled: true
    host: "0.0.0.0"
    port: 8000
    routes:
      chat: "/chat"                 # Web chat UI
      api: "/api"                   # REST API
      anthropic_api: "/v1"          # Anthropic-compatible API
      p3394: "/p3394"               # P3394 native protocol

  # WhatsApp Channel (requires bridge setup)
  whatsapp:
    enabled: false
    service_phone: "${WHATSAPP_PHONE}"
    bridge_url: "http://localhost:3000"

# =============================================================================
# SKILLS
# =============================================================================
skills:
  # Core skills (always recommended)
  - name: "echo"
    enabled: true
  - name: "help"
    enabled: true
  - name: "p3394-explainer"
    enabled: true

  # Optional skills
  - name: "site-generator"
    enabled: false

# =============================================================================
# LLM CONFIGURATION
# =============================================================================
llm:
  provider: "anthropic"
  model: "claude-sonnet-4-20250514"
  max_tokens: 4096
  temperature: 0.7
  system_prompt: |
    You are {agent_name}, a helpful P3394-compliant assistant.
    Version: {agent_version}

    You support both symbolic commands (instant, no LLM) and
    natural language conversations.

# =============================================================================
# STORAGE
# =============================================================================
storage:
  type: "sqlite"                    # sqlite | supabase
  path: "./data/agent.db"           # For SQLite
  # For Supabase:
  # supabase_url: "${SUPABASE_URL}"
  # supabase_key: "${SUPABASE_KEY}"

# =============================================================================
# AUTHENTICATION (Optional)
# =============================================================================
auth:
  enabled: false                    # Enable for multi-user
  require_login: false              # Require authentication
  session_ttl_hours: 24

# =============================================================================
# LOGGING
# =============================================================================
logging:
  level: "INFO"                     # DEBUG | INFO | WARNING | ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "./logs/agent.log"          # Optional log file
```

### Environment Variables

Create `.env` file (never commit this):

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-...

# Optional - Database
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...

# Optional - WhatsApp
WHATSAPP_PHONE=+1234567890

# Optional - Deployment
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=INFO
```

Load in shell:
```bash
export $(cat .env | xargs)
```

Or use python-dotenv (included):
```python
from dotenv import load_dotenv
load_dotenv()
```

### Directory Structure

After installation, your project should look like:

```
my-agent/
├── agent.yaml              # Main configuration
├── .env                    # Environment variables (git-ignored)
├── .claude/
│   └── skills/             # Custom skills
│       ├── echo/
│       ├── help/
│       └── your-skill/
├── data/                   # Runtime data (git-ignored)
│   └── agent.db
├── logs/                   # Log files (git-ignored)
├── src/
│   └── p3394_agent/        # Source code
├── pyproject.toml
└── uv.lock
```

---

## Verification

### Step 1: Check Installation

```bash
# Verify Python version
python --version  # Should be 3.11+

# Verify uv
uv --version

# Verify package installation
uv run python -c "import p3394_agent; print(p3394_agent.__version__)"
```

### Step 2: Run Tests

```bash
# Run test suite
uv run pytest

# Run with coverage
uv run pytest --cov=src/p3394_agent
```

### Step 3: Start Agent

```bash
# Start daemon
uv run python -m p3394_agent --daemon

# In another terminal, connect
uv run python -m p3394_agent
```

### Step 4: Test Commands

```
>>> /version
>>> /status
>>> /help
>>> Hello, are you working?
```

### Step 5: Test Web Interface

```bash
# If web channel enabled
curl http://localhost:8000/api/health
curl http://localhost:8000/api/version
```

Expected response:
```json
{"status": "healthy", "agent": "My Agent", "version": "0.1.0"}
```

---

## Troubleshooting

### Common Issues

#### "ANTHROPIC_API_KEY not set"

```bash
# Check if set
echo $ANTHROPIC_API_KEY

# Set it
export ANTHROPIC_API_KEY='sk-ant-api03-...'

# Or add to .bashrc/.zshrc
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
source ~/.zshrc
```

#### "Address already in use"

```bash
# Find process using port
lsof -i :8000

# Kill it
kill -9 <PID>

# Or use different port
uv run python -m p3394_agent --daemon --port 8001
```

#### "Socket file exists"

```bash
# Remove stale socket
rm -f /tmp/p3394-agent.sock

# Restart daemon
uv run python -m p3394_agent --daemon
```

#### "Module not found"

```bash
# Reinstall dependencies
rm -rf .venv uv.lock
uv sync
```

#### "Permission denied"

```bash
# Fix permissions
chmod +x scripts/*.sh
chmod 755 data/
```

#### Docker: Container exits immediately

```bash
# Check logs
docker logs my-agent

# Run interactively to debug
docker run -it --rm \
  -e ANTHROPIC_API_KEY='your-key' \
  p3394-agent:0.2.0 bash
```

### Getting Help

1. **Check logs**: `./logs/agent.log` or `docker logs`
2. **Enable debug**: Set `LOG_LEVEL=DEBUG` in environment
3. **Run tests**: `uv run pytest -v` to identify issues
4. **GitHub Issues**: [Report bugs](https://github.com/neolaf2/ieee3394-exemplar-agent/issues)

---

## Next Steps

After successful installation:

1. **Customize identity** - Edit `agent.yaml` with your agent's name and description
2. **Add skills** - Create custom skills in `.claude/skills/`
3. **Configure channels** - Enable web, WhatsApp, or MCP as needed
4. **Set up authentication** - For multi-user deployments
5. **Deploy** - Use Docker or systemd for production

See [docs/SDK_DEVELOPER_GUIDE.md](./docs/SDK_DEVELOPER_GUIDE.md) for building Companion or Task agents.
