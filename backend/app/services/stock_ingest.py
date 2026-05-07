import asyncio
from datetime import datetime
from typing import Any, Dict, List

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import Stock
from app.models.postgres import AsyncSessionLocal


VN_INDEX_SYMBOLS = ['VNINDEX', 'HNX', 'UPCOM']
DEFAULT_WATCHLIST = ['SSI', 'VNM', 'VCB', 'FPT', 'MWG', 'VHM', 'PNJ', 'HPG', 'TPB', 'ACB', 'BVH', 'MSN', 'NVL', 'GAS']


async def fetch_market_data() -> List[Dict[str, Any]]:
    url = 'https://finfo-api.vndirect.com.vn/v4/stock_prices?date=' + datetime.utcnow().strftime('%Y%m%d')
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict) and payload.get('data'):
                return payload['data'][:50]
        except Exception:
            return []
    return []


async def sync_market_snapshot() -> None:
    rows = await fetch_market_data()
    async with AsyncSessionLocal() as session:
        for row in rows:
            symbol = row.get('symbol') or row.get('code')
            if not symbol:
                continue
            query = await session.execute(
                Stock.__table__.select().where(Stock.symbol == symbol),
            )
            existing = query.scalar_one_or_none()
            values = {
                'symbol': symbol,
                'name': row.get('name', symbol),
                'exchange': row.get('exchange', 'VN'),
                'last_price': float(row.get('close', 0.0) or 0.0),
                'change': float(row.get('change', 0.0) or 0.0),
                'volume': float(row.get('totalVolume', 0.0) or 0.0),
                'metadata': row,
            }
            if existing:
                await session.execute(
                    Stock.__table__.update().where(Stock.id == existing.id).values(**values),
                )
            else:
                session.add(Stock(**values))
        await session.commit()


async def load_watchlist_symbols() -> List[str]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(Stock.__table__.select().limit(20))
        rows = result.fetchall()
        symbols = [row[0].symbol for row in rows]
        return symbols if symbols else DEFAULT_WATCHLIST


async def load_watchlist_items() -> List[Dict[str, Any]]:
    symbols = await load_watchlist_symbols()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Stock).where(Stock.symbol.in_(symbols)))
        stocks = result.scalars().all()

    stock_map = {stock.symbol: stock for stock in stocks}
    return [
        {
            'symbol': symbol,
            'price': float(stock_map[symbol].last_price or 0.0) if symbol in stock_map else 0.0,
            'change': float(stock_map[symbol].change or 0.0) if symbol in stock_map else 0.0,
        }
        for symbol in symbols
    ]


async def periodic_market_sync() -> None:
    while True:
        try:
            await sync_market_snapshot()
        except Exception:
            pass
        await asyncio.sleep(180)
