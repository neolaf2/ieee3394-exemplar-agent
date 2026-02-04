#!/usr/bin/env python3
"""
Search for Claude Code skills across multiple sources.
Usage: python search_skills.py <query> [--local-only] [--verbose]
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


def search_local_skills(query: str, verbose: bool = False) -> list[dict]:
    """Search locally installed skills."""
    skills_dir = Path.home() / ".claude" / "skills"
    results = []

    if not skills_dir.exists():
        return results

    query_lower = query.lower()

    for skill_path in skills_dir.iterdir():
        if not skill_path.is_dir():
            continue

        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            continue

        content = skill_md.read_text()

        # Extract frontmatter
        frontmatter_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not frontmatter_match:
            continue

        frontmatter = frontmatter_match.group(1)

        # Extract name and description
        name_match = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
        desc_match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)

        name = name_match.group(1).strip() if name_match else skill_path.name
        description = desc_match.group(1).strip() if desc_match else ""

        # Check if query matches
        if query_lower in name.lower() or query_lower in description.lower() or query_lower in content.lower():
            results.append({
                "source": "local",
                "name": name,
                "description": description,
                "path": str(skill_path),
                "match_in_content": query_lower in content.lower() and query_lower not in name.lower() and query_lower not in description.lower()
            })

    return results


def format_results(results: list[dict], query: str) -> str:
    """Format search results for display."""
    if not results:
        return f"No skills found matching '{query}'"

    output = [f"\n=== Skills matching '{query}' ===\n"]

    # Group by source
    by_source = {}
    for r in results:
        source = r["source"]
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(r)

    for source, skills in by_source.items():
        output.append(f"\n## {source.upper()}\n")
        for skill in skills:
            output.append(f"  [{skill['name']}]")
            if skill.get("description"):
                # Truncate long descriptions
                desc = skill["description"]
                if len(desc) > 100:
                    desc = desc[:97] + "..."
                output.append(f"    {desc}")
            if skill.get("path"):
                output.append(f"    Path: {skill['path']}")
            if skill.get("url"):
                output.append(f"    URL: {skill['url']}")
            if skill.get("match_in_content"):
                output.append(f"    (match found in skill content)")
            output.append("")

    output.append(f"\nTotal: {len(results)} skill(s) found")
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Search for Claude Code skills")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--local-only", action="store_true", help="Search only local skills")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    all_results = []

    # Always search local skills
    local_results = search_local_skills(args.query, args.verbose)
    all_results.extend(local_results)

    if not args.local_only:
        print("Tip: For online sources, use WebSearch with these patterns:")
        print(f'  - SkillsMP: site:skillsmp.com "{args.query}"')
        print(f'  - GitHub: github claude code skill "{args.query}"')
        print(f'  - Anthropic: site:github.com/anthropics/skills "{args.query}"')
        print("")

    print(format_results(all_results, args.query))


if __name__ == "__main__":
    main()
