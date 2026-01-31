# Simple Chatbot Example

A minimal P3394-compliant chatbot demonstrating the starter kit.

## What This Example Shows

1. **Basic Configuration** - How to customize `agent.yaml`
2. **CLI Channel** - Interactive terminal chat
3. **Symbolic Commands** - Built-in `/help`, `/about`, `/status` commands
4. **LLM Integration** - Natural language conversations

## Setup

1. Copy this example to a new directory:
   ```bash
   cp -r examples/simple-chatbot my-chatbot
   cd my-chatbot
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Set your API key:
   ```bash
   export ANTHROPIC_API_KEY='your-key'
   ```

4. Run the agent:
   ```bash
   uv run python -m p3394_agent --daemon
   ```

5. Connect in a new terminal:
   ```bash
   uv run python -m p3394_agent
   ```

## Configuration

The `agent.yaml` for this example:

```yaml
agent:
  id: "simple-chatbot"
  name: "Simple Chatbot"
  version: "0.1.0"
  description: "A simple P3394 chatbot example"

channels:
  cli:
    enabled: true

llm:
  provider: "anthropic"
  model: "claude-sonnet-4-20250514"
  system_prompt: |
    You are a friendly chatbot. Be helpful, concise, and engaging.
    When users greet you, respond warmly.
    When asked questions, provide clear answers.
```

## Example Conversation

```
>>> Hello!
Hello! How can I help you today?

>>> What can you do?
I can:
- Answer questions
- Have conversations
- Help with tasks

Try asking me something!

>>> /help
# Simple Chatbot - Help

## Available Commands
- /help - Show this help
- /about - About this chatbot
- /status - Check status

>>> /status
# Agent Status
Agent: Simple Chatbot
Version: 0.1.0
Status: 🟢 Operational
```

## Next Steps

- Add custom skills in `.claude/skills/`
- Enable the web channel for a web interface
- Add WhatsApp for mobile messaging
