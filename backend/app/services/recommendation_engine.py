"""
Advanced Recommendation Engine with Buy/Sell Timing.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from app.services.historical_analyzer import historical_analyzer
from app.services.fundamental_analyzer import fundamental_analyzer
from app.services.technical_calculator import technical_calculator


class RecommendationEngine:
    """Generates detailed buy/sell recommendations with timing."""

    @staticmethod
    async def calculate_entry_exit_points(
        symbol: str,
        agent_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate optimal entry and exit points based on all analyses.
        """
        try:
            # Get historical data
            prices = await historical_analyzer.get_historical_prices(symbol, days=60)
            if not prices:
                return {'status': 'no_data'}

            # Get technical indicators
            indicators = await technical_calculator.calculate_all_indicators(prices)
            
            # Get historical analysis
            hist_analysis = await historical_analyzer.full_historical_analysis(symbol)

            current_price = prices[-1]['close'] if prices else 0
            support = hist_analysis.get('support_resistance', {}).get('support', current_price * 0.95)
            resistance = hist_analysis.get('support_resistance', {}).get('resistance', current_price * 1.05)

            rsi = indicators['rsi']['rsi']
            macd = indicators['macd']
            atr = indicators['atr']
            bollinger = indicators['bollinger']

            # Entry point calculation
            entry_points = RecommendationEngine._calculate_entry_points(
                current_price,
                support,
                resistance,
                rsi,
                macd,
                atr,
                bollinger,
            )

            # Exit point calculation
            exit_points = RecommendationEngine._calculate_exit_points(
                current_price,
                support,
                resistance,
                atr,
            )

            # Buy/Sell timing
            buy_timing = RecommendationEngine._determine_buy_timing(
                rsi,
                macd,
                indicators['volume'],
            )

            sell_timing = RecommendationEngine._determine_sell_timing(
                rsi,
                macd,
            )

            return {
                'symbol': symbol,
                'current_price': round(current_price, 2),
                'entry_points': entry_points,
                'exit_points': exit_points,
                'buy_timing': buy_timing,
                'sell_timing': sell_timing,
                'risk_reward': round((exit_points['take_profit'] - entry_points['recommended_entry']) / 
                                     (entry_points['recommended_entry'] - exit_points['stop_loss']), 2) 
                                     if (entry_points['recommended_entry'] - exit_points['stop_loss']) > 0 else 0,
                'indicators_snapshot': {
                    'rsi': rsi,
                    'macd_histogram': macd['histogram'],
                    'volume_trend': indicators['volume']['trend'],
                },
                'timestamp': datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def _calculate_entry_points(
        current: float,
        support: float,
        resistance: float,
        rsi: float,
        macd: Dict[str, Any],
        atr: float,
        bollinger: Dict[str, float],
    ) -> Dict[str, Any]:
        """Calculate potential entry points."""
        
        # Primary entry: at support or on pullback
        if rsi < 30:  # Oversold
            primary_entry = current * 0.98  # Slight pullback
            entry_type = 'Aggressive (Oversold)'
        elif rsi < 40:  # Near oversold
            primary_entry = support * 1.01  # Slight above support
            entry_type = 'Moderate (Near Support)'
        else:
            primary_entry = support * 0.99  # Slight below support
            entry_type = 'Conservative (At Support)'

        # Secondary entry: breakout above resistance
        secondary_entry = resistance * 1.02
        
        # MACD-based entry
        if 'bullish' in macd['crossover_signal']:
            macd_entry = current * 0.99
            macd_timing = 'Now - MACD bullish cross'
        else:
            macd_entry = support
            macd_timing = 'Wait for MACD bullish signal'

        return {
            'recommended_entry': round(primary_entry, 2),
            'entry_type': entry_type,
            'secondary_entry': round(secondary_entry, 2),
            'breakout_entry': round(resistance * 1.01, 2),
            'macd_entry': round(macd_entry, 2),
            'macd_timing': macd_timing,
            'alternative_entries': [
                {'price': round(support * 0.98, 2), 'description': 'Below support'},
                {'price': round(support * 1.02, 2), 'description': 'At support'},
                {'price': round(current, 2), 'description': 'Current price'},
                {'price': round(resistance * 0.98, 2), 'description': 'Below resistance'},
            ],
        }

    @staticmethod
    def _calculate_exit_points(
        current: float,
        support: float,
        resistance: float,
        atr: float,
    ) -> Dict[str, Any]:
        """Calculate stop-loss and take-profit levels."""
        
        # Stop loss: below support
        stop_loss = support * 0.98
        stop_loss_pct = ((current - stop_loss) / current) * 100

        # Take profit levels (multiple exits)
        tp1 = current + (atr * 2)  # Quick profit
        tp2 = resistance  # Resistance level
        tp3 = resistance + (atr * 1.5)  # Extended target

        tp1_pct = ((tp1 - current) / current) * 100
        tp2_pct = ((tp2 - current) / current) * 100
        tp3_pct = ((tp3 - current) / current) * 100

        return {
            'stop_loss': round(stop_loss, 2),
            'stop_loss_pct': round(stop_loss_pct, 2),
            'take_profit_1': round(tp1, 2),
            'tp1_pct': round(tp1_pct, 2),
            'take_profit_2': round(tp2, 2),
            'tp2_pct': round(tp2_pct, 2),
            'take_profit_3': round(tp3, 2),
            'tp3_pct': round(tp3_pct, 2),
            'take_profit': round(tp2, 2),  # Recommended TP
            'risk_stop': round(stop_loss_pct, 2),
            'suggested_exit_strategy': (
                f"Exit 1/3 at {round(tp1_pct, 1)}% gains, "
                f"1/3 at {round(tp2_pct, 1)}%, "
                f"1/3 at {round(tp3_pct, 1)}% or on stop loss at -{round(stop_loss_pct, 1)}%"
            ),
        }

    @staticmethod
    def _determine_buy_timing(
        rsi: float,
        macd: Dict[str, Any],
        volume: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Determine best time to buy."""
        
        buy_signals = []
        wait_signals = []

        # RSI signals
        if rsi < 30:
            buy_signals.append('RSI oversold (< 30)')
        elif rsi < 40:
            buy_signals.append('RSI near oversold')
        else:
            wait_signals.append('RSI not in buy zone')

        # MACD signals
        if 'bullish_cross' in macd['crossover_signal']:
            buy_signals.append('MACD bullish crossover')
        elif 'bullish' in macd['crossover_signal']:
            buy_signals.append('MACD above signal line')
        else:
            wait_signals.append('MACD not bullish')

        # Volume signals
        if volume['trend'] in ['spike', 'above_average']:
            buy_signals.append('Volume spike detected')

        # Timing recommendation
        if len(buy_signals) >= 2:
            timing = 'BUY NOW'
            urgency = 'High'
        elif len(buy_signals) >= 1:
            timing = 'BUY ON PULLBACK'
            urgency = 'Medium'
        else:
            timing = 'WAIT FOR SIGNAL'
            urgency = 'Low'

        return {
            'timing': timing,
            'urgency': urgency,
            'buy_signals': buy_signals,
            'wait_reasons': wait_signals,
            'next_check_hours': 4 if urgency == 'High' else 12,
        }

    @staticmethod
    def _determine_sell_timing(
        rsi: float,
        macd: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Determine best time to sell."""
        
        sell_signals = []

        # RSI signals
        if rsi > 70:
            sell_signals.append('RSI overbought (> 70)')
        elif rsi > 60:
            sell_signals.append('RSI extended high')

        # MACD signals
        if 'bearish_cross' in macd['crossover_signal']:
            sell_signals.append('MACD bearish crossover')
        elif 'bearish' in macd['crossover_signal']:
            sell_signals.append('MACD below signal line')

        # Timing recommendation
        if len(sell_signals) >= 2:
            timing = 'SELL NOW'
            urgency = 'High'
        elif len(sell_signals) >= 1:
            timing = 'SELL ON SPIKE'
            urgency = 'Medium'
        else:
            timing = 'HOLD'
            urgency = 'Low'

        return {
            'timing': timing,
            'urgency': urgency,
            'sell_signals': sell_signals,
        }

    @staticmethod
    async def generate_full_recommendation(
        symbol: str,
        agent_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate complete recommendation with entry/exit points."""
        
        entry_exit = await RecommendationEngine.calculate_entry_exit_points(
            symbol,
            agent_results,
        )

        return {
            'symbol': symbol,
            'recommendation': agent_results.get('decision', {}).get('verdict', 'hold'),
            'confidence': round(agent_results.get('decision', {}).get('score', 0.5) * 100, 1),
            **entry_exit,
            'generated_at': datetime.utcnow().isoformat(),
        }


# Singleton
recommendation_engine = RecommendationEngine()
