#!/usr/bin/env python3
"""
IEEE Action Item Tracker

Tracks action items from working group meetings, sends reminders,
and generates status reports.
"""

import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from enum import Enum


class Priority(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Status(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    BLOCKED = "Blocked"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class ActionItem:
    """Represents a single action item"""

    def __init__(
        self,
        item_id: str,
        owner: str,
        description: str,
        assigned_date: str,
        due_date: str,
        priority: Priority = Priority.MEDIUM,
        status: Status = Status.OPEN,
        dependencies: Optional[str] = None,
        notes: Optional[str] = None
    ):
        self.item_id = item_id
        self.owner = owner
        self.description = description
        self.assigned_date = datetime.fromisoformat(assigned_date)
        self.due_date = datetime.fromisoformat(due_date)
        self.priority = Priority(priority) if isinstance(priority, str) else priority
        self.status = Status(status) if isinstance(status, str) else status
        self.dependencies = dependencies
        self.notes = notes
        self.last_update = datetime.now()

    def days_until_due(self) -> int:
        """Calculate days until due date"""
        delta = self.due_date - datetime.now()
        return delta.days

    def is_overdue(self) -> bool:
        """Check if action item is overdue"""
        return self.status not in [Status.COMPLETED, Status.CANCELLED] and self.days_until_due() < 0

    def is_at_risk(self) -> bool:
        """Check if action item is at risk (due soon or overdue)"""
        if self.status in [Status.COMPLETED, Status.CANCELLED]:
            return False
        days_left = self.days_until_due()
        return days_left < 7 or days_left < 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for CSV export"""
        return {
            'item_id': self.item_id,
            'owner': self.owner,
            'description': self.description,
            'assigned_date': self.assigned_date.date().isoformat(),
            'due_date': self.due_date.date().isoformat(),
            'priority': self.priority.value,
            'status': self.status.value,
            'dependencies': self.dependencies or '',
            'notes': self.notes or '',
            'last_update': self.last_update.date().isoformat()
        }


class ActionItemTracker:
    """Track and manage action items"""

    def __init__(self, csv_file: str = "action_items.csv"):
        self.csv_file = Path(csv_file)
        self.items: List[ActionItem] = []
        self.fieldnames = [
            'item_id', 'owner', 'description', 'assigned_date', 'due_date',
            'priority', 'status', 'dependencies', 'notes', 'last_update'
        ]

    def load(self) -> int:
        """Load action items from CSV file"""
        if not self.csv_file.exists():
            return 0

        self.items = []
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                item = ActionItem(
                    item_id=row['item_id'],
                    owner=row['owner'],
                    description=row['description'],
                    assigned_date=row['assigned_date'],
                    due_date=row['due_date'],
                    priority=row['priority'],
                    status=row['status'],
                    dependencies=row.get('dependencies'),
                    notes=row.get('notes')
                )
                self.items.append(item)

        return len(self.items)

    def save(self):
        """Save action items to CSV file"""
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()
            for item in self.items:
                writer.writerow(item.to_dict())

    def add_item(
        self,
        owner: str,
        description: str,
        due_date: str,
        priority: Priority = Priority.MEDIUM,
        dependencies: Optional[str] = None
    ) -> ActionItem:
        """Add a new action item"""
        # Generate new ID
        max_id = 0
        for item in self.items:
            try:
                item_num = int(item.item_id.replace('AI-', ''))
                max_id = max(max_id, item_num)
            except:
                pass

        new_id = f"AI-{max_id + 1:03d}"

        item = ActionItem(
            item_id=new_id,
            owner=owner,
            description=description,
            assigned_date=datetime.now().date().isoformat(),
            due_date=due_date,
            priority=priority,
            dependencies=dependencies
        )

        self.items.append(item)
        self.save()
        return item

    def get_item(self, item_id: str) -> Optional[ActionItem]:
        """Get action item by ID"""
        for item in self.items:
            if item.item_id == item_id:
                return item
        return None

    def update_status(self, item_id: str, status: Status, notes: Optional[str] = None):
        """Update action item status"""
        item = self.get_item(item_id)
        if item:
            item.status = status
            if notes:
                item.notes = notes
            item.last_update = datetime.now()
            self.save()
            return True
        return False

    def get_by_status(self, status: Status) -> List[ActionItem]:
        """Get all items with specific status"""
        return [item for item in self.items if item.status == status]

    def get_by_owner(self, owner: str) -> List[ActionItem]:
        """Get all items for specific owner"""
        return [item for item in self.items if item.owner.lower() == owner.lower()]

    def get_overdue(self) -> List[ActionItem]:
        """Get all overdue items"""
        return [item for item in self.items if item.is_overdue()]

    def get_at_risk(self) -> List[ActionItem]:
        """Get all at-risk items"""
        return [item for item in self.items if item.is_at_risk()]

    def get_active(self) -> List[ActionItem]:
        """Get all active (not completed/cancelled) items"""
        return [item for item in self.items
                if item.status not in [Status.COMPLETED, Status.CANCELLED]]

    def generate_summary_report(self) -> str:
        """Generate summary status report"""
        active = self.get_active()
        overdue = self.get_overdue()
        at_risk = self.get_at_risk()
        completed = self.get_by_status(Status.COMPLETED)

        report = f"""
{'=' * 70}
Action Item Status Report
{'=' * 70}

SUMMARY
{'-' * 70}
Total Active Items:        {len(active)}
Completed This Period:     {len([i for i in completed if (datetime.now() - i.last_update).days <= 7])}
Overdue Items:             {len(overdue)} {'⚠️' if overdue else ''}
At Risk Items:             {len(at_risk)} {'⚠️' if at_risk else ''}

BY PRIORITY
{'-' * 70}
High Priority:             {len([i for i in active if i.priority == Priority.HIGH])}
Medium Priority:           {len([i for i in active if i.priority == Priority.MEDIUM])}
Low Priority:              {len([i for i in active if i.priority == Priority.LOW])}

BY STATUS
{'-' * 70}
Open:                      {len(self.get_by_status(Status.OPEN))}
In Progress:               {len(self.get_by_status(Status.IN_PROGRESS))}
Blocked:                   {len(self.get_by_status(Status.BLOCKED))}
Completed:                 {len(completed)}
Cancelled:                 {len(self.get_by_status(Status.CANCELLED))}
"""

        if overdue:
            report += f"\n{'=' * 70}\nOVERDUE ITEMS 🔴\n{'=' * 70}\n\n"
            for item in sorted(overdue, key=lambda x: x.days_until_due()):
                days_overdue = abs(item.days_until_due())
                report += f"[{item.item_id}] {item.description}\n"
                report += f"  Owner: {item.owner} | Due: {item.due_date.date()} ({days_overdue} days overdue)\n"
                report += f"  Status: {item.status.value} | Priority: {item.priority.value}\n\n"

        if at_risk and not overdue:  # Don't duplicate overdue items
            at_risk_not_overdue = [i for i in at_risk if not i.is_overdue()]
            if at_risk_not_overdue:
                report += f"\n{'=' * 70}\nAT RISK ITEMS ⚠️\n{'=' * 70}\n\n"
                for item in sorted(at_risk_not_overdue, key=lambda x: x.days_until_due()):
                    days_left = item.days_until_due()
                    report += f"[{item.item_id}] {item.description}\n"
                    report += f"  Owner: {item.owner} | Due: {item.due_date.date()} ({days_left} days left)\n"
                    report += f"  Status: {item.status.value} | Priority: {item.priority.value}\n\n"

        report += f"\n{'=' * 70}\n"
        report += f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"{'=' * 70}\n"

        return report

    def generate_owner_report(self, owner: str) -> str:
        """Generate report for specific owner"""
        items = self.get_by_owner(owner)
        active = [i for i in items if i.status not in [Status.COMPLETED, Status.CANCELLED]]

        report = f"""
{'=' * 70}
Action Items for: {owner}
{'=' * 70}

SUMMARY
{'-' * 70}
Total Active:              {len(active)}
Overdue:                   {len([i for i in items if i.is_overdue()])}
Due This Week:             {len([i for i in active if 0 <= i.days_until_due() <= 7])}

YOUR ACTION ITEMS
{'-' * 70}
"""

        # Group by priority
        for priority in [Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
            priority_items = [i for i in active if i.priority == priority]
            if priority_items:
                report += f"\n{priority.value} Priority:\n"
                for item in sorted(priority_items, key=lambda x: x.due_date):
                    days_left = item.days_until_due()
                    status_indicator = "🔴" if days_left < 0 else "⚠️" if days_left < 7 else "🟢"
                    report += f"\n{status_indicator} [{item.item_id}] {item.description}\n"
                    report += f"   Due: {item.due_date.date()} "
                    if days_left < 0:
                        report += f"({abs(days_left)} days OVERDUE)\n"
                    else:
                        report += f"({days_left} days left)\n"
                    report += f"   Status: {item.status.value}\n"
                    if item.dependencies:
                        report += f"   Dependencies: {item.dependencies}\n"

        report += f"\n{'=' * 70}\n"
        return report

    def export_to_markdown(self, output_file: str):
        """Export all active items to markdown file"""
        active = self.get_active()

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Action Item Tracker\n\n")
            f.write(f"**Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## Summary\n\n")
            f.write(f"- **Total Active**: {len(active)}\n")
            f.write(f"- **Overdue**: {len(self.get_overdue())}\n")
            f.write(f"- **At Risk**: {len(self.get_at_risk())}\n\n")

            f.write("## Active Action Items\n\n")
            f.write("| ID | Owner | Description | Due Date | Priority | Status | Days Left |\n")
            f.write("|----|-------|-------------|----------|----------|--------|-----------|\n")

            for item in sorted(active, key=lambda x: (x.due_date, x.priority.value)):
                days_left = item.days_until_due()
                days_str = f"{days_left}" if days_left >= 0 else f"**OVERDUE {abs(days_left)}**"

                status_emoji = {
                    Status.OPEN: "🟢",
                    Status.IN_PROGRESS: "🟡",
                    Status.BLOCKED: "🔴"
                }.get(item.status, "")

                f.write(f"| {item.item_id} | {item.owner} | {item.description} | "
                       f"{item.due_date.date()} | {item.priority.value} | "
                       f"{status_emoji} {item.status.value} | {days_str} |\n")

            f.write("\n---\n\n")

            # By owner
            owners = set(item.owner for item in active)
            for owner in sorted(owners):
                owner_items = [i for i in active if i.owner == owner]
                f.write(f"### {owner} ({len(owner_items)} items)\n\n")

                for item in sorted(owner_items, key=lambda x: x.due_date):
                    f.write(f"**{item.item_id}**: {item.description}\n")
                    f.write(f"- Due: {item.due_date.date()} ({item.days_until_due()} days)\n")
                    f.write(f"- Priority: {item.priority.value}\n")
                    f.write(f"- Status: {item.status.value}\n")
                    if item.dependencies:
                        f.write(f"- Dependencies: {item.dependencies}\n")
                    f.write("\n")

        print(f"Markdown report exported to: {output_file}")


def main():
    """Command-line interface"""

    if len(sys.argv) < 2:
        print("IEEE Action Item Tracker")
        print()
        print("Usage:")
        print("  action_item_tracker.py add <owner> <description> <due_date> [priority]")
        print("  action_item_tracker.py update <item_id> <status> [notes]")
        print("  action_item_tracker.py report [owner]")
        print("  action_item_tracker.py list [status|owner|overdue|at-risk]")
        print("  action_item_tracker.py export <output.md>")
        print()
        print("Examples:")
        print("  action_item_tracker.py add 'John' 'Draft Section 5' '2024-03-15' high")
        print("  action_item_tracker.py update AI-001 'In Progress' 'Started work'")
        print("  action_item_tracker.py report")
        print("  action_item_tracker.py report 'John'")
        print("  action_item_tracker.py list overdue")
        print("  action_item_tracker.py export action_items.md")
        return

    tracker = ActionItemTracker()
    tracker.load()

    command = sys.argv[1].lower()

    if command == 'add':
        if len(sys.argv) < 5:
            print("Error: add requires owner, description, and due_date")
            return

        owner = sys.argv[2]
        description = sys.argv[3]
        due_date = sys.argv[4]
        priority = Priority(sys.argv[5].capitalize()) if len(sys.argv) > 5 else Priority.MEDIUM

        item = tracker.add_item(owner, description, due_date, priority)
        print(f"✓ Created {item.item_id}: {description}")
        print(f"  Owner: {owner} | Due: {due_date} | Priority: {priority.value}")

    elif command == 'update':
        if len(sys.argv) < 4:
            print("Error: update requires item_id and status")
            return

        item_id = sys.argv[2]
        status = Status(sys.argv[3].replace('_', ' ').title().replace(' ', '_').upper())
        notes = sys.argv[4] if len(sys.argv) > 4 else None

        if tracker.update_status(item_id, status, notes):
            print(f"✓ Updated {item_id} to {status.value}")
            if notes:
                print(f"  Notes: {notes}")
        else:
            print(f"Error: Item {item_id} not found")

    elif command == 'report':
        if len(sys.argv) > 2:
            # Owner report
            owner = sys.argv[2]
            print(tracker.generate_owner_report(owner))
        else:
            # Summary report
            print(tracker.generate_summary_report())

    elif command == 'list':
        filter_type = sys.argv[2].lower() if len(sys.argv) > 2 else 'active'

        if filter_type == 'overdue':
            items = tracker.get_overdue()
            print(f"\nOverdue Items ({len(items)}):")
        elif filter_type == 'at-risk':
            items = tracker.get_at_risk()
            print(f"\nAt Risk Items ({len(items)}):")
        elif filter_type == 'active':
            items = tracker.get_active()
            print(f"\nActive Items ({len(items)}):")
        elif filter_type in ['open', 'in_progress', 'blocked', 'completed', 'cancelled']:
            status = Status(filter_type.replace('_', ' ').title().replace(' ', '_').upper())
            items = tracker.get_by_status(status)
            print(f"\n{status.value} Items ({len(items)}):")
        else:
            # Assume it's an owner name
            items = tracker.get_by_owner(filter_type)
            print(f"\nItems for {filter_type} ({len(items)}):")

        print("-" * 70)
        for item in sorted(items, key=lambda x: x.due_date):
            days_left = item.days_until_due()
            status_str = "OVERDUE" if days_left < 0 else f"{days_left} days"
            print(f"[{item.item_id}] {item.description}")
            print(f"  {item.owner} | Due: {item.due_date.date()} ({status_str}) | {item.status.value}")

    elif command == 'export':
        if len(sys.argv) < 3:
            print("Error: export requires output filename")
            return

        output_file = sys.argv[2]
        tracker.export_to_markdown(output_file)

    else:
        print(f"Unknown command: {command}")


if __name__ == '__main__':
    main()
