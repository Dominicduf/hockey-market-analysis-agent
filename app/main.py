import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langgraph.errors import GraphRecursionError
from openai import APIStatusError, RateLimitError

from app.agent import agent
from app.config import settings
from app.schemas import QueryRequest, QueryResponse

REPORTS_DIR = Path(__file__).parent.parent / "reports"
STATIC_DIR = Path(__file__).parent.parent / "static"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(
    title="Market Analysis Agent",
    description="Market analysis using LangGraph and OpenRouter",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/reports/{filename}")
async def download_report(filename: str):
    file_path = REPORTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Report '{filename}' not found.")
    return FileResponse(path=str(file_path), media_type="application/pdf", filename=filename)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=QueryResponse)
async def analyze(request: QueryRequest):
    try:
        result = await asyncio.wait_for(
            agent.ainvoke(
                {"messages": [{"role": "user", "content": request.query}]},
                config={"recursion_limit": settings.max_recursion},
            ),
            timeout=settings.agent_timeout,
        )
        return QueryResponse(response=result["messages"][-1].content)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Analysis timed out. Please try again.")
    except RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limit reached. Please try again later.")
    except APIStatusError as e:
        raise HTTPException(status_code=e.status_code, detail=f"LLM provider error: {e.message}")
    except GraphRecursionError:
        raise HTTPException(
            status_code=500, detail="Agent exceeded maximum steps. Please try a simpler query."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
