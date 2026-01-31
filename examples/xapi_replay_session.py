"""
Example: Replay a session from xAPI logs

This script demonstrates how to:
1. Read xAPI statements from a session
2. Reconstruct the conversation flow
3. Analyze interaction patterns
4. Export in various formats
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

from src.p3394_agent.core.storage import AgentStorage


async def replay_session(agent_name: str, session_id: str):
    """Replay a session from xAPI logs"""

    print(f"\n{'='*70}")
    print(f"Session Replay: {session_id}")
    print(f"{'='*70}\n")

    # Load storage
    storage = AgentStorage(agent_name=agent_name)

    # Read xAPI statements
    statements = await storage.read_xapi_statements(session_id)

    if not statements:
        print(f"❌ No xAPI statements found for session: {session_id}")
        return

    print(f"Found {len(statements)} interactions\n")

    # Sort by timestamp
    statements.sort(key=lambda s: s['timestamp'])

    # Replay conversation
    print(f"{'─'*70}")
    print("Conversation Flow")
    print(f"{'─'*70}\n")

    for i, stmt in enumerate(statements, 1):
        timestamp = stmt['timestamp']
        actor = stmt['actor']['name']
        verb = stmt['verb']['display']['en-US']
        obj_def = stmt['object']['definition']
        obj_name = obj_def['name']['en-US']

        # Get description if available
        description = obj_def.get('description', {}).get('en-US', '')

        # Format timestamp
        ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        time_str = ts.strftime('%H:%M:%S')

        # Display interaction
        print(f"[{time_str}] {actor} {verb}:")

        if description:
            # Indent and wrap description
            lines = description.split('\n')
            for line in lines[:3]:  # Show first 3 lines
                print(f"  {line}")
            if len(lines) > 3 or len(description) > 200:
                print(f"  ...")
        else:
            print(f"  {obj_name}")

        print()

    # Analyze patterns
    print(f"\n{'─'*70}")
    print("Interaction Analysis")
    print(f"{'─'*70}\n")

    # Count verbs
    verb_counts = Counter(s['verb']['display']['en-US'] for s in statements)
    print("Verb Distribution:")
    for verb, count in verb_counts.most_common():
        bar = '█' * (count * 2)
        print(f"  {verb:15s} {bar} {count}")

    # Count activity types
    activity_types = Counter()
    for s in statements:
        activity_type = s['object']['definition']['type']
        # Extract just the last part of the type URL
        type_name = activity_type.split('/')[-1]
        activity_types[type_name] += 1

    print("\nActivity Types:")
    for atype, count in activity_types.most_common():
        print(f"  {atype:15s} {count}")

    # Calculate session duration
    if len(statements) >= 2:
        start_time = datetime.fromisoformat(statements[0]['timestamp'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(statements[-1]['timestamp'].replace('Z', '+00:00'))
        duration = end_time - start_time
        print(f"\nSession Duration: {duration.total_seconds():.1f} seconds")

    # Identify actors
    actors = set(s['actor']['name'] for s in statements)
    print(f"Participants: {', '.join(actors)}")

    # Export options
    print(f"\n{'─'*70}")
    print("Export Options")
    print(f"{'─'*70}\n")

    session_dir = storage.get_server_session_dir(session_id)
    if session_dir:
        xapi_file = session_dir / "xapi_statements.jsonl"
        print(f"Raw xAPI JSONL: {xapi_file}")

        # Export as pretty JSON
        json_export = session_dir / "xapi_statements_pretty.json"
        with json_export.open('w') as f:
            json.dump(statements, f, indent=2)
        print(f"Pretty JSON:    {json_export}")

        # Export as markdown
        md_export = session_dir / "session_transcript.md"
        with md_export.open('w') as f:
            f.write(f"# Session Transcript\n\n")
            f.write(f"**Session ID:** `{session_id}`\n\n")
            f.write(f"**Duration:** {duration.total_seconds():.1f} seconds\n\n")
            f.write(f"**Participants:** {', '.join(actors)}\n\n")
            f.write(f"---\n\n")

            for stmt in statements:
                timestamp = stmt['timestamp']
                ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                actor = stmt['actor']['name']
                verb = stmt['verb']['display']['en-US']
                description = stmt['object']['definition'].get('description', {}).get('en-US', '')

                f.write(f"## {ts.strftime('%H:%M:%S')} - {actor} {verb}\n\n")
                if description:
                    f.write(f"{description}\n\n")
                f.write(f"---\n\n")

        print(f"Markdown:       {md_export}")

        # Export as CSV
        csv_export = session_dir / "session_summary.csv"
        with csv_export.open('w') as f:
            f.write("timestamp,actor,verb,object,message_id\n")
            for stmt in statements:
                timestamp = stmt['timestamp']
                actor = stmt['actor']['name']
                verb = stmt['verb']['display']['en-US']
                obj_name = stmt['object']['definition']['name']['en-US']
                msg_id = stmt['context']['extensions'].get(
                    'http://id.tincanapi.com/extension/p3394-message-id', ''
                )
                f.write(f"{timestamp},{actor},{verb},{obj_name},{msg_id}\n")

        print(f"CSV:            {csv_export}")

    print(f"\n{'='*70}\n")


async def list_sessions(agent_name: str):
    """List all available sessions with xAPI logs"""

    print(f"\n{'='*70}")
    print(f"Available Sessions for: {agent_name}")
    print(f"{'='*70}\n")

    storage = AgentStorage(agent_name=agent_name)

    # Scan STM/server directory for sessions
    sessions = []
    if storage.stm_server_dir.exists():
        for session_dir in storage.stm_server_dir.iterdir():
            if session_dir.is_dir():
                xapi_file = session_dir / "xapi_statements.jsonl"
                if xapi_file.exists():
                    # Count statements
                    with xapi_file.open('r') as f:
                        count = sum(1 for line in f if line.strip())

                    # Get creation time
                    context_file = session_dir / "context.json"
                    created_at = "Unknown"
                    if context_file.exists():
                        with context_file.open('r') as f:
                            context = json.load(f)
                            created_at = context.get('created_at', 'Unknown')

                    sessions.append({
                        'id': session_dir.name,
                        'created_at': created_at,
                        'statement_count': count,
                        'path': session_dir
                    })

    if not sessions:
        print("No sessions with xAPI logs found.\n")
        return

    # Sort by creation time
    sessions.sort(key=lambda s: s['created_at'], reverse=True)

    print(f"Found {len(sessions)} session(s):\n")

    for i, session in enumerate(sessions, 1):
        print(f"{i}. {session['id']}")
        print(f"   Created: {session['created_at']}")
        print(f"   Statements: {session['statement_count']}")
        print(f"   Path: {session['path']}")
        print()

    return [s['id'] for s in sessions]


async def main():
    """Main entry point"""

    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python xapi_replay_session.py list [agent_name]")
        print("  python xapi_replay_session.py replay <session_id> [agent_name]")
        print("\nExample:")
        print("  python xapi_replay_session.py list ieee3394-exemplar")
        print("  python xapi_replay_session.py replay abc123 ieee3394-exemplar")
        return

    command = sys.argv[1]
    agent_name = sys.argv[3] if len(sys.argv) > 3 else "ieee3394-exemplar"

    if command == "list":
        await list_sessions(agent_name)

    elif command == "replay":
        if len(sys.argv) < 3:
            print("Error: session_id required")
            return

        session_id = sys.argv[2]
        await replay_session(agent_name, session_id)

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())
