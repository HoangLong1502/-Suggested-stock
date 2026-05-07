from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.stock_ingest import load_watchlist_items, sync_market_snapshot
from app.services.agent_orchestrator import orchestrator

router = APIRouter()


@router.get('/market/overview')
async def market_overview():
    await sync_market_snapshot()
    watchlist_items = await load_watchlist_items()
    return JSONResponse(
        {
            'indices': [
                {'symbol': 'VNINDEX', 'price': 1200.45, 'change': 0.72},
                {'symbol': 'HNX', 'price': 310.12, 'change': -0.18},
                {'symbol': 'UPCOM', 'price': 82.92, 'change': 0.15},
            ],
            'watchlist': watchlist_items,
            'top_gainers': [
                {'symbol': 'VNM', 'change': 4.5},
                {'symbol': 'SSI', 'change': 3.8},
            ],
            'top_losers': [
                {'symbol': 'AAA', 'change': -5.4},
                {'symbol': 'XYZ', 'change': -3.2},
            ],
            'sector_heatmap': [
                {'sector': 'Banking', 'strength': 0.7},
                {'sector': 'Real Estate', 'strength': 0.3},
            ],
        }
    )


@router.get('/stock/{symbol}')
async def stock_detail(symbol: str):
    return JSONResponse(
        {
            'symbol': symbol.upper(),
            'company_name': 'Sample Corp',
            'last_price': 12.34,
            'change': 1.12,
            'volume': 1580000,
            'indicators': {
                'rsi': 64.2,
                'macd': 0.45,
                'ema_20': 11.9,
                'bollinger': {'lower': 10.1, 'upper': 13.0},
            },
            'fundamentals': {
                'pe': 12.4,
                'pb': 1.6,
                'roe': 18.2,
                'debt_to_equity': 0.4,
            },
            'news': [
                {'title': 'Sample headline about the stock', 'sentiment': 'positive'},
            ],
        }
    )


@router.get('/agents/{symbol}/recommendation')
async def recommendation(symbol: str):
    payload = await orchestrator.run_stock_pipeline(symbol.upper())
    return JSONResponse(payload)
