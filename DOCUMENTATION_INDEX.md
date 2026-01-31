# Documentation Index

Complete index of all documentation for the IEEE 3394 Exemplar Agent.

## Getting Started

### Essential First Steps

| Document | Description | Audience |
|----------|-------------|----------|
| **[README.md](./README.md)** | Project overview and quick start | Everyone |
| **[QUICKSTART.md](./QUICKSTART.md)** | Step-by-step getting started guide | New users |
| **[DAEMON.md](./DAEMON.md)** | Daemon management (start/stop/restart) | Developers |

---

## Security & Authentication

### Authentication System

| Document | Description | Audience |
|----------|-------------|----------|
| **[ADMIN_CAPABILITIES.md](./ADMIN_CAPABILITIES.md)** | Admin access requirements and policy rules | Admins, Developers |
| **[ADMIN_ACCESS_IMPLEMENTATION.md](./ADMIN_ACCESS_IMPLEMENTATION.md)** | Implementation summary with test results | Developers |
| **[CLI_CHANNEL_AUTHENTICATION.md](./CLI_CHANNEL_AUTHENTICATION.md)** | CLI progressive authentication (NONE → LOW → MEDIUM → HIGH) | Developers |
| **[REQ_CAP_CH_AUTH_COMPLETE.md](./REQ_CAP_CH_AUTH_COMPLETE.md)** | Channel authentication compliance verification | Developers, Auditors |
| **[AUTHENTICATION.md](./AUTHENTICATION.md)** | General authentication architecture | Developers |
| **[CURRENT_STATE_SUMMARY.md](./CURRENT_STATE_SUMMARY.md)** | Current authentication state and status | Developers |

### Capability Access Control

| Document | Description | Audience |
|----------|-------------|----------|
| **[docs/CAPABILITY_ACL.md](./docs/CAPABILITY_ACL.md)** | Three-layer authorization cascade (Channel→Principal→Capability) | Developers, Auditors |
| **[docs/CHANNEL_BINDING.md](./docs/CHANNEL_BINDING.md)** | Channel binding and authentication | Developers |

### Key Concepts

- **Three-Layer Authorization Cascade**: Channel Auth → Principal Resolution → Capability Role Mapping
- **Visibility Tiers**: PUBLIC, LISTED, PROTECTED, PRIVATE, ADMIN for capability visibility
- **LRXMD Permissions**: List, Read, Execute, Modify, Delete for fine-grained access
- **Progressive Authentication**: CLI supports NONE → LOW → MEDIUM → HIGH → CRYPTOGRAPHIC assurance levels
- **Dual Principal Model**: Client Principal (CP) + Service Principal (SP) per P3394 standard
- **MCP Memory Server**: Swappable memory backend for ACL configuration
- **Bootstrap Configuration**: Preload memory server with principals, bindings, and ACLs

---

## Channel Configuration

### WhatsApp Channel

| Document | Description | Audience |
|----------|-------------|----------|
| **[.claude/skills/whatsapp-config/SKILL.md](./.claude/skills/whatsapp-config/SKILL.md)** | WhatsApp configuration skill (admin-only) | Admins |
| **[.claude/skills/whatsapp-config/references/meta_setup_guide.md](./.claude/skills/whatsapp-config/references/meta_setup_guide.md)** | Complete Meta Business API setup guide | Admins |
| **[.claude/skills/whatsapp-config/references/webhook_troubleshooting.md](./.claude/skills/whatsapp-config/references/webhook_troubleshooting.md)** | Webhook troubleshooting and diagnostics | Admins, Support |

**Configuration requires**:
- HIGH assurance (admin login via `/login` command)
- Meta Business Account (verified)
- WhatsApp Business API access

---

## Architecture & Design

### Core Architecture

| Document | Description | Audience |
|----------|-------------|----------|
| **[ARCHITECTURE.md](./ARCHITECTURE.md)** | Channel adapter architecture | Developers |
| **[CLAUDE.md](./CLAUDE.md)** | Complete architecture specification | Developers |
| **[CHANNEL_COMMAND_ROUTING.md](./CHANNEL_COMMAND_ROUTING.md)** | Message routing and command dispatch | Developers |
| **[CONTENT_NEGOTIATION.md](./CONTENT_NEGOTIATION.md)** | Content negotiation between channels | Developers |
| **[ACD_IMPLEMENTATION_SUMMARY.md](./ACD_IMPLEMENTATION_SUMMARY.md)** | Agent Capability Descriptor implementation | Developers |

### Storage & Memory

| Document | Description | Audience |
|----------|-------------|----------|
| **[STORAGE.md](./STORAGE.md)** | Storage architecture (STM/LTM) | Developers |
| **[XAPI.md](./XAPI.md)** | xAPI (Experience API) integration | Developers |

---

## SDK Integration

### Claude Agent SDK (v0.2.0-sdk)

| Document | Description | Audience |
|----------|-------------|----------|
| **[SDK_INTEGRATION.md](./SDK_INTEGRATION.md)** | Complete SDK integration guide | Developers |
| **[REFACTOR_STATUS.md](./REFACTOR_STATUS.md)** | SDK refactor progress and status | Developers |
| **[MERGE_GUIDE.md](./MERGE_GUIDE.md)** | Guide for merging SDK refactor branch | Maintainers |
| **[CHANGELOG.md](./CHANGELOG.md)** | Version history and changes | Everyone |

---

## API & Protocol

### Anthropic API Channel

| Document | Description | Audience |
|----------|-------------|----------|
| **[ANTHROPIC_API.md](./ANTHROPIC_API.md)** | Anthropic API channel adapters | Developers |
| **[ANTHROPIC_API_IMPLEMENTATION.md](./ANTHROPIC_API_IMPLEMENTATION.md)** | Implementation details and examples | Developers |

### P3394 Protocol

| Document | Description | Audience |
|----------|-------------|----------|
| **[P3394-Capability-Mapping-to-skills.md](./P3394-Capability-Mapping-to-skills.md)** | Capability to skill mapping | Developers |
| Documentation in `/docs/` directory | Additional P3394 specifications | Spec authors |

---

## Testing

### Test Documentation

| Document | Description | Audience |
|----------|-------------|----------|
| **[TESTING_GUIDE.md](./TESTING_GUIDE.md)** | Complete testing guide | Developers |
| **[TEST_RESULTS.md](./TEST_RESULTS.md)** | Test results and coverage | Developers |
| `tests/test_admin_access_control.py` | Admin access control test suite | Developers |

**Test Suites**:
- Authentication & Authorization (8 tests)
- Channel adapters
- Gateway routing
- UMF message handling
- Skills system
- KSTAR memory

---

## Skills

### Built-in Skills

| Skill | Description | Access Level |
|-------|-------------|--------------|
| **[p3394-explainer](./.claude/skills/p3394-explainer/SKILL.md)** | Explains P3394 concepts | Public |
| **[site-generator](./.claude/skills/site-generator/SKILL.md)** | Generates static HTML pages | Admin |
| **[whatsapp-config](./.claude/skills/whatsapp-config/SKILL.md)** | Configures WhatsApp channel | Admin only (HIGH) |
| **[skill-creator](./.claude/skills/skill-creator/SKILL.md)** | Creates new skills | Admin |
| **[ieee-wg-manager](./.claude/skills/ieee-wg-manager/SKILL.md)** | IEEE working group management | Members |
| **[docx](./.claude/skills/docx/SKILL.md)** | Word document manipulation | Public |
| **[pdf](./.claude/skills/pdf/SKILL.md)** | PDF manipulation | Public |
| **[pptx](./.claude/skills/pptx/SKILL.md)** | PowerPoint manipulation | Public |

### Skills System

| Document | Description | Audience |
|----------|-------------|----------|
| **[.claude/skills/README.md](./.claude/skills/README.md)** | Skills directory overview | Developers |
| **[.claude/skills/skill-creator/SKILL.md](./.claude/skills/skill-creator/SKILL.md)** | How to create new skills | Skill creators |

---

## Implementation Status

### Current Status

| Document | Description | Audience |
|----------|-------------|----------|
| **[IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)** | Overall implementation status | Maintainers |
| **[IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)** | Implementation summary | Maintainers |
| **[SESSION_WORK_SUMMARY.md](./SESSION_WORK_SUMMARY.md)** | Recent work session summary | Developers |
| **[BRANCH_READY.md](./BRANCH_READY.md)** | Branch merge readiness | Maintainers |

---

## Project Management

### Planning & Requirements

| Document | Description | Audience |
|----------|-------------|----------|
| Requirements in `/docs/requirements/` | Detailed P3394 requirements | Spec authors |
| Various `REQ_*.md` files | Specific requirement implementations | Developers |

---

## Quick Navigation

### By Role

**New Users**:
1. Start with [README.md](./README.md)
2. Follow [QUICKSTART.md](./QUICKSTART.md)
3. Explore skills in [.claude/skills/](./.claude/skills/)

**Developers**:
1. Read [ARCHITECTURE.md](./ARCHITECTURE.md)
2. Review [SDK_INTEGRATION.md](./SDK_INTEGRATION.md)
3. Study [AUTHENTICATION.md](./AUTHENTICATION.md)
4. Check [TESTING_GUIDE.md](./TESTING_GUIDE.md)

**Admins**:
1. Review [ADMIN_CAPABILITIES.md](./ADMIN_CAPABILITIES.md)
2. Read [QUICKSTART.md](./QUICKSTART.md) authentication section
3. Follow [whatsapp-config skill](./.claude/skills/whatsapp-config/SKILL.md) for channel setup
4. Reference [CLI_CHANNEL_AUTHENTICATION.md](./CLI_CHANNEL_AUTHENTICATION.md)

**Security Auditors**:
1. Review [ADMIN_ACCESS_IMPLEMENTATION.md](./ADMIN_ACCESS_IMPLEMENTATION.md)
2. Study [REQ_CAP_CH_AUTH_COMPLETE.md](./REQ_CAP_CH_AUTH_COMPLETE.md)
3. Check test results in [TEST_RESULTS.md](./TEST_RESULTS.md)
4. Examine policy engine in `src/ieee3394_agent/core/auth/policy.py`

### By Topic

**Authentication & Security**:
- [ADMIN_CAPABILITIES.md](./ADMIN_CAPABILITIES.md) - Requirements and access control
- [CLI_CHANNEL_AUTHENTICATION.md](./CLI_CHANNEL_AUTHENTICATION.md) - Progressive authentication
- [ADMIN_ACCESS_IMPLEMENTATION.md](./ADMIN_ACCESS_IMPLEMENTATION.md) - Implementation details

**Channel Configuration**:
- [whatsapp-config skill](./.claude/skills/whatsapp-config/SKILL.md) - WhatsApp setup
- [ANTHROPIC_API.md](./ANTHROPIC_API.md) - Anthropic API channel

**Development**:
- [SDK_INTEGRATION.md](./SDK_INTEGRATION.md) - SDK integration
- [TESTING_GUIDE.md](./TESTING_GUIDE.md) - Testing
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Architecture

**Skills**:
- [skill-creator](./.claude/skills/skill-creator/SKILL.md) - Creating skills
- [.claude/skills/README.md](./.claude/skills/README.md) - Skills overview

---

## External Resources

- **IEEE P3394 Standard**: https://ieee3394.org
- **Claude Agent SDK**: Anthropic documentation
- **Meta WhatsApp Business API**: https://developers.facebook.com/docs/whatsapp/cloud-api

---

## Document Status

| Status | Description |
|--------|-------------|
| ✅ Complete | Document is complete and up-to-date |
| 🔄 In Progress | Document is being actively updated |
| 📝 Draft | Document is in draft form |
| 🗂️ Archive | Historical document, may be outdated |

**Last Updated**: 2026-01-29

---

## Contributing to Documentation

When adding new documentation:

1. Add the document to this index
2. Update README.md if it's a major feature
3. Cross-reference related documents
4. Follow markdown conventions
5. Include audience indicators (who should read it)
6. Update "Last Updated" date in this index

---

*This is the definitive index of all agent documentation. Keep it synchronized with actual docs.*
