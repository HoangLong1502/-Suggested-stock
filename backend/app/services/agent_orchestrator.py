import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List

from app.services.llm_provider import llm_provider
from app.services.pubsub import publish
from app.services.stock_ingest import load_watchlist_symbols


@dataclass
class AgentResult:
    agent: str
    stock_symbol: str
    verdict: str
    score: float
    rationale: str
    extra: Dict[str, Any] = field(default_factory=dict)


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
        })


class MarketScannerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__('MarketScanner')

    async def evaluate(self, symbol: str, context: Dict[str, Any]) -> AgentResult:
        prompt = f"Analyze market momentum for {symbol} using available Vietnamese stock signals."  # local stub
        rationale = await llm_provider.complete(prompt)
        result = AgentResult(
            agent=self.name,
            stock_symbol=symbol,
            verdict='candidate',
            score=0.75,
            rationale=rationale,
            extra={'momentum': 'positive', 'breakout': True},
        )
        await self.publish(result)
        return result


class FundamentalAnalystAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__('FundamentalAnalyst')

    async def evaluate(self, symbol: str, context: Dict[str, Any]) -> AgentResult:
        prompt = f"Evaluate PE, PB, ROE, debt, revenue growth, profit growth, insider ownership for {symbol}."
        rationale = await llm_provider.complete(prompt)
        score = 0.65
        result = AgentResult(
            agent=self.name,
            stock_symbol=symbol,
            verdict='hold' if score < 0.7 else 'buy',
            score=score,
            rationale=rationale,
            extra={'fundamental_quality': score},
        )
        await self.publish(result)
        return result


class TechnicalAnalystAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__('TechnicalAnalyst')

    async def evaluate(self, symbol: str, context: Dict[str, Any]) -> AgentResult:
        prompt = f"Analyze RSI, MACD, EMA, Bollinger Bands, support/resistance for {symbol}."
        rationale = await llm_provider.complete(prompt)
        score = 0.8
        result = AgentResult(
            agent=self.name,
            stock_symbol=symbol,
            verdict='buy' if score >= 0.7 else 'hold',
            score=score,
            rationale=rationale,
            extra={'signal': 'bullish-cross'},
        )
        await self.publish(result)
        return result


class SentimentAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__('SentimentAgent')

    async def evaluate(self, symbol: str, context: Dict[str, Any]) -> AgentResult:
        prompt = f"Classify news and social sentiment for {symbol} from Vietnamese market sources."
        rationale = await llm_provider.complete(prompt)
        score = 0.7
        verdict = 'buy' if score >= 0.65 else 'hold'
        result = AgentResult(
            agent=self.name,
            stock_symbol=symbol,
            verdict=verdict,
            score=score,
            rationale=rationale,
            extra={'sentiment': 'positive'},
        )
        await self.publish(result)
        return result


class RiskManagementAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__('RiskManager')

    async def evaluate(self, symbol: str, context: Dict[str, Any]) -> AgentResult:
        prompt = f"Estimate volatility, stop loss and position sizing for {symbol}."
        rationale = await llm_provider.complete(prompt)
        score = 0.55
        result = AgentResult(
            agent=self.name,
            stock_symbol=symbol,
            verdict='hold',
            score=score,
            rationale=rationale,
            extra={'risk': 'medium', 'suggested_stoploss': '5%'},
        )
        await self.publish(result)
        return result


class DecisionMakerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__('DecisionMaker')

    async def evaluate(self, symbol: str, context: Dict[str, Any]) -> AgentResult:
        pieces = [f"{r['agent']} said {r['verdict']} with score {r['score']}" for r in context.get('history', [])]
        prompt = f"Synthesize these opinions for {symbol}: {'; '.join(pieces)}"
        rationale = await llm_provider.complete(prompt)
        avg_score = sum([r['score'] for r in context.get('history', [])]) / max(len(context.get('history', [])), 1)
        if avg_score >= 0.7:
            action = 'buy'
        elif avg_score >= 0.5:
            action = 'hold'
        else:
            action = 'sell'
        result = AgentResult(
            agent=self.name,
            stock_symbol=symbol,
            verdict=action,
            score=avg_score,
            rationale=rationale,
            extra={'confidence': avg_score, 'entry': 'market price', 'target': '2-4%'},
        )
        await self.publish(result)
        return result


class AgentOrchestrator:
    def __init__(self) -> None:
        self.market = MarketScannerAgent()
        self.fundamental = FundamentalAnalystAgent()
        self.technical = TechnicalAnalystAgent()
        self.sentiment = SentimentAgent()
        self.risk = RiskManagementAgent()
        self.decision = DecisionMakerAgent()

    async def run_stock_pipeline(self, symbol: str) -> Dict[str, Any]:
        context = {'symbol': symbol, 'history': []}
        tasks = [
            self.market.evaluate(symbol, context),
            self.fundamental.evaluate(symbol, context),
            self.technical.evaluate(symbol, context),
            self.sentiment.evaluate(symbol, context),
            self.risk.evaluate(symbol, context),
        ]
        results = await asyncio.gather(*tasks)
        context['history'] = [r.__dict__ for r in results]
        final = await self.decision.evaluate(symbol, context)
        return {
            'symbol': symbol,
            'agents': context['history'],
            'decision': final.__dict__,
        }

    async def run_watchlist_cycle(self) -> None:
        symbols = await load_watchlist_symbols()
        for symbol in symbols[:8]:
            try:
                await self.run_stock_pipeline(symbol)
            except Exception:
                continue


orchestrator = AgentOrchestrator()
