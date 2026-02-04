# Documentation Index

Complete index of all documentation for the Student Companion Agent.

## Quick Reference

| Document | Description | Audience |
|----------|-------------|----------|
| **[README.md](../../README.md)** | Project overview and quick start | Everyone |
| **[QUICKSTART.md](../guides/QUICKSTART.md)** | Step-by-step getting started guide | New users |
| **[INSTALLATION.md](../guides/INSTALLATION.md)** | Detailed installation instructions | Developers |

---

## Documentation by Category

### Getting Started

| Document | Description |
|----------|-------------|
| [Quick Start](../guides/QUICKSTART.md) | Get running in 5 minutes |
| [Installation Guide](../guides/INSTALLATION.md) | Complete setup instructions |
| [SDK Developer Guide](../guides/SDK_DEVELOPER_GUIDE.md) | Building with the SDK |
| [Testing Guide](../guides/TESTING_GUIDE.md) | Running and writing tests |
| [SDK Integration](../guides/SDK_INTEGRATION.md) | SDK integration patterns |

### Architecture

| Document | Description |
|----------|-------------|
| [Architecture Overview](../architecture/ARCHITECTURE.md) | System design |
| [Authentication](../architecture/AUTHENTICATION.md) | Auth system design |
| [Storage](../architecture/STORAGE.md) | Data persistence layer |
| [Daemon](../architecture/DAEMON.md) | Agent host architecture |
| [Channel Routing](../architecture/CHANNEL_COMMAND_ROUTING.md) | Message routing |
| [Content Negotiation](../architecture/CONTENT_NEGOTIATION.md) | Format handling |
| [MCP Channel](../architecture/MCP_CHANNEL.md) | MCP integration |
| [P3394 Memory Spec](../architecture/P3394-LONG-TERM-MEMORY-SPEC.md) | Long-term memory |

### API Documentation

| Document | Description |
|----------|-------------|
| [Anthropic API](../api/ANTHROPIC_API.md) | Anthropic-compatible API |
| [Anthropic API Implementation](../api/ANTHROPIC_API_IMPLEMENTATION.md) | Implementation details |
| [XAPI](../api/XAPI.md) | Experience API integration |

### Technical Reference

| Document | Description |
|----------|-------------|
| [Capability ACL](../reference/CAPABILITY_ACL.md) | Access control system |
| [Capability Catalog](../reference/CAPABILITY_CATALOG.md) | Capability registry |
| [Channel Binding](../reference/CHANNEL_BINDING.md) | Channel authentication |

### Implementation Status

| Document | Description |
|----------|-------------|
| [Implementation Status](../implementation/IMPLEMENTATION_STATUS.md) | Overall status |
| [Implementation Summary](../implementation/IMPLEMENTATION_SUMMARY.md) | Summary |
| [ACD Implementation](../implementation/ACD_IMPLEMENTATION_SUMMARY.md) | Agent Capability Descriptor |
| [Refactor Status](../implementation/REFACTOR_STATUS.md) | SDK refactor progress |
| [Test Results](../implementation/TEST_RESULTS.md) | Test coverage |
| [Capability Mapping](../implementation/P3394-Capability-Mapping-to-skills.md) | Capability to skill mapping |

### Development

| Document | Description |
|----------|-------------|
| [Changelog](./CHANGELOG.md) | Version history |
| [Merge Guide](./MERGE_GUIDE.md) | Branch merging |
| [Branch Ready](./BRANCH_READY.md) | Merge readiness |
| [Session Summary](./SESSION_WORK_SUMMARY.md) | Work session notes |

---

## Skills

### Student Companion Skills

| Skill | Description |
|-------|-------------|
| [Study Planner](../../.claude/skills/study-planner/SKILL.md) | Create personalized study schedules |
| [Concept Explainer](../../.claude/skills/concept-explainer/SKILL.md) | Break down complex concepts |
| [Quiz Generator](../../.claude/skills/quiz-generator/SKILL.md) | Generate practice assessments |
| [Homework Helper](../../.claude/skills/homework-helper/SKILL.md) | Guided homework assistance |

### Other Skills

| Skill | Description |
|-------|-------------|
| [Skills Overview](../../.claude/skills/README.md) | Skills directory |
| [Echo](../../.claude/skills/echo/SKILL.md) | Test skill |
| [Help](../../.claude/skills/help/SKILL.md) | Help system |

---

## Reading Paths

### For New Users
1. Start with [README.md](../../README.md)
2. Follow [Quick Start](../guides/QUICKSTART.md)
3. Explore the [Skills](../../.claude/skills/README.md)

### For Developers
1. Read [Architecture](../architecture/ARCHITECTURE.md)
2. Review [SDK Integration](../guides/SDK_INTEGRATION.md)
3. Study [Authentication](../architecture/AUTHENTICATION.md)
4. Check [Testing Guide](../guides/TESTING_GUIDE.md)

### For API Integration
1. Review [Anthropic API](../api/ANTHROPIC_API.md)
2. Study [Channel Binding](../reference/CHANNEL_BINDING.md)
3. Check [Capability Catalog](../reference/CAPABILITY_CATALOG.md)

---

## Key Concepts

- **P3394 Universal Message Format (UMF)**: Standard message structure for agent communication
- **Channel Adapters**: Transform native protocols (HTTP, CLI, WebSocket) to/from UMF
- **Capability Catalog**: Unified view of all agent capabilities
- **KSTAR Memory**: Knowledge-Situation-Task-Action-Result memory system
- **Skills**: Markdown-defined capabilities that extend agent behavior
