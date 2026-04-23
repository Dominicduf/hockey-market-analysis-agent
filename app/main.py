import logging

from fastapi import FastAPI, HTTPException

from app.agent import agent
from app.schemas import QueryRequest, QueryResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(
    title="Market Analysis Agent",
    description="AI-powered market analysis using LangGraph and OpenRouter",
    version="0.1.0",
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=QueryResponse)
async def analyze(request: QueryRequest):
    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": request.query}]}
        )
        return QueryResponse(response=result["messages"][-1].content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
