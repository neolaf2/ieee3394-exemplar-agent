---
name: echo
description: Simple echo skill that demonstrates the P3394 skill system
triggers:
  - "echo"
  - "repeat after me"
  - "say back"
---

# Echo Skill

A simple skill that echoes back user input. This serves as:
1. A template for creating new skills
2. A test for verifying the skill loading system
3. An example of P3394 skill structure

## Usage

Simply send a message starting with "echo" followed by what you want echoed:

```
echo Hello, World!
```

The agent will respond with your message.

## How It Works

1. The skill loader detects messages matching the triggers ("echo", "repeat after me", "say back")
2. The gateway routes the message to the LLM with this skill's context
3. The LLM processes the request according to these instructions
4. The response is sent back through the originating channel

## Instructions

When this skill is invoked:

1. Extract the text after the trigger word
2. Echo it back verbatim
3. If the message is just "echo" with nothing after, respond with a helpful message

Example responses:
- Input: "echo Hello" → Output: "Hello"
- Input: "echo" → Output: "Usage: echo <message> - I'll repeat what you say!"

## Creating Your Own Skills

To create a new skill:

1. Create a directory under `.claude/skills/` with your skill name
2. Add a `SKILL.md` file with:
   - YAML frontmatter (name, description, triggers)
   - Instructions for the LLM
3. The skill will be automatically loaded on agent startup

See the [Skill Creator Guide](../skill-creator/SKILL.md) for more details.
