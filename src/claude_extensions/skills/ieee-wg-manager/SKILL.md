---
name: ieee-wg-manager
description: Manage IEEE Working Group processes including meeting scheduling, document reviews, ballot management, and standards development lifecycle tracking. Use when coordinating IEEE standard development activities, preparing ballots, managing review comments, or tracking PAR milestones.
---

# IEEE Working Group Manager

Manage common IEEE Working Group administrative and coordination tasks throughout the standards development lifecycle.

## When to Use This Skill

Use this skill when:
- Scheduling or documenting IEEE working group meetings
- Coordinating draft standard reviews and comment periods
- Preparing or managing IEEE ballots (WG ballot, sponsor ballot, recirculation)
- Tracking standards development milestones (PAR to publication)
- Generating standard IEEE working group documents (agendas, minutes, comment templates)
- Managing action items and deliverables from working group activities

## Core Workflows

### Meeting Management

**Scheduling Meetings:**
1. Check `references/meeting_schedule_template.md` for standard meeting formats
2. Generate calendar invitations with IEEE-standard format (include bridge/WebEx details)
3. Create meeting agenda using templates in `assets/agenda_template.md`
4. Send pre-meeting reminders 48 hours before meeting

**Recording Minutes:**
1. Use `assets/minutes_template.md` for consistent format
2. Include: attendance, agenda items, decisions, action items, next meeting
3. Track action items in separate action log (see `references/action_item_tracking.md`)
4. Distribute minutes within 5 business days

### Document Review Coordination

**Starting a Review Period:**
1. Announce review period with clear start/end dates (typically 30-45 days)
2. Provide document access (IEEE SA myProject or working group repository)
3. Use comment template from `assets/comment_template.md`
4. Set up comment collection mechanism (spreadsheet, myProject, email)

**Processing Review Comments:**
1. Consolidate comments using `scripts/consolidate_comments.py`
2. Categorize comments: Editorial, Technical, General
3. Assign comments to technical editors or subgroups
4. Track disposition: Accepted, Rejected, Accepted in Principle
5. Generate comment disposition document using `assets/comment_disposition_template.md`

**Comment Resolution:**
- Accepted: Implement as stated
- Rejected: Provide technical rationale
- Accepted in Principle: Implement with modification, explain difference

### Ballot Management

**Types of IEEE Ballots:**
- **Working Group Ballot**: Initial technical review by WG members
- **Sponsor Ballot**: Formal review by sponsor ballot group
- **Recirculation Ballot**: Review of changes after previous ballot

**Preparing Ballot Materials:**
1. Review `references/ballot_process.md` for requirements
2. Prepare ballot statement (what is being balloted)
3. Include: draft standard, ballot instructions, return date
4. Coordinate with IEEE SA staff for sponsor ballot pool formation

**Tracking Ballot Responses:**
1. Use `scripts/ballot_tracker.py` to log responses
2. Track: Approve, Disapprove, Abstain
3. For Disapprove votes, collect and categorize comments
4. Calculate approval percentage (need 75% for sponsor ballot)

**Resolving Ballot Comments:**
1. Address all Disapprove comments with technical responses
2. Make necessary changes to draft
3. Determine if recirculation ballot is needed
4. Document all resolutions in comment disposition log

### Standards Development Lifecycle Tracking

**Project Stages:**
1. **PAR Approval**: Project Authorization Request approved by NesCom
2. **Working Draft (WD)**: Initial drafts, working group review
3. **Committee Draft (CD)**: Working group ballot complete
4. **Final Draft (FD)**: Sponsor ballot complete, ready for submission
5. **Publication**: IEEE SA Board approval, published as standard

**Milestone Tracking:**
- Use `references/lifecycle_milestones.md` for standard timeline
- Track PAR expiration date (typically 4 years from approval)
- Monitor mandatory coordination dates (2-year, 3.5-year reviews)
- Prepare PAR extensions if needed (submit 6 months before expiration)

**Document Version Control:**
- Maintain clear version numbering (D1.0, D1.1, D2.0, etc.)
- Include revision history in document
- Archive previous versions with ballot results
- Tag final versions (FD1.0, FD2.0 for recirculation)

## Key IEEE Terminology

- **PAR**: Project Authorization Request - authorization to develop a standard
- **WG**: Working Group - technical experts developing the standard
- **NesCom**: New Standards Committee - approves/extends PARs
- **RevCom**: Standards Review Committee - final technical review before publication
- **Sponsor**: IEEE Society or Standards Committee sponsoring the standard
- **Ballot Group**: Pool of qualified individuals voting on draft standard
- **Disapprove**: Negative ballot vote requiring technical comment
- **Abstain**: Ballot vote not counting toward approval percentage
- **Recirculation**: Re-ballot of changes after previous ballot

## Document Templates

All templates are located in the `assets/` directory:
- `agenda_template.md` - Standard meeting agenda format
- `minutes_template.md` - Meeting minutes format with action items
- `comment_template.md` - Review comment submission template
- `comment_disposition_template.md` - Comment resolution tracking
- `ballot_instructions.md` - Standard ballot voting instructions
- `par_extension_template.md` - PAR extension request format

## Scripts

- `scripts/consolidate_comments.py` - Merge review comments from multiple sources
- `scripts/ballot_tracker.py` - Track ballot responses and calculate approval rate
- `scripts/action_item_tracker.py` - Manage meeting action items and deadlines

## References

Detailed process documentation in `references/`:
- `meeting_schedule_template.md` - Meeting planning and scheduling guidance
- `action_item_tracking.md` - Action item management best practices
- `ballot_process.md` - Complete IEEE ballot process requirements
- `lifecycle_milestones.md` - Standards development timeline and checkpoints
- `ieee_policies.md` - Relevant IEEE SA policies and procedures

## Best Practices

**Communication:**
- Use clear subject lines: "[WG Name] Meeting Reminder", "[WG Name] Ballot Announcement"
- Include working group number in all communications (e.g., IEEE P3394)
- Maintain email distribution list for all WG members

**Transparency:**
- All meetings should be announced publicly via working group email list
- Meeting materials should be available before meeting (agenda, slides)
- Ballots should include all necessary context and instructions

**Documentation:**
- Archive all meeting minutes, ballot results, and comment dispositions
- Maintain version control for all draft documents
- Keep audit trail of all decisions and rationale

**Deadlines:**
- Set realistic review periods (minimum 30 days for technical content)
- Allow 60-90 days for sponsor ballots
- Plan 6-12 months from sponsor ballot to publication

## Common Workflows

**Quarterly Meeting Cycle:**
1. Schedule meeting 4-6 weeks in advance
2. Send agenda 1 week before meeting
3. Conduct meeting with recorded minutes
4. Distribute minutes within 5 days
5. Follow up on action items 2 weeks before next meeting

**Draft Review Cycle:**
1. Announce review period start
2. Mid-period reminder at 2 weeks
3. Final reminder 1 week before close
4. Close review, consolidate comments
5. Working group review of comments
6. Publish comment dispositions
7. Release updated draft with changes

**Ballot Cycle:**
1. Prepare ballot materials
2. Coordinate ballot pool (for sponsor ballot)
3. Announce ballot with return date (60-90 days)
4. Send reminder at mid-point
5. Final reminder 1 week before close
6. Close ballot, compile results
7. Resolve all Disapprove comments
8. Determine if recirculation needed
9. Conduct recirculation if required
10. Submit to RevCom when complete

## Integration Points

**IEEE SA myProject:**
- Use for document repository
- Track PAR status and milestones
- Manage ballot pools for sponsor ballots
- Submit final draft for publication

**Email Lists:**
- Primary communication channel
- Announce all meetings, ballots, reviews
- Distribute materials and updates

**Web Conferencing:**
- WebEx or Zoom for virtual meetings
- Record sessions when appropriate
- Share screen for draft reviews

## Troubleshooting

**Low Meeting Attendance:**
- Try different time zones (rotate if international)
- Provide dial-in and WebEx options
- Record sessions for later viewing
- Send detailed minutes to all members

**Ballot Not Achieving 75%:**
- Review ballot pool composition
- Address technical comments thoroughly
- Consider working group pre-ballot
- Extend ballot period if needed

**PAR Expiration Approaching:**
- Submit extension 6 months early
- Include progress summary
- Justify need for extension
- Update timeline estimate

**Comment Overload:**
- Categorize comments (editorial vs. technical)
- Create comment tracking spreadsheet
- Assign owners for comment resolution
- Set up comment review subgroup

## Output Examples

When asked to generate meeting agenda:
```markdown
# IEEE P3394 Working Group Meeting
**Date:** [Date]
**Time:** [Time with timezone]
**Location:** [Virtual/Physical]

## Agenda
1. Call to Order
2. Introductions and Attendance
3. Review of Previous Minutes
4. Working Group Updates
   - Draft Status
   - Ballot Results
   - Action Items
5. Technical Discussion
   - [Topic 1]
   - [Topic 2]
6. New Business
7. Action Items Summary
8. Next Meeting
9. Adjournment
```

When processing ballot results:
```
Ballot Results - IEEE P3394 Draft 2.0
Total Ballots: 45
Returns: 40 (88.9% return rate)
Approve: 32 (80.0%)
Disapprove: 5 (12.5%)
Abstain: 3 (7.5%)

Status: PASSED (>75% approval)
Comments: 12 technical comments to resolve
Next Step: Resolve comments, prepare recirculation
```
