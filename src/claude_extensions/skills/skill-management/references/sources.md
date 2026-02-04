# Skill Discovery Sources

Detailed information about each skill source for discovery.

## 1. SkillsMP Marketplace

**URL**: https://skillsmp.com/

### Overview
SkillsMP is the largest agent skills marketplace with 71,000+ skills indexed from public GitHub repositories. It provides intelligent search, category filtering, and quality indicators.

### Key Features
- Smart search across all indexed skills
- Category filtering (see categories below)
- Quality indicators (minimum 2 stars required)
- Compatible with Claude Code, Codex CLI, and ChatGPT

### API/Search Patterns
- Browse categories: `https://skillsmp.com/categories`
- Search: `https://skillsmp.com/search?q=<query>`
- WebSearch fallback: `site:skillsmp.com "<keyword>"`

### Categories Available
- AI & Machine Learning
- Analytics & Data
- API & Integration
- Automation
- Business & Marketing
- Code Quality
- Database
- Design & Creative
- DevOps & Infrastructure
- Document Processing
- Enterprise
- Gaming
- Media & Video
- Productivity
- Scientific & Research
- Security
- Web Development
- Workflow

### Quality Indicators
- Star count (minimum 2 to be listed)
- Last update date
- Documentation completeness
- Community adoption

---

## 2. Anthropic Official Skills

**URL**: https://github.com/anthropics/skills

### Overview
Production-ready skills maintained by Anthropic. High quality, well-documented, and regularly updated.

### Skill Categories

#### Document Skills
| Skill | Description |
|-------|-------------|
| **pdf** | Extract form fields, manipulate PDF files |
| **docx** | Word document creation and editing |
| **pptx** | PowerPoint presentation creation |
| **xlsx** | Excel spreadsheet creation and manipulation |

#### Development Skills
- Code review and analysis
- Testing frameworks
- Git automation

#### Creative Skills
- Design tools
- Asset management

### Installation
```bash
git clone https://github.com/anthropics/skills.git /tmp/anthropic-skills
cp -r /tmp/anthropic-skills/skills/<skill-name> ~/.claude/skills/
```

### License
- Most skills: Apache 2.0 (open source)
- Document skills: Source-available (check LICENSE.txt)

---

## 3. davila7/claude-code-templates

**URL**: https://github.com/davila7/claude-code-templates/tree/main/cli-tool/components/skills/

### Overview
Community-maintained skill templates organized by domain/category. Good starting points for customization.

### Available Categories

| Category | Description |
|----------|-------------|
| **ai-research** | AI research and exploration tools |
| **analytics/google-analytics** | Google Analytics integration |
| **business-marketing** | Marketing automation and business tools |
| **creative-design** | Design workflows and creative tools |
| **database/postgres-schema-design** | PostgreSQL database design |
| **development** | General software development |
| **document-processing** | Document manipulation utilities |
| **enterprise-communication** | Business communication systems |
| **media** | Media handling and processing |
| **productivity** | Task and time management |
| **railway** | Railway platform deployment |
| **scientific** | Scientific computing and research |
| **sentry** | Error tracking integration |
| **utilities** | General purpose utilities |
| **video** | Video processing and editing |
| **web-development** | Frontend/backend web development |
| **workflow-automation** | Process automation |

### Installation
```bash
git clone https://github.com/davila7/claude-code-templates.git /tmp/claude-templates
cp -r /tmp/claude-templates/cli-tool/components/skills/<category>/<skill> ~/.claude/skills/
```

---

## 4. awesome-claude-skills

**URL**: https://github.com/travisvn/awesome-claude-skills

### Overview
Curated list of community Claude skills. Manually reviewed for quality and usefulness.

### How to Use
1. Browse the README for categorized skill listings
2. Each entry includes: name, description, and source link
3. Follow source link to install

### WebSearch Pattern
```
site:github.com/travisvn/awesome-claude-skills "<keyword>"
```

---

## 5. Other GitHub Sources

### daymade/claude-code-skills
**URL**: https://github.com/daymade/claude-code-skills

Professional skills for enhanced development workflows.

### mhattingpete/claude-skills-marketplace
**URL**: https://github.com/mhattingpete/claude-skills-marketplace

Git automation, testing, and code review skills.

### General GitHub Search
```
# Search for Claude Code skills on GitHub
WebSearch: "github claude code skill SKILL.md <keyword>"
WebSearch: "github anthropic skill <keyword>"
```

---

## 6. Local Skills

**Path**: `~/.claude/skills/`

### Discovery Commands

```bash
# List all installed skills
ls ~/.claude/skills/

# Get skill name and description
for f in ~/.claude/skills/*/SKILL.md; do
  skill_name=$(dirname "$f" | xargs basename)
  description=$(grep "^description:" "$f" | sed 's/description: //')
  echo "$skill_name: $description"
done

# Search skill content
grep -r "<keyword>" ~/.claude/skills/

# Find skills by functionality
grep -l "pdf\|PDF" ~/.claude/skills/*/SKILL.md
```

### Skill Structure Validation
```bash
# Check if skill has valid structure
for dir in ~/.claude/skills/*/; do
  if [ -f "$dir/SKILL.md" ]; then
    name=$(grep "^name:" "$dir/SKILL.md")
    desc=$(grep "^description:" "$dir/SKILL.md")
    if [ -n "$name" ] && [ -n "$desc" ]; then
      echo "✓ $(basename $dir)"
    else
      echo "✗ $(basename $dir) - missing frontmatter"
    fi
  else
    echo "✗ $(basename $dir) - no SKILL.md"
  fi
done
```

---

## Search Strategy by Use Case

### "I need a skill for X task"
1. Start with SkillsMP search
2. Check Anthropic official skills
3. Search GitHub broadly
4. Check if already installed locally

### "What skills exist for category Y?"
1. Browse SkillsMP categories
2. Check davila7 category folders
3. Review awesome-claude-skills curated list

### "I want high-quality, production-ready skills"
1. Prioritize Anthropic official skills
2. Filter SkillsMP by star count (10+)
3. Check last update date (within 6 months)

### "I want to explore community innovations"
1. Search GitHub broadly
2. Check awesome-claude-skills for curated picks
3. Browse SkillsMP newest additions
