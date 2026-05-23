import asyncio
import time
from typing import List, Annotated, Any, Dict, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.models.postgres import AsyncSessionLocal
from app.models.schema import Stock
from app.services.stock_ingest import (
    DEFAULT_WATCHLIST,
    QUOTE_MAX_DELAY_SECONDS,
    SYNC_TTL_SECONDS,
    VN_INDEX_SYMBOLS,
    batch_ohlc_day_pct,
    load_watchlist_items,
    sync_market_snapshot,
    sync_market_snapshot_if_stale,
    vietnam_market_session,
)
from app.services.agent_orchestrator import orchestrator
from app.services.recommendation_engine import recommendation_engine
from app.services.historical_analyzer import historical_analyzer
from app.services.demo_seed import ensure_demo_historical_data, ensure_watchlist_historical_gaps
from app.services.fundamental_analyzer import fundamental_analyzer
from app.services.technical_calculator import technical_calculator
from app.services.investment_committee import build_committee_report
from app.services.stock_ranker import stock_ranker, _public_stock_row
from app.services.sector_analyzer import sector_analyzer
from app.services.vn_realtime_quotes import fetch_vci_symbol_detail
from app.services.symbol_user_brief import build_symbol_user_brief

router = APIRouter()

_overview_cache: Dict[str, Any] = {'ts': 0.0, 'body': None}
OVERVIEW_CACHE_SECONDS = 25


@router.get('/market/overview')
async def market_overview(fast: bool = Query(True, description='Bỏ qua sync VNDirect nếu vừa sync gần đây')):
    """Market overview — đọc DB nhanh; sync giá nền / theo TTL."""
    now = time.monotonic()
    cached = _overview_cache.get('body')
    if cached is not None and now - float(_overview_cache.get('ts') or 0) < OVERVIEW_CACHE_SECONDS:
        return JSONResponse(cached)

    if fast:
        # Sync VCI batch (~4s) tối đa mỗi 8–10s; không seed OHLC nặng.
        try:
            await sync_market_snapshot_if_stale()
        except Exception:
            pass
        watchlist_items = await load_watchlist_items(skip_sync=True)
    else:
        await ensure_demo_historical_data()
        await ensure_watchlist_historical_gaps()
        try:
            await sync_market_snapshot_if_stale()
            await sync_market_snapshot()
        except Exception:
            pass
        watchlist_items = await load_watchlist_items(skip_sync=False)

    async with AsyncSessionLocal() as session:
        gainers_result = await session.execute(
            select(Stock).order_by(Stock.change.desc()).limit(8)
        )
        losers_result = await session.execute(
            select(Stock).order_by(Stock.change.asc()).limit(8)
        )
        indices_result = await session.execute(
            select(Stock).where(Stock.symbol.in_(VN_INDEX_SYMBOLS))
        )
        gainer_stocks = gainers_result.scalars().all()
        loser_stocks = losers_result.scalars().all()
        index_stocks = indices_result.scalars().all()

    def _sig(pct: float) -> tuple[str, str]:
        if pct > 0.05:
            return 'bull', 'Tích cực'
        if pct < -0.05:
            return 'bear', 'Tiêu cực'
        return 'flat', 'Trung lập'

    stock_gainers = []
    for stock in gainer_stocks:
        ch = float(stock.change or 0.0)
        sig, sig_vi = _sig(ch)
        stock_gainers.append(
            {
                'symbol': stock.symbol,
                'change': ch,
                'change_pct': ch,
                'last_close': round(float(stock.last_price or 0.0), 2) if (stock.last_price or 0) > 0 else None,
                'signal': sig,
                'signal_vi': sig_vi,
            }
        )
    stock_losers = []
    for stock in loser_stocks:
        ch = float(stock.change or 0.0)
        sig, sig_vi = _sig(ch)
        stock_losers.append(
            {
                'symbol': stock.symbol,
                'change': ch,
                'change_pct': ch,
                'last_close': round(float(stock.last_price or 0.0), 2) if (stock.last_price or 0) > 0 else None,
                'signal': sig,
                'signal_vi': sig_vi,
            }
        )

    mover_symbols = list(
        dict.fromkeys(
            [
                *[str(it.get('symbol', '')).upper() for it in watchlist_items if it.get('symbol')],
                *DEFAULT_WATCHLIST,
            ],
        ),
    )
    hg, hl = await historical_analyzer.snapshot_movers_from_db(8, symbols=mover_symbols)
    top_gainers = hg if hg else stock_gainers
    top_losers = hl if hl else stock_losers
    if not top_gainers or all(abs(float(g.get('change') or 0)) < 1e-6 for g in top_gainers):
        if hg:
            top_gainers = hg
    if not top_losers or all(abs(float(g.get('change') or 0)) < 1e-6 for g in top_losers):
        if hl:
            top_losers = hl

    stock_map = {str(stock.symbol).strip().upper(): stock for stock in index_stocks}
    indices: List[Dict[str, Any]] = []
    for symbol in VN_INDEX_SYMBOLS:
        st = stock_map.get(symbol)
        if st is not None:
            indices.append(
                {
                    'symbol': symbol,
                    'price': float(st.last_price or 0.0),
                    'change': float(st.change or 0.0),
                }
            )
        else:
            indices.append({'symbol': symbol, 'price': 0.0, 'change': 0.0})

    idx_hist = await batch_ohlc_day_pct(VN_INDEX_SYMBOLS)
    for row in indices:
        h = idx_hist.get(row['symbol'])
        if not h:
            continue
        if row['price'] <= 0:
            row['price'] = float(h['close'])
        if abs(float(row['change'] or 0)) < 1e-9:
            row['change'] = float(h.get('pct') or 0.0)

    chart_preview = await historical_analyzer.sparkline_series(VN_INDEX_SYMBOLS[0], 7)

    body = {
        'indices': indices,
        'watchlist': watchlist_items,
        'top_gainers': top_gainers,
        'top_losers': top_losers,
        'chart_preview': chart_preview,
        'sector_heatmap': [
            {'sector': 'Banking', 'strength': 0.7},
            {'sector': 'Real Estate', 'strength': 0.3},
        ],
        'market_session': vietnam_market_session(),
        'quote_source': (
            f'Giá watchlist: vnstock/VCI realtime (~{SYNC_TTL_SECONDS}s/lần, trễ ≤{QUOTE_MAX_DELAY_SECONDS}s). '
            'Fallback VNDirect finho hoặc OHLC demo khi thiếu mã.'
        ),
    }
    _overview_cache['body'] = body
    _overview_cache['ts'] = time.monotonic()
    return JSONResponse(body)


@router.get('/market/stock/{symbol}')
async def stock_symbol_detail(symbol: str):
    """Chi tiết 1 mã: trần/sàn/TC, sổ lệnh, áp lực mua-bán (VCI / vnstock)."""
    sym = symbol.strip().upper()
    detail = await fetch_vci_symbol_detail(sym)
    if detail:
        detail['market_session'] = vietnam_market_session()
        return JSONResponse(detail)

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Stock).where(Stock.symbol == sym))
        st = res.scalar_one_or_none()
    if st is None:
        return JSONResponse({'error': f'Không có dữ liệu cho {sym}'}, status_code=404)

    meta = st.stock_metadata or {}
    ref = float(meta.get('refPrice') or meta.get('basicPrice') or 0)
    last = float(st.last_price or 0)
    return JSONResponse(
        {
            'symbol': sym,
            'name': st.name or sym,
            'prices': {
                'last': last,
                'reference': ref,
                'ceiling': None,
                'floor': None,
                'high': None,
                'low': None,
                'open': None,
                'avg_match': None,
            },
            'change_pct': float(st.change or 0),
            'volume': float(st.volume or 0),
            'order_flow': {
                'pressure': 'balanced',
                'pressure_label_vi': 'Chưa có sổ lệnh — chỉ dữ liệu DB',
                'bid_levels': [],
                'ask_levels': [],
            },
            'quote_source': meta.get('quote_source', 'database'),
            'market_session': vietnam_market_session(),
        },
    )


_sector_cache: Dict[str, Any] = {'ts': 0.0, 'body': None}
SECTOR_CACHE_SECONDS = 120


@router.get('/market/sectors')
async def market_sectors(
    fast: bool = Query(True, description='Bỏ gọi VNDirect finfo (mặc định nhanh, chỉ DB)'),
):
    """Phân tích ngành: % trung bình, mã dẫn dắt, tăng/giảm trong từng nhóm."""
    now = time.monotonic()
    if _sector_cache.get('body') and now - float(_sector_cache.get('ts') or 0) < SECTOR_CACHE_SECONDS:
        return JSONResponse(_sector_cache['body'])

    try:
        await ensure_demo_historical_data()
        await ensure_watchlist_historical_gaps()
        body = await sector_analyzer.build_sector_analysis(include_finfo=not fast)
        _sector_cache['body'] = body
        _sector_cache['ts'] = time.monotonic()
        return JSONResponse(body)
    except Exception as e:
        stale = _sector_cache.get('body')
        if stale is not None:
            stale = {**stale, 'stale': True, 'server_message': str(e)}
            return JSONResponse(stale)
        return JSONResponse({'error': str(e), 'sectors': []}, status_code=500)


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
        extra = decision.get('extra', {}) or {}
        timing = await recommendation_engine.generate_full_recommendation(symbol, agent_results)
        market_detail = await fetch_vci_symbol_detail(symbol)
        user_brief = await build_symbol_user_brief(
            symbol,
            agent_results,
            market_detail=market_detail,
            timing=timing,
        )

        return JSONResponse({
            'symbol': symbol,
            'user_brief': user_brief,
            'debate': debate,
            'consensus': {
                'verdict': decision.get('verdict', 'hold'),
                'confidence': round(decision.get('score', 0.0) * 100, 1),
                'reasoning': decision.get('rationale', ''),
                'overall_reasoning': decision.get('rationale', ''),
                'consensus_strength': round(extra.get('consensus_strength', 0) * 100, 1),
                'agent_votes': {
                    'buy': int(extra.get('buy_agents', 0)),
                    'hold': int(extra.get('hold_agents', 0)),
                    'sell': int(extra.get('sell_agents', 0)),
                },
            },
            'buy_timing': timing.get('buy_timing'),
            'sell_timing': timing.get('sell_timing'),
            'entry_points': timing.get('entry_points'),
            'exit_points': timing.get('exit_points'),
            'current_price': timing.get('current_price'),
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

_best_stock_cache: Dict[str, Any] = {'ts': 0.0, 'body': None}
BEST_STOCK_CACHE_SECONDS = 600
_best_stock_lock = asyncio.Lock()
_best_stock_inflight: Optional[asyncio.Task] = None


def _best_stock_degraded(message: str) -> Dict[str, Any]:
    return {
        'status': 'degraded',
        'server_message': message,
        'best_stock': None,
        'recommendation': None,
        'confidence': None,
        'analysis_period': '60 days (2 months)',
    }


@router.get('/agents/best-stock')
async def get_best_stock():
    """
    🎯 Get the single BEST stock based on 2 months (60 days) AI analysis.
    Multiple AI agents collaborate to analyze all watched stocks.
    
    Returns the stock with highest confidence consensus along with buy timing.
    """
    now = time.monotonic()
    cached = _best_stock_cache.get('body')
    if cached is not None and now - float(_best_stock_cache.get('ts') or 0) < BEST_STOCK_CACHE_SECONDS:
        return JSONResponse(cached)

    global _best_stock_inflight

    async def _compute() -> Dict[str, Any]:
        try:
            await ensure_demo_historical_data()
            result = await stock_ranker.get_best_stock()
            if result.get('status') == 'error':
                body = _best_stock_degraded(result.get('message', 'Ranking failed'))
                body['timestamp'] = result.get('timestamp')
                return body
            if result.get('status') == 'no_high_confidence_stocks':
                return result
            return result
        except Exception as e:
            return _best_stock_degraded(str(e))

    async with _best_stock_lock:
        now = time.monotonic()
        cached = _best_stock_cache.get('body')
        if cached is not None and now - float(_best_stock_cache.get('ts') or 0) < BEST_STOCK_CACHE_SECONDS:
            return JSONResponse(cached)
        if _best_stock_inflight is None:
            _best_stock_inflight = asyncio.create_task(_compute())
        task = _best_stock_inflight

    body = await task

    async with _best_stock_lock:
        if _best_stock_inflight is task:
            _best_stock_inflight = None

    if body.get('status') == 'ok':
        _best_stock_cache['body'] = body
        _best_stock_cache['ts'] = time.monotonic()
    return JSONResponse(body)


@router.get('/agents/top-stocks')
async def get_top_stocks(
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
    min_confidence: Annotated[float, Query(ge=0.0, le=1.0)] = 0.45
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
        await ensure_demo_historical_data()
        ranking = await stock_ranker.rank_all_stocks(min_confidence=min_confidence)

        if ranking.get('status') == 'error':
            return JSONResponse(
                {
                    'timestamp': ranking.get('timestamp'),
                    'status': 'degraded',
                    'server_message': ranking.get('message', 'Ranking failed'),
                    'analysis_period_days': 60,
                    'analysis_period_text': '2 months',
                    'min_confidence_threshold': min_confidence,
                    'summary': {
                        'total_analyzed': 0,
                        'high_confidence': 0,
                        'buy_signals': 0,
                        'hold_signals': 0,
                        'sell_signals': 0,
                    },
                    'best_stock': None,
                    'buy_recommendations': [],
                    'hold_recommendations': [],
                    'sell_recommendations': [],
                    'all_ranked': [],
                },
                status_code=200,
            )
        
        # Limit results (strip internal pipeline cache from JSON)
        all_ranked = [_public_stock_row(s) for s in ranking.get('all_ranked', [])[:limit]]
        buy_stocks = [_public_stock_row(s) for s in ranking.get('top_buy_stocks', [])[:limit]]
        hold_stocks = [_public_stock_row(s) for s in ranking.get('hold_stocks', [])[:limit]]
        sell_stocks = [_public_stock_row(s) for s in ranking.get('sell_stocks', [])[:limit]]
        
        committee = await build_committee_report(ranking)
        return JSONResponse({
            'timestamp': ranking.get('timestamp'),
            'analysis_period_days': 60,
            'analysis_period_text': '2 months',
            'min_confidence_threshold': min_confidence,
            'summary': ranking.get('summary', {}),
            'workflow': committee.get('workflow'),
            'pipeline': ranking.get('pipeline'),
            'scan_passed': ranking.get('scan_passed', []),
            'sell_top_candidates': ranking.get('sell_top_candidates', []),
            'excluded_stocks': ranking.get('excluded_stocks', []),
            'case_catalog': ranking.get('case_catalog', []),
            'best_stock': committee.get('best_stock') or (all_ranked[0]['symbol'] if all_ranked else None),
            'worst_stock': committee.get('worst_stock'),
            'best_pick': committee.get('best_pick'),
            'worst_pick': committee.get('worst_pick'),
            'early_sell_alerts': committee.get('early_sell_alerts', []),
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
        full_recommendation = await recommendation_engine.generate_full_recommendation(
            symbol,
            agent_results,
        )

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
            'buy_timing': full_recommendation.get('buy_timing', {}),
            'entry_points': full_recommendation.get('entry_points', {}),
            'recommended_entry': full_recommendation.get('entry_points', {}).get('recommended_entry'),
            'current_price': full_recommendation.get('current_price'),
            'technical_snapshot': full_recommendation.get('indicators_snapshot', {}),
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
