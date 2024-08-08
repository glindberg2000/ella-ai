import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import asyncio
import json
from typing import AsyncGenerator

vapi_app = FastAPI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = "https://api.openai.com/v1/chat/completions"

async def stream_openai_response(messages: list) -> AsyncGenerator[str, None]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            OPENAI_API_BASE,
            json={
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "stream": True,
            },
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=None,
            stream=True,
        )
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                yield line + "\n\n"

@vapi_app.get("/vapi/test")
async def test_endpoint():
    return {"message": "Hello, Vapi world!"}

@vapi_app.post("/vapi/chat/completions")
async def chat_completions(request: Request):
    try:
        data = await request.json()
        messages = data.get("messages", [])
        
        return StreamingResponse(
            stream_openai_response(messages),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(vapi_app, host="0.0.0.0", port=9090)