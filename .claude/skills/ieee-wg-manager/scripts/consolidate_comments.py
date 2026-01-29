#!/usr/bin/env python3
"""
IEEE Comment Consolidation Tool

Consolidates review comments from multiple sources, groups similar comments,
and helps generate comment disposition documents.
"""

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class Comment:
    """Represents a single review comment"""

    def __init__(
        self,
        comment_id: str,
        commenter: str,
        affiliation: str,
        section: str,
        page: Optional[str],
        line: Optional[str],
        comment_type: str,
        issue: str,
        proposed_resolution: str,
        category: Optional[str] = None
    ):
        self.comment_id = comment_id
        self.commenter = commenter
        self.affiliation = affiliation
        self.section = section
        self.page = page
        self.line = line
        self.comment_type = comment_type  # Technical, Editorial, General
        self.issue = issue
        self.proposed_resolution = proposed_resolution
        self.category = category  # For grouping similar comments

        # Disposition fields (filled in later)
        self.disposition = None  # Accept, Reject, Accept in Principle
        self.wg_response = None
        self.changes_made = None
        self.resolved_by = None
        self.resolved_date = None


class CommentConsolidator:
    """Consolidate and analyze review comments"""

    def __init__(self):
        self.comments: List[Comment] = []
        self.categories = defaultdict(list)

    def load_from_csv(self, filepath: str) -> int:
        """
        Load comments from CSV file.

        Expected columns:
        - comment_id, commenter, affiliation, section, page, line,
          comment_type, issue, proposed_resolution
        """
        count = 0
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                comment = Comment(
                    comment_id=row.get('comment_id', f'C{count+1:03d}'),
                    commenter=row['commenter'],
                    affiliation=row.get('affiliation', ''),
                    section=row['section'],
                    page=row.get('page'),
                    line=row.get('line'),
                    comment_type=row.get('comment_type', 'General'),
                    issue=row['issue'],
                    proposed_resolution=row.get('proposed_resolution', ''),
                    category=row.get('category')
                )
                self.comments.append(comment)
                count += 1

        return count

    def add_comment(self, comment: Comment):
        """Add a single comment"""
        self.comments.append(comment)

    def categorize_by_section(self) -> Dict[str, List[Comment]]:
        """Group comments by section"""
        by_section = defaultdict(list)
        for comment in self.comments:
            by_section[comment.section].append(comment)
        return dict(by_section)

    def categorize_by_type(self) -> Dict[str, List[Comment]]:
        """Group comments by type (Technical, Editorial, General)"""
        by_type = defaultdict(list)
        for comment in self.comments:
            by_type[comment.comment_type].append(comment)
        return dict(by_type)

    def categorize_by_commenter(self) -> Dict[str, List[Comment]]:
        """Group comments by commenter"""
        by_commenter = defaultdict(list)
        for comment in self.comments:
            by_commenter[comment.commenter].append(comment)
        return dict(by_commenter)

    def find_similar_comments(self, threshold: float = 0.6) -> List[List[Comment]]:
        """
        Group similar comments together using simple keyword matching.

        In production, could use NLP/embeddings for better similarity detection.
        """
        groups = []
        ungrouped = self.comments.copy()

        while ungrouped:
            current = ungrouped.pop(0)
            group = [current]

            # Find similar comments
            remaining = []
            for comment in ungrouped:
                if self._are_similar(current, comment, threshold):
                    group.append(comment)
                else:
                    remaining.append(comment)

            ungrouped = remaining
            groups.append(group)

        return groups

    def _are_similar(self, c1: Comment, c2: Comment, threshold: float) -> bool:
        """Simple similarity check based on keywords"""
        # Same section is a strong signal
        if c1.section == c2.section:
            # Check for keyword overlap in issues
            keywords1 = set(c1.issue.lower().split())
            keywords2 = set(c2.issue.lower().split())

            # Remove common words
            stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'to', 'for'}
            keywords1 -= stop_words
            keywords2 -= stop_words

            if not keywords1 or not keywords2:
                return False

            overlap = len(keywords1 & keywords2)
            union = len(keywords1 | keywords2)

            similarity = overlap / union if union > 0 else 0
            return similarity >= threshold

        return False

    def generate_summary_stats(self) -> Dict:
        """Generate summary statistics"""
        by_type = self.categorize_by_type()
        by_section = self.categorize_by_section()
        by_commenter = self.categorize_by_commenter()

        return {
            'total_comments': len(self.comments),
            'by_type': {k: len(v) for k, v in by_type.items()},
            'by_section': {k: len(v) for k, v in by_section.items()},
            'unique_commenters': len(by_commenter),
            'commenters': list(by_commenter.keys())
        }

    def export_disposition_template(self, output_file: str):
        """
        Export a comment disposition spreadsheet template.

        Working group can fill in disposition, response, changes made.
        """
        fieldnames = [
            'comment_id', 'commenter', 'affiliation', 'section', 'page', 'line',
            'comment_type', 'issue', 'proposed_resolution',
            'disposition', 'wg_response', 'changes_made', 'resolved_by', 'resolved_date'
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for comment in self.comments:
                writer.writerow({
                    'comment_id': comment.comment_id,
                    'commenter': comment.commenter,
                    'affiliation': comment.affiliation,
                    'section': comment.section,
                    'page': comment.page or '',
                    'line': comment.line or '',
                    'comment_type': comment.comment_type,
                    'issue': comment.issue,
                    'proposed_resolution': comment.proposed_resolution,
                    'disposition': '',
                    'wg_response': '',
                    'changes_made': '',
                    'resolved_by': '',
                    'resolved_date': ''
                })

        print(f"Disposition template exported to: {output_file}")

    def export_grouped_report(self, output_file: str):
        """Export comments grouped by section with similar comments together"""
        by_section = self.categorize_by_section()

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Comment Consolidation Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            stats = self.generate_summary_stats()
            f.write("## Summary Statistics\n\n")
            f.write(f"- **Total Comments**: {stats['total_comments']}\n")
            f.write(f"- **Unique Commenters**: {stats['unique_commenters']}\n\n")

            f.write("### By Type\n\n")
            for comment_type, count in stats['by_type'].items():
                f.write(f"- **{comment_type}**: {count}\n")
            f.write("\n")

            f.write("### By Section\n\n")
            for section, count in sorted(stats['by_section'].items()):
                f.write(f"- **{section}**: {count}\n")
            f.write("\n")

            f.write("---\n\n")

            # Group by section
            for section in sorted(by_section.keys()):
                comments = by_section[section]
                f.write(f"## Section: {section}\n\n")
                f.write(f"**Comment Count**: {len(comments)}\n\n")

                for i, comment in enumerate(comments, 1):
                    f.write(f"### Comment {comment.comment_id}\n\n")
                    f.write(f"- **Commenter**: {comment.commenter} ({comment.affiliation})\n")
                    f.write(f"- **Type**: {comment.comment_type}\n")

                    if comment.page:
                        f.write(f"- **Page**: {comment.page}\n")
                    if comment.line:
                        f.write(f"- **Line**: {comment.line}\n")

                    f.write(f"\n**Issue**:\n{comment.issue}\n\n")

                    if comment.proposed_resolution:
                        f.write(f"**Proposed Resolution**:\n{comment.proposed_resolution}\n\n")

                    f.write("**Disposition**: _[To be filled in]_\n\n")
                    f.write("**WG Response**: _[To be filled in]_\n\n")
                    f.write("---\n\n")

        print(f"Grouped report exported to: {output_file}")

    def export_similar_groups(self, output_file: str):
        """Export report showing similar comments grouped together"""
        groups = self.find_similar_comments()

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Similar Comments Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Comment Groups**: {len(groups)}\n\n")
            f.write("Comments addressing similar issues are grouped together for efficient resolution.\n\n")
            f.write("---\n\n")

            for i, group in enumerate(groups, 1):
                if len(group) > 1:
                    f.write(f"## Group {i}: {len(group)} Similar Comments\n\n")
                    f.write(f"**Section**: {group[0].section}\n\n")

                    for comment in group:
                        f.write(f"### {comment.comment_id} - {comment.commenter}\n\n")
                        f.write(f"**Issue**: {comment.issue}\n\n")

                    f.write("**Recommended Approach**: _[Address all similar comments with one resolution]_\n\n")
                    f.write("---\n\n")
                else:
                    # Unique comment
                    comment = group[0]
                    f.write(f"## Unique Comment: {comment.comment_id}\n\n")
                    f.write(f"**Commenter**: {comment.commenter}\n")
                    f.write(f"**Section**: {comment.section}\n")
                    f.write(f"**Issue**: {comment.issue}\n\n")
                    f.write("---\n\n")

        print(f"Similar groups report exported to: {output_file}")


def main():
    """Command-line interface for comment consolidation"""

    if len(sys.argv) < 2:
        print("IEEE Comment Consolidation Tool")
        print()
        print("Usage:")
        print("  consolidate_comments.py <input.csv> [--output-dir <dir>]")
        print()
        print("Input CSV should have columns:")
        print("  commenter, affiliation, section, page, line, comment_type,")
        print("  issue, proposed_resolution")
        print()
        print("Generates:")
        print("  - disposition_template.csv (for WG to fill in)")
        print("  - grouped_report.md (comments grouped by section)")
        print("  - similar_comments.md (similar comments grouped)")
        print()
        return

    input_file = sys.argv[1]

    # Parse output directory
    output_dir = "."
    if "--output-dir" in sys.argv:
        idx = sys.argv.index("--output-dir")
        if idx + 1 < len(sys.argv):
            output_dir = sys.argv[idx + 1]

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Load and process comments
    print(f"Loading comments from: {input_file}")
    consolidator = CommentConsolidator()

    try:
        count = consolidator.load_from_csv(input_file)
        print(f"✓ Loaded {count} comments")
    except Exception as e:
        print(f"Error loading comments: {e}")
        return

    # Generate statistics
    stats = consolidator.generate_summary_stats()
    print()
    print("Summary:")
    print(f"  Total Comments: {stats['total_comments']}")
    print(f"  Unique Commenters: {stats['unique_commenters']}")
    print(f"  Technical: {stats['by_type'].get('Technical', 0)}")
    print(f"  Editorial: {stats['by_type'].get('Editorial', 0)}")
    print(f"  General: {stats['by_type'].get('General', 0)}")
    print()

    # Export reports
    disposition_file = output_dir / "disposition_template.csv"
    grouped_file = output_dir / "grouped_report.md"
    similar_file = output_dir / "similar_comments.md"

    print("Generating reports...")
    consolidator.export_disposition_template(str(disposition_file))
    consolidator.export_grouped_report(str(grouped_file))
    consolidator.export_similar_groups(str(similar_file))

    print()
    print("✓ All reports generated successfully")
    print()
    print("Next steps:")
    print(f"  1. Review {grouped_file} for overview")
    print(f"  2. Check {similar_file} for related comments")
    print(f"  3. Fill in {disposition_file} with dispositions")


if __name__ == '__main__':
    main()
