from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.agent_orchestrator import orchestrator

router = APIRouter()


@router.post('/agents/{symbol}/run')
async def run_agents(symbol: str):
    result = await orchestrator.run_stock_pipeline(symbol.upper())
    return JSONResponse(result)


@router.get('/agents/debate/{symbol}')
async def get_debate(symbol: str):
    debates = [
        {'agent': 'TechnicalAnalyst', 'message': 'Strong momentum on EMA crossover', 'confidence': 0.81},
        {'agent': 'FundamentalAnalyst', 'message': 'Healthy ROE and stable debt', 'confidence': 0.68},
        {'agent': 'RiskManager', 'message': 'Volatility medium, recommend 3% stop loss', 'confidence': 0.64},
    ]
    return JSONResponse({'symbol': symbol.upper(), 'debate': debates})
