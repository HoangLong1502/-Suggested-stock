import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List
from datetime import datetime, timezone

from app.services.llm_provider import llm_provider
from app.services.pubsub import publish
from app.services.stock_ingest import load_watchlist_symbols
from app.services.historical_analyzer import historical_analyzer
from app.services.fundamental_analyzer import fundamental_analyzer
from app.services.technical_calculator import technical_calculator


@dataclass
class AgentResult:
    agent: str
    stock_symbol: str
    verdict: str
    score: float
    rationale: str
    extra: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BaseAgent:
    def __init__(self, name: str) -> None:
        self.name = name
        self.memory: List[Dict[str, Any]] = []

    async def evaluate(self, symbol: str, context: Dict[str, Any]) -> AgentResult:
        raise NotImplementedError

    async def publish(self, result: AgentResult) -> None:
        self.memory.append(result.__dict__)
        await publish('agent-results', {
            'agent': result.agent,
            'symbol': result.stock_symbol,
            'verdict': result.verdict,
            'score': result.score,
            'rationale': result.rationale,
            'extra': result.extra,
            'timestamp': result.timestamp,
        })


class MarketScannerAgent(BaseAgent):
    """Analyzes market trends using historical data."""
    def __init__(self) -> None:
        super().__init__('MarketScanner')

    async def evaluate(self, symbol: str, context: Dict[str, Any]) -> AgentResult:
        try:
            historical = await historical_analyzer.full_historical_analysis(symbol, days=60)
            
            if historical.get('status') == 'no_data':
                return AgentResult(
                    agent=self.name,
                    stock_symbol=symbol,
                    verdict='hold',
                    score=0.3,
                    rationale='No historical data available',
                    extra={'status': 'no_data'},
                )

            trend = historical['trend']
            momentum = historical['momentum']
            volatility = historical['volatility']

            # Score calculation
            trend_score = 0.7 if trend['direction'] == 'uptrend' else 0.3
            momentum_score = (momentum['score'] + 1) / 2  # Convert -1..1 to 0..1
            strength_weight = trend['strength']

            score = trend_score * 0.6 + momentum_score * 0.4

            # Verdict
            if score >= 0.65 and momentum['momentum'] in ['strong_bullish', 'bullish']:
                verdict = 'buy'
            elif score >= 0.5:
                verdict = 'hold'
            else:
                verdict = 'sell'

            rationale = (
                f"Market trend: {trend['direction']} (strength: {trend['strength']}). "
                f"Momentum: {momentum['momentum']}. "
                f"Volume profile indicates market interest. "
                f"Support at {historical['support_resistance']['support']}, "
                f"Resistance at {historical['support_resistance']['resistance']}."
            )

            result = AgentResult(
                agent=self.name,
                stock_symbol=symbol,
                verdict=verdict,
                score=score,
                rationale=rationale,
                extra={
                    'trend': trend['direction'],
                    'momentum': momentum['momentum'],
                    'volatility_level': volatility['level'],
                    'support': historical['support_resistance']['support'],
                    'resistance': historical['support_resistance']['resistance'],
                },
            )
            await self.publish(result)
            return result

        except Exception as e:
            return AgentResult(
                agent=self.name,
                stock_symbol=symbol,
                verdict='hold',
                score=0.0,
                rationale=f'Error analyzing market: {str(e)}',
                extra={'error': str(e)},
            )


class BusinessAnalystAgent(BaseAgent):
    """Analyzes company fundamentals and business quality."""
    def __init__(self) -> None:
        super().__init__('BusinessAnalyst')

    async def evaluate(self, symbol: str, context: Dict[str, Any]) -> AgentResult:
        try:
            analysis = await fundamental_analyzer.full_business_analysis(symbol)
            fundamentals = analysis['fundamentals']
            scoring = analysis['scoring']

            if fundamentals.get('status') in ['error', 'vnstock_not_available']:
                return AgentResult(
                    agent=self.name,
                    stock_symbol=symbol,
                    verdict='hold',
                    score=0.5,
                    rationale='Unable to fetch business fundamentals',
                    extra={'status': 'no_data'},
                )

            total_score = scoring['total_score'] / 100  # Normalize to 0-1
            rating = scoring['rating']

            # Verdict based on rating
            if rating in ['Excellent', 'Good']:
                verdict = 'buy'
            elif rating in ['Fair']:
                verdict = 'hold'
            else:
                verdict = 'sell'

            rationale = (
                f"Business Quality: {rating} (Score: {scoring['total_score']}/100). "
                f"Valuation: {scoring['components']['valuation']:.0f}/100, "
                f"Profitability: {scoring['components']['profitability']:.0f}/100, "
                f"Growth: {scoring['components']['growth']:.0f}/100. "
                f"PE Ratio: {fundamentals.get('pe_ratio', 'N/A')}, "
                f"ROE: {fundamentals.get('roe', 'N/A')}, "
                f"Debt-to-Equity: {fundamentals.get('debt_to_equity', 'N/A')}."
            )

            result = AgentResult(
                agent=self.name,
                stock_symbol=symbol,
                verdict=verdict,
                score=total_score,
                rationale=rationale,
                extra={
                    'rating': rating,
                    'pe_ratio': fundamentals.get('pe_ratio'),
                    'roe': fundamentals.get('roe'),
                    'growth_revenue': fundamentals.get('revenue_growth_yoy'),
                    'growth_profit': fundamentals.get('profit_growth_yoy'),
                },
            )
            await self.publish(result)
            return result

        except Exception as e:
            return AgentResult(
                agent=self.name,
                stock_symbol=symbol,
                verdict='hold',
                score=0.5,
                rationale=f'Error analyzing business: {str(e)}',
                extra={'error': str(e)},
            )


class TechnicalAnalystAgent(BaseAgent):
    """Analyzes technical indicators for entry/exit signals."""
    def __init__(self) -> None:
        super().__init__('TechnicalAnalyst')

    async def evaluate(self, symbol: str, context: Dict[str, Any]) -> AgentResult:
        try:
            historical = await historical_analyzer.get_historical_prices(symbol, days=60)
            
            if not historical:
                return AgentResult(
                    agent=self.name,
                    stock_symbol=symbol,
                    verdict='hold',
                    score=0.5,
                    rationale='No price data available',
                    extra={'status': 'no_data'},
                )

            indicators = await technical_calculator.calculate_all_indicators(historical)

            rsi = indicators['rsi']
            macd = indicators['macd']
            bollinger = indicators['bollinger']
            volume = indicators['volume']

            # Score calculation
            rsi_signal_score = 0.0
            if rsi['signal'] in ['oversold', 'strong_bearish']:
                rsi_signal_score = 0.8  # Good buy signal
            elif rsi['signal'] in ['strong_bullish']:
                rsi_signal_score = 0.6
            elif rsi['signal'] in ['overbought', 'strong_bullish']:
                rsi_signal_score = 0.3
            else:
                rsi_signal_score = 0.5

            macd_signal_score = 0.7 if 'bullish' in macd['crossover_signal'] else 0.3

            volume_signal_score = 0.6 if volume['trend'] == 'spike' else 0.4

            score = (rsi_signal_score * 0.4 + macd_signal_score * 0.4 + volume_signal_score * 0.2)

            # Verdict
            if score >= 0.65:
                verdict = 'buy'
            elif score >= 0.4:
                verdict = 'hold'
            else:
                verdict = 'sell'

            rationale = (
                f"RSI: {rsi['rsi']} ({rsi['signal']}). "
                f"MACD: {macd['crossover_signal']}. "
                f"Bollinger Bands position: {bollinger['current_position']}. "
                f"Volume: {volume['trend']} (Ratio: {volume['volume_ratio']}x)."
            )

            result = AgentResult(
                agent=self.name,
                stock_symbol=symbol,
                verdict=verdict,
                score=score,
                rationale=rationale,
                extra={
                    'rsi': rsi['rsi'],
                    'macd_signal': macd['crossover_signal'],
                    'bollinger_position': bollinger['current_position'],
                    'volume_trend': volume['trend'],
                    'atr': indicators['atr'],
                },
            )
            await self.publish(result)
            return result

        except Exception as e:
            return AgentResult(
                agent=self.name,
                stock_symbol=symbol,
                verdict='hold',
                score=0.5,
                rationale=f'Error analyzing technicals: {str(e)}',
                extra={'error': str(e)},
            )


class SentimentAnalysisAgent(BaseAgent):
    """Analyzes market sentiment from available data."""
    def __init__(self) -> None:
        super().__init__('SentimentAnalysis')

    async def evaluate(self, symbol: str, context: Dict[str, Any]) -> AgentResult:
        try:
            # For now, use historical volatility and momentum as sentiment proxy
            historical = await historical_analyzer.full_historical_analysis(symbol)
            
            if historical.get('status') == 'no_data':
                score = 0.5
                verdict = 'hold'
                rationale = 'No market data for sentiment analysis'
            else:
                momentum = historical['momentum']
                overbought_oversold = historical['overbought_oversold']

                # Sentiment score
                momentum_score = (momentum['score'] + 1) / 2  # Convert to 0-1
                
                if overbought_oversold['condition'] in ['oversold', 'underextended']:
                    overbought_score = 0.8
                elif overbought_oversold['condition'] in ['overbought', 'overextended']:
                    overbought_score = 0.2
                else:
                    overbought_score = 0.5

                score = momentum_score * 0.6 + overbought_score * 0.4

                if score >= 0.65:
                    verdict = 'buy'
                elif score >= 0.4:
                    verdict = 'hold'
                else:
                    verdict = 'sell'

                rationale = (
                    f"Market sentiment shows {momentum['momentum']}. "
                    f"Price condition: {overbought_oversold['condition']}. "
                    f"Position at {overbought_oversold['normalized_position']:.0f}% of 14-day range."
                )

            result = AgentResult(
                agent=self.name,
                stock_symbol=symbol,
                verdict=verdict,
                score=score,
                rationale=rationale,
                extra={
                    'sentiment_direction': 'positive' if score >= 0.6 else 'negative' if score <= 0.4 else 'neutral',
                    'confidence': score,
                },
            )
            await self.publish(result)
            return result

        except Exception as e:
            return AgentResult(
                agent=self.name,
                stock_symbol=symbol,
                verdict='hold',
                score=0.5,
                rationale=f'Error analyzing sentiment: {str(e)}',
                extra={'error': str(e)},
            )


class RiskManagementAgent(BaseAgent):
    """Analyzes risk and suggests stop-loss/take-profit levels."""
    def __init__(self) -> None:
        super().__init__('RiskManagement')

    async def evaluate(self, symbol: str, context: Dict[str, Any]) -> AgentResult:
        try:
            historical = await historical_analyzer.full_historical_analysis(symbol)
            
            if historical.get('status') == 'no_data':
                return AgentResult(
                    agent=self.name,
                    stock_symbol=symbol,
                    verdict='hold',
                    score=0.5,
                    rationale='No data for risk analysis',
                    extra={},
                )

            volatility = historical['volatility']
            support_resistance = historical['support_resistance']
            
            current_price = support_resistance['current_price']
            support = support_resistance['support']
            resistance = support_resistance['resistance']

            # Risk score (lower volatility = higher score)
            atr_percent = volatility['atr_percent']
            if atr_percent < 2:
                risk_score = 0.9
                risk_level = 'low'
            elif atr_percent < 4:
                risk_score = 0.7
                risk_level = 'medium'
            elif atr_percent < 6:
                risk_score = 0.5
                risk_level = 'high'
            else:
                risk_score = 0.3
                risk_level = 'very_high'

            # Calculate stop loss and take profit
            stop_loss = support
            take_profit = resistance
            position_size = 100 if risk_level == 'low' else 50 if risk_level == 'medium' else 25

            verdict = 'hold' if risk_level in ['low', 'medium'] else 'caution'

            rationale = (
                f"Risk Level: {risk_level} (ATR: {volatility['atr_percent']:.2f}%). "
                f"Stop Loss: {stop_loss:.2f} ({support_resistance['distance_to_support_pct']:.1f}% below). "
                f"Take Profit: {take_profit:.2f} ({support_resistance['distance_to_resistance_pct']:.1f}% above). "
                f"Suggested Position Size: {position_size} units."
            )

            result = AgentResult(
                agent=self.name,
                stock_symbol=symbol,
                verdict=verdict,
                score=risk_score,
                rationale=rationale,
                extra={
                    'risk_level': risk_level,
                    'stop_loss': round(stop_loss, 2),
                    'take_profit': round(take_profit, 2),
                    'position_size': position_size,
                    'risk_reward_ratio': round((take_profit - current_price) / (current_price - stop_loss), 2) if (current_price - stop_loss) > 0 else 0,
                },
            )
            await self.publish(result)
            return result

        except Exception as e:
            return AgentResult(
                agent=self.name,
                stock_symbol=symbol,
                verdict='hold',
                score=0.5,
                rationale=f'Error analyzing risk: {str(e)}',
                extra={'error': str(e)},
            )


class DecisionMakerAgent(BaseAgent):
    """Synthesizes all agent recommendations into final decision with debate analysis."""
    def __init__(self) -> None:
        super().__init__('DecisionMaker')

    async def _perform_agent_debate(self, history: List[Dict[str, Any]]) -> str:
        """
        Use LLM to synthesize agent opinions into final reasoning.
        Considers agent confidence, agreement level, and rationale.
        """
        try:
            # Prepare agent opinions for debate
            agent_consensus = "\n".join([
                f"- {r['agent']} ({r['verdict'].upper()}, confidence: {r['score']:.2f}): {r['rationale']}"
                for r in history
            ])
            
            prompt = f"""
Based on these AI agents' analysis of stock data over 60 days (2 months):

{agent_consensus}

Provide a concise synthesis of:
1. Areas of strong agreement between agents
2. Key disagreements and why they matter
3. Most important factors supporting the consensus
4. Overall investment outlook

Keep response under 200 words."""
            
            debate_response = await llm_provider.complete(prompt)
            return debate_response
        except Exception as e:
            return f"Debate synthesis unavailable: {str(e)}"

    async def evaluate(self, symbol: str, context: Dict[str, Any]) -> AgentResult:
        history = context.get('history', [])
        
        if not history:
            return AgentResult(
                agent=self.name,
                stock_symbol=symbol,
                verdict='hold',
                score=0.5,
                rationale='No agent data available',
                extra={},
            )

        # Calculate weighted scores
        scores = [r['score'] for r in history]
        avg_score = sum(scores) / len(scores)
        
        # Weight scores by agent type (Business & Technical = higher weight)
        weighted_scores = []
        for r in history:
            agent_name = r['agent']
            if agent_name in ['BusinessAnalyst', 'TechnicalAnalyst']:
                weight = 1.2  # Higher weight
            elif agent_name in ['MarketScanner', 'SentimentAnalysis']:
                weight = 1.0  # Standard weight
            elif agent_name == 'RiskManagement':
                weight = 0.8  # Lower weight (supportive)
            else:
                weight = 1.0
            weighted_scores.append(r['score'] * weight)
        
        weighted_avg = sum(weighted_scores) / len(weighted_scores) if weighted_scores else avg_score

        # Count verdicts
        verdicts = [r['verdict'] for r in history]
        buy_count = verdicts.count('buy')
        sell_count = verdicts.count('sell')
        hold_count = verdicts.count('hold')
        
        # Calculate consensus strength (0-1)
        consensus_strength = max(buy_count, sell_count, hold_count) / len(history)

        # Weighted decision logic
        buy_weight = buy_count * 0.6 + (avg_score >= 0.65) * 0.4
        sell_weight = sell_count * 0.6 + (avg_score <= 0.35) * 0.4
        hold_weight = hold_count * 0.6 + (0.35 < avg_score < 0.65) * 0.4

        if buy_weight > sell_weight and buy_weight > hold_weight:
            verdict = 'buy'
        elif sell_weight > buy_weight and sell_weight > hold_weight:
            verdict = 'sell'
        else:
            verdict = 'hold'

        # Generate debate-based rationale
        agent_opinions = '; '.join([
            f"{r['agent']}: {r['verdict'].upper()} ({r['score']:.2f})"
            for r in history
        ])
        
        # Consensus quality assessment
        if consensus_strength >= 0.8:
            consensus_quality = "Strong consensus among all agents"
        elif consensus_strength >= 0.65:
            consensus_quality = "Moderate consensus with some disagreement"
        else:
            consensus_quality = "Weak consensus - agents are divided"

        rationale = (
            f"{consensus_quality}. "
            f"Agent Analysis: {agent_opinions}. "
            f"Average Confidence: {avg_score:.2f} | Weighted Score: {weighted_avg:.2f}. "
            f"Verdict: {verdict.upper()}"
        )

        result = AgentResult(
            agent=self.name,
            stock_symbol=symbol,
            verdict=verdict,
            score=weighted_avg,
            rationale=rationale,
            extra={
                'confidence': weighted_avg,
                'consensus_strength': consensus_strength,
                'buy_agents': buy_count,
                'sell_agents': sell_count,
                'hold_agents': hold_count,
                'consensus_quality': consensus_quality,
                'average_score': avg_score,
                'weighted_score': weighted_avg,
            },
        )
        await self.publish(result)
        return result


class AgentOrchestrator:
    """Orchestrates all agents to analyze stocks."""
    def __init__(self) -> None:
        self.market = MarketScannerAgent()
        self.business = BusinessAnalystAgent()
        self.technical = TechnicalAnalystAgent()
        self.sentiment = SentimentAnalysisAgent()
        self.risk = RiskManagementAgent()
        self.decision = DecisionMakerAgent()

    async def run_stock_pipeline(self, symbol: str) -> Dict[str, Any]:
        """Run all agents for a single stock."""
        context = {'symbol': symbol, 'history': []}
        
        # Run all agents in parallel
        tasks = [
            self.market.evaluate(symbol, context),
            self.business.evaluate(symbol, context),
            self.technical.evaluate(symbol, context),
            self.sentiment.evaluate(symbol, context),
            self.risk.evaluate(symbol, context),
        ]
        results = await asyncio.gather(*tasks)
        context['history'] = [r.__dict__ for r in results]
        
        # Final decision
        final = await self.decision.evaluate(symbol, context)
        
        return {
            'symbol': symbol,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'agents': context['history'],
            'decision': final.__dict__,
        }

    async def run_watchlist_cycle(self) -> None:
        """Run pipeline for all watchlist stocks."""
        symbols = await load_watchlist_symbols()
        for symbol in symbols[:8]:
            try:
                await self.run_stock_pipeline(symbol)
            except Exception as e:
                print(f'Error processing {symbol}: {e}')
                continue


orchestrator = AgentOrchestrator()
