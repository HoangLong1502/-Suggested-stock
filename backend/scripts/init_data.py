"""
Data initialization script for populating sample historical prices.
Run this after starting the database.
"""
import asyncio
from datetime import datetime, timedelta
import random
import sys

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

    # Sample stocks
    watchlist = [
        {'symbol': 'SSI', 'name': 'Sài Gòn Securities', 'exchange': 'HOSE'},
        {'symbol': 'VNM', 'name': 'Vinamilk', 'exchange': 'HOSE'},
        {'symbol': 'VCB', 'name': 'Vietcombank', 'exchange': 'HOSE'},
        {'symbol': 'FPT', 'name': 'FPT Corporation', 'exchange': 'HOSE'},
        {'symbol': 'MWG', 'name': 'Mobile World', 'exchange': 'HOSE'},
        {'symbol': 'VHM', 'name': 'Vinhomes', 'exchange': 'HOSE'},
        {'symbol': 'PNJ', 'name': 'PNJ', 'exchange': 'HOSE'},
        {'symbol': 'HPG', 'name': 'Hoa Phat Group', 'exchange': 'HOSE'},
        {'symbol': 'TPB', 'name': 'Techcombank', 'exchange': 'HOSE'},
        {'symbol': 'ACB', 'name': 'Asia Commercial Bank', 'exchange': 'HOSE'},
    ]

    async with async_session() as session:
        # Add stocks
        for stock_info in watchlist:
            existing = await session.get(Stock, stock_info['symbol'])
            if not existing:
                stock = Stock(**stock_info)
                session.add(stock)

        await session.commit()

        # Add historical price data for last 60 days
        now = datetime.utcnow()
        
        for stock_info in watchlist:
            symbol = stock_info['symbol']
            
            # Generate 60 days of historical prices
            for i in range(60, 0, -1):
                date = now - timedelta(days=i)
                
                # Generate realistic price movement
                base_price = random.uniform(10, 100)
                daily_change = random.uniform(-2, 3)  # -2% to +3%
                
                open_price = base_price
                close_price = base_price * (1 + daily_change / 100)
                high = max(open_price, close_price) * random.uniform(1.00, 1.03)
                low = min(open_price, close_price) * random.uniform(0.97, 1.00)
                volume = random.randint(100000, 5000000)
                
                historical_price = HistoricalPrice(
                    stock_symbol=symbol,
                    date=date,
                    open_price=round(open_price, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close_price=round(close_price, 2),
                    volume=volume,
                    metadata={'source': 'sample_data'},
                )
                session.add(historical_price)

            await session.commit()
            print(f'✓ Added 60 days of historical data for {symbol}')

    print('\n✓ Data initialization complete!')


if __name__ == '__main__':
    asyncio.run(init_sample_data())
