# Retail Supply Chain Agent

> **What you will build:** an AI-powered retail operations assistant that reads store inventory and demand data, explains supply-chain risks, compares pricing, and prepares reorder drafts that require human approval.

## What this agent does

The Retail Supply Chain Agent is a conversational operations assistant for store and product decisions. It uses Amazon Bedrock AgentCore, an MCP gateway, AWS Lambda, and Amazon DynamoDB to answer questions grounded in supply-chain snapshot data.

The agent can:

- Retrieve the latest inventory snapshot for a store and product
- Review SKU inventory history across a date range
- List store snapshots for a region and date
- Explain current inventory, estimated daily demand, forecast variance, and competitor price gaps
- Highlight weather, season, category, and holiday context recorded in a snapshot
- Simulate a reorder quantity using inventory, daily demand, lead time, and target cover days
- Clearly state that every reorder is a draft and requires human approval

The reorder tool does **not** place or execute an order. It calculates a recommendation and marks it with `requires_human_approval: true`.

## How the application works

```text
User
  |
  v
Next.js frontend
  |
  v
FastAPI backend
  |
  v
Amazon Bedrock AgentCore Runtime
  |
  v
Amazon Bedrock AgentCore Gateway (MCP)
  |
  v
AWS Lambda MCP tools
  |
  v
Amazon DynamoDB
```

1. A user enters a request in the Next.js interface.
2. The FastAPI backend sends the prompt and session ID to the AgentCore runtime.
3. Claude, running through Amazon Bedrock, receives the prompt and connected MCP tools.
4. The agent chooses the appropriate Lambda-backed tool.
5. Lambda reads or calculates data in DynamoDB.
6. The agent explains the tool result and asks for clarification when required information is missing.

## Prerequisites

Before starting, make sure you have:

- An AWS account with permission to create DynamoDB tables, IAM roles, Lambda functions, AgentCore gateways, and AgentCore runtimes
- The AWS CLI, installed and configured
- Python 3.12 or later
- Node.js 18 or later and npm
- Bedrock model access for `us.anthropic.claude-haiku-4-5-20251001-v1:0`
- Amazon Bedrock AgentCore support in the selected AWS Region
- `us-east-1` as the Region for the commands in this guide

Check your AWS identity:

```bash
aws sts get-caller-identity
aws configure get region
```

Set the AWS Region explicitly:

```bash
export AWS_REGION=us-east-1
```

> The repository contains examples for AWS account `920375856513`. If you deploy to another account, replace the account IDs and resource names throughout `.env.example`, policy JSON files, and deployment scripts.

## Repository structure

```text
agent/       Bedrock AgentCore runtime agent and MCP client
backend/     FastAPI proxy used by the frontend
frontend/    Next.js chat interface
infra/       DynamoDB, IAM, MCP, and runtime policy examples
lambda/      DynamoDB-backed MCP tool implementation
```

## Deployment lesson

### Lesson 1 — Prepare the project

Clone the repository and enter its directory:

```bash
git clone https://github.com/Donaldnaz/retail_supply_chain_agent.git
cd retail_supply_chain_agent
```

Create a local environment file:

```bash
cp .env.example .env
```

Review `.env.example` and replace sample AWS resource values with values for your account when necessary.

### Lesson 2 — Create the DynamoDB table

Create the retail snapshot table:

```bash
bash infra/dynamodb-table.sh
```

This script creates `retail_supply_chain_snapshots` in `us-east-1`, configures the `region_date_index`, and inserts the sample SKU snapshot for `S001#P0001`.

Verify the table:

```bash
aws dynamodb describe-table \
  --table-name retail_supply_chain_snapshots \
  --region us-east-1
```

Verify the sample item:

```bash
aws dynamodb get-item \
  --table-name retail_supply_chain_snapshots \
  --key '{"store_product_key":{"S":"S001#P0001"},"snapshot_date":{"S":"2024-01-01"}}' \
  --region us-east-1
```

The sample item represents store `S001`, product `P0001`, region `East`, on `2024-01-01`.

### Lesson 3 — Create the Lambda execution role

Create the trust role from the supplied policy:

```bash
aws iam create-role \
  --role-name supply-chain-mcp-lambda-role \
  --assume-role-policy-document file://infra/lambda-trust-policy.json

aws iam attach-role-policy \
  --role-name supply-chain-mcp-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

Add DynamoDB read access:

```bash
aws iam put-role-policy \
  --role-name supply-chain-mcp-lambda-role \
  --policy-name DynamoDBReadAccess \
  --policy-document file://infra/dynamodb-tool-policy.json
```

Wait for the role to propagate before creating the Lambda function:

```bash
sleep 10
```

### Lesson 4 — Package and deploy the Lambda tools

Install the Lambda dependency and create a deployment archive:

```bash
python3.12 -m pip install -r lambda/requirements.txt -t lambda/package
cp lambda/lambda_function.py lambda/package/lambda_function.py
cd lambda/package
zip -r ../lambda.zip .
cd ../..
```

Get the role ARN:

```bash
LAMBDA_ROLE_ARN=$(aws iam get-role \
  --role-name supply-chain-mcp-lambda-role \
  --query 'Role.Arn' \
  --output text)
```

Create the function:

```bash
aws lambda create-function \
  --function-name retail-supply-chain-mcp-tools \
  --runtime python3.12 \
  --role "$LAMBDA_ROLE_ARN" \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda/lambda.zip \
  --region us-east-1
```

If the function already exists, update it instead:

```bash
aws lambda update-function-code \
  --function-name retail-supply-chain-mcp-tools \
  --zip-file fileb://lambda/lambda.zip \
  --region us-east-1
```

Set the table and Region environment variables:

```bash
aws lambda update-function-configuration \
  --function-name retail-supply-chain-mcp-tools \
  --environment 'Variables={TABLE_NAME=retail_supply_chain_snapshots,AWS_REGION=us-east-1}' \
  --region us-east-1
```

Test the latest-snapshot tool:

```bash
aws lambda invoke \
  --function-name retail-supply-chain-mcp-tools \
  --cli-binary-format raw-in-base64-out \
  --payload file://lambda/lambda-test-payload.json \
  response.json \
  --region us-east-1

cat response.json
```

### Lesson 5 — Create the MCP gateway

The gateway exposes the Lambda tool as MCP tools for the Bedrock agent.

Review and use the tool definitions in:

```text
infra/mcp-tool-schemas.json
```

Create the gateway using the MCP tool definitions and Lambda ARN through the Bedrock AgentCore console or AgentCore CLI. Connect these tools:

- `get_latest_sku_snapshot`
- `get_sku_history`
- `list_region_day_snapshots`
- `simulate_reorder_recommendation`

At the end of this lesson, copy the gateway MCP URL. It should resemble:

```text
https://retail-supply-chain-gateway-<id>.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp
```

Set it for the next steps:

```bash
export GATEWAY_MCP_URL="PASTE_YOUR_MCP_GATEWAY_URL"
```

### Lesson 6 — Install and deploy the AgentCore runtime

Create a Python virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r agent/requirements.txt
```

Configure the runtime:

```bash
cd agent
agentcore configure -e agent.py --region us-east-1
```

Deploy it:

```bash
agentcore deploy
agentcore status
cd ..
```

If deployment returns an ARN, copy it for the FastAPI backend:

```bash
export AGENT_RUNTIME_ARN="PASTE_YOUR_AGENT_RUNTIME_ARN"
```

### Lesson 7 — Run the FastAPI backend

Install backend dependencies:

```bash
python3.12 -m pip install -r backend/requirements.txt
```

Start the proxy:

```bash
AGENT_RUNTIME_ARN="$AGENT_RUNTIME_ARN" \
AWS_REGION=us-east-1 \
uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload
```

Keep this terminal running. In another terminal, test the health endpoint:

```bash
curl http://localhost:8000/api/health
```

Test a chat request. Replace `SESSION_ID` with at least 33 characters:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Get the latest snapshot for store S001 and product P0001","sessionId":"retail-supply-chain-session-123456789"}'
```

### Lesson 8 — Run the Next.js frontend

Open a third terminal and install the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

The browser stores a session ID locally and sends it with each prompt.

## Example questions

Try these prompts:

```text
What is the latest inventory for store S001 and product P0001?
```

```text
Show the SKU history for S001/P0001 from 2024-01-01 through 2024-01-31.
```

```text
List snapshot risk for the East region on 2024-01-01.
```

```text
Create a reorder draft for S001/P0001 with 7 cover days and a 3-day lead time.
```

For a reorder draft, inspect:

- Current inventory
- Estimated daily demand
- Projected stock at arrival
- Draft recommended order quantity
- `requires_human_approval: true`

## Safety and approval behavior

The reorder feature is intentionally non-executing:

- Lambda only calculates and returns a draft quantity.
- The agent must say that human approval is required.
- The frontend never calls a purchase or order API.
- Approve and Reject buttons send conversational prompts; they do not create an external purchase.

Do not remove these safeguards or present a draft quantity as an already placed order.

## Troubleshooting

### DynamoDB sample item is missing

Run:

```bash
bash infra/dynamodb-table.sh
```

Then retry the DynamoDB get-item command.

### Lambda cannot access DynamoDB

Confirm the IAM role has:

- `dynamodb:GetItem`
- `dynamodb:Query`
- `dynamodb:Scan`

Review `infra/dynamodb-tool-policy.json` and ensure its table ARN matches your account.

### AgentCore cannot reach the gateway

Confirm:

- `GATEWAY_MCP_URL` contains the `/mcp` path
- The MCP protocol version is `2025-11-25`
- The gateway tools use the deployed Lambda function
- The AgentCore runtime credentials allow gateway invocation

### Backend returns a 502 response

Check:

- `AGENT_RUNTIME_ARN` is the ARN of the deployed runtime
- AWS credentials are configured for the backend process
- The runtime and gateway are deployed in `us-east-1`
- CloudWatch Logs are enabled and inspected for runtime errors

### Frontend cannot reach the backend

Confirm the backend is listening on port `8000` and set the frontend API URL when needed:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Cleanup

Remove local files and stop local processes first. Then remove AWS resources in the reverse deployment order:

```bash
aws lambda delete-function --function-name retail-supply-chain-mcp-tools --region us-east-1
aws iam delete-role-policy --role-name supply-chain-mcp-lambda-role --policy-name DynamoDBReadAccess
aws iam detach-role-policy \
  --role-name supply-chain-mcp-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role --role-name supply-chain-mcp-lambda-role
aws dynamodb delete-table --table-name retail_supply_chain_snapshots --region us-east-1
```

Delete the AgentCore runtime and gateway from the Bedrock AgentCore console or CLI after confirming they are no longer needed.
