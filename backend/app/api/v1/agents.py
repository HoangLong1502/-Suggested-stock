from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.agent_orchestrator import orchestrator
from app.services.stock_ingest import load_watchlist_symbols

router = APIRouter()


@router.post('/agents/{symbol}/run')
async def run_agents(symbol: str):
    result = await orchestrator.run_stock_pipeline(symbol.upper())
    return JSONResponse(result)


@router.get('/agents/suggest')
async def suggest_stock():
    symbols = await load_watchlist_symbols()
    best_result = None
    best_score = -1.0

    for symbol in symbols[:8]:
        try:
            result = await orchestrator.run_stock_pipeline(symbol.upper())
            decision = result.get('decision', {})
            score = float(decision.get('score', 0.0))
            if score > best_score:
                best_score = score
                best_result = result
        except Exception:
            continue

    return JSONResponse({'suggested': best_result})


@router.get('/agents/debate/{symbol}')
async def get_debate(symbol: str):
    try:
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
    except Exception:
        return JSONResponse({'symbol': symbol.upper(), 'debate': [], 'decision': None})
