"""WebSocket push giá — client không cần reload trang."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from fastapi import WebSocket

from app.services.stock_ingest import (
    VN_INDEX_SYMBOLS,
    load_watchlist_items,
    vietnam_market_session,
)
from app.models.postgres import AsyncSessionLocal
from app.models.schema import Stock
from sqlalchemy import select

_connections: Set[WebSocket] = set()
_lock = asyncio.Lock()


def _signal_tags(pct: float) -> tuple[str, str]:
    if pct > 0.05:
        return 'bull', 'Tích cực'
    if pct < -0.05:
        return 'bear', 'Tiêu cực'
    return 'flat', 'Trung lập'


def _movers_from_watchlist(items: List[Dict[str, Any]], limit: int = 8) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    for it in items:
        sym = str(it.get('symbol', '')).upper()
        if not sym:
            continue
        ch = float(it.get('change_pct') or it.get('change') or 0)
        price = float(it.get('price') or 0)
        sig, sig_vi = _signal_tags(ch)
        rows.append(
            {
                'symbol': sym,
                'change': ch,
                'change_pct': ch,
                'last_close': round(price, 2) if price > 0 else None,
                'signal': sig,
                'signal_vi': sig_vi,
            },
        )
    rows.sort(key=lambda x: x['change'], reverse=True)
    gainers = rows[:limit]
    losers = sorted(rows, key=lambda x: x['change'])[:limit]
    return gainers, losers


async def build_market_push_payload() -> Dict[str, Any]:
    watchlist = await load_watchlist_items(skip_sync=True)
    top_gainers, top_losers = _movers_from_watchlist(watchlist)

    indices: List[Dict[str, Any]] = []
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Stock).where(Stock.symbol.in_(VN_INDEX_SYMBOLS)))
        stock_map = {str(s.symbol).strip().upper(): s for s in res.scalars().all()}
    for symbol in VN_INDEX_SYMBOLS:
        st = stock_map.get(symbol)
        if st is not None:
            indices.append(
                {
                    'symbol': symbol,
                    'price': float(st.last_price or 0.0),
                    'change': float(st.change or 0.0),
                },
            )
        else:
            indices.append({'symbol': symbol, 'price': 0.0, 'change': 0.0})

    return {
        'type': 'market_update',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'watchlist': watchlist,
        'indices': indices,
        'top_gainers': top_gainers,
        'top_losers': top_losers,
        'market_session': vietnam_market_session(),
    }


async def register(websocket: WebSocket) -> None:
    await websocket.accept()
    async with _lock:
        _connections.add(websocket)
    try:
        await websocket.send_json(await build_market_push_payload())
    except Exception:
        pass


async def unregister(websocket: WebSocket) -> None:
    async with _lock:
        _connections.discard(websocket)


async def broadcast_market_update() -> None:
    if not _connections:
        return
    payload = await build_market_push_payload()
    async with _lock:
        targets = list(_connections)
    dead: List[WebSocket] = []
    for ws in targets:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    if dead:
        async with _lock:
            for ws in dead:
                _connections.discard(ws)


async def notify_market_update() -> None:
    """Gọi sau mỗi lần sync giá — không chặn pipeline sync."""
    try:
        await broadcast_market_update()
    except Exception:
        pass
