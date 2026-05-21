"""
Stock Ranker Service - Ranks all watched stocks based on AI consensus analysis.
Analyzes 2+ months of historical data to provide comprehensive rankings.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import asyncio
import time

from app.services.agent_orchestrator import orchestrator
from app.services.recommendation_engine import recommendation_engine
from app.services.stock_ingest import load_watchlist_symbols

MAX_RANK_SYMBOLS = 10
RANK_CACHE_SECONDS = 300
_rank_cache: Dict[str, Any] = {'ts': 0.0, 'min_confidence': None, 'body': None}


def _public_stock_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Strip internal keys (e.g. cached pipeline) before API responses."""
    return {k: v for k, v in row.items() if not k.startswith('_')}


class StockRanker:
    """Ranks stocks based on AI agent analysis with 2+ months of data."""

    @staticmethod
    def _when_to_buy_payload(entry_exit: Dict[str, Any]) -> Dict[str, Any]:
        bt = entry_exit.get('buy_timing') or {}
        ep = entry_exit.get('entry_points') or {}
        parts = [
            f"Khuyến nghị thời điểm: {bt.get('timing', 'CHƯA XÁC ĐỊNH')} "
            f"(mức độ ưu tiên: {bt.get('urgency', 'N/A')}).",
        ]
        if bt.get('buy_signals'):
            parts.append('Tín hiệu thuận: ' + '; '.join(str(x) for x in bt['buy_signals']) + '.')
        if bt.get('wait_reasons'):
            parts.append('Cần lưu ý: ' + '; '.join(str(x) for x in bt['wait_reasons']) + '.')
        if ep.get('macd_timing'):
            parts.append(str(ep['macd_timing']) + '.')
        return {
            'summary_vi': ' '.join(parts).strip(),
            'timing': bt.get('timing'),
            'urgency': bt.get('urgency'),
            'buy_signals': bt.get('buy_signals', []),
            'wait_reasons': bt.get('wait_reasons', []),
            'next_check_hours': bt.get('next_check_hours'),
            'recommended_entry_price': ep.get('recommended_entry'),
            'macd_timing_note': ep.get('macd_timing'),
            'technical_reference_price': entry_exit.get('current_price'),
        }

    @staticmethod
    async def _enrich_buy_rows(buy_rows: List[Dict[str, Any]]) -> None:
        """Attach when_to_buy / why_this_stock using technical timing (no extra LLM calls)."""

        async def enrich(row: Dict[str, Any]) -> None:
            sym = row['symbol']
            ee = await recommendation_engine.calculate_entry_exit_points(sym, {})
            if ee.get('status') in ('no_data', 'error'):
                row['when_to_buy'] = {
                    'summary_vi': 'Chưa đủ dữ liệu lịch sử giá để gợi ý thời điểm mua chi tiết.',
                    'timing': None,
                    'urgency': None,
                }
            else:
                row['when_to_buy'] = StockRanker._when_to_buy_payload(ee)
            agents_buy = row.get('agents_buy', 0)
            conf = row.get('confidence', 0)
            base = row.get('reasoning', '') or ''
            timing_txt = (row.get('when_to_buy') or {}).get('summary_vi', '')
            row['why_this_stock'] = (
                f"{base}\n\n"
                f"Sau phiên thảo luận 5 agent: {agents_buy} agent chọn MUA, "
                f"mức tin cậy đồng thuận {conf}%.\n"
                f"{timing_txt}"
            ).strip()

        await asyncio.gather(*[enrich(r) for r in buy_rows])

    @staticmethod
    async def rank_all_stocks(min_confidence: float = 0.65) -> Dict[str, Any]:
        """
        Analyze and rank all watched stocks.
        
        Args:
            min_confidence: Minimum confidence score to include (0-1)
        
        Returns:
            Dictionary with ranked stocks by confidence score
        """
        now = time.monotonic()
        cached = _rank_cache.get('body')
        if (
            cached is not None
            and _rank_cache.get('min_confidence') == min_confidence
            and now - float(_rank_cache.get('ts') or 0) < RANK_CACHE_SECONDS
        ):
            return cached

        try:
            symbols = (await load_watchlist_symbols())[:MAX_RANK_SYMBOLS]

            # Giới hạn song song: mỗi mã chạy 5 agent — quá nhiều mã → timeout/500.
            sem = asyncio.Semaphore(2)

            async def run_one(sym: str):
                async with sem:
                    return await orchestrator.run_stock_pipeline(sym)

            results = await asyncio.gather(*[run_one(s) for s in symbols], return_exceptions=True)
            
            # Process results
            ranked_stocks = []
            failed_stocks = []
            
            for i, symbol in enumerate(symbols):
                if isinstance(results[i], Exception):
                    failed_stocks.append({'symbol': symbol, 'error': str(results[i])})
                    continue
                
                pipeline_result = results[i]
                decision = pipeline_result.get('decision', {})
                agents = pipeline_result.get('agents', [])
                
                decision_score = float(decision.get('score', 0.0))
                consensus_strength = decision.get('extra', {}).get('consensus_strength', 0)

                ranked_stocks.append({
                    'symbol': symbol,
                    'recommendation': decision.get('verdict', 'hold'),
                    'confidence': round(decision_score * 100, 1),
                    'meets_min_confidence': decision_score >= min_confidence,
                    'consensus_strength': round(consensus_strength * 100, 1),
                    'reasoning': decision.get('rationale', ''),
                    'agents_buy': decision.get('extra', {}).get('buy_agents', 0),
                    'agents_sell': decision.get('extra', {}).get('sell_agents', 0),
                    'agents_hold': decision.get('extra', {}).get('hold_agents', 0),
                    'agent_details': [
                        {
                            'agent': agent['agent'],
                            'verdict': agent['verdict'],
                            'confidence': round(agent['score'] * 100, 1),
                            'rationale': agent['rationale'],
                        }
                        for agent in agents
                    ],
                    '_pipeline': pipeline_result,
                })
            
            # Sort by confidence descending
            ranked_stocks.sort(key=lambda x: x['confidence'], reverse=True)
            
            # Group by recommendation type (buy list respects min confidence)
            buy_stocks = [
                s for s in ranked_stocks
                if s['recommendation'] == 'buy' and s.get('meets_min_confidence', False)
            ]
            hold_stocks = [s for s in ranked_stocks if s['recommendation'] == 'hold']
            sell_stocks = [s for s in ranked_stocks if s['recommendation'] == 'sell']

            if buy_stocks:
                await StockRanker._enrich_buy_rows(buy_stocks)

            payload = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'analysis_period_days': 60,
                'min_confidence': min_confidence,
                'summary': {
                    'total_analyzed': len(symbols),
                    'high_confidence': sum(1 for s in ranked_stocks if s.get('meets_min_confidence')),
                    'buy_signals': len(buy_stocks),
                    'hold_signals': len(hold_stocks),
                    'sell_signals': len(sell_stocks),
                    'failed': len(failed_stocks),
                },
                'top_buy_stocks': buy_stocks,
                'hold_stocks': hold_stocks,
                'sell_stocks': sell_stocks,
                'all_ranked': ranked_stocks,
                'failed_analysis': failed_stocks,
            }
            _rank_cache['body'] = payload
            _rank_cache['ts'] = time.monotonic()
            _rank_cache['min_confidence'] = min_confidence
            return payload

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }

    @staticmethod
    async def _attach_timing_to_best(payload: Dict[str, Any], pipeline: Dict[str, Any] | None) -> None:
        """Enrich best-stock payload from cached pipeline (no second agent run)."""
        symbol = payload.get('best_stock')
        if not symbol or not pipeline:
            return
        try:
            full = await recommendation_engine.generate_full_recommendation(symbol, pipeline)
            payload['buy_timing'] = full.get('buy_timing', {})
            payload['recommended_entry'] = (full.get('entry_points') or {}).get('recommended_entry')
            payload['current_price'] = full.get('current_price')
            payload['entry_points'] = full.get('entry_points', {})
            payload['technical_snapshot'] = full.get('indicators_snapshot', {})
            payload['timestamp'] = full.get('timestamp') or payload.get('timestamp')
            bt = full.get('buy_timing') or {}
            sig = '; '.join(bt.get('buy_signals') or []) or (
                'xem RSI/MACD/khối lượng trong khối buy_timing.'
            )
            payload['why_this_stock'] = (
                f"{payload.get('reasoning', '')}\n\n"
                f"Tổng hợp sau debate + bối cảnh kỹ thuật 60 ngày: {bt.get('timing', '')} "
                f"(mức ưu tiên {bt.get('urgency', '')}). Tín hiệu: {sig}"
            ).strip()
        except Exception as exc:
            payload['timing_error'] = str(exc)

    @staticmethod
    async def get_best_stock() -> Dict[str, Any]:
        """Get the single best stock based on 2 months analysis."""
        ranking = await StockRanker.rank_all_stocks(min_confidence=0.65)

        if ranking.get('status') == 'error':
            return ranking

        all_ranked = ranking.get('all_ranked', [])
        if not all_ranked:
            return {
                'status': 'no_high_confidence_stocks',
                'message': 'No stocks could be analyzed (check DB / watchlist)',
                'timestamp': ranking.get('timestamp'),
                'best_stock': None,
            }

        best = all_ranked[0]
        pipeline = best.get('_pipeline')

        payload: Dict[str, Any] = {
            'status': 'ok',
            'best_stock': best['symbol'],
            'recommendation': best['recommendation'],
            'confidence': best['confidence'],
            'consensus_strength': best['consensus_strength'],
            'reasoning': best['reasoning'],
            'agent_breakdown': best['agent_details'],
            'analysis_period': '60 days (2 months)',
            'timestamp': ranking.get('timestamp', datetime.now(timezone.utc).isoformat()),
        }
        await StockRanker._attach_timing_to_best(payload, pipeline)
        return payload

    @staticmethod
    async def compare_stocks(symbols: List[str]) -> Dict[str, Any]:
        """
        Compare specific stocks side-by-side.
        
        Args:
            symbols: List of stock symbols to compare
        
        Returns:
            Comparison with all agent analyses
        """
        try:
            tasks = [orchestrator.run_stock_pipeline(s.upper()) for s in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            comparison = []
            
            for i, symbol in enumerate(symbols):
                if isinstance(results[i], Exception):
                    comparison.append({
                        'symbol': symbol,
                        'error': str(results[i]),
                    })
                    continue
                
                pipeline = results[i]
                decision = pipeline.get('decision', {})
                
                comparison.append({
                    'symbol': symbol,
                    'recommendation': decision.get('verdict', 'hold'),
                    'confidence': round(decision.get('score', 0.0) * 100, 1),
                    'consensus_strength': round(
                        decision.get('extra', {}).get('consensus_strength', 0) * 100, 1
                    ),
                    'reasoning': decision.get('rationale', ''),
                    'agent_votes': {
                        'buy': decision.get('extra', {}).get('buy_agents', 0),
                        'sell': decision.get('extra', {}).get('sell_agents', 0),
                        'hold': decision.get('extra', {}).get('hold_agents', 0),
                    },
                    'agent_details': [
                        {
                            'agent': agent['agent'],
                            'verdict': agent['verdict'],
                            'confidence': round(agent['score'] * 100, 1),
                        }
                        for agent in pipeline.get('agents', [])
                    ],
                })
            
            # Sort by confidence
            comparison.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            return {
                'comparison': comparison,
                'best_stock': comparison[0]['symbol'] if comparison else None,
                'analysis_period': '60 days (2 months)',
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}


stock_ranker = StockRanker()
