import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.agents import router as agent_router
from app.api.v1.routes import router as market_router
from app.models.schema import Base
from app.models.postgres import engine
from app.services.demo_seed import ensure_demo_historical_data, ensure_watchlist_historical_gaps
from app.services.market_ws import register as ws_register, unregister as ws_unregister
from app.services.stock_ingest import ensure_default_watchlist, periodic_market_sync

app = FastAPI(title='BotTrading AI Stock Platform')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(market_router, prefix='/api/v1')
app.include_router(agent_router, prefix='/api/v1')

async def _wait_for_database(max_attempts: int = 30, delay_sec: float = 1.0) -> None:
    """Postgres/DNS có thể chưa sẵn sàng ngay khi container backend start (đặc biệt trên Windows)."""
    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            async with engine.begin() as conn:
                await conn.execute(text('SELECT 1'))
            return
        except Exception as exc:
            last_err = exc
            if attempt < max_attempts:
                await asyncio.sleep(delay_sec)
    raise RuntimeError(f'Database not reachable after {max_attempts} attempts') from last_err


@app.on_event('startup')
async def startup_event():
    await _wait_for_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text("ALTER TABLE historical_prices ADD COLUMN IF NOT EXISTS data_metadata JSON DEFAULT '{}'"
            )
        )
    await ensure_demo_historical_data()
    await ensure_watchlist_historical_gaps()
    await ensure_default_watchlist()

    async def _bootstrap_sync() -> None:
        await asyncio.sleep(1)
        try:
            from app.services.stock_ingest import sync_market_snapshot

            await sync_market_snapshot()
        except Exception:
            pass

    _ = asyncio.create_task(_bootstrap_sync())
    _ = asyncio.create_task(periodic_market_sync())


@app.get('/')
async def root():
    return JSONResponse({'service': 'BotTrading AI backend', 'status': 'running'})


@app.websocket('/ws/market')
async def websocket_endpoint(websocket: WebSocket):
    await ws_register(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == 'ping':
                await websocket.send_json({'type': 'pong'})
    except WebSocketDisconnect:
        await ws_unregister(websocket)
    except Exception:
        await ws_unregister(websocket)
