#!/usr/bin/env python3
"""
Compute SHA256 checksums for skill content and directories.
Used for tracking local modifications vs upstream changes.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Optional


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of string content."""
    sha256 = hashlib.sha256(content.encode('utf-8'))
    return f"sha256:{sha256.hexdigest()}"


def compute_skill_hash(skill_path: Path, include_git: bool = False) -> dict:
    """
    Compute hashes for a skill directory.

    Returns dict with:
        - skill_md_hash: Hash of SKILL.md file
        - content_hash: Combined hash of all relevant files
        - file_hashes: Individual file hashes
    """
    if skill_path.is_file():
        skill_path = skill_path.parent

    result = {
        'skill_md_hash': None,
        'content_hash': None,
        'file_hashes': {}
    }

    # Files to include in content hash
    relevant_extensions = {'.md', '.py', '.sh', '.json', '.yaml', '.yml', '.txt'}
    ignore_dirs = {'.git', '__pycache__', '.venv', 'node_modules'}

    all_hashes = []

    for file_path in sorted(skill_path.rglob('*')):
        if file_path.is_dir():
            continue

        # Skip ignored directories
        if any(ignored in file_path.parts for ignored in ignore_dirs):
            if not include_git:
                continue

        # Check extension
        if file_path.suffix.lower() not in relevant_extensions:
            continue

        rel_path = file_path.relative_to(skill_path)
        file_hash = compute_file_hash(file_path)

        result['file_hashes'][str(rel_path)] = file_hash
        all_hashes.append(f"{rel_path}:{file_hash}")

        # Special case for SKILL.md
        if file_path.name == 'SKILL.md':
            result['skill_md_hash'] = file_hash

    # Compute combined content hash
    if all_hashes:
        combined = '\n'.join(all_hashes)
        result['content_hash'] = compute_content_hash(combined)

    return result


def compare_hashes(hash1: str, hash2: str) -> bool:
    """Compare two hashes, handling None values."""
    if hash1 is None or hash2 is None:
        return False
    return hash1 == hash2


def detect_modifications(
    current_hash: str,
    base_hash: str,
    upstream_hash: Optional[str] = None
) -> dict:
    """
    Detect modification state by comparing hashes.

    Returns:
        - local_modified: True if current differs from base
        - upstream_modified: True if upstream differs from base
        - needs_merge: True if both local and upstream modified
    """
    local_modified = not compare_hashes(current_hash, base_hash)
    upstream_modified = False
    needs_merge = False

    if upstream_hash:
        upstream_modified = not compare_hashes(upstream_hash, base_hash)
        needs_merge = local_modified and upstream_modified

    return {
        'local_modified': local_modified,
        'upstream_modified': upstream_modified,
        'needs_merge': needs_merge,
        'current_hash': current_hash,
        'base_hash': base_hash,
        'upstream_hash': upstream_hash
    }


def main():
    parser = argparse.ArgumentParser(description='Compute checksums for skills')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Hash command
    hash_cmd = subparsers.add_parser('hash', help='Compute hash of skill or file')
    hash_cmd.add_argument('path', type=Path, help='Path to skill directory or file')
    hash_cmd.add_argument('--json', action='store_true', help='Output as JSON')
    hash_cmd.add_argument('--content-only', action='store_true',
                         help='Output only the content hash')

    # Compare command
    compare_cmd = subparsers.add_parser('compare', help='Compare current vs base hash')
    compare_cmd.add_argument('path', type=Path, help='Path to skill directory')
    compare_cmd.add_argument('--base-hash', required=True, help='Base hash to compare against')
    compare_cmd.add_argument('--upstream-hash', help='Upstream hash (if checking for merge)')
    compare_cmd.add_argument('--json', action='store_true', help='Output as JSON')

    # Verify command
    verify_cmd = subparsers.add_parser('verify', help='Verify a hash matches')
    verify_cmd.add_argument('path', type=Path, help='Path to skill directory or file')
    verify_cmd.add_argument('expected_hash', help='Expected hash value')

    args = parser.parse_args()

    if args.command == 'hash':
        try:
            if args.path.is_file():
                file_hash = compute_file_hash(args.path)
                if args.json:
                    print(json.dumps({'hash': file_hash, 'path': str(args.path)}))
                else:
                    print(file_hash)
            else:
                result = compute_skill_hash(args.path)
                if args.content_only:
                    print(result['content_hash'])
                elif args.json:
                    print(json.dumps(result, indent=2))
                else:
                    print(f"SKILL.md hash: {result['skill_md_hash']}")
                    print(f"Content hash:  {result['content_hash']}")
                    if result['file_hashes']:
                        print(f"\nFile hashes ({len(result['file_hashes'])} files):")
                        for path, hash_val in result['file_hashes'].items():
                            print(f"  {path}: {hash_val[:30]}...")

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'compare':
        try:
            result = compute_skill_hash(args.path)
            current_hash = result['content_hash']

            comparison = detect_modifications(
                current_hash,
                args.base_hash,
                args.upstream_hash
            )

            if args.json:
                print(json.dumps(comparison, indent=2))
            else:
                if comparison['local_modified']:
                    print("Local modifications detected")
                else:
                    print("No local modifications")

                if args.upstream_hash:
                    if comparison['upstream_modified']:
                        print("Upstream changes available")
                    else:
                        print("Upstream unchanged")

                    if comparison['needs_merge']:
                        print("MERGE REQUIRED: Both local and upstream have changes")

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'verify':
        try:
            if args.path.is_file():
                actual_hash = compute_file_hash(args.path)
            else:
                result = compute_skill_hash(args.path)
                actual_hash = result['content_hash']

            if compare_hashes(actual_hash, args.expected_hash):
                print("MATCH: Hash verified")
                sys.exit(0)
            else:
                print(f"MISMATCH: Expected {args.expected_hash}, got {actual_hash}")
                sys.exit(1)

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
