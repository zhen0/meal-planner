# Weekly Meal Planning Agent

A durable execution agent that generates personalized weekly meal plans using Prefect, Claude (Anthropic), Slack approval workflows, and Todoist integration. Built with strict security controls to ensure grocery tasks are only created in the designated Grocery project.

## Features

- **Natural Language Preferences**: Describe your dietary preferences in plain English
- **AI-Powered Meal Generation**: Claude generates 2 quick meals (<20 min cook time) tailored to your preferences
- **Human-in-the-Loop Approval**: Slack-based approval workflow with pause/resume flow control
- **Feedback Loop**: Regenerate meals with feedback if you're not satisfied
- **Automated Grocery Lists**: Ingredients automatically added to Todoist Grocery project
- **Security-First**: Strict validation ensures ONLY the Grocery project can be written to
- **Full Observability**: Logfire integration for tracing, metrics, and audit logs
- **Durable Execution**: Prefect Cloud Managed Execution with 24-hour approval timeout

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Prefect Cloud (Managed Execution)            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Weekly Meal Planner Flow (Saturdays @ 5pm)              │  │
│  │                                                           │  │
│  │  1. Parse Preferences (Claude)                           │  │
│  │  2. Generate Meals (Claude)                              │  │
│  │  3. Post to Slack                                        │  │
│  │  4. ⏸ PAUSE (wait_for_input=ApprovalInput)              │  │
│  │     └─> Flow state stored in Prefect Cloud              │  │
│  │  5. Resume with approval decision                        │  │
│  │  6. If feedback: Loop back to step 2                     │  │
│  │  7. Create Grocery Tasks (MCP) ✓ Security validated      │  │
│  │  8. Post Final Confirmation                              │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │  Slack Thread Monitoring (Background)
                            ▼
                    ┌───────────────┐
                    │  Slack Bot    │
                    │  - Posts meal │
                    │  - Monitors   │
                    │  - Resumes    │
                    └───────────────┘
                            │
                    User responds: "approve" / "feedback: ..."
                            │
                            ▼
                    Prefect REST API
                    POST /flow_runs/{id}/resume
                    { run_input: ApprovalInput }
```

## Prerequisites

- Python 3.11+
- Prefect Cloud account (with API key)
- Anthropic API key (Claude access)
- Slack workspace with bot configured
- Todoist account with MCP server hosted
- Logfire account (for observability)

## Installation

1. **Clone the repository:**
   ```bash
   cd meal-planner-agent
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

## Configuration

### Required Environment Variables

Create a `.env` file with the following variables:

```bash
# Dietary Preferences (Natural Language)
DIETARY_PREFERENCES="I'm vegetarian, no mushrooms. I like Mediterranean and Asian flavors."

# Anthropic / Claude
ANTHROPIC_API_KEY="sk-ant-api03-..."

# Slack
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C..."

# Todoist MCP Server (GROCERY PROJECT ONLY)
TODOIST_GROCERY_PROJECT_ID="2345678901"
TODOIST_MCP_SERVER_URL="https://your-hosted-mcp-server.com"

# Prefect Cloud
PREFECT_API_KEY="pnu_..."
PREFECT_API_URL="https://api.prefect.cloud/api/accounts/<account-id>/workspaces/<workspace-id>"

# Logfire
LOGFIRE_TOKEN="..."
LOGFIRE_PROJECT_NAME="meal-planner-agent"
```

### Dietary Preferences Format

The `DIETARY_PREFERENCES` variable accepts natural language. Examples:

```bash
# Example 1: Vegetarian with restrictions
DIETARY_PREFERENCES="I'm vegetarian, no mushrooms or cilantro. I like Mediterranean and Asian flavors. I have chickpeas, lentils, and tofu on hand. Prefer quick salads and stir-fries."

# Example 2: Vegan with time constraint
DIETARY_PREFERENCES="Vegan diet. No nuts due to allergy. Love spicy food. Maximum 15 minutes cook time."

# Example 3: Flexible omnivore
DIETARY_PREFERENCES="I eat everything except seafood. Prefer one-pot meals and sheet pan dinners. Like bold flavors."
```

### Slack Bot Setup

1. Create a Slack app: https://api.slack.com/apps
2. Enable bot features and add these scopes:
   - `chat:write` - Post messages
   - `conversations.history` - Read thread replies
3. Install app to workspace
4. Copy bot token (starts with `xoxb-`)
5. Invite bot to your meal planning channel

### Todoist MCP Server Setup

The agent requires a hosted MCP server for Todoist integration. The MCP server must:

1. Accept task creation requests with project ID
2. Validate project ID before creating tasks
3. Return task creation responses

**Security Note**: The agent validates the project ID on EVERY task creation. Only tasks for the configured Grocery project will be allowed.

## Usage

### Manual Testing

Run the manual test script to verify configuration:

```bash
python manual_test.py
```

This will test:
- Configuration loading
- Security validation
- Slack response parsing
- Meal plan formatting
- (Optional) Claude API integration

### Running Locally

Test the flow locally:

```bash
python -m src.main
```

### Deploying to Prefect Cloud

1. **Authenticate with Prefect Cloud:**
   ```bash
   prefect cloud login
   ```

2. **Create work pool (if not exists):**
   ```bash
   prefect work-pool create managed-execution --type managed
   ```

3. **Deploy the flow:**
   ```bash
   prefect deploy -f deployment/prefect_deployment.yaml
   ```

4. **Set environment variables as Prefect secrets:**
   ```bash
   prefect variable set ANTHROPIC_API_KEY <your-key>
   prefect variable set SLACK_BOT_TOKEN <your-token>
   # ... set all other variables
   ```

5. **Verify deployment:**
   ```bash
   prefect deployment inspect weekly-meal-planner
   ```

The flow will now run every Saturday at 5pm UTC.

### Approval Workflow

1. **Flow generates meals** and posts to Slack:
   ```
   🍽️ YOUR WEEKLY MEAL PLAN (for approval)

   Meal 1: Mediterranean Chickpea Salad
   Active: 15 min | Serves 2 | Ingredients: 7 items

   Meal 2: Asian Tofu Stir-Fry
   Active: 17 min | Serves 2 | Ingredients: 8 items

   📊 Shared Ingredients: 5 items

   How to respond:
   • Reply `approve` to accept
   • Reply `reject` to reject
   • Reply `feedback: <text>` to regenerate
   ```

2. **You respond in the thread:**
   - `approve` or `✓` - Accept the plan
   - `reject` or `✗` - Reject without regeneration
   - `feedback: make it spicier` - Regenerate with feedback
   - `feedback: no tomatoes` - Regenerate avoiding tomatoes

3. **Flow resumes** with your decision:
   - If approved: Creates grocery tasks
   - If feedback: Regenerates meals and re-posts
   - If timeout (24 hours): Uses last generated plan

4. **Final confirmation** posted to Slack with full meal details and ingredient list.

## Security

### Grocery Project Restriction

The agent has **strict security controls** to ensure it only writes to the Grocery project:

1. **Pre-call validation**: Every task creation validates `project_id == TODOIST_GROCERY_PROJECT_ID`
2. **Hard fail policy**: If validation fails, a `ProjectAccessDenied` exception is raised
3. **Audit logging**: All validation attempts are logged to Logfire with security flags
4. **No fallback**: The agent never defaults to another project or retries with different IDs

Example validation code:
```python
def validate_project_id(project_id: str) -> None:
    """Validate project ID matches Grocery project."""
    if project_id != config.todoist_grocery_project_id:
        logfire.error("SECURITY: Wrong project", security_incident=True)
        raise ProjectAccessDenied(f"Only Grocery project allowed")
```

## Testing

### Run Unit Tests

```bash
pytest tests/ -v
```

### Run Integration Tests

```bash
pytest tests/test_integration.py -v
```

### Run with Coverage

```bash
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

## Observability

### Logfire Dashboard

The agent automatically traces all operations to Logfire:

1. **Claude API calls**: Token usage, latency, prompts/responses
2. **Custom spans**: Preference parsing, meal generation, approval waiting
3. **Security events**: All project ID validations and access attempts
4. **Business metrics**: Meals generated, regeneration count, approval time
5. **Error tracking**: Failed API calls, validation errors, timeouts

View traces at: https://logfire.pydantic.dev

### Key Metrics

- **Approval wait time**: Time between posting to Slack and receiving response
- **Regeneration count**: How many times meals were regenerated per flow
- **API latency**: Claude API response times
- **Security incidents**: Attempted access to wrong projects (should be 0!)

## Troubleshooting

### Flow doesn't pause

**Issue**: Flow doesn't wait for Slack approval

**Solution**: Ensure you're using `pause_flow_run(wait_for_input=ApprovalInput)` not `suspend_flow_run()`

### Security validation fails

**Issue**: `ProjectAccessDenied` exception even with correct project

**Solution**:
1. Verify `TODOIST_GROCERY_PROJECT_ID` exactly matches your Todoist project ID
2. Check Logfire logs for the attempted vs. allowed project IDs
3. Ensure no extra whitespace in the project ID

### Slack bot not responding

**Issue**: Bot doesn't see thread replies

**Solution**:
1. Verify bot has `conversations.history` scope
2. Ensure bot is invited to the channel
3. Check Slack thread polling interval (default 30 seconds)

### Claude API errors

**Issue**: `401 Unauthorized` or rate limit errors

**Solution**:
1. Verify `ANTHROPIC_API_KEY` is correct and starts with `sk-ant-`
2. Check API key has sufficient credits
3. Review Logfire for detailed error traces

### Prefect flow timeout

**Issue**: Flow times out before approval

**Solution**:
1. Default timeout is 24 hours (86400 seconds)
2. Adjust `APPROVAL_TIMEOUT_SECONDS` if needed
3. Flow timeout in deployment YAML should exceed approval timeout

## Project Structure

```
meal-planner-agent/
├── src/
│   ├── __init__.py                 # Package init
│   ├── main.py                     # Main Prefect flow
│   ├── config.py                   # Configuration management
│   ├── models.py                   # Data models (ApprovalInput, MealPlan, etc.)
│   ├── claude_integration.py       # Claude API integration
│   ├── slack_integration.py        # Slack API + Prefect resume
│   ├── todoist_mcp_integration.py  # MCP client with security
│   └── security_validation.py      # Project ID validation
├── tests/
│   ├── test_models.py              # Model tests
│   ├── test_security_validation.py # Security tests
│   ├── test_slack_integration.py   # Slack tests
│   └── test_integration.py         # End-to-end tests
├── deployment/
│   └── prefect_deployment.yaml     # Prefect Cloud deployment
├── .env.example                    # Example environment variables
├── logfire.toml                    # Logfire configuration
├── requirements.txt                # Python dependencies
├── manual_test.py                  # Manual testing script
└── README.md                       # This file
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues or questions:

- GitHub Issues: [your-repo/issues](https://github.com/your-org/meal-planner-agent/issues)
- Prefect docs: https://docs.prefect.io
- Anthropic docs: https://docs.anthropic.com
- Logfire docs: https://logfire.pydantic.dev

---

**Built with:**
- [Prefect](https://www.prefect.io/) - Workflow orchestration
- [Claude (Anthropic)](https://www.anthropic.com/) - AI meal generation
- [Slack](https://slack.com/) - Approval interface
- [Todoist](https://todoist.com/) - Grocery list management
- [Logfire](https://logfire.pydantic.dev/) - Observability
