"""
Lọc sơ bộ watchlist — nhận diện đủ kịch bản trước pipeline 5 agent.
"""
from __future__ import annotations

import asyncio
import statistics
from typing import Any, Dict, List, Optional, Tuple

from app.services.historical_analyzer import HistoricalAnalyzer, historical_analyzer
from app.services.stock_ingest import batch_ohlc_day_pct

MIN_POTENTIAL_SCORE = 42.0  # thang 0–100
MAX_DEEP_ANALYSIS = 8
SCAN_CONCURRENCY = 14

# case_id → (label_vi, mặc định có qua lọc không)
CASE_META: Dict[str, Dict[str, Any]] = {
    'uptrend_healthy': {'label_vi': 'Xu hướng tăng lành mạnh', 'default_pass': True, 'action_hint': 'buy'},
    'breakout_volume': {'label_vi': 'Breakout / volume đột biến tích cực', 'default_pass': True, 'action_hint': 'buy'},
    'pullback_uptrend': {'label_vi': 'Chỉnh trong xu hướng tăng dài hạn', 'default_pass': True, 'action_hint': 'buy'},
    'whale_shakeout_recovery': {
        'label_vi': 'Cá voi xả rồi hồi (shakeout / gom hàng)',
        'default_pass': True,
        'action_hint': 'buy',
    },
    'bottom_fishing': {
        'label_vi': 'Bắt đáy — gần hỗ trợ + oversold + bắt đầu hồi',
        'default_pass': True,
        'action_hint': 'buy',
    },
    'oversold_bounce': {'label_vi': 'Oversold — đang hồi kỹ thuật', 'default_pass': True, 'action_hint': 'buy'},
    'sideways_accumulation': {'label_vi': 'Đi ngang — tích lũy / chờ breakout', 'default_pass': True, 'action_hint': 'hold'},
    'top_distribution': {
        'label_vi': 'Bán đỉnh — gần kháng cự + quá mua + yếu dần',
        'default_pass': False,
        'action_hint': 'sell',
    },
    'neutral_watch': {'label_vi': 'Trung tính — theo dõi thêm', 'default_pass': False, 'action_hint': 'hold'},
    'overextended_risk': {'label_vi': 'Quá mua / kéo giá — rủi ro chỉnh', 'default_pass': False, 'action_hint': 'sell'},
    'true_downtrend': {'label_vi': 'Giảm xu hướng thật — tránh (không bắt đáy)', 'default_pass': False, 'action_hint': 'avoid'},
    'panic_sell': {'label_vi': 'Bán tháo / lao dốc mạnh', 'default_pass': False, 'action_hint': 'avoid'},
    'low_liquidity': {'label_vi': 'Thanh khoản thấp', 'default_pass': False, 'action_hint': 'avoid'},
    'no_data': {'label_vi': 'Thiếu dữ liệu', 'default_pass': False, 'action_hint': 'avoid'},
    'error': {'label_vi': 'Lỗi phân tích', 'default_pass': False, 'action_hint': 'avoid'},
}


def _detect_bottom_fishing(
    sr: Dict[str, Any],
    ob: Dict[str, Any],
    momentum: Dict[str, Any],
    prices: List[Dict[str, Any]],
    day_pct: Optional[float],
) -> bool:
    """Bắt đáy: sát hỗ trợ + vùng oversold + tín hiệu hồi (không lao dốc)."""
    dist_sup = float(sr.get('distance_to_support_pct') or 99)
    ob_cond = ob.get('condition', '')
    r5 = float(momentum.get('return_5d') or 0)
    if len(prices) < 5:
        return False
    closes = [float(p['close']) for p in prices]
    turning = closes[-1] >= closes[-2] or (day_pct is not None and day_pct > 0.2)
    return (
        dist_sup <= 5.0
        and ob_cond in ('oversold', 'underextended')
        and turning
        and r5 > -7.0
        and float(momentum.get('score') or 0) > -0.15
    )


def _detect_sell_top(
    sr: Dict[str, Any],
    ob: Dict[str, Any],
    momentum: Dict[str, Any],
    day_pct: Optional[float],
) -> bool:
    """Bán đỉnh: sát kháng cự + quá mua / kéo giá + momentum suy yếu."""
    dist_res = float(sr.get('distance_to_resistance_pct') or 99)
    ob_cond = ob.get('condition', '')
    r5 = float(momentum.get('return_5d') or 0)
    r10 = float(momentum.get('return_10d') or 0)
    weakening = r5 < r10 or (day_pct is not None and day_pct < 0)
    return (
        dist_res <= 4.5
        and ob_cond in ('overbought', 'overextended')
        and weakening
    )


def _volume_profile(prices: List[Dict[str, Any]]) -> Dict[str, Any]:
    if len(prices) < 5:
        return {'trend': 'insufficient', 'volume_ratio': 1.0, 'dump_volume_spike': False}
    volumes = [float(p.get('volume') or 0) for p in prices]
    avg_vol = statistics.mean(volumes) if volumes else 1.0
    recent = volumes[-5:]
    last_vol = volumes[-1]
    recent_avg = statistics.mean(recent) if recent else avg_vol
    ratio = last_vol / (avg_vol + 1e-9)
    dump_spike = any(v > avg_vol * 1.45 for v in recent[:-1]) if len(recent) > 1 else False
    if last_vol > recent_avg * 1.5:
        trend = 'spike'
    elif last_vol > recent_avg * 1.1:
        trend = 'above_average'
    elif last_vol < recent_avg * 0.65:
        trend = 'below_average'
    else:
        trend = 'normal'
    return {
        'trend': trend,
        'volume_ratio': round(ratio, 2),
        'dump_volume_spike': dump_spike,
        'avg_volume': round(avg_vol, 0),
    }


def _detect_whale_shakeout(
    prices: List[Dict[str, Any]],
    momentum: Dict[str, Any],
    day_pct: Optional[float],
) -> bool:
    """Giảm nhanh có volume + bắt đầu hồi — không cần dữ liệu tick whale."""
    if len(prices) < 25:
        return False
    closes = [float(p['close']) for p in prices]
    r30 = float(momentum.get('return_30d') or 0)
    r5 = float(momentum.get('return_5d') or 0)
    r10 = float(momentum.get('return_10d') or 0)

    peak_20 = max(closes[-22:-5]) if len(closes) >= 22 else max(closes[:-5])
    trough_5 = min(closes[-8:])
    current = closes[-1]
    dump_depth = (peak_20 - trough_5) / (peak_20 + 1e-9) * 100
    recovery_from_trough = (current - trough_5) / (trough_5 + 1e-9) * 100

    vol = _volume_profile(prices)
    last_green = len(closes) >= 2 and closes[-1] >= closes[-2]
    day_recovering = day_pct is not None and day_pct > 0.3

    return (
        dump_depth >= 4.0
        and (r30 > -8 or r10 > r5)
        and vol.get('dump_volume_spike')
        and (last_green or day_recovering or r5 > -2)
        and recovery_from_trough >= 0.5
        and float(momentum.get('score') or 0) > -0.12
    )


def _detect_pullback_uptrend(momentum: Dict[str, Any], trend: Dict[str, Any]) -> bool:
    r30 = float(momentum.get('return_30d') or 0)
    r5 = float(momentum.get('return_5d') or 0)
    return r30 >= 4.0 and r5 <= 1.5 and r5 >= -6.0 and trend.get('direction') in ('downtrend', 'sideways')


def _classify_case(
    hist: Dict[str, Any],
    prices: List[Dict[str, Any]],
    day_pct: Optional[float],
) -> Dict[str, Any]:
    """Gán 1 case chính + điểm 0–100 và quyết định pass."""
    trend = hist.get('trend') or {}
    momentum = hist.get('momentum') or {}
    ob = hist.get('overbought_oversold') or {}
    sr = hist.get('support_resistance') or {}
    vol_hist = hist.get('volatility') or {}
    vol_prof = _volume_profile(prices)

    direction = trend.get('direction', 'sideways')
    mom_label = momentum.get('momentum', 'neutral')
    mom_score = float(momentum.get('score') or 0.0)
    r5 = float(momentum.get('return_5d') or 0)
    r10 = float(momentum.get('return_10d') or 0)
    r30 = float(momentum.get('return_30d') or 0)
    ob_cond = ob.get('condition', 'balanced')
    day_pct = float(day_pct) if day_pct is not None else None

    signals: List[str] = []
    score = 50.0

    # --- Ưu tiên case đặc biệt (thứ tự quan trọng) ---
    if _detect_sell_top(sr, ob, momentum, day_pct):
        case_id = 'top_distribution'
        score = 38 + min(12, 4.5 - float(sr.get('distance_to_resistance_pct') or 4))
        signals = [
            f"gần kháng cự {sr.get('resistance')}",
            ob_cond,
            'momentum suy yếu — cân nhắc chốt lời / bán đỉnh',
        ]

    elif _detect_bottom_fishing(sr, ob, momentum, prices, day_pct):
        case_id = 'bottom_fishing'
        score = 68 + min(12, 5.0 - float(sr.get('distance_to_support_pct') or 5))
        signals = [
            f"gần hỗ trợ {sr.get('support')}",
            ob_cond,
            'bắt đáy có xác nhận hồi',
        ]

    elif _detect_whale_shakeout(prices, momentum, day_pct):
        case_id = 'whale_shakeout_recovery'
        score = 62 + min(15, r5 + 5) + (8 if vol_prof.get('dump_volume_spike') else 0)
        signals = ['có nhịp xả volume', 'đang hồi sau đáy', f'30d: {r30:.1f}%']

    elif day_pct is not None and day_pct <= -6.0 and mom_label in ('strong_bearish', 'bearish'):
        case_id = 'panic_sell'
        score = 18
        signals = [f'la dốc {day_pct:.1f}%', f'momentum {mom_label}']

    elif direction == 'downtrend' and mom_label == 'strong_bearish' and r30 < -5:
        case_id = 'true_downtrend'
        score = 22 + max(0, r30 + 5)
        signals = ['xu hướng giảm', 'momentum yếu dài hạn']

    elif ob_cond in ('overbought', 'overextended') and r5 < 0 and day_pct is not None and day_pct < 0:
        case_id = 'overextended_risk'
        score = 35
        signals = [f'vùng {ob_cond}', 'điều chỉnh ngắn hạn']

    elif vol_prof.get('trend') == 'below_average' and vol_prof.get('volume_ratio', 1) < 0.55:
        case_id = 'low_liquidity'
        score = 30
        signals = ['khối lượng thấp']

    elif _detect_pullback_uptrend(momentum, trend):
        case_id = 'pullback_uptrend'
        score = 58 + min(12, r30 / 2)
        signals = [f'30d +{r30:.1f}%', f'chỉnh 5d {r5:.1f}%']

    elif ob_cond in ('oversold', 'underextended') and (day_pct is None or day_pct >= -1.5):
        case_id = 'oversold_bounce'
        score = 55 + (10 if day_pct and day_pct > 0 else 0)
        signals = [f'{ob_cond}', 'có thể hồi kỹ thuật']

    elif direction == 'uptrend' and mom_label in ('bullish', 'strong_bullish', 'neutral'):
        case_id = 'uptrend_healthy'
        score = 65 + float(trend.get('strength') or 0) * 20 + mom_score * 15
        signals = ['xu hướng tăng', f'momentum {mom_label}']

    elif vol_prof.get('trend') in ('spike', 'above_average') and (
        day_pct is None or day_pct > 0 or mom_score > 0
    ):
        case_id = 'breakout_volume'
        score = 60 + min(10, (vol_prof.get('volume_ratio') or 1) * 3)
        signals = [f"volume {vol_prof.get('trend')}", f'KL ratio {vol_prof.get("volume_ratio")}x']

    elif direction == 'sideways':
        case_id = 'sideways_accumulation'
        score = 48 + (8 if vol_prof.get('trend') in ('spike', 'above_average') else 0)
        signals = ['đi ngang', 'chờ hướng rõ']

    else:
        case_id = 'neutral_watch'
        score = 45 + mom_score * 12
        signals = [f'{direction}', f'momentum {mom_label}']

    if day_pct is not None:
        if day_pct >= 2.5:
            score += 4
            signals.append(f'phiên +{day_pct:.1f}%')
        elif day_pct <= -4.0 and case_id not in ('panic_sell', 'true_downtrend'):
            score -= 8
            signals.append(f'phiên {day_pct:.1f}%')

    if vol_hist.get('level') == 'high' and case_id not in ('panic_sell',):
        score -= 3
        signals.append('biến động cao')

    score = round(max(0.0, min(100.0, score)), 1)
    meta = CASE_META.get(case_id, CASE_META['neutral_watch'])
    action_hint = str(meta.get('action_hint', 'hold'))
    default_pass = bool(meta.get('default_pass'))

    # Bán đỉnh: không đưa vào pipeline MUA (best pick)
    if case_id == 'top_distribution':
        passed = False
        action_hint = 'sell'
    elif case_id in ('panic_sell', 'true_downtrend', 'no_data', 'error', 'low_liquidity'):
        passed = False
        action_hint = 'avoid'
    elif case_id in (
        'bottom_fishing',
        'whale_shakeout_recovery',
        'uptrend_healthy',
        'breakout_volume',
        'pullback_uptrend',
        'oversold_bounce',
    ):
        passed = score >= MIN_POTENTIAL_SCORE - 5
        action_hint = 'buy'
    elif case_id == 'sideways_accumulation':
        passed = score >= MIN_POTENTIAL_SCORE
        action_hint = 'hold'
    elif case_id == 'overextended_risk':
        passed = False
        action_hint = 'sell'
    else:
        passed = default_pass and score >= MIN_POTENTIAL_SCORE

    return {
        'case_id': case_id,
        'case_label_vi': meta.get('label_vi', case_id),
        'action_hint': action_hint,
        'passed': passed,
        'potential_score': score,
        'filter_reason': case_id if not passed else 'passed',
        'filter_reason_vi': meta.get('label_vi', '') if not passed else 'Đủ điều kiện phân tích sâu',
        'signals': signals,
        'support': sr.get('support'),
        'resistance': sr.get('resistance'),
        'distance_to_support_pct': sr.get('distance_to_support_pct'),
        'distance_to_resistance_pct': sr.get('distance_to_resistance_pct'),
        'volume_trend': vol_prof.get('trend'),
        'volume_ratio': vol_prof.get('volume_ratio'),
    }


async def quick_scan_symbol(symbol: str, day_pct: float | None = None) -> Dict[str, Any]:
    """Đánh giá nhanh 1 mã — phân loại đủ case thị trường."""
    sym = symbol.upper().strip()
    try:
        prices = await historical_analyzer.get_historical_prices(sym, days=60)
        if not prices or len(prices) < 10:
            meta = CASE_META['no_data']
            return {
                'symbol': sym,
                'passed': False,
                'potential_score': 0.0,
                'case_id': 'no_data',
                'case_label_vi': meta['label_vi'],
                'filter_reason': 'no_data',
                'filter_reason_vi': meta['label_vi'],
                'signals': [],
            }

        hist = {
            'trend': HistoricalAnalyzer.calculate_trend(prices),
            'momentum': HistoricalAnalyzer.calculate_price_momentum(prices),
            'overbought_oversold': HistoricalAnalyzer.identify_overbought_oversold(prices),
            'volatility': HistoricalAnalyzer.calculate_volatility(prices),
            'support_resistance': HistoricalAnalyzer.detect_support_resistance(prices),
        }
        classified = _classify_case(hist, prices, day_pct)
        trend = hist['trend']
        momentum = hist['momentum']

        return {
            'symbol': sym,
            'passed': classified['passed'],
            'potential_score': classified['potential_score'],
            'case_id': classified['case_id'],
            'case_label_vi': classified['case_label_vi'],
            'filter_reason': classified['filter_reason'],
            'filter_reason_vi': classified['filter_reason_vi'],
            'signals': classified['signals'],
            'trend': trend.get('direction'),
            'momentum': momentum.get('momentum'),
            'return_5d': momentum.get('return_5d'),
            'return_30d': momentum.get('return_30d'),
            'day_change_pct': day_pct,
            'action_hint': classified.get('action_hint'),
            'support': classified.get('support'),
            'resistance': classified.get('resistance'),
            'distance_to_support_pct': classified.get('distance_to_support_pct'),
            'distance_to_resistance_pct': classified.get('distance_to_resistance_pct'),
            'volume_trend': classified.get('volume_trend'),
            'volume_ratio': classified.get('volume_ratio'),
        }
    except Exception as exc:
        return {
            'symbol': sym,
            'passed': False,
            'potential_score': 0.0,
            'case_id': 'error',
            'case_label_vi': CASE_META['error']['label_vi'],
            'filter_reason': 'error',
            'filter_reason_vi': str(exc),
            'signals': [],
        }


async def scan_watchlist(
    symbols: List[str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Quét watchlist. Returns: (mua/đáy → phân tích sâu, bán đỉnh, loại)."""
    syms = list(dict.fromkeys(s.strip().upper() for s in symbols if s and str(s).strip()))
    if not syms:
        return [], [], []

    ohlc = await batch_ohlc_day_pct(syms)
    sem = asyncio.Semaphore(SCAN_CONCURRENCY)

    async def run_one(sym: str) -> Dict[str, Any]:
        async with sem:
            pct_row = ohlc.get(sym)
            day_pct = float(pct_row['pct']) if pct_row else None
            return await quick_scan_symbol(sym, day_pct=day_pct)

    results = await asyncio.gather(*[run_one(s) for s in syms], return_exceptions=True)
    rows: List[Dict[str, Any]] = []
    for i, sym in enumerate(syms):
        if isinstance(results[i], Exception):
            rows.append(
                {
                    'symbol': sym,
                    'passed': False,
                    'potential_score': 0.0,
                    'case_id': 'error',
                    'case_label_vi': CASE_META['error']['label_vi'],
                    'filter_reason': 'error',
                    'filter_reason_vi': str(results[i]),
                    'signals': [],
                }
            )
        else:
            rows.append(results[i])

    sell_top = sorted(
        [r for r in rows if r.get('action_hint') == 'sell'],
        key=lambda x: x['potential_score'],
        reverse=True,
    )
    passed = sorted(
        [r for r in rows if r.get('passed') and r.get('action_hint') in ('buy', 'hold')],
        key=lambda x: x['potential_score'],
        reverse=True,
    )
    excluded = sorted(
        [r for r in rows if not r.get('passed') and r.get('action_hint') not in ('sell',)],
        key=lambda x: x['potential_score'],
        reverse=True,
    )
    return passed, sell_top, excluded


def deep_analysis_symbols(passed: List[Dict[str, Any]], limit: int = MAX_DEEP_ANALYSIS) -> List[str]:
    """Top mã sau lọc — ưu tiên case đặc biệt rồi điểm."""
    priority_cases = {
        'bottom_fishing',
        'whale_shakeout_recovery',
        'uptrend_healthy',
        'breakout_volume',
        'pullback_uptrend',
        'oversold_bounce',
    }

    def sort_key(r: Dict[str, Any]) -> Tuple[int, float]:
        cid = r.get('case_id') or ''
        pri = 0 if cid in priority_cases else 1
        return (pri, -float(r.get('potential_score') or 0))

    ordered = sorted(passed, key=sort_key)
    return [p['symbol'] for p in ordered[:limit] if p.get('symbol')]


def list_all_cases() -> List[Dict[str, Any]]:
    """Metadata cho UI / docs."""
    return [
        {
            'id': k,
            'label_vi': v['label_vi'],
            'default_pass': v['default_pass'],
            'action_hint': v.get('action_hint', 'hold'),
        }
        for k, v in CASE_META.items()
    ]
