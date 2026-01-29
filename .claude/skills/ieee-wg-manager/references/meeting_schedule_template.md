# IEEE Working Group Meeting Schedule Template

## Meeting Cadence Planning

### Regular Meetings
- **Frequency**: [Monthly/Bi-weekly/Weekly]
- **Day of Week**: [Monday/Tuesday/etc.]
- **Time**: [HH:MM] [Timezone]
- **Duration**: [60/90/120] minutes
- **Platform**: [WebEx/Zoom/Teams]

### Special Meetings
- Interim meetings during IEEE standards meetings
- Face-to-face sessions at conferences
- Ad-hoc technical deep dives

---

## Meeting Series Template

### Series: [Year] Regular Working Group Meetings

| # | Date | Time (UTC) | Time (Local) | Type | Agenda Focus | Chair |
|---|------|------------|--------------|------|--------------|-------|
| 1 | YYYY-MM-DD | HH:MM | HH:MM TZ | Regular | Kickoff, PAR review | [Name] |
| 2 | YYYY-MM-DD | HH:MM | HH:MM TZ | Regular | Section 1-3 review | [Name] |
| 3 | YYYY-MM-DD | HH:MM | HH:MM TZ | Regular | Section 4-6 review | [Name] |
| 4 | YYYY-MM-DD | HH:MM | HH:MM TZ | Special | Ballot preparation | [Name] |

---

## Timezone Coordination

### Multi-Timezone Meeting Planner

**Example for global WG with members in US West, US East, Europe, Asia:**

| Location | Timezone | 8am PT | 11am PT | 2pm PT | 5pm PT |
|----------|----------|--------|---------|--------|--------|
| US Pacific | UTC-8 | 8:00 AM | 11:00 AM | 2:00 PM | 5:00 PM |
| US Eastern | UTC-5 | 11:00 AM | 2:00 PM | 5:00 PM | 8:00 PM |
| London | UTC+0 | 4:00 PM | 7:00 PM | 10:00 PM | 1:00 AM+1 |
| Paris | UTC+1 | 5:00 PM | 8:00 PM | 11:00 PM | 2:00 AM+1 |
| Tokyo | UTC+9 | 1:00 AM+1 | 4:00 AM+1 | 7:00 AM+1 | 10:00 AM+1 |
| Sydney | UTC+11 | 3:00 AM+1 | 6:00 AM+1 | 9:00 AM+1 | 12:00 PM+1 |

**Best Times for Global Meetings:**
- **Europe + Americas**: 11am-2pm US Pacific (7pm-10pm London)
- **Americas + Asia**: 5pm-8pm US Pacific (9am-12pm Tokyo next day)
- **All regions**: Consider rotating times to share inconvenience

---

## Meeting Invitation Template

```
Subject: IEEE [WG Number] - [Meeting Type] - [Date]

Dear IEEE [WG Number] Members,

You are invited to attend the [Meeting Type] meeting of IEEE [Working Group Name].

DATE: [Day of week, Month DD, YYYY]
TIME: [HH:MM - HH:MM] [Timezone]
      [HH:MM - HH:MM] [Other Timezone]
      [HH:MM - HH:MM] [Other Timezone]

PLATFORM: [WebEx/Zoom/Teams]
MEETING LINK: [URL]
MEETING ID: [ID]
PASSWORD: [Password]

AGENDA:
1. Call to Order
2. Roll Call and Agenda Review
3. [Topic 1]
4. [Topic 2]
5. [Topic 3]
6. Action Items Review
7. Next Meeting
8. Adjournment

MATERIALS:
- Draft standard: [Link]
- Previous minutes: [Link]
- Presentations: [Link]

Please confirm your attendance by replying to this email.

Looking forward to your participation.

Best regards,
[Chair Name]
[WG Number] Chair
[Email]
```

---

## Calendar Integration

### iCalendar (.ics) Format

```ics
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//IEEE [WG Number]//EN
BEGIN:VEVENT
UID:[unique-id]@ieee.org
DTSTAMP:[YYYYMMDDTHHmmssZ]
DTSTART:[YYYYMMDDTHHmmssZ]
DTEND:[YYYYMMDDTHHmmssZ]
SUMMARY:IEEE [WG Number] - [Meeting Type]
DESCRIPTION:Regular meeting of IEEE [Working Group Name]
LOCATION:[WebEx/Zoom URL]
STATUS:CONFIRMED
SEQUENCE:0
BEGIN:VALARM
TRIGGER:-PT15M
DESCRIPTION:Meeting starts in 15 minutes
ACTION:DISPLAY
END:VALARM
END:VEVENT
END:VCALENDAR
```

---

## Attendance Tracking

### Meeting Attendance Log

| Member Name | Affiliation | Jan | Feb | Mar | Apr | May | Jun | Notes |
|-------------|-------------|-----|-----|-----|-----|-----|-----|-------|
| [Name] | [Company] | ✓ | ✓ | - | R | ✓ | ✓ | R=Regrets |
| [Name] | [Company] | ✓ | - | ✓ | ✓ | - | ✓ | |

**Legend:**
- ✓ = Present
- - = Absent (no notice)
- R = Regrets sent
- P = Proxy vote designated

**Participation Requirements:**
- IEEE SA requires participation in 2 out of 4 consecutive meetings to maintain voting rights
- Track attendance for quorum purposes
- Note any special participation arrangements

---

## Scheduling Best Practices

### Planning Principles

1. **Consistency**: Same day/time reduces confusion
2. **Advance Notice**: Announce meetings 2+ weeks ahead
3. **Holiday Awareness**: Check major holidays in all regions
4. **IEEE Events**: Coordinate with IEEE standards meetings
5. **Draft Deadlines**: Schedule around ballot/comment deadlines

### Conflict Management

**Common Conflicts:**
- Other IEEE WG meetings
- National/religious holidays
- Major conferences
- Company blackout periods (end of quarter, etc.)

**Resolution:**
- Maintain alternate times for conflicts
- Record and distribute for those who can't attend
- Designate proxy voters when possible

### Tools

**Recommended Scheduling Tools:**
- **Doodle/When2Meet**: Find common availability
- **World Time Buddy**: Timezone conversion
- **IEEE Calendar**: Check IEEE event conflicts
- **Outlook/Google Calendar**: Recurring meeting series

---

## Annual Meeting Calendar

### Planning Template

**Q1 (Jan-Mar):**
- January: New year kickoff, review objectives
- February: Technical content review
- March: Mid-year progress check

**Q2 (Apr-Jun):**
- April: Prepare for IEEE events
- May: IEEE standards meetings (face-to-face)
- June: Post-event follow-up

**Q3 (Jul-Sep):**
- July: Summer planning (some regions on holiday)
- August: Ballot preparation
- September: Ballot launch

**Q4 (Oct-Dec):**
- October: Ballot results review
- November: Comment resolution
- December: Year-end wrap-up, next year planning

### Special Meeting Types

**Face-to-Face Meetings:**
- Typically during IEEE standards meetings
- Full-day or multi-day sessions
- More intensive technical work
- Opportunity for social bonding

**Virtual Ad-Hoc Meetings:**
- Called as needed for urgent issues
- Shorter duration (30-60 minutes)
- Focused on specific technical topic
- Informal, often unscheduled in advance

**Subgroup Meetings:**
- May occur between main WG meetings
- Focus on specific section or topic
- Report back to full WG

---

## Meeting Reminders

### Reminder Schedule

**2 Weeks Before:**
- Send initial invitation
- Attach draft materials
- Request agenda items

**1 Week Before:**
- Send reminder with confirmed agenda
- Update materials if needed
- Confirm guest speakers/presenters

**1 Day Before:**
- Final reminder
- Confirm meeting link working
- Share any last-minute materials

**15 Minutes Before:**
- Send "starting soon" message
- Open meeting room early for tech checks

---

## Post-Meeting Follow-Up

### Immediate Actions (Within 24 Hours)
- [ ] Distribute draft minutes
- [ ] Send recording link (if recorded)
- [ ] Distribute presentation materials
- [ ] Send thank you to presenters

### Short-Term Actions (Within 1 Week)
- [ ] Finalize and approve minutes
- [ ] Send action item reminders
- [ ] Schedule any follow-up meetings
- [ ] Update project tracking

---

## Sample Annual Schedule

```markdown
# IEEE P[Number] 2024 Meeting Schedule

## Regular Meetings (2nd Tuesday, 11am Pacific)
- January 9, 2024
- February 13, 2024
- March 12, 2024
- April 9, 2024
- May 14, 2024
- June 11, 2024
- July 9, 2024 (CANCELED - Summer break)
- August 13, 2024
- September 10, 2024
- October 8, 2024
- November 12, 2024
- December 10, 2024 (CANCELED - Year-end)

## Special Meetings
- May 20-23, 2024: Face-to-face at IEEE Standards Meeting (New Orleans)
- September 15-18, 2024: Face-to-face at IEEE Standards Meeting (Berlin)

## Key Deadlines
- March 31, 2024: Working Group Ballot closes
- June 30, 2024: Sponsor Ballot opens
- September 30, 2024: Sponsor Ballot closes
- December 15, 2024: RevCom submission
```
