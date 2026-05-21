"""
Historical price analysis service for Vietnamese stocks.
Analyzes trends, volatility, and patterns from past data.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import statistics
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.postgres import AsyncSessionLocal
from app.models.schema import HistoricalPrice


class HistoricalAnalyzer:
    """Analyzes historical price data to identify trends and patterns."""

    @staticmethod
    async def get_historical_prices(
        symbol: str,
        days: int = 60,
        session: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical prices for a stock.
        
        Args:
            symbol: Stock symbol (e.g., 'SSI')
            days: Number of days to fetch (default: 60)
            session: Database session
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        if session is None:
            async with AsyncSessionLocal() as session:
                return await HistoricalAnalyzer._fetch_prices_with_session(symbol, cutoff_date, session)

        return await HistoricalAnalyzer._fetch_prices_with_session(symbol, cutoff_date, session)

    @staticmethod
    async def _fetch_prices_with_session(symbol: str, cutoff_date: datetime, session: AsyncSession) -> List[Dict[str, Any]]:
        query = select(HistoricalPrice).where(
            HistoricalPrice.stock_symbol == symbol,
            HistoricalPrice.date >= cutoff_date,
        ).order_by(HistoricalPrice.date.asc())

        result = await session.execute(query)
        prices = result.scalars().all()

        return [
            {
                'date': p.date,
                'open': p.open_price,
                'high': p.high,
                'low': p.low,
                'close': p.close_price,
                'volume': p.volume,
            }
            for p in prices
        ]

    @staticmethod
    def calculate_trend(prices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trend direction and strength."""
        if len(prices) < 5:
            return {'direction': 'insufficient_data', 'strength': 0.0}

        closes = [p['close'] for p in prices]
        short_term = closes[-5:]  # Last 5 days
        long_term = closes[-20:] if len(closes) >= 20 else closes  # Last 20 days

        short_avg = statistics.mean(short_term)
        long_avg = statistics.mean(long_term)

        # Trend direction
        if short_avg > long_avg * 1.02:
            direction = 'uptrend'
        elif short_avg < long_avg * 0.98:
            direction = 'downtrend'
        else:
            direction = 'sideways'

        # Trend strength (0-1)
        price_range = max(closes) - min(closes)
        current_price = closes[-1]
        current_position = (current_price - min(closes)) / (price_range + 0.0001)
        strength = min(abs(short_avg - long_avg) / long_avg, 1.0)

        return {
            'direction': direction,
            'strength': round(strength, 3),
            'short_term_avg': round(short_avg, 2),
            'long_term_avg': round(long_avg, 2),
            'current_position': round(current_position, 3),
        }

    @staticmethod
    def calculate_volatility(prices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate historical volatility and ATR."""
        if len(prices) < 2:
            return {'volatility': 0.0, 'atr': 0.0, 'level': 'low'}

        closes = [p['close'] for p in prices]
        highs = [p['high'] for p in prices]
        lows = [p['low'] for p in prices]

        # Calculate daily returns
        returns = []
        for i in range(1, len(closes)):
            ret = (closes[i] - closes[i - 1]) / closes[i - 1]
            returns.append(ret)

        # Standard deviation of returns
        volatility = statistics.stdev(returns) if len(returns) > 1 else 0.0

        # Calculate ATR (Average True Range)
        true_ranges = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            true_ranges.append(tr)

        atr = statistics.mean(true_ranges) if true_ranges else 0.0
        atr_percent = (atr / closes[-1]) * 100 if closes[-1] > 0 else 0.0

        # Volatility level
        if volatility > 0.03:
            level = 'high'
        elif volatility > 0.015:
            level = 'medium'
        else:
            level = 'low'

        return {
            'volatility': round(volatility * 100, 3),  # As percentage
            'atr': round(atr, 2),
            'atr_percent': round(atr_percent, 2),
            'level': level,
        }

    @staticmethod
    def detect_support_resistance(prices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect support and resistance levels."""
        if len(prices) < 10:
            return {'support': None, 'resistance': None}

        closes = [p['close'] for p in prices]
        lows = [p['low'] for p in prices]
        highs = [p['high'] for p in prices]

        # Simple method: recent low = support, recent high = resistance
        recent_prices = closes[-20:]
        support = min(lows[-20:]) if len(lows) >= 20 else min(lows)
        resistance = max(highs[-20:]) if len(highs) >= 20 else max(highs)
        current = closes[-1]

        distance_to_support = ((current - support) / support * 100) if support > 0 else 0
        distance_to_resistance = ((resistance - current) / current * 100) if current > 0 else 0

        return {
            'support': round(support, 2),
            'resistance': round(resistance, 2),
            'current_price': round(current, 2),
            'distance_to_support_pct': round(distance_to_support, 2),
            'distance_to_resistance_pct': round(distance_to_resistance, 2),
            'support_strength': 'strong' if distance_to_support < 5 else 'weak',
        }

    @staticmethod
    def calculate_price_momentum(prices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate momentum indicators."""
        if len(prices) < 10:
            return {'momentum': 'insufficient_data', 'score': 0.0}

        closes = [p['close'] for p in prices]
        current = closes[-1]
        price_5d_ago = closes[-5] if len(closes) >= 5 else closes[0]
        price_10d_ago = closes[-10] if len(closes) >= 10 else closes[0]
        price_30d_ago = closes[-30] if len(closes) >= 30 else closes[0]

        # Calculate returns
        return_5d = ((current - price_5d_ago) / price_5d_ago * 100) if price_5d_ago > 0 else 0
        return_10d = ((current - price_10d_ago) / price_10d_ago * 100) if price_10d_ago > 0 else 0
        return_30d = ((current - price_30d_ago) / price_30d_ago * 100) if price_30d_ago > 0 else 0

        # Momentum score
        momentum_score = (return_5d + return_10d + return_30d) / 3 / 10  # Normalize
        momentum_score = max(-1.0, min(1.0, momentum_score))  # Clamp to [-1, 1]

        if momentum_score > 0.1:
            momentum = 'strong_bullish'
        elif momentum_score > 0.03:
            momentum = 'bullish'
        elif momentum_score > -0.03:
            momentum = 'neutral'
        elif momentum_score > -0.1:
            momentum = 'bearish'
        else:
            momentum = 'strong_bearish'

        return {
            'momentum': momentum,
            'score': round(momentum_score, 3),
            'return_5d': round(return_5d, 2),
            'return_10d': round(return_10d, 2),
            'return_30d': round(return_30d, 2),
        }

    @staticmethod
    def identify_overbought_oversold(prices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify overbought/oversold conditions based on price position."""
        if len(prices) < 10:
            return {'condition': 'insufficient_data', 'score': 0.0}

        closes = [p['close'] for p in prices]
        highs = [p['high'] for p in prices]
        lows = [p['low'] for p in prices]

        # Calculate normalized position (0-100)
        period = min(14, len(closes))
        highest = max(highs[-period:])
        lowest = min(lows[-period:])
        current = closes[-1]

        normalized = ((current - lowest) / (highest - lowest + 0.0001)) * 100 if (highest - lowest) > 0 else 50

        if normalized > 80:
            condition = 'overbought'
        elif normalized > 70:
            condition = 'overextended'
        elif normalized < 20:
            condition = 'oversold'
        elif normalized < 30:
            condition = 'underextended'
        else:
            condition = 'balanced'

        return {
            'condition': condition,
            'normalized_position': round(normalized, 2),
            'highest_14d': round(highest, 2),
            'lowest_14d': round(lowest, 2),
        }

    @staticmethod
    async def full_historical_analysis(symbol: str, days: int = 60) -> Dict[str, Any]:
        """Perform comprehensive historical analysis."""
        prices = await HistoricalAnalyzer.get_historical_prices(symbol, days)

        if not prices:
            return {'status': 'no_data', 'symbol': symbol}

        return {
            'symbol': symbol,
            'data_points': len(prices),
            'date_range': {
                'from': prices[0]['date'].isoformat() if prices else None,
                'to': prices[-1]['date'].isoformat() if prices else None,
            },
            'trend': HistoricalAnalyzer.calculate_trend(prices),
            'volatility': HistoricalAnalyzer.calculate_volatility(prices),
            'support_resistance': HistoricalAnalyzer.detect_support_resistance(prices),
            'momentum': HistoricalAnalyzer.calculate_price_momentum(prices),
            'overbought_oversold': HistoricalAnalyzer.identify_overbought_oversold(prices),
        }

    @staticmethod
    async def snapshot_movers_from_db(
        limit: int = 8,
        symbols: Optional[List[str]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Top gainers/losers từ 2 nến đóng gần nhất (batch query, không quét toàn DB).
        """
        from app.services.stock_ingest import DEFAULT_WATCHLIST, batch_ohlc_day_pct

        syms = symbols or list(DEFAULT_WATCHLIST)
        hist = await batch_ohlc_day_pct(syms)

        movers: List[Dict[str, Any]] = []
        for sym, row in hist.items():
            pct = float(row.get('pct') or 0)
            c0 = float(row.get('close') or 0)
            c1 = row.get('prev_close')
            if c0 <= 0:
                continue
            sig = 'bull' if pct > 0.05 else ('bear' if pct < -0.05 else 'flat')
            sig_vi = 'Tích cực' if sig == 'bull' else ('Tiêu cực' if sig == 'bear' else 'Trung lập')
            movers.append(
                {
                    'symbol': sym,
                    'change': pct,
                    'change_pct': pct,
                    'last_close': round(c0, 2),
                    'prev_close': round(float(c1), 2) if c1 is not None else None,
                    'trading_date': row.get('trading_date'),
                    'signal': sig,
                    'signal_vi': sig_vi,
                }
            )

        movers.sort(key=lambda x: x['change'], reverse=True)
        gainers = movers[:limit]
        losers_sorted = sorted(movers, key=lambda x: x['change'])
        losers = losers_sorted[:limit]
        return gainers, losers

    @staticmethod
    async def last_close_and_day_pct(symbol: str, days: int = 5) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        prices = await HistoricalAnalyzer.get_historical_prices(symbol, days=days)
        if not prices:
            return None, None, None
        last = prices[-1]
        c = float(last['close'])
        date_s = last['date'].isoformat()[:10] if hasattr(last['date'], 'isoformat') else str(last['date'])[:10]
        if len(prices) < 2:
            return c, 0.0, date_s
        p = float(prices[-2]['close'])
        if p <= 0:
            return c, 0.0, date_s
        pct = round(((c - p) / p) * 100, 4)
        return c, pct, date_s

    @staticmethod
    async def sparkline_series(symbol: str, n: int = 7) -> List[Dict[str, Any]]:
        """Last n closes as chart points (time labels illustrative)."""
        prices = await HistoricalAnalyzer.get_historical_prices(symbol, days=max(20, n + 3))
        if len(prices) < 2:
            return []
        tail = prices[-n:]
        slots = ['09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00']
        out: List[Dict[str, Any]] = []
        for i, p in enumerate(tail):
            label = slots[i] if i < len(slots) else f'T+{i}'
            out.append({'name': label, 'value': round(float(p['close']), 2)})
        return out


# Singleton instance
historical_analyzer = HistoricalAnalyzer()
