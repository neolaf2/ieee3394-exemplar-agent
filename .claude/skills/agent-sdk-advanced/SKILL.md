---
name: Agent SDK Advanced Patterns
description: This skill should be used when the user asks about "multi-agent systems", "agent orchestration", "domain modeling for agents", "layered architecture", "agent memory", "property graphs", "KSTAR pattern", or wants to build sophisticated agent architectures. Provides advanced patterns including domain-driven design and hybrid database strategies.
version: 0.1.0
---

# Claude Agent SDK Advanced Patterns

Advanced architectural patterns for building sophisticated agent systems. Combines Claude Agent SDK with domain-driven design, layered architecture, and hybrid database strategies.

## Overview

This skill covers patterns for:
- Multi-agent systems and orchestration
- Domain-driven agent design
- Layered architecture for agents
- Agent memory with property graphs
- Hybrid database integration (Graph + Document + Relational)

## Multi-Agent Architecture

### Orchestrator Pattern

A central orchestrator delegates tasks to specialized agents:

```python
from claude_agent_sdk import Agent

class AgentOrchestrator:
    """Orchestrates multiple specialized agents."""

    def __init__(self):
        self.agents = {
            "researcher": Agent(
                model="claude-sonnet-4-20250514",
                system_prompt="You are a research specialist...",
            ),
            "writer": Agent(
                model="claude-sonnet-4-20250514",
                system_prompt="You are a technical writer...",
            ),
            "reviewer": Agent(
                model="claude-sonnet-4-20250514",
                system_prompt="You are a code reviewer...",
            ),
        }

    async def execute_task(self, task: str) -> str:
        # Analyze task to determine required agents
        plan = await self._create_plan(task)

        # Execute plan across agents
        results = []
        for step in plan.steps:
            agent = self.agents[step.agent_name]
            result = await agent.run(step.prompt)
            results.append(result)

        # Synthesize final result
        return await self._synthesize(results)
```

### Specialized Agent Types

**Research Agent:**
```python
research_agent = Agent(
    model="claude-sonnet-4-20250514",
    system_prompt="""You are a research specialist.
Your role:
- Gather and synthesize information
- Identify key facts and patterns
- Provide source citations
- Flag uncertain or conflicting information""",
    tools=[search_web, query_database, read_document],
)
```

**Execution Agent:**
```python
execution_agent = Agent(
    model="claude-sonnet-4-20250514",
    system_prompt="""You are an execution specialist.
Your role:
- Implement specific technical tasks
- Write and modify code
- Run tests and validate results
- Report outcomes clearly""",
    tools=[write_file, run_command, run_tests],
    permissions={"allow_file_write": True, "allow_shell": True},
)
```

## Domain-Driven Agent Design

### Domain Modeling First

Before implementing agents, define domain entities:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class AgentEntity:
    """Core agent domain entity."""
    agent_id: str
    name: str
    capabilities: List[str]
    state: dict
    created_at: datetime

@dataclass
class Memory:
    """Agent memory entity."""
    memory_id: str
    agent_id: str
    content: str
    context: dict
    timestamp: datetime
    importance: float  # 0-1 score

@dataclass
class Task:
    """Task entity for agent execution."""
    task_id: str
    agent_id: str
    description: str
    status: str  # pending, in_progress, completed, failed
    result: Optional[dict]
    parent_task_id: Optional[str]  # For subtask hierarchy
```

### Layered Architecture

Organize agent code into layers:

```
my-agent/
├── src/
│   ├── domain/           # Domain layer
│   │   ├── entities.py   # Domain entities
│   │   ├── services.py   # Domain services
│   │   └── repositories.py  # Repository interfaces
│   │
│   ├── agent/            # Agent layer
│   │   ├── skills/       # Agent skills
│   │   ├── config.py     # Agent configuration
│   │   └── executor.py   # Agent execution logic
│   │
│   ├── infrastructure/   # Infrastructure layer
│   │   └── db/
│   │       ├── graph/    # Property graph (Neo4j)
│   │       ├── document/ # Document DB (MongoDB)
│   │       └── relational/  # SQL database
│   │
│   └── api/              # Application layer
│       └── main.py
```

### Domain Services Pattern

```python
# src/domain/services.py
from .entities import Agent, Memory, Task
from .repositories import MemoryRepository, TaskRepository

class AgentService:
    """Domain service for agent operations."""

    def __init__(
        self,
        memory_repo: MemoryRepository,
        task_repo: TaskRepository,
    ):
        self.memory_repo = memory_repo
        self.task_repo = task_repo

    async def store_memory(
        self,
        agent: Agent,
        content: str,
        context: dict,
        importance: float = 0.5,
    ) -> Memory:
        """Store agent memory with importance scoring."""
        memory = Memory(
            memory_id=generate_id(),
            agent_id=agent.agent_id,
            content=content,
            context=context,
            timestamp=datetime.now(),
            importance=importance,
        )
        await self.memory_repo.save(memory)
        return memory

    async def recall_relevant(
        self,
        agent: Agent,
        query: str,
        limit: int = 10,
    ) -> List[Memory]:
        """Recall relevant memories for a query."""
        return await self.memory_repo.search(
            agent_id=agent.agent_id,
            query=query,
            limit=limit,
        )
```

## Agent Memory with Property Graphs

### KSTAR Memory Pattern

Knowledge-Situation-Task-Action-Result pattern for structured memory:

```python
@dataclass
class KSTARMemory:
    """Structured memory following KSTAR pattern."""
    memory_id: str
    knowledge: str      # What was known before
    situation: str      # Context/environment
    task: str           # What needed to be done
    action: str         # What was done
    result: str         # Outcome achieved
    timestamp: datetime
    metadata: dict

    def to_graph_node(self) -> dict:
        """Convert to property graph node."""
        return {
            "id": self.memory_id,
            "type": "KSTARMemory",
            "properties": {
                "knowledge": self.knowledge,
                "situation": self.situation,
                "task": self.task,
                "action": self.action,
                "result": self.result,
                "timestamp": self.timestamp.isoformat(),
            }
        }
```

### Graph-Based Memory Storage

Use property graphs for relationship-rich memory:

```python
# Store memory with relationships
async def store_kstar_memory(
    graph: PropertyGraph,
    memory: KSTARMemory,
    related_memories: List[str] = None,
):
    """Store KSTAR memory in property graph."""
    # Create memory node
    node_id = await graph.create_node(
        label="Memory",
        properties=memory.to_graph_node()["properties"],
    )

    # Create relationships to related memories
    for related_id in (related_memories or []):
        await graph.create_edge(
            from_node={"memory_id": memory.memory_id},
            to_node={"memory_id": related_id},
            relation_type="RELATES_TO",
        )

    return node_id

# Query related memories
async def find_related_memories(
    graph: PropertyGraph,
    memory_id: str,
    depth: int = 2,
) -> List[dict]:
    """Find memories related within N hops."""
    cypher = """
    MATCH (m:Memory {memory_id: $memory_id})
          -[r*1..$depth]-
          (related:Memory)
    RETURN related.memory_id as id,
           related.task as task,
           related.result as result
    """
    return await graph.query(cypher, {
        "memory_id": memory_id,
        "depth": depth,
    })
```

## Hybrid Database Strategy

### When to Use Each Database

| Data Type | Database | Reason |
|-----------|----------|--------|
| Relationships | Property Graph (Neo4j) | Efficient traversal |
| Flexible content | Document DB (MongoDB) | Schema flexibility |
| Structured metadata | Relational (PostgreSQL) | ACID, constraints |

### Database Router Pattern

Route operations to appropriate database:

```python
class DatabaseRouter:
    """Route data operations to appropriate database."""

    def __init__(
        self,
        graph: PropertyGraph,
        document: DocumentStore,
        relational: SQLRepository,
    ):
        self.graph = graph
        self.document = document
        self.relational = relational

    async def store_memory(self, memory: Memory) -> dict:
        """Store memory across databases."""
        results = {}

        # Content in document DB (flexible, searchable)
        doc_id = await self.document.insert({
            "memory_id": memory.memory_id,
            "content": memory.content,
            "context": memory.context,
        })
        results["document_id"] = str(doc_id)

        # Relationships in graph DB
        node_id = await self.graph.create_node(
            label="Memory",
            properties={
                "memory_id": memory.memory_id,
                "importance": memory.importance,
            },
        )
        results["graph_node_id"] = node_id

        # Metadata in relational DB
        await self.relational.insert_memory_metadata(
            memory_id=memory.memory_id,
            agent_id=memory.agent_id,
            timestamp=memory.timestamp,
        )

        return results
```

## Agent Skills as SDK Components

### Skill Structure

Build skills as part of the agent package:

```python
# src/agent/skills/base_skill.py
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseAgentSkill(ABC):
    """Base class for agent skills."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Any:
        """Execute the skill with given parameters."""
        pass

    def to_tool(self):
        """Convert skill to SDK tool."""
        from claude_agent_sdk import Tool
        return Tool(self.execute)
```

### Memory Skill Example

```python
# src/agent/skills/memory_skill.py
from .base_skill import BaseAgentSkill

class MemorySkill(BaseAgentSkill):
    """Skill for managing agent memory."""

    def __init__(self, db_router: DatabaseRouter):
        super().__init__(
            name="memory_management",
            description="Store and retrieve agent memories",
        )
        self.router = db_router

    async def execute(self, params: Dict[str, Any]) -> Any:
        action = params.get("action")

        if action == "store":
            return await self._store(params)
        elif action == "recall":
            return await self._recall(params)
        elif action == "connect":
            return await self._connect(params)

    async def _store(self, params: Dict[str, Any]) -> dict:
        memory = Memory(
            memory_id=generate_id(),
            content=params["content"],
            context=params.get("context", {}),
            importance=params.get("importance", 0.5),
            **params,
        )
        return await self.router.store_memory(memory)
```

## Additional Resources

### Reference Files

For detailed implementation patterns:
- **`references/multi-agent-patterns.md`** - Orchestration and coordination patterns
- **`references/graph-database-integration.md`** - Neo4j integration details

### Related Skills

- **agent-sdk-basics** - Core SDK patterns for beginners
- Learn basics before implementing advanced architectures

## Implementation Workflow

1. **Model the domain first** - Define entities before code
2. **Design layer boundaries** - Clear separation of concerns
3. **Choose databases per use case** - Right tool for each data type
4. **Build skills as components** - Reusable, testable units
5. **Orchestrate with agents** - Coordinate specialized agents
