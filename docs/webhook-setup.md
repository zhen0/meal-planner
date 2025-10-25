# Slack Webhook Setup for Flow Approval

This guide explains how to set up a Prefect webhook that receives Slack messages and resumes the paused meal planner flow.

## Architecture

```
Slack User responds → Slack Events API → Prefect Webhook → Call resume_flow_run API
```

The meal planner flow stores its `flow_run_id` in the Slack message metadata, so the webhook can extract it and resume the correct flow.

## Setup Steps

### 1. Create Prefect Webhook

In Prefect Cloud UI:

1. Navigate to **Webhooks** → **Create Webhook**
2. **Name**: `slack-meal-approval`
3. **Template** (Jinja2):

```json
{
  "event": "slack.message.approval",
  "resource": {
    "prefect.resource.id": "flow-run.{{ body.event.message.metadata.event_payload.flow_run_id }}",
    "flow_run_id": "{{ body.event.message.metadata.event_payload.flow_run_id }}",
    "channel_id": "{{ body.event.channel }}",
    "user_id": "{{ body.event.user }}",
    "message_text": "{{ body.event.text }}",
    "approved": "{% if 'approve' in body.event.text or '\u2713' in body.event.text %}true{% else %}false{% endif %}",
    "feedback": "{% if 'feedback:' in body.event.text %}{{ body.event.text.split('feedback:')[1] | trim }}{% else %}{% endif %}"
  }
}
```

4. Save and **copy the webhook URL** (e.g., `https://api.prefect.cloud/hooks/YOUR_WEBHOOK_ID`)

### 2. Configure Slack Events API

In your Slack App settings (https://api.slack.com/apps):

1. Go to **Event Subscriptions** → **Enable Events**
2. Set **Request URL** to your Prefect webhook URL
3. Under **Subscribe to bot events**, add:
   - `message.channels` - Messages posted to public channels
4. **Save Changes**
5. **Reinstall your app** to workspace

### 3. Create Prefect Automation

In Prefect Cloud UI:

1. Navigate to **Automations** → **Create Automation**
2. **Trigger**:
   - Type: **Custom Event**
   - Event: `slack.message.approval`
   - Match: `resource.id` contains `slack.thread.`

3. **Action**: **Resume Flow Run**
   - Source: **Inferred from event**
   - Run Input (Jinja2):
```json
{
  "approved": {{ event.resource.approved }},
  "feedback": "{{ event.resource.feedback }}",
  "regenerate": {{ event.resource.feedback != "" }}
}
```

4. **Save Automation**

## How It Works

1. User posts meal plan to Slack with thread_ts containing flow_run_id
2. User replies in thread: `approve`, `reject`, or `feedback: make it spicier`
3. Slack sends event to Prefect webhook
4. Webhook parses message and creates Prefect event
5. Automation detects event and resumes flow with approval input
6. Flow continues from pause point

## Webhook Template Filters

You'll need to add custom Jinja2 filters in the webhook template (Prefect Cloud supports this):

### `extract_flow_run_id`
Extracts flow run ID from thread metadata (stored in thread_ts or message)

### `is_approval`
Returns `true` if message is "approve" or "✓", `false` otherwise

### `extract_feedback`
Extracts feedback text after "feedback:" prefix, empty string if none

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
