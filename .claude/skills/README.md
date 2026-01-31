# IEEE 3394 Exemplar Agent Skills

This directory contains skills that extend the agent's capabilities for domain-specific tasks.

## Installed Skills

### Admin-Only Skills

#### whatsapp-config ⚠️ ADMIN ONLY
**Purpose**: Configure WhatsApp channel for Meta Business API integration.

**Access Requirements**:
- HIGH assurance (must `/login` with admin API key)
- Permissions: `["admin"]`
- CLI channel only

**Capabilities**:
- Meta Business API credential validation
- Service principal creation with encryption
- Webhook configuration instructions
- Troubleshooting guidance

**Key Resources**:
- `SKILL.md` - Complete configuration workflow (7 steps)
- `scripts/configure_whatsapp.py` - Main configuration script
- `scripts/validate_whatsapp_creds.py` - Credential validation against Meta API
- `references/meta_setup_guide.md` - Complete Meta Business setup guide
- `references/webhook_troubleshooting.md` - Webhook diagnostics and fixes

**Triggers**:
- "configure whatsapp"
- "setup whatsapp channel"
- "connect whatsapp"

**Security**: All credentials encrypted with Fernet, changes audited to KSTAR memory.

---

#### skill-creator
**Purpose**: Guide users through creating new skills for the agent.

**Access**: Admin recommended (creates agent capabilities)

**Capabilities**:
- Skill initialization with proper structure
- Template generation
- Validation and packaging

---

### IEEE Working Group Management

#### ieee-wg-manager
**Purpose**: Manage IEEE Working Group processes throughout the standards development lifecycle.

**Capabilities**:
- Meeting scheduling and documentation
- Ballot preparation and tracking
- Comment consolidation and disposition
- Action item management
- Standards lifecycle milestone tracking

**Key Resources**:
- `SKILL.md` - Main skill with workflows and instructions
- `scripts/` - Python tools for ballot tracking, comment consolidation, action item management
- `references/` - IEEE process documentation (ballot process, lifecycle milestones, policies)
- `assets/` - Templates for agendas, minutes, comments, ballot instructions

**Usage**: Automatically loaded when agent starts. Invoked when users ask about IEEE WG management tasks.

---

### P3394 Standard Skills

#### p3394-explainer
**Purpose**: Explain IEEE P3394 standard concepts clearly with examples.

**Triggers**:
- "explain p3394"
- "what is UMF"
- "how do channels work"

---

#### site-generator
**Purpose**: Generate static HTML pages for the IEEE 3394 website.

**Triggers**:
- "generate site"
- "update website"
- "rebuild static pages"

---

### Document Skills

#### docx
**Purpose**: Create and manipulate Microsoft Word documents (.docx).

**Capabilities**:
- Document creation from scratch
- Editing existing documents
- Extracting text and structure

---

#### pdf
**Purpose**: Create and manipulate PDF documents.

**Capabilities**:
- PDF creation
- Text extraction
- Form field manipulation
- PDF merging and splitting

---

#### pptx
**Purpose**: Create and manipulate PowerPoint presentations (.pptx).

**Capabilities**:
- Presentation creation
- Slide manipulation
- Template application

---

## How Skills Work

Skills are automatically loaded from this directory when the agent initializes. Each skill:

1. **Has YAML frontmatter** with `name` and `description` in SKILL.md
2. **Bundles resources** in `scripts/`, `references/`, and `assets/` subdirectories
3. **Provides workflows** that Claude follows when the skill is relevant
4. **Is invoked automatically** by the Claude Agent SDK when the task matches the skill's description

## Adding New Skills

To add a new skill to this agent:

1. Create skill using the `skill-creator` skill in your Claude Code session
2. Validate and package: `python /path/to/skill-creator/scripts/package_skill.py skill-name`
3. Copy to this directory: `cp -r skill-name .claude/skills/`
4. Restart agent (if running) to load the new skill

## Skill Structure

```
skill-name/
├── SKILL.md              # Required: Main skill file with YAML frontmatter
├── scripts/              # Optional: Executable tools (Python, Bash, etc.)
├── references/           # Optional: Documentation loaded into context as needed
└── assets/               # Optional: Files used in output (templates, etc.)
```

## Best Practices

- **Keep SKILL.md focused**: Core workflows and instructions only
- **Put details in references/**: Large documentation goes in references/, not SKILL.md
- **Scripts for repeatability**: Any code written repeatedly should become a script
- **Templates in assets/**: Files that get copied or filled out go in assets/

## Access Control

Skills can specify access requirements in their metadata or implementation:

| Access Level | Description | Examples |
|--------------|-------------|----------|
| **Public** | Available to all authenticated users | p3394-explainer, docx, pdf, pptx |
| **Member** | Requires member permissions | ieee-wg-manager |
| **Admin** | Requires HIGH assurance via `/login` | whatsapp-config, skill-creator |

**Admin-only skills** require:
1. CLI channel access (not available from other channels)
2. HIGH assurance level (must `/login <admin-api-key>`)
3. Admin permissions in credential binding

See **[ADMIN_CAPABILITIES.md](../ADMIN_CAPABILITIES.md)** for complete documentation.

## Maintenance

- Review skills quarterly for relevance
- Update reference documents when IEEE policies change
- Enhance scripts based on user feedback
- Add new skills as domain needs emerge
- Update access control requirements as needed
