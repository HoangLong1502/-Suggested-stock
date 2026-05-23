"""
Hội đồng đầu tư — tổng hợp sau 5 agent (mô phỏng desk chứng khoán).
Best mua / Worst tránh / Cảnh báo SELL sớm khi downtrend hình thành.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.services.historical_analyzer import historical_analyzer
from app.services.recommendation_engine import recommendation_engine

AGENT_ROSTER = [
    {'id': 'MarketScanner', 'role_vi': 'Phân tích xu hướng & thanh khoản thị trường'},
    {'id': 'BusinessAnalyst', 'role_vi': 'Phân tích doanh nghiệp & định giá'},
    {'id': 'TechnicalAnalyst', 'role_vi': 'Chỉ báo kỹ thuật (RSI, MACD, BB)'},
    {'id': 'SentimentAnalysis', 'role_vi': 'Tâm lý thị trường & vị thế giá'},
    {'id': 'RiskManagement', 'role_vi': 'Rủi ro ro, stop-loss, size vị thế'},
    {'id': 'DecisionMaker', 'role_vi': 'Chủ tịch hội đồng — đồng thuận cuối'},
]

WORKFLOW_VI = [
    'Quét toàn bộ watchlist (lọc sơ bộ: bắt đáy, bán đỉnh, cá voi, downtrend…)',
    'Top mã tiềm năng → 5 agent + Chủ tịch phân tích sâu (60 ngày)',
    'Hội đồng chọn: BEST mua giá tốt, WORST tránh/downtrend, danh sách SELL sớm',
]


def _public_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in row.items() if not str(k).startswith('_')}


async def _technical_exit_plan(symbol: str, pipeline: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    try:
        full = await recommendation_engine.generate_full_recommendation(symbol, pipeline or {})
        exit_pts = full.get('exit_points') or {}
        sell_timing = full.get('sell_timing') or {}
        return {
            'current_price': full.get('current_price'),
            'exit_points': exit_pts,
            'sell_timing': sell_timing,
            'recommended_exit_price': exit_pts.get('take_profit') or exit_pts.get('stop_loss'),
            'stop_loss': exit_pts.get('stop_loss'),
            'take_profit_1': exit_pts.get('take_profit_1'),
            'take_profit_2': exit_pts.get('take_profit_2'),
            'suggested_exit_strategy': exit_pts.get('suggested_exit_strategy'),
        }
    except Exception as exc:
        return {'error': str(exc)}


async def detect_early_downtrend_sell(
    symbol: str,
    pipeline: Dict[str, Any],
    scan_meta: Optional[Dict[str, Any]] = None,
    *,
    committee_recommendation: Optional[str] = None,
    agents_buy: int = 0,
    agents_sell: int = 0,
) -> Optional[Dict[str, Any]]:
    """
    Tín hiệu SELL sớm: downtrend hình thành trước khi lỡ vùng bán đỉnh.
    Kết hợp vote agent + kỹ thuật 60 ngày.
    """
    decision = pipeline.get('decision', {})
    agents = pipeline.get('agents', [])
    verdict = str(decision.get('verdict', 'hold')).lower()
    extra = decision.get('extra', {}) or {}
    sell_votes = int(extra.get('sell_agents', 0) or agents_sell)
    buy_votes = int(extra.get('buy_agents', 0) or agents_buy)
    rec = str(committee_recommendation or verdict).lower()

    # Đồng thuận MUA — không đưa vào cảnh báo downtrend (tránh PXL vừa best vừa SELL)
    if rec == 'buy' and buy_votes >= sell_votes and verdict != 'sell':
        return None
    if rec == 'buy' and buy_votes >= 2:
        return None

    hist = await historical_analyzer.full_historical_analysis(symbol, days=60)
    if hist.get('status') == 'no_data':
        if verdict == 'sell' and sell_votes >= 2:
            return {
                'symbol': symbol,
                'urgency': 'SELL NOW',
                'action': 'sell',
                'signals': ['Đồng thuận agent SELL', f'{sell_votes} agent bán'],
                'reason_vi': 'Nhiều agent báo bán — thoát sớm dù thiếu OHLC chi tiết.',
            }
        return None

    trend = hist.get('trend', {})
    mom = hist.get('momentum', {})
    direction = trend.get('direction', '')
    mom_label = mom.get('momentum', '')
    r5 = float(mom.get('return_5d') or 0)
    r10 = float(mom.get('return_10d') or 0)

    signals: List[str] = []
    score = 0

    if direction == 'downtrend':
        score += 2
        signals.append('xu hướng giảm (MA ngắn < dài)')
    if mom_label in ('bearish', 'strong_bearish'):
        score += 2
        signals.append(f'momentum {mom_label}')
    if r5 < -2.5 and r5 < r10:
        score += 2
        signals.append(f'đảo chiều: 5d {r5:.1f}%')
    if verdict == 'sell':
        score += 2
        signals.append('Chủ tịch HĐ: SELL')
    if sell_votes >= 3:
        score += 2
        signals.append(f'{sell_votes}/5 agent chọn BÁN')
    elif sell_votes >= 2 and buy_votes == 0:
        score += 1
        signals.append(f'{sell_votes} agent bán, không có MUA')

    scan_id = (scan_meta or {}).get('case_id', '')
    if scan_id in ('true_downtrend', 'panic_sell', 'top_distribution'):
        score += 2
        signals.append((scan_meta or {}).get('case_label_vi', scan_id))

    for ag in agents:
        if ag.get('verdict') == 'sell' and ag.get('agent') in ('TechnicalAnalyst', 'MarketScanner'):
            score += 1
            signals.append(f"{ag['agent']}: SELL")

    if score < 3:
        return None

    if score >= 6 or (verdict == 'sell' and sell_votes >= 3):
        urgency = 'SELL NOW'
    elif score >= 4:
        urgency = 'SELL ON WEAKNESS'
    else:
        urgency = 'REDUCE / HEDGE'

    return {
        'symbol': symbol,
        'urgency': urgency,
        'action': 'sell',
        'risk_score': min(100, score * 12),
        'signals': list(dict.fromkeys(signals))[:8],
        'reason_vi': (
            'Downtrend / đảo chiều đang hình thành — hội đồng khuyên thoát trước khi mất vùng bán đỉnh. '
            + '; '.join(signals[:4])
        ),
        'trend': direction,
        'momentum': mom_label,
    }


def select_best_pick(
    all_ranked: List[Dict[str, Any]],
    *,
    exclude_symbols: Optional[set[str]] = None,
) -> Optional[Dict[str, Any]]:
    if not all_ranked:
        return None
    blocked = {str(s).upper() for s in (exclude_symbols or set())}

    def _ok(row: Dict[str, Any]) -> bool:
        sym = str(row.get('symbol', '')).upper()
        if not sym or sym in blocked:
            return False
        if str(row.get('recommendation', '')).lower() == 'sell':
            return False
        return True

    buy_first = [s for s in all_ranked if _ok(s) and s.get('recommendation') == 'buy']
    bottom_first = [
        s
        for s in all_ranked
        if _ok(s)
        and s.get('scan_case_id') in ('bottom_fishing', 'whale_shakeout_recovery', 'oversold_bounce')
        and int(s.get('agents_sell', 0) or 0) < int(s.get('agents_buy', 0) or 0)
    ]
    hold_ok = [s for s in all_ranked if _ok(s) and str(s.get('recommendation', '')).lower() == 'hold']
    if buy_first:
        return buy_first[0]
    if bottom_first:
        return bottom_first[0]
    if hold_ok:
        return hold_ok[0]
    return None


def select_worst_pick(
    all_ranked: List[Dict[str, Any]],
    sell_top_scan: List[Dict[str, Any]],
    scan_excluded: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Mã rủi ro downtrend cao nhất — ưu tiên SELL từ agent rồi lọc scan."""
    candidates: List[Tuple[float, Dict[str, Any]]] = []

    for row in all_ranked:
        sym = row.get('symbol')
        if not sym:
            continue
        sell_v = int(row.get('agents_sell', 0))
        rec = str(row.get('recommendation', '')).lower()
        conf = float(row.get('confidence', 50))
        risk = 0.0
        if rec == 'sell':
            risk += 50 + sell_v * 10 + (100 - conf)
        elif sell_v >= 2:
            risk += 30 + sell_v * 8
        elif rec == 'hold' and sell_v > buy_votes(row):
            risk += 15
        if risk > 0:
            candidates.append((risk, {**row, '_source': 'deep_analysis'}))

    for row in sell_top_scan:
        sym = row.get('symbol')
        if sym:
            candidates.append((45 + (100 - float(row.get('potential_score', 50))), {**row, '_source': 'scan_sell_top'}))

    for row in scan_excluded:
        cid = row.get('case_id', '')
        if cid in ('true_downtrend', 'panic_sell'):
            candidates.append(
                (60 if cid == 'panic_sell' else 50, {**row, '_source': 'scan_exclude', 'symbol': row.get('symbol')}),
            )

    if not candidates:
        if all_ranked:
            worst = min(all_ranked, key=lambda x: float(x.get('confidence', 100)))
            return {**worst, '_source': 'lowest_confidence'}
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def buy_votes(row: Dict[str, Any]) -> int:
    return int(row.get('agents_buy', 0))


async def build_committee_report(ranking: Dict[str, Any]) -> Dict[str, Any]:
    """Tổng hợp quyết định hội đồng từ kết quả rank_all_stocks."""
    ts = ranking.get('timestamp', datetime.now(timezone.utc).isoformat())

    if ranking.get('status') in ('error', 'no_candidates', 'no_high_confidence_stocks'):
        return {
            'status': ranking.get('status', 'error'),
            'message': ranking.get('message', ''),
            'timestamp': ts,
            'workflow': {'steps_vi': WORKFLOW_VI, 'agents': AGENT_ROSTER},
            'best_pick': None,
            'worst_pick': None,
            'early_sell_alerts': [],
            'pipeline': ranking.get('pipeline'),
        }

    all_ranked = ranking.get('all_ranked', [])
    sell_top = ranking.get('sell_top_candidates', [])
    excluded = ranking.get('excluded_stocks', [])
    scan_by_sym = {r['symbol']: r for r in ranking.get('scan_passed', [])}

    early_alerts: List[Dict[str, Any]] = []
    for row in all_ranked:
        sym = row.get('symbol')
        if not sym:
            continue
        alert = await detect_early_downtrend_sell(
            sym,
            row.get('_pipeline', {}),
            scan_by_sym.get(sym),
            committee_recommendation=str(row.get('recommendation', '')),
            agents_buy=int(row.get('agents_buy', 0) or 0),
            agents_sell=int(row.get('agents_sell', 0) or 0),
        )
        if alert:
            early_alerts.append(alert)

    early_syms = {str(a['symbol']).upper() for a in early_alerts}

    for row in sell_top:
        sym = row.get('symbol')
        if not sym:
            continue
        su = str(sym).upper()
        if su in early_syms:
            continue
        early_alerts.append(
            {
                'symbol': sym,
                'urgency': 'SELL ON STRENGTH',
                'action': 'sell',
                'signals': [row.get('case_label_vi', 'Gần kháng cự / quá mua')],
                'reason_vi': 'Lọc sơ bộ: vùng bán đỉnh — cân nhắc chốt lời.',
            },
        )
        early_syms.add(su)

    early_alerts.sort(key=lambda a: a.get('risk_score', 0), reverse=True)

    best = select_best_pick(all_ranked, exclude_symbols=early_syms)
    worst = select_worst_pick(all_ranked, sell_top, excluded)

    if best:
        best_sym = str(best['symbol']).upper()
        early_alerts = [a for a in early_alerts if str(a['symbol']).upper() != best_sym]

    best_pick: Optional[Dict[str, Any]] = None
    if best:
        bp = _public_row(best)
        plan = await _technical_exit_plan(best['symbol'], best.get('_pipeline'))
        bt = plan.get('sell_timing') or {}
        best_pick = {
            **bp,
            'symbol': best['symbol'],
            'recommendation': best.get('recommendation'),
            'confidence': best.get('confidence'),
            'consensus_strength': best.get('consensus_strength'),
            'scan_case_label_vi': best.get('scan_case_label_vi'),
            'agent_breakdown': best.get('agent_details'),
            'buy_timing': plan.get('buy_timing') if 'buy_timing' in plan else None,
            'entry_points': plan.get('entry_points') if 'entry_points' in plan else None,
            'why_vi': (
                f"Hội đồng chọn MUA {best['symbol']}: {best.get('reasoning', '')[:400]}"
            ),
        }
        buy_full = await recommendation_engine.generate_full_recommendation(
            best['symbol'], best.get('_pipeline', {}),
        )
        best_pick['buy_timing'] = buy_full.get('buy_timing', {})
        best_pick['recommended_entry'] = (buy_full.get('entry_points') or {}).get('recommended_entry')
        best_pick['current_price'] = buy_full.get('current_price')
        best_pick['entry_points'] = buy_full.get('entry_points', {})
        best_pick['technical_snapshot'] = buy_full.get('indicators_snapshot', {})
        bti = buy_full.get('buy_timing') or {}
        best_pick['why_vi'] = (
            f"{best.get('reasoning', '')}\n\n"
            f"Desk chứng khoán — giá tốt để mua: {bti.get('timing', 'xem entry')}. "
            f"Entry gợi ý {best_pick.get('recommended_entry', '—')}."
        ).strip()

    worst_pick: Optional[Dict[str, Any]] = None
    if worst:
        sym = worst.get('symbol')
        if sym:
            plan = await _technical_exit_plan(sym, worst.get('_pipeline'))
            sell_t = plan.get('sell_timing') or {}
            ep = plan.get('exit_points') or {}
            early = await detect_early_downtrend_sell(sym, worst.get('_pipeline', {}), scan_by_sym.get(sym))
            worst_pick = {
                'symbol': sym,
                'recommendation': worst.get('recommendation', 'sell'),
                'confidence': worst.get('confidence'),
                'agents_sell': worst.get('agents_sell'),
                'scan_case_label_vi': worst.get('scan_case_label_vi'),
                'downtrend_risk': 'cao' if (worst.get('agents_sell', 0) >= 2 or worst.get('recommendation') == 'sell') else 'trung bình',
                'current_price': plan.get('current_price'),
                'sell_timing': sell_t,
                'recommended_exit_price': plan.get('recommended_exit_price'),
                'stop_loss': plan.get('stop_loss'),
                'take_profit_targets': {
                    'tp1': plan.get('take_profit_1'),
                    'tp2': plan.get('take_profit_2'),
                },
                'exit_strategy': plan.get('suggested_exit_strategy'),
                'early_sell_alert': early,
                'why_vi': (
                    f"Mã cần tránh / thoát: {sym}. "
                    f"{worst.get('reasoning', '')[:350]}\n\n"
                    f"Giá nên bán (tham chiếu): {plan.get('recommended_exit_price', '—')} — "
                    f"{sell_t.get('timing', 'HOLD')}. "
                    + (
                        f"CẢNH BÁO SỚM: {early.get('urgency')} — {early.get('reason_vi', '')}"
                        if early
                        else 'Theo dõi thêm nến đỏ / gãy hỗ trợ.'
                    )
                ),
            }

    return {
        'status': 'ok',
        'timestamp': ts,
        'analysis_period': '60 days (2 months)',
        'workflow': {
            'title_vi': 'Quy trình phòng phân tích (mô phỏng công ty chứng khoán)',
            'steps_vi': WORKFLOW_VI,
            'agents': AGENT_ROSTER,
        },
        'best_stock': best_pick['symbol'] if best_pick else None,
        'worst_stock': worst_pick['symbol'] if worst_pick else None,
        'best_pick': best_pick,
        'worst_pick': worst_pick,
        'early_sell_alerts': early_alerts[:15],
        'pipeline': ranking.get('pipeline'),
        'scan_passed': ranking.get('scan_passed', []),
        'sell_top_candidates': sell_top,
        'excluded_stocks': excluded,
        'deep_candidates': [
            {'symbol': s['symbol'], 'recommendation': s['recommendation'], 'confidence': s['confidence']}
            for s in all_ranked
        ],
        'summary': ranking.get('summary', {}),
    }
