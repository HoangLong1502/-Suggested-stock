import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.agents import router as agent_router
from app.api.v1.routes import router as market_router
from app.models.schema import Base
from app.models.postgres import engine
from app.services.agent_orchestrator import orchestrator
from app.services.stock_ingest import periodic_market_sync

app = FastAPI(title='BotTrading AI Stock Platform')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(market_router, prefix='/api/v1')
app.include_router(agent_router, prefix='/api/v1')

connected_websockets: list[WebSocket] = []


@app.on_event('startup')
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _ = asyncio.create_task(periodic_market_sync())


@app.get('/')
async def root():
    return JSONResponse({'service': 'BotTrading AI backend', 'status': 'running'})


@app.websocket('/ws/market')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == 'ping':
                await websocket.send_json({'type': 'pong'})
    except WebSocketDisconnect:
        connected_websockets.remove(websocket)
