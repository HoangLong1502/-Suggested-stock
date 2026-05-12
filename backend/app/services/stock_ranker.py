"""
Stock Ranker Service - Ranks all watched stocks based on AI consensus analysis.
Analyzes 2+ months of historical data to provide comprehensive rankings.
"""
from typing import Dict, List, Any
from datetime import datetime, timezone
import asyncio

from app.services.agent_orchestrator import orchestrator
from app.services.stock_ingest import load_watchlist_symbols


class StockRanker:
    """Ranks stocks based on AI agent analysis with 2+ months of data."""

    @staticmethod
    async def rank_all_stocks(min_confidence: float = 0.65) -> Dict[str, Any]:
        """
        Analyze and rank all watched stocks.
        
        Args:
            min_confidence: Minimum confidence score to include (0-1)
        
        Returns:
            Dictionary with ranked stocks by confidence score
        """
        try:
            symbols = await load_watchlist_symbols()
            
            # Run analysis for all stocks in parallel
            tasks = [orchestrator.run_stock_pipeline(symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
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
                
                confidence = float(decision.get('score', 0.0))
                
                # Only include if confidence meets threshold
                if confidence >= min_confidence:
                    consensus_strength = decision.get('extra', {}).get('consensus_strength', 0)
                    
                    ranked_stocks.append({
                        'symbol': symbol,
                        'recommendation': decision.get('verdict', 'hold'),
                        'confidence': round(confidence * 100, 1),
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
                    })
            
            # Sort by confidence descending
            ranked_stocks.sort(key=lambda x: x['confidence'], reverse=True)
            
            # Group by recommendation type
            buy_stocks = [s for s in ranked_stocks if s['recommendation'] == 'buy']
            hold_stocks = [s for s in ranked_stocks if s['recommendation'] == 'hold']
            sell_stocks = [s for s in ranked_stocks if s['recommendation'] == 'sell']
            
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'analysis_period_days': 60,
                'min_confidence': min_confidence,
                'summary': {
                    'total_analyzed': len(symbols),
                    'high_confidence': len(ranked_stocks),
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
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }

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
                'message': 'No stocks meet minimum confidence threshold',
                'timestamp': ranking.get('timestamp'),
            }
        
        best = all_ranked[0]
        
        return {
            'best_stock': best['symbol'],
            'recommendation': best['recommendation'],
            'confidence': best['confidence'],
            'consensus_strength': best['consensus_strength'],
            'reasoning': best['reasoning'],
            'agent_breakdown': best['agent_details'],
            'analysis_period': '60 days (2 months)',
            'timestamp': ranking.get('timestamp', datetime.now(timezone.utc).isoformat()),
        }

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
