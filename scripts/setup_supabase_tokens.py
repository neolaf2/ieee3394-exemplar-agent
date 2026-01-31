#!/usr/bin/env python3
"""
Setup script for Supabase Control Token tables.

Usage:
    python scripts/setup_supabase_tokens.py --print-schema  # Print SQL to run manually
    python scripts/setup_supabase_tokens.py --setup         # Run setup via Supabase API
"""

import argparse
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def print_schema():
    """Print the SQL schema for manual execution."""
    from p3394_agent.memory.supabase_token_store import SUPABASE_SCHEMA

    print("=" * 70)
    print("KSTAR+ Control Tokens - Supabase Schema")
    print("=" * 70)
    print()
    print("Run this SQL in your Supabase SQL Editor:")
    print()
    print("-" * 70)
    print(SUPABASE_SCHEMA)
    print("-" * 70)
    print()
    print("After running the schema, add these environment variables:")
    print()
    print("  export SUPABASE_URL='https://your-project.supabase.co'")
    print("  export SUPABASE_KEY='your-service-role-key'")
    print()


def setup_via_api():
    """Setup tables via Supabase API (requires credentials)."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set")
        print()
        print("  export SUPABASE_URL='https://your-project.supabase.co'")
        print("  export SUPABASE_KEY='your-service-role-key'")
        sys.exit(1)

    from supabase import create_client
    from p3394_agent.memory.supabase_token_store import SUPABASE_SCHEMA

    client = create_client(url, key)

    print("Setting up Control Token tables...")
    print()

    # Note: Supabase client doesn't support raw SQL directly
    # You need to use the SQL Editor in the dashboard
    print("⚠️  The Supabase Python client doesn't support raw SQL execution.")
    print("   Please run the schema manually in the Supabase SQL Editor.")
    print()
    print_schema()


def test_connection():
    """Test connection to Supabase."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("❌ SUPABASE_URL and SUPABASE_KEY not set")
        return False

    try:
        from supabase import create_client
        client = create_client(url, key)

        # Try to query the table
        result = client.table("control_tokens").select("token_id").limit(1).execute()
        print("✓ Connected to Supabase")
        print(f"✓ control_tokens table exists")
        return True

    except Exception as e:
        if "relation" in str(e) and "does not exist" in str(e):
            print("✓ Connected to Supabase")
            print("❌ control_tokens table does not exist - run the schema first")
        else:
            print(f"❌ Connection failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Setup Supabase for KSTAR+ Control Tokens"
    )
    parser.add_argument(
        "--print-schema", "-p",
        action="store_true",
        help="Print the SQL schema for manual execution"
    )
    parser.add_argument(
        "--setup", "-s",
        action="store_true",
        help="Attempt to setup via Supabase API"
    )
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Test connection to Supabase"
    )

    args = parser.parse_args()

    if args.print_schema:
        print_schema()
    elif args.setup:
        setup_via_api()
    elif args.test:
        test_connection()
    else:
        # Default: print schema
        print_schema()


if __name__ == "__main__":
    main()
