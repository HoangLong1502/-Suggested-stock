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
    result = await orchestrator.run_stock_pipeline(symbol.upper())
    debate = [
        {
            'agent': agent['agent'],
            'message': agent.get('rationale', ''),
            'confidence': round(agent.get('score', 0.0), 2),
        }
        for agent in result.get('agents', [])
    ]
    return JSONResponse({'symbol': symbol.upper(), 'debate': debate, 'decision': result.get('decision', {})})
