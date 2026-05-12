from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Text, Boolean
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Stock(Base):
    __tablename__ = 'stocks'

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(32), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=True)
    exchange = Column(String(32), nullable=True)
    last_price = Column(Float, nullable=True)
    change = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    stock_metadata = Column(JSON, default={})
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentMessage(Base):
    __tablename__ = 'agent_messages'

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(64), nullable=False)
    stock_symbol = Column(String(32), nullable=False)
    message = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    payload = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)


class Recommendation(Base):
    __tablename__ = 'recommendations'

    id = Column(Integer, primary_key=True, index=True)
    stock_symbol = Column(String(32), nullable=False)
    action = Column(String(16), nullable=False)
    score = Column(Float, nullable=False)
    rationale = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)


class Watchlist(Base):
    __tablename__ = 'watchlists'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), nullable=False)
    symbols = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)


class TradeHistory(Base):
    __tablename__ = 'trade_history'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), nullable=False)
    stock_symbol = Column(String(32), nullable=False)
    action = Column(String(16), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class HistoricalPrice(Base):
    __tablename__ = 'historical_prices'

    id = Column(Integer, primary_key=True, index=True)
    stock_symbol = Column(String(32), index=True, nullable=False)
    date = Column(DateTime, index=True, nullable=False)
    open_price = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    data_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)


class CompanyFundamental(Base):
    __tablename__ = 'company_fundamentals'

    id = Column(Integer, primary_key=True, index=True)
    stock_symbol = Column(String(32), unique=True, index=True, nullable=False)
    company_name = Column(String(256), nullable=True)
    sector = Column(String(64), nullable=True)
    industry = Column(String(64), nullable=True)
    
    # Financial metrics
    pe_ratio = Column(Float, nullable=True)
    pb_ratio = Column(Float, nullable=True)
    roe = Column(Float, nullable=True)  # Return on Equity
    roa = Column(Float, nullable=True)  # Return on Assets
    debt_to_equity = Column(Float, nullable=True)
    current_ratio = Column(Float, nullable=True)
    quick_ratio = Column(Float, nullable=True)
    
    # Growth metrics
    revenue_growth_yoy = Column(Float, nullable=True)  # Year-over-Year
    profit_growth_yoy = Column(Float, nullable=True)
    revenue_growth_qoq = Column(Float, nullable=True)  # Quarter-over-Quarter
    profit_growth_qoq = Column(Float, nullable=True)
    
    # Market cap
    market_cap = Column(Float, nullable=True)
    earnings_per_share = Column(Float, nullable=True)
    
    # Other metrics
    dividend_yield = Column(Float, nullable=True)
    insider_ownership = Column(Float, nullable=True)
    analyst_rating = Column(String(32), nullable=True)
    
    # Metadata
    data_source = Column(String(64), default='vnstock')
    last_updated = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TechnicalIndicator(Base):
    __tablename__ = 'technical_indicators'

    id = Column(Integer, primary_key=True, index=True)
    stock_symbol = Column(String(32), index=True, nullable=False)
    date = Column(DateTime, index=True, nullable=False)
    
    # Momentum indicators
    rsi_14 = Column(Float, nullable=True)
    macd_value = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_histogram = Column(Float, nullable=True)
    
    # Trend indicators
    ema_20 = Column(Float, nullable=True)
    ema_50 = Column(Float, nullable=True)
    ema_200 = Column(Float, nullable=True)
    sma_20 = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    
    # Volatility indicators
    bollinger_upper = Column(Float, nullable=True)
    bollinger_middle = Column(Float, nullable=True)
    bollinger_lower = Column(Float, nullable=True)
    atr = Column(Float, nullable=True)  # Average True Range
    
    # Volume
    volume_sma = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)
    
    data_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
