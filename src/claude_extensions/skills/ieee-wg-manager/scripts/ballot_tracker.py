#!/usr/bin/env python3
"""
IEEE Ballot Tracker

Tracks ballot responses, calculates approval rates, and generates reports.
"""

import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple


class BallotTracker:
    """Track IEEE ballot responses and calculate results"""

    def __init__(self, ballot_file: str = "ballot_responses.csv"):
        self.ballot_file = Path(ballot_file)
        self.responses = []

    def load_responses(self) -> List[Dict]:
        """Load ballot responses from CSV file"""
        if not self.ballot_file.exists():
            return []

        with open(self.ballot_file, 'r') as f:
            reader = csv.DictReader(f)
            self.responses = list(reader)

        return self.responses

    def add_response(
        self,
        name: str,
        affiliation: str,
        vote: str,
        has_comments: bool = False,
        comment_count: int = 0
    ) -> None:
        """Add a new ballot response"""
        response = {
            'name': name,
            'affiliation': affiliation,
            'vote': vote.upper(),
            'has_comments': str(has_comments),
            'comment_count': str(comment_count),
            'timestamp': datetime.now().isoformat()
        }

        self.responses.append(response)
        self.save_responses()

    def save_responses(self) -> None:
        """Save ballot responses to CSV file"""
        if not self.responses:
            return

        fieldnames = ['name', 'affiliation', 'vote', 'has_comments', 'comment_count', 'timestamp']

        with open(self.ballot_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.responses)

    def calculate_results(self) -> Tuple[Dict, Dict]:
        """Calculate ballot results"""
        vote_counts = {
            'APPROVE': 0,
            'DISAPPROVE': 0,
            'ABSTAIN': 0,
            'TOTAL': 0
        }

        disapprove_with_comments = 0
        disapprove_without_comments = 0

        for response in self.responses:
            vote = response['vote'].upper()
            vote_counts[vote] = vote_counts.get(vote, 0) + 1
            vote_counts['TOTAL'] += 1

            if vote == 'DISAPPROVE':
                if response['has_comments'].lower() == 'true':
                    disapprove_with_comments += 1
                else:
                    disapprove_without_comments += 1

        # Calculate approval percentage (excluding abstentions)
        approve_disapprove_total = vote_counts['APPROVE'] + vote_counts['DISAPPROVE']

        if approve_disapprove_total > 0:
            approval_pct = (vote_counts['APPROVE'] / approve_disapprove_total) * 100
        else:
            approval_pct = 0.0

        # Calculate return rate
        # Note: You need to provide total ballot pool size
        return_rate = 0.0  # Would need total invitations count

        stats = {
            'votes': vote_counts,
            'approval_percentage': approval_pct,
            'return_rate': return_rate,
            'disapprove_with_comments': disapprove_with_comments,
            'disapprove_without_comments': disapprove_without_comments,
            'passed': approval_pct >= 75.0,
            'sponsor_threshold_met': approval_pct >= 75.0
        }

        return stats, vote_counts

    def generate_report(self, ballot_name: str = "IEEE Ballot") -> str:
        """Generate a ballot results report"""
        stats, votes = self.calculate_results()

        report = f"""
{'=' * 70}
{ballot_name} - Results Report
{'=' * 70}

BALLOT STATISTICS
{'-' * 70}
Total Responses:           {votes['TOTAL']}
Approve:                   {votes['APPROVE']} ({votes['APPROVE']/votes['TOTAL']*100 if votes['TOTAL'] > 0 else 0:.1f}%)
Disapprove:                {votes['DISAPPROVE']} ({votes['DISAPPROVE']/votes['TOTAL']*100 if votes['TOTAL'] > 0 else 0:.1f}%)
Abstain:                   {votes['ABSTAIN']} ({votes['ABSTAIN']/votes['TOTAL']*100 if votes['TOTAL'] > 0 else 0:.1f}%)

APPROVAL CALCULATION
{'-' * 70}
Approval Percentage:       {stats['approval_percentage']:.2f}%
(Calculated as: Approve / (Approve + Disapprove))

Sponsor Threshold (75%):   {'✓ MET' if stats['sponsor_threshold_met'] else '✗ NOT MET'}
Status:                    {'PASSED' if stats['passed'] else 'FAILED'}

DISAPPROVE ANALYSIS
{'-' * 70}
With Comments:             {stats['disapprove_with_comments']}
Without Comments:          {stats['disapprove_without_comments']}

{'⚠ WARNING: Disapprove votes without comments will not be counted.' if stats['disapprove_without_comments'] > 0 else ''}

NEXT STEPS
{'-' * 70}
"""

        if stats['passed']:
            report += """
✓ Ballot PASSED
  - Review all Disapprove comments
  - Prepare comment disposition document
  - Determine if recirculation is needed
  - If no recirculation: Proceed to next stage
  - If recirculation needed: Address comments and re-ballot
"""
        else:
            report += f"""
✗ Ballot FAILED (need 75%, got {stats['approval_percentage']:.2f}%)
  - Review ballot pool composition
  - Analyze Disapprove comments for patterns
  - Consider technical improvements to draft
  - Address all substantive comments
  - Consider working group pre-ballot before re-balloting
"""

        report += f"\n{'=' * 70}\n"
        report += f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"{'=' * 70}\n"

        return report

    def list_disapprovals(self) -> List[Dict]:
        """List all disapprove votes with details"""
        return [r for r in self.responses if r['vote'].upper() == 'DISAPPROVE']

    def export_summary(self, output_file: str = "ballot_summary.txt") -> None:
        """Export summary report to file"""
        report = self.generate_report()

        with open(output_file, 'w') as f:
            f.write(report)

        print(f"Summary exported to: {output_file}")


def main():
    """Command-line interface for ballot tracker"""
    if len(sys.argv) < 2:
        print("IEEE Ballot Tracker")
        print()
        print("Usage:")
        print("  ballot_tracker.py add <name> <affiliation> <vote> [has_comments]")
        print("  ballot_tracker.py report [ballot_name]")
        print("  ballot_tracker.py list-disapprovals")
        print()
        print("Votes: APPROVE, DISAPPROVE, ABSTAIN")
        print()
        print("Examples:")
        print("  ballot_tracker.py add 'John Smith' 'Acme Corp' APPROVE")
        print("  ballot_tracker.py add 'Jane Doe' 'Tech Inc' DISAPPROVE true 3")
        print("  ballot_tracker.py report 'IEEE P3394 Draft 2.0'")
        return

    tracker = BallotTracker()
    tracker.load_responses()

    command = sys.argv[1].lower()

    if command == 'add':
        if len(sys.argv) < 5:
            print("Error: add requires name, affiliation, and vote")
            return

        name = sys.argv[2]
        affiliation = sys.argv[3]
        vote = sys.argv[4]
        has_comments = sys.argv[5].lower() == 'true' if len(sys.argv) > 5 else False
        comment_count = int(sys.argv[6]) if len(sys.argv) > 6 else 0

        tracker.add_response(name, affiliation, vote, has_comments, comment_count)
        print(f"✓ Added ballot response from {name} ({vote})")

    elif command == 'report':
        ballot_name = sys.argv[2] if len(sys.argv) > 2 else "IEEE Ballot"
        print(tracker.generate_report(ballot_name))

    elif command == 'list-disapprovals':
        disapprovals = tracker.list_disapprovals()
        if disapprovals:
            print(f"\nDisapprove Votes ({len(disapprovals)}):")
            print("-" * 70)
            for d in disapprovals:
                comment_status = "✓" if d['has_comments'].lower() == 'true' else "✗ NO COMMENTS"
                print(f"  {d['name']} ({d['affiliation']}) - {comment_status}")
                if d['comment_count'] and d['comment_count'] != '0':
                    print(f"    Comments: {d['comment_count']}")
        else:
            print("\nNo disapprove votes recorded.")

    else:
        print(f"Unknown command: {command}")


if __name__ == '__main__':
    main()
