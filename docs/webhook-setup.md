# Slack Webhook Setup for Flow Approval

This guide explains how to set up automated flow resumption when users respond in Slack.

## Architecture

```
User replies in Slack → Slack Events API → Prefect Webhook → Prefect Event → Automation → Resume Flow
```

## Prerequisites

- Prefect Cloud account
- Slack bot already configured (see main README)
- Flow deployed and running

## Complete Setup Guide

### Step 1: Create Prefect Webhook

1. Go to Prefect Cloud UI → **Webhooks** → **Create Webhook**
2. **Name**: `slack-meal-approval`
3. **Template** (Jinja2):

```json
{
  "event": "slack.message.reply",
  "resource": {
    "prefect.resource.id": "slack.thread.{{ body.event.ts }}",
    "flow_run_id": "{{ body.event.message.metadata.event_payload.flow_run_id }}",
    "message_text": "{{ body.event.text }}",
    "user_id": "{{ body.event.user }}",
    "thread_ts": "{{ body.event.thread_ts }}"
  }
}
```

4. Click **Create**
5. **Copy the webhook URL** - you'll need it for Slack setup

The URL looks like: `https://api.prefect.cloud/hooks/AbCdEf1234567890`

### Step 2: Configure Slack Events API

1. Go to https://api.slack.com/apps
2. Select your Meal Planner Bot app
3. Go to **Event Subscriptions**
4. **Enable Events** (toggle to ON)
5. **Request URL**: Paste your Prefect webhook URL
   - Slack will send a verification challenge
   - Prefect automatically responds - wait for "Verified" checkmark
6. **Subscribe to bot events** → **Add Bot User Event**:
   - Add: `message.channels` (A message was posted to a channel)
7. Click **Save Changes**
8. **Reinstall App** (Slack will prompt you)

### Step 3: Create Prefect Automation

Now we'll create an automation that resumes the flow when the webhook event arrives.

**Option A: Via Prefect Cloud UI**

1. Go to Prefect Cloud → **Automations** → **Create Automation**
2. **Name**: `Resume flow on Slack approval`
3. **Trigger**:
   - **Trigger Type**: Custom Event
   - **Match related resources**:
     - **Event name**: `slack.message.reply`
4. **Actions** → **Add Action** → **Resume a Flow Run**
   - **Source**: Inferred from event
   - **Flow run ID**: `{{ event.resource.flow_run_id }}`
   - **Run input**:
```json
{
  "approved": {% if "approve" in event.resource.message_text or "✓" in event.resource.message_text %}true{% else %}false{% endif %},
  "feedback": {% if "feedback:" in event.resource.message_text %}"{{ event.resource.message_text.split('feedback:')[1] | trim }}"{% else %}null{% endif %},
  "regenerate": {% if "feedback:" in event.resource.message_text %}true{% else %}false{% endif %}
}
```

5. Click **Create**

**Option B: Via Python Script** (recommended - easier to get the JSON right)

Run the setup script:

```bash
python scripts/setup_webhook_automation.py
```

This script will create the automation with the correct configuration. The script will:
- Create a custom event trigger for `slack.message.reply` events
- Set up a resume flow action with Jinja2 template to parse approval/feedback/reject
- Handle all the JSON templating automatically

## How It Works

1. User posts meal plan to Slack with thread_ts containing flow_run_id
2. User replies in thread: `approve`, `reject`, or `feedback: make it spicier`
3. Slack sends event to Prefect webhook
4. Webhook parses message and creates Prefect event
5. Automation detects event and resumes flow with approval input
6. Flow continues from pause point

## Understanding the Data Flow

### Webhook Template Variables
The webhook template uses Jinja2 to extract data from the Slack event payload:
- `body.event.ts`: Event timestamp
- `body.event.text`: The actual message text from the user
- `body.event.user`: Slack user ID who sent the message
- `body.event.thread_ts`: Thread timestamp (for replies)
- `body.event.message.metadata.event_payload.flow_run_id`: Our flow run ID (from original message metadata)

### Automation Action Template
The automation uses Jinja2 to parse the message text and create the correct ApprovalInput:
- Checks if message contains "approve" or "✓" → sets `approved: true`
- Checks if message starts with "feedback:" → extracts feedback text
- Sets `regenerate: true` when feedback is provided

## Testing

Test the webhook directly:

```bash
curl -X POST https://api.prefect.cloud/hooks/YOUR_WEBHOOK_ID \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "type": "message",
      "channel": "C01234",
      "user": "U01234",
      "text": "approve",
      "thread_ts": "1234567890.123456"
    }
  }'
```

Check the Event Feed in Prefect Cloud to see if the event was created.

## Troubleshooting

- **Webhook not receiving events**: Check Slack Event Subscriptions Request URL verification
- **Automation not triggering**: Verify event name matches exactly in automation trigger
- **Flow not resuming**: Check that flow_run_id is correctly extracted from thread
- **Parse errors**: View webhook logs in Prefect Cloud to debug template

## Alternative: Store flow_run_id in Slack Message

To simplify, you can include the flow_run_id in the original Slack message metadata:

```python
# In post_meal_plan_to_slack()
metadata = {
    "event_type": "meal_plan_approval",
    "event_payload": {
        "flow_run_id": current_flow_run_id,
        "channel_id": channel_id,
        "thread_ts": thread_ts
    }
}
```

Then webhook can extract it directly from the message context.

## Summary

Once setup is complete, the approval flow works as follows:

1. **Flow runs** and pauses at the approval step
2. **Meal plan posted** to Slack with `flow_run_id` in metadata
3. **User replies** in thread: `approve`, `reject`, or `feedback: <text>`
4. **Slack sends event** to Prefect webhook URL
5. **Webhook transforms** Slack event into Prefect event with parsed data
6. **Automation detects** event and resumes flow with ApprovalInput
7. **Flow continues** - creates grocery tasks or regenerates based on input

## Benefits of Webhook Approach

Compared to polling Slack API:
- **Instant response**: Flow resumes immediately when user responds
- **No polling overhead**: No background tasks consuming resources
- **Simpler architecture**: No separate monitoring flow to maintain
- **Prefect-native**: Uses built-in webhook and automation features
- **Scalable**: Handles multiple concurrent flows without coordination

## Next Steps

After completing setup:
1. Deploy your flow to Prefect Cloud
2. Run a test flow and verify it pauses at approval step
3. Check Slack Events API logs to confirm events are being sent
4. Monitor Prefect Event Feed to see webhook events arriving
5. Reply in Slack and verify flow resumes correctly
6. Check Logfire for complete trace of the approval workflow
