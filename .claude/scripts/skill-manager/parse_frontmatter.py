#!/usr/bin/env python3
"""
Parse and manipulate YAML frontmatter in SKILL.md files.
Supports the extended frontmatter schema for skill-manager.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("Error: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


FRONTMATTER_PATTERN = re.compile(r'^---\n(.*?)\n---\n?', re.DOTALL)


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from skill content.

    Returns:
        Tuple of (frontmatter_dict, body_content)
    """
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content

    frontmatter_yaml = match.group(1)
    body = content[match.end():]

    try:
        frontmatter = yaml.safe_load(frontmatter_yaml) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML frontmatter: {e}")

    return frontmatter, body


def serialize_frontmatter(frontmatter: dict[str, Any], body: str) -> str:
    """
    Serialize frontmatter dict and body back to SKILL.md content.
    """
    yaml_content = yaml.dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120
    )
    return f"---\n{yaml_content}---\n{body}"


def read_skill(skill_path: Path) -> tuple[dict[str, Any], str]:
    """
    Read a skill's SKILL.md and parse its frontmatter.

    Args:
        skill_path: Path to skill directory or SKILL.md file

    Returns:
        Tuple of (frontmatter_dict, body_content)
    """
    if skill_path.is_dir():
        skill_file = skill_path / "SKILL.md"
    else:
        skill_file = skill_path

    if not skill_file.exists():
        raise FileNotFoundError(f"SKILL.md not found at {skill_file}")

    content = skill_file.read_text(encoding='utf-8')
    return parse_frontmatter(content)


def write_skill(skill_path: Path, frontmatter: dict[str, Any], body: str) -> None:
    """
    Write frontmatter and body back to SKILL.md.
    """
    if skill_path.is_dir():
        skill_file = skill_path / "SKILL.md"
    else:
        skill_file = skill_path

    content = serialize_frontmatter(frontmatter, body)
    skill_file.write_text(content, encoding='utf-8')


def update_frontmatter(skill_path: Path, updates: dict[str, Any]) -> dict[str, Any]:
    """
    Update specific fields in a skill's frontmatter.

    Args:
        skill_path: Path to skill directory or SKILL.md file
        updates: Dictionary of fields to update (supports nested keys with dot notation)

    Returns:
        Updated frontmatter dict
    """
    frontmatter, body = read_skill(skill_path)

    for key, value in updates.items():
        # Support nested keys like "source.type"
        if '.' in key:
            parts = key.split('.')
            current = frontmatter
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        else:
            frontmatter[key] = value

    write_skill(skill_path, frontmatter, body)
    return frontmatter


def validate_required_fields(frontmatter: dict[str, Any]) -> list[str]:
    """
    Validate that required fields are present.

    Returns:
        List of missing required fields
    """
    required = ['name', 'description']
    missing = [field for field in required if field not in frontmatter or not frontmatter[field]]
    return missing


def get_version(frontmatter: dict[str, Any]) -> str:
    """Get version from frontmatter, defaulting to 1.0.0 if not present."""
    return frontmatter.get('version', '1.0.0')


def get_source_info(frontmatter: dict[str, Any]) -> dict[str, Any]:
    """Get source tracking information from frontmatter."""
    return frontmatter.get('source', {})


def get_local_info(frontmatter: dict[str, Any]) -> dict[str, Any]:
    """Get local modification information from frontmatter."""
    return frontmatter.get('local', {})


def get_dependencies(frontmatter: dict[str, Any]) -> dict[str, Any]:
    """Get dependency information from frontmatter."""
    return frontmatter.get('dependencies', {})


def main():
    parser = argparse.ArgumentParser(description='Parse and manipulate skill frontmatter')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Parse command
    parse_cmd = subparsers.add_parser('parse', help='Parse frontmatter from SKILL.md')
    parse_cmd.add_argument('path', type=Path, help='Path to skill directory or SKILL.md')
    parse_cmd.add_argument('--json', action='store_true', help='Output as JSON')
    parse_cmd.add_argument('--field', type=str, help='Extract specific field')

    # Update command
    update_cmd = subparsers.add_parser('update', help='Update frontmatter fields')
    update_cmd.add_argument('path', type=Path, help='Path to skill directory or SKILL.md')
    update_cmd.add_argument('--set', nargs=2, action='append', metavar=('KEY', 'VALUE'),
                           help='Set field value (can be used multiple times)')
    update_cmd.add_argument('--json-set', nargs=2, action='append', metavar=('KEY', 'JSON_VALUE'),
                           help='Set field with JSON value')

    # Validate command
    validate_cmd = subparsers.add_parser('validate', help='Validate frontmatter')
    validate_cmd.add_argument('path', type=Path, help='Path to skill directory or SKILL.md')

    args = parser.parse_args()

    if args.command == 'parse':
        try:
            frontmatter, body = read_skill(args.path)

            if args.field:
                # Support nested field access
                value = frontmatter
                for part in args.field.split('.'):
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = None
                        break

                if args.json:
                    print(json.dumps(value))
                else:
                    print(value if value is not None else '')
            else:
                if args.json:
                    print(json.dumps(frontmatter, indent=2))
                else:
                    print(yaml.dump(frontmatter, default_flow_style=False))

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'update':
        try:
            updates = {}

            if args.set:
                for key, value in args.set:
                    updates[key] = value

            if args.json_set:
                for key, json_value in args.json_set:
                    updates[key] = json.loads(json_value)

            if updates:
                updated = update_frontmatter(args.path, updates)
                print(json.dumps(updated, indent=2))
            else:
                print("No updates specified", file=sys.stderr)
                sys.exit(1)

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'validate':
        try:
            frontmatter, _ = read_skill(args.path)
            missing = validate_required_fields(frontmatter)

            if missing:
                print(f"Missing required fields: {', '.join(missing)}", file=sys.stderr)
                sys.exit(1)
            else:
                print("Validation passed")

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
