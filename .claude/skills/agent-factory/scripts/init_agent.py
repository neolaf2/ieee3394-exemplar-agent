#!/usr/bin/env python3
"""
Initialize a new P3394 agent from the template.

Usage:
    python init_agent.py <agent-name> [--path <directory>]
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Initialize a new P3394 agent")
    parser.add_argument("name", help="Agent name (kebab-case)")
    parser.add_argument("--path", "-p", default=".", help="Target directory")
    parser.add_argument("--branch", "-b", default="v0.2.0", help="Git branch/tag to clone")

    args = parser.parse_args()

    agent_name = args.name
    target_dir = Path(args.path) / agent_name

    if target_dir.exists():
        print(f"Error: Directory {target_dir} already exists")
        sys.exit(1)

    print(f"Creating agent '{agent_name}' in {target_dir}...")

    # Clone template
    repo_url = "https://github.com/neolaf2/ieee3394-exemplar-agent.git"
    subprocess.run([
        "git", "clone", "--branch", args.branch,
        repo_url, str(target_dir)
    ], check=True)

    # Remove .git to start fresh
    subprocess.run(["rm", "-rf", str(target_dir / ".git")], check=True)

    # Initialize new git repo
    subprocess.run(["git", "init"], cwd=target_dir, check=True)

    # Update agent.yaml with agent name
    agent_yaml = target_dir / "agent.yaml"
    if agent_yaml.exists():
        content = agent_yaml.read_text()
        content = content.replace('id: "ieee3394-exemplar"', f'id: "{agent_name}"')
        content = content.replace('name: "IEEE 3394 Exemplar Agent"', f'name: "{agent_name.replace("-", " ").title()}"')
        agent_yaml.write_text(content)

    print(f"""
Agent '{agent_name}' created successfully!

Next steps:
  cd {target_dir}
  export ANTHROPIC_API_KEY='your-key'
  uv sync
  uv run python -m p3394_agent --daemon

See QUICKSTART.md for more details.
""")


if __name__ == "__main__":
    main()
