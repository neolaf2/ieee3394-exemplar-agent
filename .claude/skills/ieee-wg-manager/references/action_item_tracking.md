# Action Item Tracking System

## Overview

Effective action item tracking is critical for IEEE Working Group success. This document provides templates and best practices for tracking action items from initiation through completion.

---

## Action Item Template

### Standard Format

```markdown
**Action Item #[Number]**
- **Owner**: [Name]
- **Assigned**: [Date]
- **Due**: [Date]
- **Status**: [Open/In Progress/Blocked/Completed]
- **Priority**: [High/Medium/Low]
- **Description**: [Clear description of what needs to be done]
- **Success Criteria**: [How do we know it's done?]
- **Dependencies**: [What needs to happen first?]
- **Related Issues**: [Links to related items]
- **Notes**: [Updates, blockers, etc.]
```

### Example

```markdown
**Action Item #042**
- **Owner**: John Smith
- **Assigned**: 2024-01-15
- **Due**: 2024-02-15
- **Status**: In Progress
- **Priority**: High
- **Description**: Draft Section 5.3 (Security Requirements) for committee review
- **Success Criteria**: Section includes at least 8 requirements with rationale and examples
- **Dependencies**: Section 5.1-5.2 must be approved first (AI #038, #039)
- **Related Issues**: Comment #127 from ballot
- **Notes**:
  - 2024-01-20: Draft 60% complete
  - 2024-01-27: Waiting on security subgroup review
  - 2024-02-03: Incorporated subgroup feedback, ready for WG review
```

---

## Action Item Log

### Spreadsheet Format

| ID | Owner | Assigned | Due | Status | Priority | Description | Dependencies | Last Update |
|----|-------|----------|-----|--------|----------|-------------|--------------|-------------|
| 001 | Alice | 2024-01-05 | 2024-01-20 | ✅ Completed | High | Review Section 3 | None | 2024-01-18 |
| 002 | Bob | 2024-01-05 | 2024-02-01 | 🟡 In Progress | Medium | Draft use cases | AI #001 | 2024-01-25 |
| 003 | Carol | 2024-01-12 | 2024-02-15 | 🔴 Blocked | High | Security analysis | Waiting on vendor | 2024-01-26 |
| 004 | Dave | 2024-01-19 | 2024-02-28 | 🟢 Open | Low | Update references | None | 2024-01-19 |

**Status Legend:**
- 🟢 Open - Not yet started
- 🟡 In Progress - Work underway
- 🔴 Blocked - Cannot proceed
- ✅ Completed - Done
- ❌ Cancelled - No longer needed

---

## Action Item Categories

### By Type

**Technical:**
- Draft standard sections
- Resolve technical comments
- Conduct technical analysis
- Create diagrams/figures

**Administrative:**
- Schedule meetings
- Distribute materials
- Collect votes
- Update documentation

**Review:**
- Review draft sections
- Provide technical feedback
- Editorial review
- Cross-reference check

**External:**
- Coordinate with other WGs
- Vendor outreach
- Expert consultation
- Standards body liaison

---

## Priority Levels

### High Priority
- **Timeline**: Critical path items, blocks other work
- **Impact**: Affects standard approval or major milestones
- **Examples**:
  - Ballot preparation
  - Critical comment resolution
  - PAR renewal deadline items

### Medium Priority
- **Timeline**: Important but some flexibility
- **Impact**: Improves quality, not blocking
- **Examples**:
  - Editorial improvements
  - Non-critical technical clarifications
  - Supplementary documentation

### Low Priority
- **Timeline**: Nice to have
- **Impact**: Minor improvements
- **Examples**:
  - Formatting consistency
  - Additional examples
  - Future enhancement notes

---

## Action Item Lifecycle

### 1. Creation
```markdown
**When to Create:**
- During meetings when tasks are assigned
- After comment resolution decisions
- When new requirements identified
- Following subgroup recommendations

**Required Information:**
- Clear description
- Owner assignment
- Due date
- Success criteria
```

### 2. Assignment
```markdown
**Assignment Principles:**
- Volunteer first, assign if needed
- Match expertise to task
- Distribute workload fairly
- Get explicit acceptance from owner

**Owner Responsibilities:**
- Accept or negotiate timeline
- Provide regular updates
- Request help if blocked
- Deliver on time or notify ASAP
```

### 3. Tracking
```markdown
**Update Frequency:**
- Weekly for high-priority items
- Bi-weekly for medium-priority
- Monthly for low-priority
- Immediately if status changes to blocked

**Update Content:**
- Progress percentage
- Blockers encountered
- Help needed
- Revised timeline if needed
```

### 4. Completion
```markdown
**Completion Criteria:**
- Deliverable meets success criteria
- Reviewed by appropriate parties
- Integrated into draft (if applicable)
- Documented in meeting minutes

**Close-Out Process:**
- Mark as completed
- Archive deliverables
- Update related items
- Thank the owner
```

---

## Tracking Tools

### Simple: Markdown Table

```markdown
| ID | Owner | Task | Due | Status |
|----|-------|------|-----|--------|
| 1 | Alice | Draft Section 4 | 2024-02-01 | ✅ |
| 2 | Bob | Review Section 4 | 2024-02-15 | 🟡 |
```

**Pros:** Simple, version controlled
**Cons:** Limited filtering/sorting

### Intermediate: Spreadsheet

**Google Sheets / Excel**
- Filtering and sorting
- Conditional formatting
- Charts and dashboards
- Collaboration features

**Pros:** Rich features, familiar
**Cons:** Not version controlled with code

### Advanced: Issue Tracking System

**GitHub Issues / Jira / Azure DevOps**
- Full workflow management
- Integration with code
- Notifications
- Advanced reporting

**Pros:** Professional, scalable
**Cons:** Learning curve, overhead

---

## Meeting Integration

### During Meetings

**Action Item Capture:**
```markdown
## Action Items from Meeting [Date]

### New Action Items
1. **AI #[N]**: [Owner] to [task] by [date]
2. **AI #[N+1]**: [Owner] to [task] by [date]

### Updates on Existing Action Items
- **AI #[X]**: Status update: [progress]
- **AI #[Y]**: COMPLETED ✅
- **AI #[Z]**: DUE DATE EXTENDED to [new date]
```

**Review Process:**
1. Review all open action items
2. Get status updates from owners
3. Identify blockers
4. Assign new action items
5. Confirm due dates

---

## Reporting

### Status Report Template

```markdown
# Action Item Status Report
**Date**: [Report Date]
**Working Group**: IEEE P[Number]

## Summary
- **Total Open**: [N]
- **Completed This Period**: [N]
- **Overdue**: [N]
- **At Risk**: [N]

## High Priority Items

### On Track ✅
- AI #[N]: [Brief description] - [Owner] - Due [Date]

### At Risk ⚠️
- AI #[N]: [Brief description] - [Owner] - Due [Date]
  - **Issue**: [What's the problem?]
  - **Mitigation**: [What's being done?]

### Overdue 🔴
- AI #[N]: [Brief description] - [Owner] - Was Due [Date]
  - **Reason**: [Why overdue?]
  - **New Timeline**: [When will it be done?]

## Completed Items ✅
- AI #[N]: [Description] - Completed by [Owner] on [Date]

## Metrics
- **Average Time to Complete**: [N] days
- **Completion Rate**: [N]%
- **On-Time Completion Rate**: [N]%
```

---

## Best Practices

### 1. Clear Descriptions
❌ Bad: "Fix the thing"
✅ Good: "Update Section 3.2 to clarify the authentication flow diagram, adding sequence numbers and error paths"

### 2. SMART Criteria
- **Specific**: Exactly what needs to be done
- **Measurable**: Clear success criteria
- **Achievable**: Owner has skills/resources
- **Relevant**: Contributes to WG goals
- **Time-bound**: Specific due date

### 3. Single Owner
- Each action item has ONE primary owner
- Can have contributors/helpers, but one person accountable
- If task is too big for one owner, split into multiple action items

### 4. Realistic Due Dates
- Discuss timeline with owner before committing
- Consider owner's other commitments
- Add buffer for review/revision cycles
- Better to have accurate timeline than missed deadline

### 5. Regular Review
- Review ALL open action items at each meeting
- Don't let items languish without updates
- Close completed items promptly
- Cancel items that are no longer needed

---

## Handling Overdue Items

### When an Item Becomes Overdue

**Step 1: Understand Why**
- Owner forgot?
- Task harder than expected?
- Blocker encountered?
- Owner's priorities changed?

**Step 2: Address the Issue**
- **If forgot**: Gentle reminder, set new date
- **If harder**: Break into smaller items, get help
- **If blocked**: Resolve blocker or find workaround
- **If priorities changed**: Reassign or cancel

**Step 3: Update Status**
- Document reason for delay
- Set realistic new timeline
- Add to "at risk" tracking
- Inform WG if impacts critical path

### Escalation Path

**Level 1: Owner Self-Report**
- Owner proactively updates when at risk

**Level 2: Chair Follow-Up**
- Chair reaches out for update
- Offer help or resources

**Level 3: Reassignment**
- If owner cannot complete, reassign
- No blame, just need to keep moving

**Level 4: Scope Change**
- If repeatedly blocked, reconsider if needed
- May be signal to adjust approach

---

## Action Item Archive

### Completed Items

**Archive Structure:**
```
action-items/
├── active/
│   └── 2024-q1-action-items.md
├── completed/
│   ├── 2023-q4-completed.md
│   ├── 2024-q1-completed.md
│   └── 2024-q2-completed.md
└── cancelled/
    └── 2024-cancelled.md
```

**Archive Entry:**
```markdown
**AI #042** - ✅ Completed 2024-02-12
- **Owner**: John Smith
- **Original Due**: 2024-02-15
- **Description**: Draft Section 5.3 (Security Requirements)
- **Outcome**: Section drafted, reviewed, and integrated into Draft 3.0
- **Related Documents**: draft-3.0.pdf, security-review-notes.md
```

---

## Metrics and Improvement

### Key Metrics to Track

**Completion Metrics:**
- On-time completion rate
- Average time to complete
- Overdue item count
- Cancellation rate

**Workload Metrics:**
- Action items per person
- Average open items
- New items per meeting
- Completion velocity

**Quality Metrics:**
- Items requiring rework
- Items split/combined
- Clarification requests

### Continuous Improvement

**Quarterly Review:**
- Analyze completion trends
- Identify bottlenecks
- Adjust processes
- Recognize top performers

**Process Adjustments:**
- If many overdue: Are due dates realistic?
- If many cancelled: Are we creating unnecessary items?
- If low completion rate: Do owners have too many items?
- If poor descriptions: Improve description template

---

## Templates for Different Scenarios

### Ballot Comment Resolution

```markdown
**AI #[N]**: Resolve Ballot Comment #[X]
- **Owner**: [Name]
- **Comment Category**: [Technical/Editorial/General]
- **Commenter**: [Name] ([Affiliation])
- **Comment Summary**: [Brief summary]
- **Proposed Disposition**: [Accept/Reject/Accept in Principle]
- **Required Action**: [What changes to make]
- **Due**: [Before recirculation ballot]
- **Review**: Technical editor to review before integration
```

### Section Drafting

```markdown
**AI #[N]**: Draft Section [X.Y] ([Title])
- **Owner**: [Name]
- **Section Scope**: [What it covers]
- **Length**: Approximately [N] pages
- **Dependencies**: Sections [X.Y] must be stable
- **Deliverable**: Draft text with examples and figures
- **Review Process**: Subgroup review → WG review → editorial review
- **Due**: [Date]
```

### Technical Analysis

```markdown
**AI #[N]**: Analyze [Topic]
- **Owner**: [Name]
- **Analysis Type**: [Performance/Security/Compatibility/etc.]
- **Deliverable**: Technical report with recommendations
- **Presentation**: Present findings at [Date] meeting
- **Decision Needed**: [What will WG decide based on this?]
- **Due**: [Date]
```
