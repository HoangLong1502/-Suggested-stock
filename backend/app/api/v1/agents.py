from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.agent_orchestrator import orchestrator

router = APIRouter()


@router.post('/agents/{symbol}/run')
async def run_agents(symbol: str):
    result = await orchestrator.run_stock_pipeline(symbol.upper())
    return JSONResponse(result)
