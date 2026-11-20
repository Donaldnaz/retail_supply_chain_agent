# Retail Supply Chain Agent

An end-to-end deployment repository for a retail supply chain operations agent built with Amazon Bedrock AgentCore, MCP, AWS Lambda, Amazon DynamoDB, FastAPI, and Next.js.

## Architecture

```text
Frontend -> FastAPI proxy -> Bedrock AgentCore Runtime
                                      |
                                      v
                              AgentCore Gateway (MCP)
                                      |
                                      v
                              AWS Lambda tools
                                      |
                                      v
                              DynamoDB snapshots
```

## Repository layout

- `agent/` — AgentCore runtime entrypoint and dependencies
- `backend/` — FastAPI invocation proxy
- `frontend/` — Next.js chat interface
- `lambda/` — DynamoDB MCP tool implementation
- `gateway/` — MCP tool JSON schemas
- `infrastructure/iam/` — AWS IAM policies
- `data/` — DynamoDB seed item
- `deploy/` — deployment shell scripts
- `docs/` — payloads and deployment reference

## Prerequisites

- AWS CLI configured for account `920375856513` in `us-east-1`
- Python 3.12
- Node.js 18+
- Bedrock AgentCore CLI
- Bedrock model access for `us.anthropic.claude-haiku-4-5-20251001-v1:0`

## Quick start

Copy the environment template:

```bash
cp .env.example .env
```

Create and seed DynamoDB:

```bash
bash deploy/01-create-dynamodb.sh
bash deploy/02-create-lambda-role.sh
bash deploy/04-seed-dynamodb.sh
bash deploy/03-deploy-lambda.sh
```

Configure the MCP gateway using `gateway/mcp-tool-schemas.json` and deploy the runtime:

```bash
cd agent
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
agentcore configure -e agent.py --region us-east-1
agentcore deploy
agentcore status
```

Run the backend:

```bash
pip install -r backend/requirements.txt
export AGENT_RUNTIME_ARN="arn:aws:bedrock-agentcore:us-east-1:920375856513:runtime/retail_supply_chain_agent-BjapTXB2zw"
uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload
```

Run the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

> The included IDs, names, and ARN values match the guide's deployed resources. Replace them for a different AWS account or deployment.

## Safety

The reorder tool is a simulation only. It sets `requires_human_approval: true` and does not place an external order. The frontend approval controls send conversational approval/rejection prompts and do not execute an order.
