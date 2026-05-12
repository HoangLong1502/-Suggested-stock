from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from typing import List, Annotated

from app.services.stock_ingest import load_watchlist_items, sync_market_snapshot
from app.services.agent_orchestrator import orchestrator
from app.services.recommendation_engine import recommendation_engine
from app.services.historical_analyzer import historical_analyzer
from app.services.fundamental_analyzer import fundamental_analyzer
from app.services.technical_calculator import technical_calculator
from app.services.stock_ranker import stock_ranker

router = APIRouter()


@router.get('/market/overview')
async def market_overview():
    """Get market overview with indices, watchlist, gainers, losers."""
    await sync_market_snapshot()
    watchlist_items = await load_watchlist_items()
    return JSONResponse(
        {
            'indices': [
                {'symbol': 'VNINDEX', 'price': 1200.45, 'change': 0.72},
                {'symbol': 'HNX', 'price': 310.12, 'change': -0.18},
                {'symbol': 'UPCOM', 'price': 82.92, 'change': 0.15},
            ],
            'watchlist': watchlist_items,
            'top_gainers': [
                {'symbol': 'VNM', 'change': 4.5},
                {'symbol': 'SSI', 'change': 3.8},
            ],
            'top_losers': [
                {'symbol': 'AAA', 'change': -5.4},
                {'symbol': 'XYZ', 'change': -3.2},
            ],
            'sector_heatmap': [
                {'sector': 'Banking', 'strength': 0.7},
                {'sector': 'Real Estate', 'strength': 0.3},
            ],
        }
    )


@router.get('/stock/{symbol}')
async def stock_detail(symbol: str):
    """Get detailed stock information with all analyses."""
    symbol = symbol.upper()
    
    try:
        # Get historical analysis
        hist_analysis = await historical_analyzer.full_historical_analysis(symbol, days=60)
        
        # Get business analysis
        business_analysis = await fundamental_analyzer.full_business_analysis(symbol)
        
        # Get technical indicators
        prices = await historical_analyzer.get_historical_prices(symbol, days=60)
        if prices:
            tech_indicators = await technical_calculator.calculate_all_indicators(prices)
        else:
            tech_indicators = {}

        return JSONResponse({
            'symbol': symbol,
            'timestamp': hist_analysis.get('timestamp') or business_analysis.get('timestamp'),
            'historical_analysis': hist_analysis,
            'business_analysis': business_analysis,
            'technical_indicators': tech_indicators,
        })
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


@router.get('/agents/{symbol}/recommendation')
async def recommendation(symbol: str):
    """Get AI recommendation with buy/sell timing."""
    symbol = symbol.upper()
    
    try:
        # Run agent pipeline
        agent_results = await orchestrator.run_stock_pipeline(symbol)
        
        # Generate full recommendation with entry/exit points
        full_recommendation = await recommendation_engine.generate_full_recommendation(
            symbol,
            agent_results,
        )
        
        return JSONResponse(full_recommendation)
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


@router.get('/agents/{symbol}/detailed-analysis')
async def detailed_analysis(symbol: str):
    """Get detailed AI analysis breakdown."""
    symbol = symbol.upper()
    
    try:
        agent_results = await orchestrator.run_stock_pipeline(symbol)
        
        return JSONResponse({
            'symbol': symbol,
            'agents': agent_results['agents'],
            'decision': agent_results['decision'],
            'timestamp': agent_results['timestamp'],
        })
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


@router.get('/agents/suggest')
async def suggest_stock():
    """Get top suggested stocks by confidence score."""
    from app.services.stock_ingest import load_watchlist_symbols
    
    symbols = await load_watchlist_symbols()
    results = []

    for symbol in symbols[:8]:
        try:
            agent_results = await orchestrator.run_stock_pipeline(symbol)
            decision = agent_results.get('decision', {})
            score = float(decision.get('score', 0.0))
            verdict = decision.get('verdict', 'hold')
            
            if score >= 0.6:  # Only include high confidence suggestions
                results.append({
                    'symbol': symbol,
                    'verdict': verdict,
                    'confidence': round(score * 100, 1),
                    'rationale': decision.get('rationale', ''),
                })
        except Exception:
            continue

    # Sort by confidence descending
    results.sort(key=lambda x: x['confidence'], reverse=True)
    
    return JSONResponse({
        'suggestions': results[:5],
        'count': len(results),
        'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
    })


@router.get('/agents/debate/{symbol}')
async def get_debate(symbol: str):
    """Get AI debate room - see how all agents analyzed the stock."""
    symbol = symbol.upper()
    
    try:
        agent_results = await orchestrator.run_stock_pipeline(symbol)
        
        debate = [
            {
                'agent': agent['agent'],
                'verdict': agent['verdict'],
                'confidence': round(agent['score'] * 100, 1),
                'rationale': agent['rationale'],
                'details': agent.get('extra', {}),
            }
            for agent in agent_results.get('agents', [])
        ]
        
        decision = agent_results.get('decision', {})
        
        return JSONResponse({
            'symbol': symbol,
            'debate': debate,
            'consensus': {
                'verdict': decision.get('verdict', 'hold'),
                'confidence': round(decision.get('score', 0.0) * 100, 1),
                'reasoning': decision.get('rationale', ''),
                'consensus_strength': round(decision.get('extra', {}).get('consensus_strength', 0) * 100, 1),
            },
            'timestamp': agent_results.get('timestamp'),
        })
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


@router.get('/technical/{symbol}')
async def technical_analysis(symbol: str):
    """Get technical indicators analysis."""
    symbol = symbol.upper()
    
    try:
        prices = await historical_analyzer.get_historical_prices(symbol, days=60)
        
        if not prices:
            return JSONResponse({'error': 'No price data'}, status_code=404)
        
        indicators = await technical_calculator.calculate_all_indicators(prices)
        
        return JSONResponse({
            'symbol': symbol,
            'indicators': indicators,
        })
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


@router.get('/fundamental/{symbol}')
async def fundamental_analysis(symbol: str):
    """Get business/fundamental analysis."""
    symbol = symbol.upper()
    
    try:
        analysis = await fundamental_analyzer.full_business_analysis(symbol)
        
        return JSONResponse(analysis)
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


@router.get('/historical/{symbol}')
async def historical_analysis(symbol: str):
    """Get historical price analysis."""
    symbol = symbol.upper()
    
    try:
        analysis = await historical_analyzer.full_historical_analysis(symbol, days=60)
        
        return JSONResponse(analysis)
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


# ============================================================
# NEW ENDPOINTS: AI Agents Ranking & Best Stock Selection
# ============================================================

@router.get('/agents/best-stock')
async def get_best_stock():
    """
    🎯 Get the single BEST stock based on 2 months (60 days) AI analysis.
    Multiple AI agents collaborate to analyze all watched stocks.
    
    Returns the stock with highest confidence consensus.
    """
    try:
        result = await stock_ranker.get_best_stock()
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


@router.get('/agents/top-stocks')
async def get_top_stocks(
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
    min_confidence: Annotated[float, Query(ge=0.0, le=1.0)] = 0.65
):
    """
    🏆 Get ranked list of best stocks based on 2 months AI analysis.
    
    Multiple AI agents analyze each stock and reach consensus.
    Results are ranked by confidence score.
    
    Args:
        limit: Number of top stocks to return (1-20)
        min_confidence: Minimum confidence threshold (0.0-1.0)
    
    Returns:
        List of top stocks ranked by confidence, grouped by recommendation type
    """
    try:
        ranking = await stock_ranker.rank_all_stocks(min_confidence=min_confidence)
        
        if ranking.get('status') == 'error':
            return JSONResponse(ranking, status_code=500)
        
        # Limit results
        all_ranked = ranking.get('all_ranked', [])[:limit]
        buy_stocks = ranking.get('top_buy_stocks', [])[:limit]
        hold_stocks = ranking.get('hold_stocks', [])[:limit]
        sell_stocks = ranking.get('sell_stocks', [])[:limit]
        
        return JSONResponse({
            'timestamp': ranking.get('timestamp'),
            'analysis_period_days': 60,
            'analysis_period_text': '2 months',
            'min_confidence_threshold': min_confidence,
            'summary': ranking.get('summary', {}),
            'best_stock': all_ranked[0]['symbol'] if all_ranked else None,
            'buy_recommendations': buy_stocks,
            'hold_recommendations': hold_stocks,
            'sell_recommendations': sell_stocks,
            'all_ranked': all_ranked,
        })
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


@router.post('/agents/compare-stocks')
async def compare_stocks_endpoint(symbols: Annotated[List[str], Query()]):
    """
    ⚖️ Compare multiple stocks side-by-side based on 2 months AI analysis.
    
    See how each AI agent rates each stock and compare consensus.
    
    Args:
        symbols: List of stock symbols to compare (e.g., ?symbols=VNM&symbols=SSI&symbols=ACB)
    
    Returns:
        Detailed comparison of all stocks with agent breakdown
    """
    try:
        if not symbols or len(symbols) < 2:
            return JSONResponse(
                {'error': 'Please provide at least 2 symbols to compare'},
                status_code=400
            )
        
        if len(symbols) > 10:
            return JSONResponse(
                {'error': 'Maximum 10 symbols can be compared at once'},
                status_code=400
            )
        
        result = await stock_ranker.compare_stocks(symbols)
        
        if result.get('status') == 'error':
            return JSONResponse(result, status_code=500)
        
        return JSONResponse({
            'timestamp': result.get('timestamp'),
            'analysis_period': result.get('analysis_period'),
            'best_stock': result.get('best_stock'),
            'comparison': result.get('comparison', []),
        })
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


@router.get('/agents/consensus-debate/{symbol}')
async def consensus_debate(symbol: str):
    """
    💬 Get detailed AI agent debate for a specific stock.
    
    See how different agents with different perspectives analyze the same stock
    over 2 months of data. Shows where they agree and disagree.
    
    Shows:
    - Individual agent analysis (Market Scanner, Business Analyst, Technical Analyst, etc.)
    - Confidence levels from each agent
    - Points of agreement and disagreement
    - Final consensus verdict
    - Consensus strength (0-100%)
    """
    symbol = symbol.upper()
    
    try:
        agent_results = await orchestrator.run_stock_pipeline(symbol)
        agents = agent_results.get('agents', [])
        decision = agent_results.get('decision', {})
        
        # Organize debate
        return JSONResponse({
            'symbol': symbol,
            'analysis_period': '60 days (2 months)',
            'agents_involved': [
                'MarketScanner (Trend & Momentum)',
                'BusinessAnalyst (Fundamentals)',
                'TechnicalAnalyst (Technical Indicators)',
                'SentimentAnalysis (Market Sentiment)',
                'RiskManagement (Risk Assessment)',
            ],
            'individual_analyses': [
                {
                    'agent': agent['agent'],
                    'verdict': agent['verdict'].upper(),
                    'confidence': round(agent['score'] * 100, 1),
                    'rationale': agent['rationale'],
                    'key_points': agent.get('extra', {}),
                }
                for agent in agents
            ],
            'consensus': {
                'verdict': decision.get('verdict', 'hold').upper(),
                'confidence': round(decision.get('score', 0.0) * 100, 1),
                'consensus_strength': round(
                    decision.get('extra', {}).get('consensus_strength', 0) * 100, 1
                ),
                'consensus_quality': decision.get('extra', {}).get('consensus_quality', ''),
                'agent_votes': {
                    'buy': decision.get('extra', {}).get('buy_agents', 0),
                    'hold': decision.get('extra', {}).get('hold_agents', 0),
                    'sell': decision.get('extra', {}).get('sell_agents', 0),
                },
                'overall_reasoning': decision.get('rationale', ''),
            },
            'timestamp': agent_results.get('timestamp'),
        })
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)
