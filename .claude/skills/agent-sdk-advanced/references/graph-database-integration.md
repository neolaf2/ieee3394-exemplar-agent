# Property Graph Integration for Agent Memory

Detailed patterns for integrating property graphs (Neo4j) with Claude Agent SDK for sophisticated memory management.

## Neo4j Setup

### Connection Configuration

```python
# src/infrastructure/db/graph/connection.py
from neo4j import AsyncGraphDatabase
from typing import Optional
import os

class Neo4jConnection:
    """Async Neo4j connection manager."""

    _driver = None

    @classmethod
    async def get_driver(cls):
        if cls._driver is None:
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            user = os.getenv("NEO4J_USER", "neo4j")
            password = os.getenv("NEO4J_PASSWORD")

            cls._driver = AsyncGraphDatabase.driver(
                uri,
                auth=(user, password),
                max_connection_pool_size=50,
            )
        return cls._driver

    @classmethod
    async def close(cls):
        if cls._driver:
            await cls._driver.close()
            cls._driver = None
```

### Property Graph Interface

```python
# src/infrastructure/db/graph/property_graph.py
from neo4j import AsyncSession
from typing import Any, Dict, List, Optional

class PropertyGraph:
    """Property graph operations for agent memory."""

    def __init__(self, driver):
        self.driver = driver

    async def create_node(
        self,
        label: str,
        properties: Dict[str, Any],
    ) -> str:
        """Create a node with given label and properties."""
        async with self.driver.session() as session:
            result = await session.execute_write(
                self._create_node_tx,
                label,
                properties,
            )
            return result

    @staticmethod
    async def _create_node_tx(
        tx,
        label: str,
        properties: Dict[str, Any],
    ) -> str:
        query = f"""
        CREATE (n:{label} $props)
        SET n.created_at = datetime()
        RETURN elementId(n) as node_id
        """
        result = await tx.run(query, props=properties)
        record = await result.single()
        return record["node_id"]

    async def create_edge(
        self,
        from_node: Dict[str, Any],
        to_node: Dict[str, Any],
        relation_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create relationship between nodes."""
        async with self.driver.session() as session:
            return await session.execute_write(
                self._create_edge_tx,
                from_node,
                to_node,
                relation_type,
                properties or {},
            )

    @staticmethod
    async def _create_edge_tx(
        tx,
        from_node: Dict[str, Any],
        to_node: Dict[str, Any],
        relation_type: str,
        properties: Dict[str, Any],
    ) -> str:
        # Build match conditions dynamically
        from_conditions = " AND ".join([
            f"from.{k} = $from_{k}"
            for k in from_node.keys()
        ])
        to_conditions = " AND ".join([
            f"to.{k} = $to_{k}"
            for k in to_node.keys()
        ])

        query = f"""
        MATCH (from) WHERE {from_conditions}
        MATCH (to) WHERE {to_conditions}
        CREATE (from)-[r:{relation_type}]->(to)
        SET r += $props
        SET r.created_at = datetime()
        RETURN elementId(r) as edge_id
        """

        params = {
            **{f"from_{k}": v for k, v in from_node.items()},
            **{f"to_{k}": v for k, v in to_node.items()},
            "props": properties,
        }

        result = await tx.run(query, **params)
        record = await result.single()
        return record["edge_id"]

    async def query(
        self,
        cypher: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict]:
        """Execute Cypher query and return results."""
        async with self.driver.session() as session:
            result = await session.run(cypher, params or {})
            return [record.data() async for record in result]

    async def find_node(
        self,
        label: str,
        properties: Dict[str, Any],
    ) -> Optional[Dict]:
        """Find single node by properties."""
        conditions = " AND ".join([
            f"n.{k} = ${k}"
            for k in properties.keys()
        ])

        query = f"""
        MATCH (n:{label})
        WHERE {conditions}
        RETURN n
        LIMIT 1
        """

        results = await self.query(query, properties)
        return results[0]["n"] if results else None

    async def delete_node(
        self,
        label: str,
        properties: Dict[str, Any],
        detach: bool = True,
    ):
        """Delete node(s) matching properties."""
        conditions = " AND ".join([
            f"n.{k} = ${k}"
            for k in properties.keys()
        ])

        detach_clause = "DETACH " if detach else ""
        query = f"""
        MATCH (n:{label})
        WHERE {conditions}
        {detach_clause}DELETE n
        """

        async with self.driver.session() as session:
            await session.run(query, properties)
```

## Memory Graph Schema

### Schema Design

```cypher
// Node labels and properties

// Agent node
(:Agent {
    agent_id: string,      // Unique identifier
    name: string,          // Display name
    capabilities: [string], // List of capabilities
    created_at: datetime
})

// Memory node
(:Memory {
    memory_id: string,     // Unique identifier
    content_hash: string,  // Hash of content (content stored in document DB)
    importance: float,     // 0-1 importance score
    memory_type: string,   // episodic, semantic, procedural
    created_at: datetime,
    accessed_at: datetime  // Last access time
})

// Concept node (for semantic memory)
(:Concept {
    concept_id: string,
    name: string,
    definition: string,
    category: string
})

// Task node
(:Task {
    task_id: string,
    description: string,
    status: string,        // pending, in_progress, completed, failed
    created_at: datetime,
    completed_at: datetime
})

// Relationships
(:Agent)-[:HAS_MEMORY]->(:Memory)
(:Agent)-[:PERFORMED]->(:Task)
(:Memory)-[:RELATES_TO]->(:Memory)
(:Memory)-[:ABOUT]->(:Concept)
(:Concept)-[:RELATED_TO]->(:Concept)
(:Task)-[:SUBTASK_OF]->(:Task)
(:Task)-[:PRODUCED]->(:Memory)
```

### Schema Initialization

```python
async def initialize_schema(graph: PropertyGraph):
    """Create indexes and constraints."""
    queries = [
        # Uniqueness constraints
        "CREATE CONSTRAINT agent_id IF NOT EXISTS FOR (a:Agent) REQUIRE a.agent_id IS UNIQUE",
        "CREATE CONSTRAINT memory_id IF NOT EXISTS FOR (m:Memory) REQUIRE m.memory_id IS UNIQUE",
        "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.concept_id IS UNIQUE",
        "CREATE CONSTRAINT task_id IF NOT EXISTS FOR (t:Task) REQUIRE t.task_id IS UNIQUE",

        # Indexes for common queries
        "CREATE INDEX memory_type IF NOT EXISTS FOR (m:Memory) ON (m.memory_type)",
        "CREATE INDEX memory_importance IF NOT EXISTS FOR (m:Memory) ON (m.importance)",
        "CREATE INDEX task_status IF NOT EXISTS FOR (t:Task) ON (t.status)",
        "CREATE INDEX concept_category IF NOT EXISTS FOR (c:Concept) ON (c.category)",
    ]

    for query in queries:
        await graph.query(query)
```

## Memory Operations

### Store Memory with Relationships

```python
class MemoryGraphService:
    """Graph-based memory service for agents."""

    def __init__(self, graph: PropertyGraph, doc_store):
        self.graph = graph
        self.doc_store = doc_store

    async def store_memory(
        self,
        agent_id: str,
        content: str,
        memory_type: str = "episodic",
        importance: float = 0.5,
        related_concepts: List[str] = None,
        related_memories: List[str] = None,
    ) -> str:
        """Store memory with relationships."""
        import hashlib
        memory_id = generate_id()
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Store content in document DB
        await self.doc_store.insert({
            "memory_id": memory_id,
            "content": content,
            "agent_id": agent_id,
        })

        # Create memory node in graph
        await self.graph.create_node("Memory", {
            "memory_id": memory_id,
            "content_hash": content_hash,
            "importance": importance,
            "memory_type": memory_type,
        })

        # Link to agent
        await self.graph.create_edge(
            from_node={"agent_id": agent_id},
            to_node={"memory_id": memory_id},
            relation_type="HAS_MEMORY",
        )

        # Link to concepts
        for concept_id in (related_concepts or []):
            await self.graph.create_edge(
                from_node={"memory_id": memory_id},
                to_node={"concept_id": concept_id},
                relation_type="ABOUT",
            )

        # Link to related memories
        for related_id in (related_memories or []):
            await self.graph.create_edge(
                from_node={"memory_id": memory_id},
                to_node={"memory_id": related_id},
                relation_type="RELATES_TO",
                properties={"created_at": "now()"},
            )

        return memory_id
```

### Query Related Memories

```python
async def find_related_memories(
    self,
    memory_id: str,
    max_depth: int = 2,
    min_importance: float = 0.3,
) -> List[Dict]:
    """Find memories related within N hops."""
    query = """
    MATCH path = (m:Memory {memory_id: $memory_id})
                 -[:RELATES_TO*1..$max_depth]-
                 (related:Memory)
    WHERE related.importance >= $min_importance
    RETURN DISTINCT
        related.memory_id as memory_id,
        related.memory_type as memory_type,
        related.importance as importance,
        length(path) as distance
    ORDER BY related.importance DESC, distance ASC
    LIMIT 20
    """

    results = await self.graph.query(query, {
        "memory_id": memory_id,
        "max_depth": max_depth,
        "min_importance": min_importance,
    })

    # Fetch full content from document DB
    memory_ids = [r["memory_id"] for r in results]
    contents = await self.doc_store.find({
        "memory_id": {"$in": memory_ids}
    }).to_list(length=20)

    # Merge graph data with content
    content_map = {c["memory_id"]: c["content"] for c in contents}
    for r in results:
        r["content"] = content_map.get(r["memory_id"])

    return results
```

### Semantic Memory Operations

```python
async def store_concept(
    self,
    name: str,
    definition: str,
    category: str,
    related_concepts: List[str] = None,
) -> str:
    """Store a semantic concept."""
    concept_id = generate_id()

    await self.graph.create_node("Concept", {
        "concept_id": concept_id,
        "name": name,
        "definition": definition,
        "category": category,
    })

    for related_id in (related_concepts or []):
        await self.graph.create_edge(
            from_node={"concept_id": concept_id},
            to_node={"concept_id": related_id},
            relation_type="RELATED_TO",
        )

    return concept_id

async def find_concepts_by_category(
    self,
    category: str,
    include_related: bool = True,
) -> List[Dict]:
    """Find concepts in a category with optional related concepts."""
    if include_related:
        query = """
        MATCH (c:Concept {category: $category})
        OPTIONAL MATCH (c)-[:RELATED_TO]-(related:Concept)
        RETURN c.concept_id as id,
               c.name as name,
               c.definition as definition,
               collect(DISTINCT related.name) as related_concepts
        """
    else:
        query = """
        MATCH (c:Concept {category: $category})
        RETURN c.concept_id as id,
               c.name as name,
               c.definition as definition
        """

    return await self.graph.query(query, {"category": category})
```

### Memory Consolidation

Consolidate similar memories to prevent redundancy:

```python
async def consolidate_memories(
    self,
    agent_id: str,
    similarity_threshold: float = 0.85,
):
    """Find and merge similar memories."""
    # Find memory clusters
    query = """
    MATCH (a:Agent {agent_id: $agent_id})-[:HAS_MEMORY]->(m:Memory)
    WITH m
    ORDER BY m.created_at DESC
    LIMIT 100
    RETURN m.memory_id as memory_id
    """

    memories = await self.graph.query(query, {"agent_id": agent_id})

    # Group similar memories (simplified - real impl would use embeddings)
    clusters = await self._cluster_similar_memories(
        [m["memory_id"] for m in memories],
        similarity_threshold,
    )

    # Merge clusters
    for cluster in clusters:
        if len(cluster) > 1:
            await self._merge_memory_cluster(cluster)

async def _merge_memory_cluster(self, memory_ids: List[str]):
    """Merge memories in a cluster into one."""
    # Keep the one with highest importance
    query = """
    MATCH (m:Memory)
    WHERE m.memory_id IN $memory_ids
    RETURN m.memory_id as id, m.importance as importance
    ORDER BY m.importance DESC
    """

    results = await self.graph.query(query, {"memory_ids": memory_ids})
    primary_id = results[0]["id"]
    secondary_ids = [r["id"] for r in results[1:]]

    # Transfer relationships to primary
    transfer_query = """
    MATCH (secondary:Memory)-[r]->(target)
    WHERE secondary.memory_id IN $secondary_ids
    MATCH (primary:Memory {memory_id: $primary_id})
    MERGE (primary)-[new_r:RELATES_TO]->(target)
    """

    await self.graph.query(transfer_query, {
        "secondary_ids": secondary_ids,
        "primary_id": primary_id,
    })

    # Delete secondary memories
    for sid in secondary_ids:
        await self.graph.delete_node("Memory", {"memory_id": sid})
```

## Performance Optimization

### Batch Operations

```python
async def batch_create_memories(
    self,
    agent_id: str,
    memories: List[Dict],
) -> List[str]:
    """Create multiple memories efficiently."""
    query = """
    UNWIND $memories as mem
    CREATE (m:Memory {
        memory_id: mem.memory_id,
        content_hash: mem.content_hash,
        importance: mem.importance,
        memory_type: mem.memory_type
    })
    WITH m, mem
    MATCH (a:Agent {agent_id: $agent_id})
    CREATE (a)-[:HAS_MEMORY]->(m)
    RETURN m.memory_id as id
    """

    results = await self.graph.query(query, {
        "agent_id": agent_id,
        "memories": memories,
    })

    return [r["id"] for r in results]
```

### Caching Frequent Queries

```python
from functools import lru_cache
import asyncio

class CachedMemoryService:
    """Memory service with query caching."""

    def __init__(self, graph: PropertyGraph, cache_ttl: int = 300):
        self.graph = graph
        self.cache = {}
        self.cache_ttl = cache_ttl

    async def get_agent_memories(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> List[Dict]:
        """Get recent memories with caching."""
        cache_key = f"agent_memories:{agent_id}:{limit}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        query = """
        MATCH (a:Agent {agent_id: $agent_id})-[:HAS_MEMORY]->(m:Memory)
        RETURN m.memory_id as id,
               m.memory_type as type,
               m.importance as importance
        ORDER BY m.created_at DESC
        LIMIT $limit
        """

        results = await self.graph.query(query, {
            "agent_id": agent_id,
            "limit": limit,
        })

        self.cache[cache_key] = results

        # Invalidate cache after TTL
        asyncio.create_task(self._invalidate_after(cache_key))

        return results

    async def _invalidate_after(self, key: str):
        await asyncio.sleep(self.cache_ttl)
        self.cache.pop(key, None)
```
