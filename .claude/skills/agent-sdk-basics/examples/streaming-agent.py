"""Streaming response example.

Demonstrates how to handle streaming responses for long-form content.

Usage:
    uv run python examples/streaming-agent.py
"""

import os
import sys
from dotenv import load_dotenv
from claude_agent_sdk import Agent

load_dotenv()


def main():
    agent = Agent(
        model="claude-sonnet-4-20250514",
        system_prompt="""You are a creative writing assistant.
When asked to write content, produce detailed, engaging text.
Use markdown formatting for structure.""",
    )

    prompt = """Write a short story (about 500 words) about a robot
who discovers it can dream. Include:
- A compelling opening
- Character development
- An unexpected twist
- A thought-provoking ending"""

    print("Generating story...\n")
    print("-" * 60)

    # Use streaming for long responses
    total_tokens = 0
    for chunk in agent.stream(prompt):
        # Print content as it arrives
        if chunk.content:
            print(chunk.content, end="", flush=True)

        # Track tool calls if any
        if chunk.tool_calls:
            for call in chunk.tool_calls:
                print(f"\n[Tool called: {call.name}]", file=sys.stderr)

    print("\n" + "-" * 60)

    # Get final usage stats from the last chunk
    if hasattr(chunk, "usage") and chunk.usage:
        print(f"\nTotal tokens used: {chunk.usage.total_tokens}")


def streaming_with_progress():
    """Alternative: Show progress indicator while streaming."""
    agent = Agent(
        model="claude-sonnet-4-20250514",
        system_prompt="You are a helpful assistant.",
    )

    print("Processing", end="", flush=True)

    content_buffer = []
    dot_count = 0

    for chunk in agent.stream("Explain quantum computing in simple terms."):
        if chunk.content:
            content_buffer.append(chunk.content)
            # Show progress dots
            dot_count += 1
            if dot_count % 10 == 0:
                print(".", end="", flush=True)

    print(" Done!\n")

    # Print complete response
    full_content = "".join(content_buffer)
    print(full_content)


def streaming_to_file():
    """Alternative: Stream response directly to a file."""
    agent = Agent(
        model="claude-sonnet-4-20250514",
        system_prompt="You are a documentation writer.",
    )

    output_path = "generated_doc.md"

    with open(output_path, "w") as f:
        print(f"Streaming to {output_path}...")

        for chunk in agent.stream("Write a README for a Python CLI tool"):
            if chunk.content:
                f.write(chunk.content)
                f.flush()  # Ensure content is written immediately

    print(f"Done! Check {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Streaming agent examples")
    parser.add_argument(
        "--mode",
        choices=["story", "progress", "file"],
        default="story",
        help="Which streaming example to run",
    )
    args = parser.parse_args()

    if args.mode == "story":
        main()
    elif args.mode == "progress":
        streaming_with_progress()
    elif args.mode == "file":
        streaming_to_file()
