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
