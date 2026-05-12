"""
Technical Indicator Calculator for Vietnamese Stocks.
Calculates RSI, MACD, EMA, Bollinger Bands, etc.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import statistics

from app.models.schema import HistoricalPrice


class TechnicalCalculator:
    """Calculates technical indicators from price data."""

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Dict[str, float]:
        """
        Calculate Relative Strength Index (RSI).
        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss
        """
        if len(prices) < period + 1:
            return {'rsi': 50.0, 'signal': 'neutral'}

        gains = []
        losses = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = statistics.mean(gains[-period:])
        avg_loss = statistics.mean(losses[-period:])

        rs = avg_gain / (avg_loss + 0.0001)
        rsi = 100 - (100 / (1 + rs))

        # Signal
        if rsi > 70:
            signal = 'overbought'
        elif rsi > 60:
            signal = 'strong_bullish'
        elif rsi > 50:
            signal = 'bullish'
        elif rsi > 40:
            signal = 'bearish'
        elif rsi > 30:
            signal = 'strong_bearish'
        else:
            signal = 'oversold'

        return {
            'rsi': round(rsi, 2),
            'signal': signal,
            'avg_gain': round(avg_gain, 4),
            'avg_loss': round(avg_loss, 4),
        }

    @staticmethod
    def calculate_macd(prices: List[float]) -> Dict[str, Any]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        MACD = EMA12 - EMA26
        Signal = EMA9 of MACD
        Histogram = MACD - Signal
        """
        if len(prices) < 26:
            return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0, 'status': 'insufficient_data'}

        ema12 = TechnicalCalculator._calculate_ema(prices, 12)
        ema26 = TechnicalCalculator._calculate_ema(prices, 26)

        macd_line = ema12 - ema26

        # Calculate signal line (EMA9 of MACD values)
        macd_values = []
        for i in range(26 - 1, len(prices)):
            ema12_val = TechnicalCalculator._calculate_ema(prices[:i+1], 12)
            ema26_val = TechnicalCalculator._calculate_ema(prices[:i+1], 26)
            macd_values.append(ema12_val - ema26_val)

        signal_line = TechnicalCalculator._calculate_ema(macd_values, 9) if len(macd_values) >= 9 else macd_line
        histogram = macd_line - signal_line

        # Signal
        if histogram > 0 and macd_line > signal_line:
            signal = 'bullish_cross'
        elif histogram < 0 and macd_line < signal_line:
            signal = 'bearish_cross'
        elif macd_line > signal_line:
            signal = 'bullish'
        else:
            signal = 'bearish'

        return {
            'macd': round(macd_line, 4),
            'signal': round(signal_line, 4),
            'histogram': round(histogram, 4),
            'crossover_signal': signal,
        }

    @staticmethod
    def _calculate_ema(prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return statistics.mean(prices)

        sma = statistics.mean(prices[-period:])
        multiplier = 2 / (period + 1)

        ema = sma
        for price in prices[-period:]:
            ema = price * multiplier + ema * (1 - multiplier)

        return ema

    @staticmethod
    def calculate_ema(prices: List[float], periods: List[int] = [20, 50, 200]) -> Dict[str, float]:
        """Calculate multiple EMAs."""
        result = {}
        for period in periods:
            if len(prices) >= period:
                result[f'ema_{period}'] = round(
                    TechnicalCalculator._calculate_ema(prices, period), 2
                )
        return result

    @staticmethod
    def calculate_bollinger_bands(
        prices: List[float], 
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, float]:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            return {
                'middle': prices[-1],
                'upper': prices[-1],
                'lower': prices[-1],
            }

        recent_prices = prices[-period:]
        middle = statistics.mean(recent_prices)
        variance = statistics.variance(recent_prices)
        std = variance ** 0.5

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        current = prices[-1]
        position = (current - lower) / (upper - lower) if (upper - lower) > 0 else 0.5

        return {
            'upper': round(upper, 2),
            'middle': round(middle, 2),
            'lower': round(lower, 2),
            'current_position': round(position, 3),  # 0 = at lower, 1 = at upper
        }

    @staticmethod
    def calculate_atr(prices_dict: List[Dict[str, float]], period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(prices_dict) < 2:
            return 0.0

        true_ranges = []
        for i in range(1, len(prices_dict)):
            high = prices_dict[i]['high']
            low = prices_dict[i]['low']
            close_prev = prices_dict[i - 1]['close']

            tr = max(
                high - low,
                abs(high - close_prev),
                abs(low - close_prev),
            )
            true_ranges.append(tr)

        if len(true_ranges) < period:
            return statistics.mean(true_ranges)

        return statistics.mean(true_ranges[-period:])

    @staticmethod
    def calculate_volume_profile(
        prices_dict: List[Dict[str, float]]
    ) -> Dict[str, Any]:
        """Analyze volume profile."""
        if len(prices_dict) < 2:
            return {'avg_volume': 0.0, 'volume_trend': 'insufficient'}

        volumes = [p['volume'] for p in prices_dict]
        recent_volumes = volumes[-10:]

        avg_volume = statistics.mean(volumes)
        recent_avg = statistics.mean(recent_volumes)
        current_volume = volumes[-1]

        # Volume trend
        if current_volume > recent_avg * 1.5:
            trend = 'spike'
        elif current_volume > recent_avg:
            trend = 'above_average'
        elif current_volume < recent_avg * 0.7:
            trend = 'below_average'
        else:
            trend = 'normal'

        volume_ratio = current_volume / (avg_volume + 0.0001)

        return {
            'current_volume': int(current_volume),
            'avg_volume': round(avg_volume, 0),
            'volume_ratio': round(volume_ratio, 2),
            'trend': trend,
        }

    @staticmethod
    async def calculate_all_indicators(
        prices_dict: List[Dict[str, float]]
    ) -> Dict[str, Any]:
        """Calculate all technical indicators at once."""
        if not prices_dict:
            return {'status': 'no_data'}

        closes = [p['close'] for p in prices_dict]

        return {
            'rsi': TechnicalCalculator.calculate_rsi(closes, 14),
            'macd': TechnicalCalculator.calculate_macd(closes),
            'ema': TechnicalCalculator.calculate_ema(closes, [20, 50, 200]),
            'bollinger': TechnicalCalculator.calculate_bollinger_bands(closes, 20),
            'atr': round(TechnicalCalculator.calculate_atr(prices_dict, 14), 2),
            'volume': TechnicalCalculator.calculate_volume_profile(prices_dict),
            'timestamp': datetime.utcnow().isoformat(),
        }


# Singleton instance
technical_calculator = TechnicalCalculator()
