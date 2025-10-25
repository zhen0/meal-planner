#!/usr/bin/env python
"""
Setup script for Prefect secrets and variables.
Run this after configuring your .env file to push config to Prefect Cloud.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def setup_secrets():
    """Create Prefect secrets from environment variables."""
    print("\n" + "="*80)
    print("Setting up Prefect Secrets (sensitive data)")
    print("="*80)

    secrets = {
        "anthropic-api-key": os.getenv("ANTHROPIC_API_KEY"),
        "slack-bot-token": os.getenv("SLACK_BOT_TOKEN"),
        "prefect-api-key": os.getenv("PREFECT_API_KEY"),
        "logfire-token": os.getenv("LOGFIRE_TOKEN"),
        "slack-signing-secret": os.getenv("SLACK_SIGNING_SECRET"),
        "todoist-mcp-auth-token": os.getenv("TODOIST_MCP_AUTH_TOKEN"),
    }

    for name, value in secrets.items():
        if value:
            # Create secret via Prefect CLI
            cmd = f'prefect block create secret {name} --value "{value}"'
            print(f"Creating secret: {name}")
            os.system(cmd)
        else:
            print(f"Skipping {name} (not set)")

    print("\n✓ Secrets setup complete")


def setup_variables():
    """Create Prefect variables from environment variables."""
    print("\n" + "="*80)
    print("Setting up Prefect Variables (non-sensitive configuration)")
    print("="*80)

    variables = {
        "slack-channel-id": os.getenv("SLACK_CHANNEL_ID"),
        "todoist-grocery-project-id": os.getenv("TODOIST_GROCERY_PROJECT_ID"),
        "todoist-mcp-server-url": os.getenv("TODOIST_MCP_SERVER_URL"),
        "prefect-api-url": os.getenv("PREFECT_API_URL"),
        "logfire-project-name": os.getenv("LOGFIRE_PROJECT_NAME", "meal-planner-agent"),
        "prefect-flow-name": os.getenv("PREFECT_FLOW_NAME", "weekly-meal-planner"),
        "prefect-work-pool-name": os.getenv("PREFECT_WORK_POOL_NAME", "managed-execution"),
        "approval-timeout-seconds": os.getenv("APPROVAL_TIMEOUT_SECONDS", "86400"),
        "slack-poll-interval-seconds": os.getenv("SLACK_POLL_INTERVAL_SECONDS", "30"),
        "max-regeneration-attempts": os.getenv("MAX_REGENERATION_ATTEMPTS", "3"),
    }

    for name, value in variables.items():
        if value:
            # Create variable via Prefect CLI
            cmd = f'prefect variable set {name} "{value}"'
            print(f"Setting variable: {name}")
            os.system(cmd)
        else:
            print(f"Skipping {name} (not set)")

    print("\n✓ Variables setup complete")


def verify_config():
    """Verify that required configuration is set."""
    print("\n" + "="*80)
    print("Verifying Configuration")
    print("="*80)

    required_secrets = [
        "ANTHROPIC_API_KEY",
        "SLACK_BOT_TOKEN",
        "PREFECT_API_KEY",
        "LOGFIRE_TOKEN",
    ]

    required_variables = [
        "SLACK_CHANNEL_ID",
        "TODOIST_GROCERY_PROJECT_ID",
        "TODOIST_MCP_SERVER_URL",
        "PREFECT_API_URL",
    ]

    missing = []

    for var in required_secrets + required_variables:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        print("\n✗ Missing required configuration:")
        for var in missing:
            print(f"  - {var}")
        print("\nPlease set these in your .env file and try again.")
        return False

    print("\n✓ All required configuration is set")
    return True


def main():
    """Main setup routine."""
    print("\n" + "#"*80)
    print("# PREFECT CONFIGURATION SETUP")
    print("#"*80)

    # Verify configuration
    if not verify_config():
        sys.exit(1)

    # Confirm with user
    print("\nThis script will:")
    print("1. Create Prefect Secret blocks for API keys/tokens")
    print("2. Create Prefect Variables for IDs/URLs")
    print("\nNote: This requires you to be logged in to Prefect Cloud")
    print("      Run 'prefect cloud login' first if you haven't already")

    response = input("\nContinue? (y/N): ").strip().lower()
    if response != 'y':
        print("\nSetup cancelled")
        sys.exit(0)

    # Setup secrets and variables
    try:
        setup_secrets()
        setup_variables()

        print("\n" + "="*80)
        print("Setup Complete!")
        print("="*80)
        print("\nYour Prefect secrets and variables are now configured.")
        print("You can view them at:")
        print("  - Secrets: Prefect Cloud UI > Blocks > Secrets")
        print("  - Variables: Prefect Cloud UI > Variables")
        print("\nNext steps:")
        print("  1. Deploy your flow: prefect deploy -f deployment/prefect_deployment.yaml")
        print("  2. Verify deployment: prefect deployment inspect weekly-meal-planner")
        print("  3. Test run: prefect deployment run weekly-meal-planner/weekly-meal-planner")

    except Exception as e:
        print(f"\n✗ Error during setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
