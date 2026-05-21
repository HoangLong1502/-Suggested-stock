"""
Data initialization script for populating sample historical prices.
Run manually: python -m scripts.init_data (from backend dir with PYTHONPATH).
"""
import asyncio
from datetime import datetime, timedelta
import random
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.schema import Base, Stock, HistoricalPrice
from app.core.config import settings


async def init_sample_data():
    """Initialize sample historical price data."""

    engine = create_async_engine(str(settings.database_url), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.services.stock_ingest import DEFAULT_WATCHLIST

    watchlist = [{'symbol': sym, 'name': sym, 'exchange': 'HOSE'} for sym in DEFAULT_WATCHLIST]

    async with async_session() as session:
        for stock_info in watchlist:
            sym = stock_info['symbol']
            res = await session.execute(select(Stock).where(Stock.symbol == sym))
            existing = res.scalar_one_or_none()
            if existing is None:
                session.add(
                    Stock(
                        symbol=sym,
                        name=stock_info['name'],
                        exchange=stock_info['exchange'],
                        last_price=0.0,
                        change=0.0,
                        volume=0.0,
                    )
                )

        await session.commit()

        rng = random.Random(2024)
        now = datetime.utcnow()

        for stock_info in watchlist:
            symbol = stock_info['symbol']
            base = 18.0 + (sum(ord(c) for c in symbol) % 70)
            close_p = base

            for i in range(60, 0, -1):
                date = now - timedelta(days=i)
                drift = rng.uniform(-0.025, 0.03)
                o = close_p
                close_p = max(1.0, round(o * (1 + drift), 2))
                high = max(o, close_p) * rng.uniform(1.0, 1.03)
                low = min(o, close_p) * rng.uniform(0.97, 1.0)
                volume = float(rng.randint(100000, 5000000))

                session.add(
                    HistoricalPrice(
                        stock_symbol=symbol,
                        date=date,
                        open_price=round(o, 2),
                        high=round(high, 2),
                        low=round(low, 2),
                        close_price=close_p,
                        volume=volume,
                        data_metadata={'source': 'sample_data'},
                    )
                )

            await session.commit()
            print(f'✓ Added 60 days of historical data for {symbol}')

    print('\n✓ Data initialization complete!')


if __name__ == '__main__':
    asyncio.run(init_sample_data())
