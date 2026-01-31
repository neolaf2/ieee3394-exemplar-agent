# Multi-Agent Patterns

Comprehensive patterns for building multi-agent systems with the Claude Agent SDK.

## Orchestration Patterns

### 1. Hub-and-Spoke Pattern

Central orchestrator delegates to specialized agents:

```
           ┌─────────────┐
           │ Orchestrator│
           └──────┬──────┘
        ┌─────────┼─────────┐
        ▼         ▼         ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │Researcher│ │ Writer  │ │Reviewer │
   └─────────┘ └─────────┘ └─────────┘
```

**Implementation:**

```python
from claude_agent_sdk import Agent
from dataclasses import dataclass
from typing import List, Dict, Any
import asyncio

@dataclass
class TaskAssignment:
    agent_name: str
    prompt: str
    depends_on: List[str] = None

class HubAndSpokeOrchestrator:
    """Central hub orchestrating specialized agents."""

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.results: Dict[str, Any] = {}

    def register_agent(self, name: str, agent: Agent):
        """Register a specialized agent."""
        self.agents[name] = agent

    async def execute_plan(
        self,
        tasks: List[TaskAssignment],
    ) -> Dict[str, Any]:
        """Execute tasks respecting dependencies."""
        completed = set()

        while len(completed) < len(tasks):
            # Find tasks ready to run
            ready = [
                t for t in tasks
                if t.agent_name not in completed
                and all(d in completed for d in (t.depends_on or []))
            ]

            # Execute ready tasks in parallel
            async def run_task(task: TaskAssignment):
                agent = self.agents[task.agent_name]
                # Inject results from dependencies
                prompt = self._inject_context(task.prompt, task.depends_on)
                result = await agent.run(prompt)
                return task.agent_name, result

            results = await asyncio.gather(*[run_task(t) for t in ready])

            for name, result in results:
                self.results[name] = result
                completed.add(name)

        return self.results

    def _inject_context(
        self,
        prompt: str,
        dependencies: List[str],
    ) -> str:
        """Inject results from dependencies into prompt."""
        if not dependencies:
            return prompt

        context_parts = []
        for dep in dependencies:
            if dep in self.results:
                context_parts.append(
                    f"[Result from {dep}]:\n{self.results[dep].content}"
                )

        if context_parts:
            return f"{prompt}\n\nContext:\n" + "\n\n".join(context_parts)
        return prompt


# Usage
orchestrator = HubAndSpokeOrchestrator()
orchestrator.register_agent("researcher", research_agent)
orchestrator.register_agent("writer", writer_agent)
orchestrator.register_agent("reviewer", reviewer_agent)

tasks = [
    TaskAssignment("researcher", "Research topic X"),
    TaskAssignment("writer", "Write article about X", depends_on=["researcher"]),
    TaskAssignment("reviewer", "Review the article", depends_on=["writer"]),
]

results = await orchestrator.execute_plan(tasks)
```

### 2. Pipeline Pattern

Sequential processing through agent stages:

```
Input → Agent1 → Agent2 → Agent3 → Output
```

```python
class AgentPipeline:
    """Sequential agent pipeline."""

    def __init__(self, stages: List[tuple[str, Agent]]):
        self.stages = stages

    async def process(self, initial_input: str) -> str:
        """Process input through all stages."""
        current = initial_input

        for stage_name, agent in self.stages:
            response = await agent.run(
                f"Previous stage output:\n{current}\n\nProcess this."
            )
            current = response.content
            print(f"[{stage_name}] completed")

        return current


# Usage
pipeline = AgentPipeline([
    ("extract", extraction_agent),
    ("transform", transformation_agent),
    ("validate", validation_agent),
])

result = await pipeline.process("Raw input data...")
```

### 3. Peer Network Pattern

Agents communicate directly with each other:

```
   ┌─────────┐     ┌─────────┐
   │ Agent A │◄───►│ Agent B │
   └────┬────┘     └────┬────┘
        │               │
        └───────┬───────┘
                ▼
          ┌─────────┐
          │ Agent C │
          └─────────┘
```

```python
from collections import defaultdict
from typing import Callable

class AgentNetwork:
    """Peer-to-peer agent communication network."""

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.connections: Dict[str, List[str]] = defaultdict(list)
        self.message_queue: Dict[str, List[dict]] = defaultdict(list)

    def add_agent(self, name: str, agent: Agent):
        self.agents[name] = agent

    def connect(self, from_agent: str, to_agent: str):
        """Create bidirectional connection."""
        self.connections[from_agent].append(to_agent)
        self.connections[to_agent].append(from_agent)

    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message: str,
    ):
        """Send message between connected agents."""
        if to_agent not in self.connections[from_agent]:
            raise ValueError(f"No connection: {from_agent} -> {to_agent}")

        self.message_queue[to_agent].append({
            "from": from_agent,
            "content": message,
        })

    async def agent_step(self, agent_name: str) -> str:
        """Process one step for an agent."""
        agent = self.agents[agent_name]
        messages = self.message_queue[agent_name]

        if not messages:
            return None

        # Format messages for agent
        formatted = "\n".join([
            f"[From {m['from']}]: {m['content']}"
            for m in messages
        ])

        response = await agent.run(
            f"You have messages:\n{formatted}\n\nRespond appropriately."
        )

        # Clear processed messages
        self.message_queue[agent_name] = []

        return response.content
```

### 4. Supervisor Pattern

A supervisor monitors and controls worker agents:

```python
from enum import Enum
from dataclasses import dataclass

class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    STUCK = "stuck"
    COMPLETED = "completed"

@dataclass
class WorkerState:
    status: AgentStatus
    current_task: str = None
    attempts: int = 0
    last_output: str = None

class SupervisorOrchestrator:
    """Supervisor monitors and helps stuck workers."""

    def __init__(self, supervisor: Agent):
        self.supervisor = supervisor
        self.workers: Dict[str, Agent] = {}
        self.worker_states: Dict[str, WorkerState] = {}
        self.max_attempts = 3

    def add_worker(self, name: str, agent: Agent):
        self.workers[name] = agent
        self.worker_states[name] = WorkerState(status=AgentStatus.IDLE)

    async def assign_task(self, worker_name: str, task: str):
        """Assign task to worker with supervision."""
        state = self.worker_states[worker_name]
        state.current_task = task
        state.status = AgentStatus.WORKING
        state.attempts = 0

        while state.status == AgentStatus.WORKING:
            state.attempts += 1

            # Worker attempts task
            response = await self.workers[worker_name].run(task)
            state.last_output = response.content

            # Supervisor evaluates
            evaluation = await self.supervisor.run(f"""
Evaluate this worker output for task: {task}

Worker output:
{response.content}

Is this:
1. COMPLETE - Task successfully finished
2. NEEDS_HELP - Worker is stuck or wrong approach
3. RETRY - Minor issues, worker should try again

Respond with just the status word.
""")

            status = evaluation.content.strip().upper()

            if "COMPLETE" in status:
                state.status = AgentStatus.COMPLETED
            elif "NEEDS_HELP" in status or state.attempts >= self.max_attempts:
                # Supervisor provides guidance
                guidance = await self.supervisor.run(f"""
The worker is stuck on: {task}

Their last output:
{response.content}

Provide specific guidance to help them complete the task.
""")
                task = f"{task}\n\nSupervisor guidance: {guidance.content}"
                state.status = AgentStatus.WORKING
            # else: retry with same task

        return state.last_output
```

## Communication Patterns

### Shared Context

```python
class SharedContext:
    """Thread-safe shared context for agents."""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any:
        async with self._lock:
            return self._data.get(key)

    async def set(self, key: str, value: Any):
        async with self._lock:
            self._data[key] = value

    async def update(self, key: str, updater: Callable):
        async with self._lock:
            self._data[key] = updater(self._data.get(key))


# Usage
context = SharedContext()

# Agent A stores findings
await context.set("research_findings", findings)

# Agent B retrieves and builds on them
findings = await context.get("research_findings")
```

### Message Passing

```python
@dataclass
class AgentMessage:
    sender: str
    recipient: str
    content: str
    message_type: str  # request, response, broadcast
    correlation_id: str = None

class MessageBus:
    """Centralized message passing."""

    def __init__(self):
        self.queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self.handlers: Dict[str, Callable] = {}

    def register(self, agent_name: str, handler: Callable):
        self.handlers[agent_name] = handler

    async def send(self, message: AgentMessage):
        await self.queues[message.recipient].put(message)

    async def broadcast(self, sender: str, content: str):
        for recipient in self.handlers:
            if recipient != sender:
                await self.send(AgentMessage(
                    sender=sender,
                    recipient=recipient,
                    content=content,
                    message_type="broadcast",
                ))

    async def receive(self, agent_name: str) -> AgentMessage:
        return await self.queues[agent_name].get()
```

## Coordination Patterns

### Consensus Building

Multiple agents must agree:

```python
class ConsensusBuilder:
    """Build consensus among multiple agents."""

    def __init__(self, agents: List[Agent], threshold: float = 0.6):
        self.agents = agents
        self.threshold = threshold

    async def reach_consensus(
        self,
        question: str,
        options: List[str],
    ) -> tuple[str, float]:
        """Get agents to vote and reach consensus."""
        votes = defaultdict(int)

        for agent in self.agents:
            response = await agent.run(f"""
Question: {question}

Options:
{chr(10).join(f'- {opt}' for opt in options)}

Choose exactly one option and explain briefly.
Start your response with the option you choose.
""")

            # Parse vote
            for opt in options:
                if opt.lower() in response.content.lower()[:100]:
                    votes[opt] += 1
                    break

        total = len(self.agents)
        winner = max(votes.keys(), key=lambda k: votes[k])
        confidence = votes[winner] / total

        if confidence >= self.threshold:
            return winner, confidence
        else:
            # No consensus - might need discussion round
            return None, confidence
```

### Work Distribution

```python
class WorkDistributor:
    """Distribute work across agents based on capability."""

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.capabilities: Dict[str, List[str]] = {}
        self.load: Dict[str, int] = defaultdict(int)

    def register(
        self,
        name: str,
        agent: Agent,
        capabilities: List[str],
    ):
        self.agents[name] = agent
        self.capabilities[name] = capabilities

    def find_capable(self, required_capability: str) -> List[str]:
        """Find agents with required capability."""
        return [
            name for name, caps in self.capabilities.items()
            if required_capability in caps
        ]

    async def assign(
        self,
        task: str,
        required_capability: str,
    ) -> tuple[str, Any]:
        """Assign task to least-loaded capable agent."""
        capable = self.find_capable(required_capability)
        if not capable:
            raise ValueError(f"No agent for: {required_capability}")

        # Choose least loaded
        agent_name = min(capable, key=lambda n: self.load[n])

        self.load[agent_name] += 1
        try:
            result = await self.agents[agent_name].run(task)
            return agent_name, result
        finally:
            self.load[agent_name] -= 1
```

## Error Handling

### Graceful Degradation

```python
class ResilientOrchestrator:
    """Handle agent failures gracefully."""

    def __init__(self, primary: Agent, fallback: Agent):
        self.primary = primary
        self.fallback = fallback

    async def run_with_fallback(
        self,
        prompt: str,
        max_retries: int = 2,
    ) -> Any:
        """Try primary, fall back on failure."""
        for attempt in range(max_retries):
            try:
                return await self.primary.run(prompt)
            except Exception as e:
                print(f"Primary failed (attempt {attempt + 1}): {e}")

        # Fall back to secondary
        print("Using fallback agent")
        return await self.fallback.run(prompt)
```

### Circuit Breaker

```python
from time import time

class CircuitBreaker:
    """Prevent repeated calls to failing agents."""

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60,
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures: Dict[str, int] = defaultdict(int)
        self.last_failure: Dict[str, float] = {}
        self.open_circuits: set = set()

    def is_open(self, agent_name: str) -> bool:
        if agent_name not in self.open_circuits:
            return False

        # Check if reset timeout passed
        if time() - self.last_failure.get(agent_name, 0) > self.reset_timeout:
            self.open_circuits.remove(agent_name)
            self.failures[agent_name] = 0
            return False

        return True

    def record_failure(self, agent_name: str):
        self.failures[agent_name] += 1
        self.last_failure[agent_name] = time()

        if self.failures[agent_name] >= self.failure_threshold:
            self.open_circuits.add(agent_name)

    def record_success(self, agent_name: str):
        self.failures[agent_name] = 0
```
