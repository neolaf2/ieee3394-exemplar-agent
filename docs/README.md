# Student Companion Agent Documentation

This directory contains all documentation for the Student Companion Agent, organized by category.

## Directory Structure

```
docs/
├── architecture/     # System design and architecture
├── api/              # API specifications and implementation
├── guides/           # User and developer guides
├── implementation/   # Implementation status and details
├── reference/        # Technical reference documentation
└── development/      # Development notes and changelog
```

## Quick Links

### Getting Started
- [Quick Start Guide](guides/QUICKSTART.md) - Get up and running quickly
- [Installation Guide](guides/INSTALLATION.md) - Detailed installation instructions
- [SDK Developer Guide](guides/SDK_DEVELOPER_GUIDE.md) - Building with the SDK

### Architecture
- [System Architecture](architecture/ARCHITECTURE.md) - Overall system design
- [Authentication](architecture/AUTHENTICATION.md) - Auth system design
- [Storage System](architecture/STORAGE.md) - Data persistence
- [Daemon Architecture](architecture/DAEMON.md) - Agent host design
- [P3394 Long-Term Memory](architecture/P3394-LONG-TERM-MEMORY-SPEC.md) - Memory system spec

### API Documentation
- [Anthropic API](api/ANTHROPIC_API.md) - Anthropic-compatible API
- [XAPI](api/XAPI.md) - Extended API specification

### Technical Reference
- [Capability ACL](reference/CAPABILITY_ACL.md) - Access control system
- [Capability Catalog](reference/CAPABILITY_CATALOG.md) - Capability registry
- [Channel Binding](reference/CHANNEL_BINDING.md) - Channel system

### Development
- [Changelog](development/CHANGELOG.md) - Version history
- [Testing Guide](guides/TESTING_GUIDE.md) - How to run tests

## IEEE P3394 Standard

This agent is built on the IEEE P3394 Agent Interface Standard, providing:
- Universal Message Format (UMF)
- Multi-channel communication
- Capability discovery
- Agent interoperability
