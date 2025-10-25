"""
Setup Prefect automation for webhook-based flow resumption.

Creates an automation that:
1. Triggers on slack.message.reply custom events from the webhook
2. Resumes the paused flow run with parsed approval input

Usage:
    python scripts/setup_webhook_automation.py

Prerequisites:
    - Prefect webhook must be created first (see docs/webhook-setup.md)
    - Flow must be deployed and running
"""

from prefect.automations import Automation
from prefect.events.schemas.automations import EventTrigger
from prefect.events.actions import ResumeFlowRun


def create_automation():
    """Create the Prefect automation for resuming flows from Slack events."""

    automation_name = "resume-flow-on-slack-approval"

    print(f"\nCreating automation: {automation_name}")

    # Define the trigger: react to slack.message.reply events
    trigger = EventTrigger(
        expect={"slack.message.reply"},
        match_related={
            "prefect.resource.id": "prefect.flow-run.*",
        },
        posture="Reactive",
        threshold=1,
    )

    # Define the action: resume the flow run with parsed approval input
    # The run_input uses Jinja2 templating to parse the Slack message
    action = ResumeFlowRun(
        source="inferred",
        run_input={
            "approved": "{% if 'approve' in event.resource.message_text or '✓' in event.resource.message_text %}true{% else %}false{% endif %}",
            "feedback": "{% if 'feedback:' in event.resource.message_text %}{{ event.resource.message_text.split('feedback:')[1] | trim }}{% else %}null{% endif %}",
            "regenerate": "{% if 'feedback:' in event.resource.message_text %}true{% else %}false{% endif %}"
        }
    )

    # Create the automation
    automation = Automation(
        name=automation_name,
        description="Resume meal planner flow when user responds in Slack",
        enabled=True,
        trigger=trigger,
        actions=[action],
    )

    # Check if automation already exists and create/update
    try:
        existing = Automation.read(name=automation_name)
        print(f"⚠️  Automation '{automation_name}' already exists (ID: {existing.id})")
        print(f"   Updating existing automation...")

        # Update the existing automation
        automation.id = existing.id
        automation.update()

        print(f"   ✓ Updated existing automation")
        created = automation

    except Exception:
        # Automation doesn't exist, create new one
        created = automation.create()
        print(f"   ✓ Created new automation")

    print(f"\n✓ Automation ready: {automation_name}")
    print(f"  - ID: {created.id}")
    print(f"  - Trigger: Custom event 'slack.message.reply'")
    print(f"  - Action: Resume flow run with parsed approval input")
    print(f"  - Status: {'Enabled' if created.enabled else 'Disabled'}")
    print(f"\n✓ Setup complete!")
    print(f"\nNext steps:")
    print(f"1. Ensure your Slack Events API is configured to send to the Prefect webhook")
    print(f"2. Deploy and run your flow")
    print(f"3. Reply to the meal plan message in Slack with 'approve', 'reject', or 'feedback: <text>'")
    print(f"4. The automation will automatically resume your flow!")

    return created


def main():
    """Main entry point."""
    try:
        create_automation()
    except Exception as e:
        print(f"\n❌ Error creating automation: {e}")
        print(f"\nTroubleshooting:")
        print(f"- Ensure you're authenticated with Prefect Cloud (run 'prefect cloud login')")
        print(f"- Check that you have permissions to create automations")
        print(f"- Verify your Prefect API URL is set correctly")
        raise


if __name__ == "__main__":
    main()
