import os

import httpx
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from mcp.client.streamable_http import streamable_http_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient

GATEWAY_URL = os.getenv(
    "GATEWAY_MCP_URL",
    "https://retail-supply-chain-gateway-asuqt3yyrm.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
)
MCP_PROTOCOL_VERSION = os.getenv("MCP_PROTOCOL_VERSION", "2025-11-25")
MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

SYSTEM_PROMPT = """You are a retail supply chain operations assistant.
Use your connected MCP supply chain tools to inspect inventory levels, daily sales,
incoming orders, demand forecasts, pricing vs. competitors, weather, holidays,
and seasonality.

Rules:
1. Ground every metric, date, store ID, product ID, and region in tool outputs.
2. Explain stock risk, forecast variance (forecast_delta), and competitor price gaps clearly.
3. For reorder recommendations, always highlight the draft order quantity and explicitly state
   that execution requires human approval—never claim an order has been placed.
4. If required identifiers (such as store_id, product_id, region, or dates) are missing,
   ask a brief clarifying question or use the appropriate snapshot/history/region tool.
"""

app = BedrockAgentCoreApp()
model = BedrockModel(model_id=MODEL_ID, region_name=AWS_REGION)


def _create_mcp_client() -> MCPClient:
    def _transport_factory():
        http_client = httpx.AsyncClient(
            headers={
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
            },
            timeout=30.0,
        )
        return streamable_http_client(url=GATEWAY_URL, http_client=http_client)

    return MCPClient(_transport_factory)


@app.entrypoint
def invoke_supply_chain_agent(payload: dict):
    prompt = (payload or {}).get("prompt", "").strip()
    if not prompt:
        return {"error": "Missing 'prompt' in request payload."}

    mcp_client = _create_mcp_client()
    with mcp_client:
        tools = mcp_client.list_tools_sync()
        agent = Agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT)
        result = agent(prompt)

    response_text = result.message["content"][0]["text"]
    return {"response": response_text}


if __name__ == "__main__":
    app.run()
