# Quick Start Guide

Get your Weekly Meal Planning Agent up and running in 10 minutes!

## Prerequisites Checklist

- [ ] Python 3.11+ installed
- [ ] Prefect Cloud account ([sign up](https://www.prefect.io/cloud))
- [ ] Anthropic API key ([get one](https://console.anthropic.com/))
- [ ] Slack workspace with admin access
- [ ] Todoist account with hosted MCP server
- [ ] Logfire account ([sign up](https://logfire.pydantic.dev/))

## Step-by-Step Setup

### 1. Install Dependencies (2 min)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install packages
make install
# or: pip install -r requirements.txt
```

### 2. Configure Slack Bot (3 min)

1. Go to https://api.slack.com/apps → Create New App
2. Add Bot Token Scopes:
   - `chat:write`
   - `conversations.history`
3. Install to workspace
4. Copy Bot User OAuth Token (starts with `xoxb-`)
5. Create/choose a channel for meal plans
6. Invite bot to channel: `/invite @your-bot-name`

### 3. Get Todoist Project ID (1 min)

1. Go to Todoist → Find your "Grocery" project
2. Click project → Settings → Copy Project ID
3. Or use Todoist API to list projects

**Critical**: This is the ONLY project the agent can write to!

### 4. Set Environment Variables (2 min)

```bash
# Copy example file
make setup-env
# or: cp .env.example .env

# Edit .env with your values
nano .env  # or use your favorite editor
```

Fill in:
- `DIETARY_PREFERENCES` - Your preferences in natural language
- `ANTHROPIC_API_KEY` - Your Claude API key
- `SLACK_BOT_TOKEN` - From step 2
- `SLACK_CHANNEL_ID` - Channel ID (right-click channel → Copy Link, ID is at end)
- `TODOIST_GROCERY_PROJECT_ID` - From step 3
- `TODOIST_MCP_SERVER_URL` - Your hosted MCP server URL
- `PREFECT_API_KEY` - From Prefect Cloud
- `PREFECT_API_URL` - From Prefect Cloud workspace settings
- `LOGFIRE_TOKEN` - From Logfire project settings

### 5. Test Locally (2 min)

```bash
# Run manual tests
make test-manual
# or: python manual_test.py

# Expected output:
# ✓ Configuration
# ✓ Security Validation
# ✓ Slack Response Parsing
# ✓ Meal Plan Formatting
# ✓ Preference Parsing (if API key configured)
# ✓ Meal Generation (if API key configured)
```

If all tests pass, you're ready to deploy!

### 6. Deploy to Prefect Cloud (2 min)

```bash
# Login to Prefect Cloud
prefect cloud login

# Create work pool (first time only)
prefect work-pool create managed-execution --type managed

# Deploy the flow
make deploy
# or: prefect deploy -f deployment/prefect_deployment.yaml

# Set environment variables in Prefect Cloud
prefect variable set ANTHROPIC_API_KEY "your-key-here"
prefect variable set SLACK_BOT_TOKEN "your-token-here"
# ... (repeat for all variables)
```

## First Run

### Option A: Wait for Schedule

The flow runs every **Saturday at 5pm UTC**. Just wait!

### Option B: Trigger Manually

```bash
# Trigger from command line
prefect deployment run weekly-meal-planner/weekly-meal-planner

# Or from Prefect Cloud UI:
# Deployments → weekly-meal-planner → Quick Run
```

## What to Expect

1. **Flow starts** - Parses your preferences, generates meals
2. **Slack notification** - You receive a message with 2 meal proposals
3. **Your turn** - Reply in thread:
   - `approve` - Accept the plan
   - `feedback: make it spicier` - Regenerate with feedback
   - `reject` - Reject without regeneration
4. **Flow resumes** - Creates grocery tasks in Todoist
5. **Final confirmation** - Full meal plan posted to Slack

## Troubleshooting

### "Config validation failed"

**Problem**: Missing or invalid environment variables

**Fix**:
```bash
# Check your .env file
cat .env | grep -v "^#" | grep -v "^$"

# Verify required fields are filled
python -c "from src.config import get_config; print(get_config())"
```

### "ProjectAccessDenied" error

**Problem**: Wrong Todoist project ID

**Fix**:
```bash
# Double-check project ID in .env matches Todoist
echo $TODOIST_GROCERY_PROJECT_ID

# Test security validation
python -c "from src.security_validation import validate_project_id; validate_project_id('your-id-here')"
```

### Slack bot doesn't respond

**Problem**: Missing permissions or not in channel

**Fix**:
1. Verify bot has `conversations.history` scope
2. Re-invite bot to channel: `/invite @bot-name`
3. Check bot token starts with `xoxb-`

### Flow doesn't pause

**Problem**: Using wrong Prefect API or pause function

**Fix**:
1. Ensure using Prefect 3.0+: `pip show prefect`
2. Verify `pause_flow_run(wait_for_input=ApprovalInput)` in main.py
3. Check Prefect Cloud deployment is using Managed Execution

## Next Steps

- **Customize preferences**: Update `DIETARY_PREFERENCES` in .env
- **Adjust schedule**: Edit `deployment/prefect_deployment.yaml` cron
- **View traces**: Open Logfire dashboard to see execution details
- **Add more meals**: Modify Claude prompts in `src/claude_integration.py`

## Need Help?

- **Documentation**: See [README.md](README.md) for full details
- **Test suite**: Run `make test` to verify all components
- **Logs**: Check Prefect Cloud and Logfire for detailed traces

---

**Happy meal planning! 🍽️**
