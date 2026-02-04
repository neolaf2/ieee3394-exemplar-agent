"""Agent with custom tools example.

Demonstrates how to define and register tools with an agent.

Usage:
    uv run python examples/agent-with-tools.py
"""

import os
from datetime import datetime
from typing import Any, Literal
from dotenv import load_dotenv
from claude_agent_sdk import Agent, Tool

load_dotenv()


# Define tools using the @Tool decorator
# Each tool needs: type hints, docstring with Args/Returns


@Tool
def get_current_time(timezone: str = "UTC") -> dict[str, str]:
    """Get the current time in a specified timezone.

    Args:
        timezone: Timezone name (e.g., 'UTC', 'US/Pacific', 'Europe/London')

    Returns:
        Current time with formatted string and ISO timestamp
    """
    from zoneinfo import ZoneInfo

    try:
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        return {
            "timezone": timezone,
            "formatted": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "iso": now.isoformat(),
        }
    except Exception as e:
        return {"error": f"Invalid timezone: {timezone}"}


@Tool
def calculate(
    operation: Literal["add", "subtract", "multiply", "divide"],
    a: float,
    b: float,
) -> dict[str, Any]:
    """Perform a mathematical calculation.

    Args:
        operation: The operation to perform
        a: First number
        b: Second number

    Returns:
        Calculation result with operation details
    """
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else None,
    }

    result = operations[operation](a, b)

    if result is None:
        return {"error": "Cannot divide by zero"}

    return {
        "operation": operation,
        "a": a,
        "b": b,
        "result": result,
        "expression": f"{a} {operation} {b} = {result}",
    }


@Tool
def search_knowledge_base(
    query: str,
    category: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search the knowledge base for relevant information.

    Args:
        query: Search query string
        category: Optional category filter
        limit: Maximum number of results (default 5)

    Returns:
        List of matching articles with id, title, and summary
    """
    # Mock implementation - replace with real search
    mock_results = [
        {
            "id": "kb-001",
            "title": "Getting Started Guide",
            "category": "guides",
            "summary": "Learn the basics of our platform...",
            "relevance": 0.95,
        },
        {
            "id": "kb-002",
            "title": "API Reference",
            "category": "technical",
            "summary": "Complete API documentation...",
            "relevance": 0.87,
        },
        {
            "id": "kb-003",
            "title": "Troubleshooting FAQ",
            "category": "support",
            "summary": "Common issues and solutions...",
            "relevance": 0.82,
        },
    ]

    # Filter by category if provided
    if category:
        mock_results = [r for r in mock_results if r["category"] == category]

    # Return limited results
    return mock_results[:limit]


def main():
    # Create agent with tools
    agent = Agent(
        model="claude-sonnet-4-20250514",
        system_prompt="""You are a helpful assistant with access to tools.

Available tools:
- get_current_time: Get the current time in any timezone
- calculate: Perform mathematical calculations
- search_knowledge_base: Search for information

Use tools when they would help answer the user's question.
Always explain your actions and results clearly.""",
        tools=[get_current_time, calculate, search_knowledge_base],
    )

    # Example interactions
    print("=" * 60)
    print("Example 1: Using the time tool")
    print("=" * 60)

    response = agent.run("What time is it in Tokyo and New York?")
    print(response.content)

    print("\n" + "=" * 60)
    print("Example 2: Using the calculator")
    print("=" * 60)

    response = agent.run("What is 15% of 250, and then add 42 to that result?")
    print(response.content)

    print("\n" + "=" * 60)
    print("Example 3: Using the knowledge base")
    print("=" * 60)

    response = agent.run("Search for guides about getting started")
    print(response.content)


if __name__ == "__main__":
    main()
