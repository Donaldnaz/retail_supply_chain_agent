import os

import boto3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AGENT_RUNTIME_ARN = os.getenv(
    "AGENT_RUNTIME_ARN",
    "arn:aws:bedrock-agentcore:us-east-1:920375856513:runtime/retail_supply_chain_agent-BjapTXB2zw",
)

app = FastAPI(title="Retail Supply Chain Operations Proxy")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

agentcore = boto3.client("bedrock-agentcore", region_name=AWS_REGION)


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    sessionId: str = Field(..., min_length=33)


@app.get("/api/health")
def health():
    return {"status": "ok", "runtime": AGENT_RUNTIME_ARN}


@app.post("/api/chat")
def chat(request: ChatRequest):
    if len(request.sessionId) < 33:
        raise HTTPException(status_code=400, detail="runtimeSessionId must be at least 33 characters")

    try:
        response = agentcore.invoke_agent_runtime(
            agentRuntimeArn=AGENT_RUNTIME_ARN,
            runtimeSessionId=request.sessionId,
            payload=request.prompt.encode("utf-8"),
        )
        body = response.get("response")
        if hasattr(body, "read"):
            body = body.read()
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        return {"response": body, "sessionId": request.sessionId}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AgentCore invocation failed: {exc}") from exc


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
