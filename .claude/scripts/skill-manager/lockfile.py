#!/usr/bin/env python3
"""
SKILLS.lock management for tracking installed skills.
Supports dual-level lockfiles: global (~/.claude/) and project-level (.claude/).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Default lockfile locations
GLOBAL_LOCKFILE = Path.home() / ".claude" / "SKILLS.lock"
PROJECT_LOCKFILE = Path(".claude") / "SKILLS.lock"

LOCKFILE_VERSION = 1


def get_lockfile_path(scope: str = "global", project_path: Optional[Path] = None) -> Path:
    """Get the appropriate lockfile path based on scope."""
    if scope == "global":
        return GLOBAL_LOCKFILE
    elif scope == "project":
        if project_path:
            return project_path / ".claude" / "SKILLS.lock"
        return PROJECT_LOCKFILE
    else:
        raise ValueError(f"Invalid scope: {scope}")


def create_empty_lockfile() -> dict:
    """Create an empty lockfile structure."""
    return {
        "version": LOCKFILE_VERSION,
        "generated": datetime.now(timezone.utc).isoformat(),
        "skills": {}
    }


def read_lockfile(path: Path) -> dict:
    """Read and parse a lockfile."""
    if not path.exists():
        return create_empty_lockfile()

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate version
        if data.get("version", 0) > LOCKFILE_VERSION:
            print(f"Warning: Lockfile version {data['version']} is newer than supported {LOCKFILE_VERSION}",
                  file=sys.stderr)

        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid lockfile JSON: {e}")


def write_lockfile(path: Path, data: dict) -> None:
    """Write lockfile to disk."""
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Update generation timestamp
    data["generated"] = datetime.now(timezone.utc).isoformat()

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def add_skill(
    lockfile_path: Path,
    skill_name: str,
    version: str,
    source: dict,
    installed_path: str,
    content_hash: str,
    dependencies: Optional[dict] = None
) -> dict:
    """
    Add or update a skill entry in the lockfile.

    Args:
        lockfile_path: Path to lockfile
        skill_name: Name of the skill
        version: Skill version
        source: Source information dict (type, url, commit, etc.)
        installed_path: Local installation path
        content_hash: SHA256 hash of skill content
        dependencies: Optional dependency information

    Returns:
        The skill entry that was added
    """
    data = read_lockfile(lockfile_path)

    now = datetime.now(timezone.utc).isoformat()

    skill_entry = {
        "version": version,
        "resolved": source,
        "installed": {
            "path": installed_path,
            "date": now,
            "contentHash": content_hash
        },
        "local": {
            "modified": False,
            "contentHash": content_hash,
            "modifiedFiles": []
        },
        "upstream": {
            "lastChecked": now,
            "latestCommit": source.get("commit"),
            "hasUpdates": False
        }
    }

    if dependencies:
        skill_entry["dependencies"] = dependencies

    data["skills"][skill_name] = skill_entry
    write_lockfile(lockfile_path, data)

    return skill_entry


def update_skill(
    lockfile_path: Path,
    skill_name: str,
    updates: dict
) -> Optional[dict]:
    """
    Update specific fields of a skill entry.

    Args:
        lockfile_path: Path to lockfile
        skill_name: Name of the skill
        updates: Dictionary of fields to update (supports nested keys with dot notation)

    Returns:
        Updated skill entry, or None if skill not found
    """
    data = read_lockfile(lockfile_path)

    if skill_name not in data["skills"]:
        return None

    skill = data["skills"][skill_name]

    for key, value in updates.items():
        if '.' in key:
            parts = key.split('.')
            current = skill
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        else:
            skill[key] = value

    write_lockfile(lockfile_path, data)
    return skill


def remove_skill(lockfile_path: Path, skill_name: str) -> bool:
    """Remove a skill from the lockfile."""
    data = read_lockfile(lockfile_path)

    if skill_name not in data["skills"]:
        return False

    del data["skills"][skill_name]
    write_lockfile(lockfile_path, data)
    return True


def get_skill(lockfile_path: Path, skill_name: str) -> Optional[dict]:
    """Get a skill entry from the lockfile."""
    data = read_lockfile(lockfile_path)
    return data["skills"].get(skill_name)


def list_skills(lockfile_path: Path) -> dict:
    """List all skills in the lockfile."""
    data = read_lockfile(lockfile_path)
    return data["skills"]


def merge_lockfiles(global_path: Path, project_path: Path) -> dict:
    """
    Merge global and project lockfiles.
    Project entries override global for same skill name.
    """
    global_data = read_lockfile(global_path)
    project_data = read_lockfile(project_path)

    merged = {
        "version": LOCKFILE_VERSION,
        "generated": datetime.now(timezone.utc).isoformat(),
        "skills": {}
    }

    # Add global skills
    for name, entry in global_data.get("skills", {}).items():
        merged["skills"][name] = {**entry, "_scope": "global"}

    # Override/add project skills
    for name, entry in project_data.get("skills", {}).items():
        merged["skills"][name] = {**entry, "_scope": "project"}

    return merged


def mark_modified(
    lockfile_path: Path,
    skill_name: str,
    new_hash: str,
    modified_files: list[str]
) -> Optional[dict]:
    """Mark a skill as locally modified."""
    return update_skill(lockfile_path, skill_name, {
        "local.modified": True,
        "local.contentHash": new_hash,
        "local.modifiedFiles": modified_files,
        "local.modifiedDate": datetime.now(timezone.utc).isoformat()
    })


def mark_synced(
    lockfile_path: Path,
    skill_name: str,
    new_hash: str,
    upstream_commit: Optional[str] = None
) -> Optional[dict]:
    """Mark a skill as synced with upstream."""
    updates = {
        "local.modified": False,
        "local.contentHash": new_hash,
        "local.modifiedFiles": [],
        "installed.contentHash": new_hash,
        "upstream.lastChecked": datetime.now(timezone.utc).isoformat(),
        "upstream.hasUpdates": False
    }

    if upstream_commit:
        updates["resolved.commit"] = upstream_commit
        updates["upstream.latestCommit"] = upstream_commit

    return update_skill(lockfile_path, skill_name, updates)


def main():
    parser = argparse.ArgumentParser(description='Manage SKILLS.lock file')
    parser.add_argument('--scope', choices=['global', 'project'], default='global',
                       help='Lockfile scope (default: global)')
    parser.add_argument('--path', type=Path, help='Custom lockfile path')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # List command
    list_cmd = subparsers.add_parser('list', help='List all tracked skills')
    list_cmd.add_argument('--json', action='store_true', help='Output as JSON')
    list_cmd.add_argument('--merged', action='store_true',
                         help='Show merged global + project lockfile')

    # Get command
    get_cmd = subparsers.add_parser('get', help='Get a skill entry')
    get_cmd.add_argument('skill_name', help='Name of the skill')
    get_cmd.add_argument('--json', action='store_true', help='Output as JSON')

    # Add command
    add_cmd = subparsers.add_parser('add', help='Add a skill to lockfile')
    add_cmd.add_argument('skill_name', help='Name of the skill')
    add_cmd.add_argument('--version', required=True, help='Skill version')
    add_cmd.add_argument('--source-type', required=True,
                        choices=['github', 'skillsmp', 'anthropic', 'local', 'composed'])
    add_cmd.add_argument('--source-url', help='Source URL')
    add_cmd.add_argument('--source-commit', help='Git commit SHA')
    add_cmd.add_argument('--installed-path', required=True, help='Local installation path')
    add_cmd.add_argument('--content-hash', required=True, help='Content hash')

    # Update command
    update_cmd = subparsers.add_parser('update', help='Update a skill entry')
    update_cmd.add_argument('skill_name', help='Name of the skill')
    update_cmd.add_argument('--set', nargs=2, action='append', metavar=('KEY', 'VALUE'),
                           help='Set field value')
    update_cmd.add_argument('--json-set', nargs=2, action='append', metavar=('KEY', 'JSON_VALUE'),
                           help='Set field with JSON value')

    # Remove command
    remove_cmd = subparsers.add_parser('remove', help='Remove a skill from lockfile')
    remove_cmd.add_argument('skill_name', help='Name of the skill')

    # Mark-modified command
    mark_cmd = subparsers.add_parser('mark-modified', help='Mark skill as locally modified')
    mark_cmd.add_argument('skill_name', help='Name of the skill')
    mark_cmd.add_argument('--hash', required=True, help='New content hash')
    mark_cmd.add_argument('--files', nargs='*', default=[], help='Modified files')

    # Mark-synced command
    sync_cmd = subparsers.add_parser('mark-synced', help='Mark skill as synced')
    sync_cmd.add_argument('skill_name', help='Name of the skill')
    sync_cmd.add_argument('--hash', required=True, help='New content hash')
    sync_cmd.add_argument('--commit', help='Upstream commit SHA')

    args = parser.parse_args()

    # Determine lockfile path
    if args.path:
        lockfile_path = args.path
    else:
        lockfile_path = get_lockfile_path(args.scope)

    if args.command == 'list':
        if args.merged:
            skills = merge_lockfiles(GLOBAL_LOCKFILE, PROJECT_LOCKFILE)["skills"]
        else:
            skills = list_skills(lockfile_path)

        if args.json:
            print(json.dumps(skills, indent=2))
        else:
            if not skills:
                print("No skills tracked")
            else:
                print(f"{'Skill':<30} {'Version':<10} {'Source':<15} {'Modified':<10}")
                print("-" * 70)
                for name, entry in skills.items():
                    source_type = entry.get("resolved", {}).get("source", "unknown")
                    modified = "Yes" if entry.get("local", {}).get("modified") else "No"
                    scope = entry.get("_scope", "")
                    scope_indicator = f" [{scope}]" if scope else ""
                    print(f"{name:<30} {entry.get('version', '?'):<10} {source_type:<15} {modified:<10}{scope_indicator}")

    elif args.command == 'get':
        skill = get_skill(lockfile_path, args.skill_name)
        if skill:
            if args.json:
                print(json.dumps(skill, indent=2))
            else:
                print(f"Name: {args.skill_name}")
                print(f"Version: {skill.get('version', 'unknown')}")
                print(f"Source: {skill.get('resolved', {}).get('source', 'unknown')}")
                print(f"Installed: {skill.get('installed', {}).get('path', 'unknown')}")
                print(f"Modified: {skill.get('local', {}).get('modified', False)}")
        else:
            print(f"Skill '{args.skill_name}' not found", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'add':
        source = {
            "source": args.source_type,
            "url": args.source_url,
            "commit": args.source_commit
        }
        entry = add_skill(
            lockfile_path,
            args.skill_name,
            args.version,
            source,
            args.installed_path,
            args.content_hash
        )
        print(f"Added {args.skill_name} to lockfile")
        print(json.dumps(entry, indent=2))

    elif args.command == 'update':
        updates = {}
        if args.set:
            for key, value in args.set:
                updates[key] = value
        if args.json_set:
            for key, json_value in args.json_set:
                updates[key] = json.loads(json_value)

        if updates:
            result = update_skill(lockfile_path, args.skill_name, updates)
            if result:
                print(f"Updated {args.skill_name}")
                print(json.dumps(result, indent=2))
            else:
                print(f"Skill '{args.skill_name}' not found", file=sys.stderr)
                sys.exit(1)
        else:
            print("No updates specified", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'remove':
        if remove_skill(lockfile_path, args.skill_name):
            print(f"Removed {args.skill_name} from lockfile")
        else:
            print(f"Skill '{args.skill_name}' not found", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'mark-modified':
        result = mark_modified(lockfile_path, args.skill_name, args.hash, args.files)
        if result:
            print(f"Marked {args.skill_name} as modified")
        else:
            print(f"Skill '{args.skill_name}' not found", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'mark-synced':
        result = mark_synced(lockfile_path, args.skill_name, args.hash, args.commit)
        if result:
            print(f"Marked {args.skill_name} as synced")
        else:
            print(f"Skill '{args.skill_name}' not found", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
