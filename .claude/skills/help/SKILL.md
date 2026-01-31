---
name: help
description: Provides help and documentation about the P3394 agent
triggers:
  - "how do I"
  - "help me"
  - "what can you do"
  - "show me how"
---

# Help Skill

Provides contextual help and documentation about the P3394 agent.

## Usage

Ask questions like:
- "How do I configure channels?"
- "Help me understand UMF messages"
- "What can you do?"
- "Show me how to create a skill"

## Instructions

When this skill is invoked, provide helpful, accurate information about:

1. **Commands** - Explain available slash commands (/help, /about, /status, etc.)
2. **Configuration** - How to use agent.yaml to customize the agent
3. **Skills** - How to create and use skills
4. **Channels** - Available communication channels (CLI, web, etc.)
5. **P3394 Standard** - Explain the Universal Message Format when relevant

Always:
- Be concise and practical
- Provide examples when helpful
- Point to relevant commands or configuration options
- Suggest next steps the user can take

## Example Responses

**Q: "How do I configure the agent?"**
A: Edit the `agent.yaml` file in your project root. Key settings include:
- `agent.id`, `agent.name` - Your agent's identity
- `channels.web.enabled` - Enable/disable web interface
- `llm.system_prompt` - Customize the agent's behavior

**Q: "What can you do?"**
A: I can help you with:
- Answering questions about P3394 and agent development
- Demonstrating the Universal Message Format
- Running skills like echo, site generation, and more
- Use `/listSkills` to see all available skills
