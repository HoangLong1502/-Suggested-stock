"""
Seed synthetic OHLC when the database has no historical rows (Docker / offline).
Lets agents and charts work without external APIs.
"""
import random
from datetime import datetime, timedelta

from sqlalchemy import select

from app.models.postgres import AsyncSessionLocal
from app.models.schema import HistoricalPrice, Stock


DEFAULT_SEED_SYMBOLS = [
    'SSI', 'VNM', 'VCB', 'FPT', 'MWG', 'VHM', 'PNJ', 'HPG', 'TPB', 'ACB', 'BVH', 'MSN', 'NVL', 'GAS',
    'VNINDEX', 'HNX', 'UPCOM',
]


async def ensure_demo_historical_data(days: int = 60) -> bool:
    """
    If historical_prices is empty, insert demo series per symbol.
    Returns True if seeding ran.
    """
    async with AsyncSessionLocal() as session:
        has_any = await session.scalar(select(HistoricalPrice.id).limit(1))
        if has_any is not None:
            return False

        rng = random.Random(42)
        now = datetime.utcnow()

        for sym in DEFAULT_SEED_SYMBOLS:
            seed = sum(ord(c) for c in sym) % 97 + 3
            prev_close = float(15 + (seed % 80))
            closes: list[float] = []

            for i in range(days, 0, -1):
                day = now - timedelta(days=i)
                drift = rng.uniform(-0.028, 0.03)
                o = prev_close
                c = max(1.0, round(o * (1 + drift), 2))
                hi = max(o, c) * rng.uniform(1.0, 1.02)
                lo = min(o, c) * rng.uniform(0.98, 1.0)
                vol = float(rng.randint(200_000, 4_000_000))
                session.add(
                    HistoricalPrice(
                        stock_symbol=sym,
                        date=day,
                        open_price=round(o, 2),
                        high=round(hi, 2),
                        low=round(lo, 2),
                        close_price=c,
                        volume=vol,
                        data_metadata={'source': 'demo_seed'},
                    )
                )
                closes.append(c)
                prev_close = c

            day_pct = (
                round(((closes[-1] - closes[-2]) / closes[-2]) * 100, 2) if len(closes) >= 2 else 0.0
            )
            last_vol = float(rng.randint(200_000, 4_000_000))

            existing = await session.execute(select(Stock).where(Stock.symbol == sym))
            st = existing.scalar_one_or_none()
            if st is None:
                session.add(
                    Stock(
                        symbol=sym,
                        name=sym,
                        exchange='VN',
                        last_price=closes[-1],
                        change=day_pct,
                        volume=last_vol,
                        stock_metadata={'source': 'demo_seed', 'demo': True},
                    )
                )
            else:
                st.last_price = closes[-1]
                st.change = day_pct
                st.volume = last_vol

        await session.commit()
    return True
