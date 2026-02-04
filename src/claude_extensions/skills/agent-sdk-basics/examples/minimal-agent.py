"""Minimal Claude Agent SDK example.

This is the simplest possible agent - just a basic query/response.

Usage:
    uv run python examples/minimal-agent.py
"""

import os
from dotenv import load_dotenv
from claude_agent_sdk import Agent

# Load environment variables from .env file
load_dotenv()


def main():
    # Create agent with minimal configuration
    agent = Agent(
        model="claude-sonnet-4-20250514",
        system_prompt="You are a helpful assistant. Be concise.",
    )

    # Run a simple query
    response = agent.run("What are 3 interesting facts about octopuses?")

    # Print the response
    print(response.content)

    # Optionally, print usage statistics
    print(f"\n--- Usage ---")
    print(f"Input tokens: {response.usage.input_tokens}")
    print(f"Output tokens: {response.usage.output_tokens}")


if __name__ == "__main__":
    main()
