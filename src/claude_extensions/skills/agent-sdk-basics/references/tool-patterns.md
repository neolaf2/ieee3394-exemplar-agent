# Tool Definition Patterns

Comprehensive guide to defining tools for Claude Agent SDK.

## Tool Decorator Deep Dive

### Basic Structure

```python
from claude_agent_sdk import Tool
from typing import Any, Optional

@Tool
def tool_name(
    required_param: str,
    optional_param: int = 10,
) -> ReturnType:
    """Short description of what the tool does.

    Args:
        required_param: Description of this parameter
        optional_param: Description with default value info

    Returns:
        Description of the return value and its structure
    """
    # Implementation
    return result
```

### Type Annotations

Supported types for parameters:

| Python Type | JSON Schema Type | Example |
|-------------|------------------|---------|
| `str` | string | `"hello"` |
| `int` | integer | `42` |
| `float` | number | `3.14` |
| `bool` | boolean | `true` |
| `list[T]` | array | `[1, 2, 3]` |
| `dict[str, T]` | object | `{"key": "value"}` |
| `Optional[T]` | T or null | `null` |
| `Literal["a", "b"]` | enum | `"a"` |

### Complex Type Examples

```python
from typing import Literal, Optional
from dataclasses import dataclass

@Tool
def create_task(
    title: str,
    priority: Literal["low", "medium", "high"],
    tags: list[str],
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create a new task with specified properties.

    Args:
        title: The task title (required)
        priority: Priority level - must be low, medium, or high
        tags: List of tags to categorize the task
        metadata: Optional additional key-value data

    Returns:
        Created task object with id, title, priority, tags, and created_at
    """
    return {
        "id": generate_id(),
        "title": title,
        "priority": priority,
        "tags": tags,
        "metadata": metadata or {},
        "created_at": datetime.now().isoformat(),
    }
```

## Tool Categories and Patterns

### 1. Data Retrieval Tools

Fetch data from external sources:

```python
@Tool
def fetch_user(user_id: str) -> dict[str, Any]:
    """Fetch user information by ID.

    Args:
        user_id: The unique user identifier

    Returns:
        User object with name, email, and role fields
    """
    user = database.get_user(user_id)
    return {
        "name": user.name,
        "email": user.email,
        "role": user.role,
    }

@Tool
def search_documents(
    query: str,
    limit: int = 10,
    filters: Optional[dict[str, str]] = None,
) -> list[dict[str, Any]]:
    """Search documents matching a query.

    Args:
        query: Search query string
        limit: Maximum results to return (default 10)
        filters: Optional field filters like {"status": "active"}

    Returns:
        List of matching documents with id, title, and snippet
    """
    results = search_engine.search(query, limit=limit, filters=filters)
    return [
        {"id": doc.id, "title": doc.title, "snippet": doc.snippet}
        for doc in results
    ]
```

### 2. Action Tools

Perform operations with side effects:

```python
@Tool
def send_notification(
    recipient: str,
    message: str,
    channel: Literal["email", "sms", "push"] = "email",
) -> dict[str, Any]:
    """Send a notification to a user.

    Args:
        recipient: User ID or contact info
        message: Notification message content
        channel: Delivery channel (default: email)

    Returns:
        Delivery status with message_id and timestamp
    """
    result = notification_service.send(
        recipient=recipient,
        message=message,
        channel=channel,
    )
    return {
        "status": "sent",
        "message_id": result.id,
        "timestamp": result.timestamp.isoformat(),
    }

@Tool
def update_record(
    record_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Update fields on an existing record.

    Args:
        record_id: ID of record to update
        updates: Dictionary of field names to new values

    Returns:
        Updated record with all current field values
    """
    record = database.update(record_id, updates)
    return record.to_dict()
```

### 3. Computation Tools

Perform calculations without side effects:

```python
@Tool
def analyze_sentiment(text: str) -> dict[str, Any]:
    """Analyze the sentiment of text.

    Args:
        text: Text to analyze

    Returns:
        Sentiment analysis with score (-1 to 1) and label
    """
    score = sentiment_analyzer.analyze(text)
    label = "positive" if score > 0.2 else "negative" if score < -0.2 else "neutral"
    return {"score": score, "label": label}

@Tool
def calculate_statistics(
    values: list[float],
    include_percentiles: bool = False,
) -> dict[str, float]:
    """Calculate statistical measures for a dataset.

    Args:
        values: List of numeric values
        include_percentiles: Whether to include 25th, 50th, 75th percentiles

    Returns:
        Statistics including mean, median, std_dev, min, max
    """
    import statistics
    result = {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
        "min": min(values),
        "max": max(values),
    }
    if include_percentiles:
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        result["p25"] = sorted_vals[n // 4]
        result["p50"] = sorted_vals[n // 2]
        result["p75"] = sorted_vals[3 * n // 4]
    return result
```

### 4. File Operation Tools

Read and write files:

```python
@Tool
def read_file(path: str, encoding: str = "utf-8") -> str:
    """Read the contents of a text file.

    Args:
        path: Path to the file to read
        encoding: File encoding (default: utf-8)

    Returns:
        Complete file contents as a string
    """
    with open(path, encoding=encoding) as f:
        return f.read()

@Tool
def write_file(
    path: str,
    content: str,
    create_dirs: bool = True,
) -> dict[str, Any]:
    """Write content to a file.

    Args:
        path: Destination file path
        content: Content to write
        create_dirs: Create parent directories if needed

    Returns:
        Write status with path and bytes_written
    """
    if create_dirs:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        bytes_written = f.write(content)
    return {"path": path, "bytes_written": bytes_written}
```

## Error Handling in Tools

### Returning Errors

Return errors as structured data rather than raising exceptions:

```python
@Tool
def safe_divide(numerator: float, denominator: float) -> dict[str, Any]:
    """Divide two numbers safely.

    Args:
        numerator: Number to divide
        denominator: Number to divide by

    Returns:
        Result with value or error message
    """
    if denominator == 0:
        return {"error": "Cannot divide by zero", "value": None}
    return {"error": None, "value": numerator / denominator}
```

### Validation

Validate inputs and return helpful errors:

```python
@Tool
def create_user(
    email: str,
    name: str,
    age: Optional[int] = None,
) -> dict[str, Any]:
    """Create a new user account.

    Args:
        email: User's email address (must be valid format)
        name: User's display name (1-100 characters)
        age: Optional age (must be 13-150 if provided)

    Returns:
        Created user object or validation error
    """
    errors = []

    if "@" not in email or "." not in email:
        errors.append("Invalid email format")

    if not (1 <= len(name) <= 100):
        errors.append("Name must be 1-100 characters")

    if age is not None and not (13 <= age <= 150):
        errors.append("Age must be between 13 and 150")

    if errors:
        return {"error": errors, "user": None}

    user = database.create_user(email=email, name=name, age=age)
    return {"error": None, "user": user.to_dict()}
```

## Tool Documentation Best Practices

### Docstring Structure

```python
@Tool
def example_tool(param: str) -> dict:
    """One-line summary of what the tool does.

    Extended description if needed. Explain any important
    behavior, side effects, or constraints.

    Args:
        param: Description of what this parameter is for.
               Can span multiple lines for complex params.

    Returns:
        Description of return value structure.
        Include field names and their meanings.

    Example:
        >>> result = example_tool("test")
        >>> print(result["status"])
        "success"
    """
```

### Good vs Bad Documentation

**Good:**
```python
@Tool
def search_products(
    query: str,
    category: Optional[str] = None,
    max_price: Optional[float] = None,
) -> list[dict[str, Any]]:
    """Search for products matching criteria.

    Searches the product catalog by name, description, and tags.
    Results are sorted by relevance score.

    Args:
        query: Search terms (supports AND, OR operators)
        category: Filter to specific category slug
        max_price: Maximum price filter in USD

    Returns:
        List of products with id, name, price, and relevance_score
    """
```

**Bad:**
```python
@Tool
def search(q, cat=None, price=None):  # Missing types
    """Search stuff."""  # Vague
    # No Args/Returns documentation
```

## Async Tools

For I/O-bound operations:

```python
import asyncio

@Tool
async def fetch_multiple_urls(urls: list[str]) -> list[dict[str, Any]]:
    """Fetch content from multiple URLs concurrently.

    Args:
        urls: List of URLs to fetch

    Returns:
        List of responses with url, status, and content
    """
    async def fetch_one(url: str) -> dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return {
                    "url": url,
                    "status": response.status,
                    "content": await response.text(),
                }

    tasks = [fetch_one(url) for url in urls]
    return await asyncio.gather(*tasks)
```

## Tool Registration Patterns

### Multiple Tools

```python
from claude_agent_sdk import Agent, Tool

# Define tools
@Tool
def tool_a(x: str) -> str:
    """Tool A."""
    return x.upper()

@Tool
def tool_b(x: int) -> int:
    """Tool B."""
    return x * 2

# Register all tools with agent
agent = Agent(
    model="claude-sonnet-4-20250514",
    system_prompt="...",
    tools=[tool_a, tool_b],
)
```

### Conditional Tools

```python
def get_tools(user_role: str) -> list:
    """Return tools based on user permissions."""
    base_tools = [read_data, search]

    if user_role == "admin":
        return base_tools + [delete_data, modify_settings]
    elif user_role == "editor":
        return base_tools + [update_data]
    else:
        return base_tools

agent = Agent(
    tools=get_tools(current_user.role),
    ...
)
```
