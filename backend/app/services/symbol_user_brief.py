"""
Tóm tắt phân tích mã cổ phiếu — ngôn ngữ dễ đọc cho người dùng (không jargon agent).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.historical_analyzer import historical_analyzer
from app.services.investment_committee import detect_early_downtrend_sell
from app.services.technical_calculator import technical_calculator


VERDICT_VI = {
    'buy': 'Cân nhắc MUA',
    'sell': 'Cân nhắc BÁN',
    'hold': 'Nên QUAN SÁT / giữ',
}

AGENT_VI = {
    'MarketScanner': 'Quét thị trường',
    'BusinessAnalyst': 'Phân tích doanh nghiệp',
    'TechnicalAnalyst': 'Kỹ thuật',
    'SentimentAnalysis': 'Tâm lý thị trường',
    'RiskManagement': 'Quản trị rủi ro',
    'DecisionMaker': 'Chủ tịch hội đồng',
}


def _tone_for_verdict(verdict: str) -> str:
    v = (verdict or 'hold').lower()
    if v == 'buy':
        return 'positive'
    if v == 'sell':
        return 'warning'
    return 'neutral'


def _liquidity_insight(vol_profile: Dict[str, Any], change_pct: float) -> Optional[Dict[str, Any]]:
    trend = vol_profile.get('trend', 'normal')
    ratio = float(vol_profile.get('volume_ratio') or 1.0)
    cur = int(vol_profile.get('current_volume') or 0)
    avg = int(vol_profile.get('avg_volume') or 0)

    if trend == 'spike' or ratio >= 1.5:
        if change_pct < -1:
            return {
                'category': 'liquidity',
                'title': 'Thanh khoản cao kèm giá giảm',
                'text': (
                    f'Khối lượng hôm nay ~{cur:,} cổ, gấp {ratio:.1f} lần TB {avg:,} — '
                    'có thể là áp lực bán mạnh (phân phối), không phải mua vào.'
                ),
                'tone': 'warning',
            }
        if change_pct > 1:
            return {
                'category': 'liquidity',
                'title': 'Thanh khoản cao kèm giá tăng',
                'text': (
                    f'KL gấp {ratio:.1f} lần trung bình — dòng tiền đang vào, '
                    'thường hỗ trợ xu hướng tăng ngắn hạn.'
                ),
                'tone': 'positive',
            }
        return {
            'category': 'liquidity',
            'title': 'Thanh khoản bất thường',
            'text': f'KL hôm nay cao hơn TB ({ratio:.1f}x) — cần xem giá đóng phiên để biết phe mua hay bán chủ đạo.',
            'tone': 'neutral',
        }
    if trend == 'below_average' or ratio < 0.7:
        return {
            'category': 'liquidity',
            'title': 'Thanh khoản thấp',
            'text': (
                f'KL chỉ ~{ratio:.1f}× mức TB — khó khớp lệnh lớn, '
                'biến động giá có thể bị “kéo” nhẹ.'
            ),
            'tone': 'neutral',
        }
    if trend == 'above_average':
        return {
            'category': 'liquidity',
            'title': 'Thanh khoản khá tốt',
            'text': f'KL trên mức trung bình ({ratio:.1f}x) — mã vẫn có thanh khoản giao dịch ổn.',
            'tone': 'positive',
        }
    return {
        'category': 'liquidity',
        'title': 'Thanh khoản bình thường',
        'text': 'Khối lượng quanh mức trung bình 20 phiên — không có tín hiệu đặc biệt từ dòng tiền.',
        'tone': 'neutral',
    }


def _trend_insight(hist: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if hist.get('status') == 'no_data':
        return None
    trend = hist.get('trend', {})
    mom = hist.get('momentum', {})
    direction = trend.get('direction', '')
    mom_label = mom.get('momentum', '')
    r5 = float(mom.get('return_5d') or 0)
    r10 = float(mom.get('return_10d') or 0)
    strength = float(trend.get('strength') or 0)

    if direction == 'downtrend':
        text = (
            f'Giá ngắn hạn yếu hơn trung hạn (độ mạnh {strength:.0%}). '
            f'5 phiên: {r5:+.1f}%, 10 phiên: {r10:+.1f}% — '
        )
        if mom_label in ('bearish', 'strong_bearish'):
            text += 'có dấu hiệu downtrend / momentum giảm.'
            tone = 'warning'
        else:
            text += 'xu hướng giảm nhưng momentum chưa quá xấu.'
            tone = 'warning'
        return {'category': 'trend', 'title': 'Dấu hiệu xu hướng giảm', 'text': text, 'tone': tone}

    if direction == 'uptrend':
        text = (
            f'Xu hướng tăng (độ mạnh {strength:.0%}). '
            f'5 phiên: {r5:+.1f}%, 10 phiên: {r10:+.1f}%'
        )
        if mom_label in ('bullish', 'strong_bullish'):
            text += ' — momentum hỗ trợ tiếp diễn.'
        return {'category': 'trend', 'title': 'Xu hướng tăng', 'text': text, 'tone': 'positive'}

    return {
        'category': 'trend',
        'title': 'Thị trường đi ngang',
        'text': (
            f'Giá chưa rõ hướng (5d: {r5:+.1f}%, 10d: {r10:+.1f}%). '
            'Nên chờ bứt phá hoặc test hỗ trợ rõ hơn.'
        ),
        'tone': 'neutral',
    }


def _technical_insight(indicators: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    rsi = float(indicators.get('rsi', {}).get('rsi') or 50)
    vol = indicators.get('volume', {})
    macd = indicators.get('macd', {})
    cross = str(macd.get('crossover_signal', ''))

    if rsi >= 70:
        out.append({
            'category': 'technical',
            'title': 'RSI quá mua',
            'text': f'RSI ~{rsi:.0f} — giá có thể điều chỉnh ngắn hạn, cẩn thận mua đuổi.',
            'tone': 'warning',
        })
    elif rsi <= 30:
        out.append({
            'category': 'technical',
            'title': 'RSI quá bán',
            'text': f'RSI ~{rsi:.0f} — có thể hồi kỹ thuật nếu xu hướng chung không xấu.',
            'tone': 'positive',
        })

    if 'bearish_cross' in cross:
        out.append({
            'category': 'technical',
            'title': 'MACD cắt xuống',
            'text': 'Tín hiệu kỹ thuật giảm — thường đi kèm giai đoạn yếu hoặc downtrend.',
            'tone': 'warning',
        })
    elif 'bullish_cross' in cross:
        out.append({
            'category': 'technical',
            'title': 'MACD cắt lên',
            'text': 'Tín hiệu kỹ thuật tích cực — hỗ trợ kịch bản hồi hoặc tiếp tăng.',
            'tone': 'positive',
        })

    vt = vol.get('trend', '')
    if vt == 'spike' and not any(i['category'] == 'liquidity' for i in out):
        out.append({
            'category': 'technical',
            'title': 'Đột biến khối lượng (kỹ thuật)',
            'text': 'Volume spike trên biểu đồ — theo dõi giá đóng cửa để xác nhận phe chủ đạo.',
            'tone': 'neutral',
        })
    return out


def _order_flow_insight(detail: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not detail:
        return None
    flow = detail.get('order_flow') or {}
    pressure = flow.get('pressure', '')
    label = flow.get('pressure_label_vi', '')
    if not label:
        return None
    tone = 'neutral'
    if pressure == 'buy_strong':
        tone = 'positive'
    elif pressure == 'sell_strong':
        tone = 'warning'
    bid = float(flow.get('bid_volume_total') or 0)
    ask = float(flow.get('ask_volume_total') or 0)
    extra = ''
    if bid > 0 and ask > 0:
        extra = f' Tổng dư mua {bid:,.0f} vs chào bán {ask:,.0f} cổ (sổ lệnh VCI).'
    return {
        'category': 'order_book',
        'title': 'Sổ lệnh realtime',
        'text': label + extra,
        'tone': tone,
    }


def _consensus_insight(decision: Dict[str, Any]) -> Dict[str, Any]:
    extra = decision.get('extra', {}) or {}
    buy = int(extra.get('buy_agents', 0))
    hold = int(extra.get('hold_agents', 0))
    sell = int(extra.get('sell_agents', 0))
    verdict = str(decision.get('verdict', 'hold')).lower()
    conf = round(float(decision.get('score', 0)) * 100)

    parts = []
    if buy:
        parts.append(f'{buy} agent khuyên MUA')
    if hold:
        parts.append(f'{hold} agent GIỮ')
    if sell:
        parts.append(f'{sell} agent khuyên BÁN')

    text = ' · '.join(parts) if parts else 'Chưa đủ phiếu agent.'
    text += f' — độ tin cậy tổng hợp ~{conf}%.'
    tone = _tone_for_verdict(verdict)
    return {
        'category': 'consensus',
        'title': 'Ý kiến 5 agent AI',
        'text': text,
        'tone': tone,
    }


async def build_symbol_user_brief(
    symbol: str,
    agent_results: Dict[str, Any],
    *,
    market_detail: Optional[Dict[str, Any]] = None,
    timing: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    sym = symbol.upper()
    decision = agent_results.get('decision', {}) or {}
    verdict = str(decision.get('verdict', 'hold')).lower()
    extra = decision.get('extra', {}) or {}

    insights: List[Dict[str, Any]] = []
    warnings: List[str] = []
    positives: List[str] = []

    change_pct = float(market_detail.get('change_pct') or 0) if market_detail else 0.0

    hist = await historical_analyzer.full_historical_analysis(sym, days=60)
    trend_ins = _trend_insight(hist)
    if trend_ins:
        insights.append(trend_ins)
        if trend_ins['tone'] == 'warning':
            warnings.append(trend_ins['title'])
        elif trend_ins['tone'] == 'positive':
            positives.append(trend_ins['title'])

    prices = await historical_analyzer.get_historical_prices(sym, days=60)
    liq_ins: Optional[Dict[str, Any]] = None
    if prices:
        vol_profile = technical_calculator.calculate_volume_profile(prices)
        liq_ins = _liquidity_insight(vol_profile, change_pct)
        if liq_ins:
            insights.append(liq_ins)
            if liq_ins['tone'] == 'warning':
                warnings.append(liq_ins['title'])
            elif liq_ins['tone'] == 'positive':
                positives.append(liq_ins['title'])

        indicators = await technical_calculator.calculate_all_indicators(prices)
        for ti in _technical_insight(indicators):
            insights.append(ti)
            if ti['tone'] == 'warning':
                warnings.append(ti['title'])
            elif ti['tone'] == 'positive':
                positives.append(ti['title'])

    flow_ins = _order_flow_insight(market_detail)
    if flow_ins:
        insights.insert(0, flow_ins)

    insights.append(_consensus_insight(decision))

    early = await detect_early_downtrend_sell(
        sym,
        agent_results,
        committee_recommendation=verdict,
        agents_buy=int(extra.get('buy_agents', 0)),
        agents_sell=int(extra.get('sell_agents', 0)),
    )
    if early:
        reason = early.get('reason_vi') or '; '.join(early.get('signals', []))
        insights.insert(
            0,
            {
                'category': 'alert',
                'title': f'Cảnh báo: {early.get("urgency", "SELL")}',
                'text': reason,
                'tone': 'warning',
            },
        )
        warnings.insert(0, 'Cảnh báo downtrend / bán sớm')

    buy_timing = (timing or {}).get('buy_timing') or {}
    sell_timing = (timing or {}).get('sell_timing') or {}
    if sell_timing.get('early_downtrend') or sell_timing.get('timing') == 'SELL NOW':
        insights.append({
            'category': 'timing',
            'title': 'Thời điểm bán',
            'text': (
                f"{sell_timing.get('timing', 'SELL')} — "
                f"{', '.join(sell_timing.get('sell_signals', [])[:3]) or 'tín hiệu kỹ thuật xấu'}"
            ),
            'tone': 'warning',
        })
    elif buy_timing.get('timing'):
        sigs = buy_timing.get('buy_signals') or []
        waits = buy_timing.get('wait_reasons') or []
        insights.append({
            'category': 'timing',
            'title': f"Thời điểm mua: {buy_timing.get('timing')}",
            'text': (
                (f"Tín hiệu: {', '.join(sigs[:3])}. " if sigs else '')
                + (f"Chưa nên vội: {', '.join(waits[:2])}." if waits else '')
            ).strip() or buy_timing.get('urgency', ''),
            'tone': 'positive' if buy_timing.get('timing') == 'BUY NOW' else 'neutral',
        })

    if market_detail and market_detail.get('foreign', {}).get('label_vi'):
        insights.append({
            'category': 'foreign',
            'title': 'Khối ngoại',
            'text': market_detail['foreign']['label_vi'],
            'tone': 'neutral',
        })

    verdict_vi = VERDICT_VI.get(verdict, VERDICT_VI['hold'])
    tone = _tone_for_verdict(verdict)
    if early:
        verdict_vi = 'Cảnh báo BÁN / tránh mua thêm'
        tone = 'warning'

    buy_v = int(extra.get('buy_agents', 0))
    sell_v = int(extra.get('sell_agents', 0))
    summary_parts = [f'{sym}: {verdict_vi}.']
    if trend_ins:
        summary_parts.append(trend_ins['title'].lower() + '.')
    if liq_ins:
        summary_parts.append(liq_ins['title'].lower() + '.')
    if buy_v or sell_v:
        summary_parts.append(f'Hội đồng AI: {buy_v} mua, {sell_v} bán.')

    action = 'Theo dõi thêm, chưa cần hành động gấp.'
    if tone == 'warning' or early:
        action = 'Ưu tiên giảm rủi ro: không mua thêm, cân nhắc chốt lời / cắt lỗ nếu đang ôm.'
    elif verdict == 'buy' and buy_v >= 3:
        action = 'Có thể chia nhỏ mua theo vùng hỗ trợ — đặt stop-loss dưới đáy gần nhất.'
    elif verdict == 'sell':
        action = 'Cân nhắc thoát dần hoặc không nắm giữ mới.'

    agent_lines: List[Dict[str, str]] = []
    for ag in agent_results.get('agents', []):
        name = ag.get('agent', '')
        v = str(ag.get('verdict', 'hold')).lower()
        v_vi = {'buy': 'Mua', 'sell': 'Bán', 'hold': 'Giữ'}.get(v, v)
        agent_lines.append({
            'agent': name,
            'agent_vi': AGENT_VI.get(name, name),
            'verdict_vi': v_vi,
            'one_liner': _agent_one_liner(name, ag),
        })

    return {
        'symbol': sym,
        'headline_vi': f'{sym} — {verdict_vi}',
        'verdict': verdict,
        'verdict_vi': verdict_vi,
        'verdict_tone': tone,
        'summary_vi': ' '.join(summary_parts),
        'action_vi': action,
        'insights': insights,
        'warnings': warnings[:5],
        'positives': positives[:5],
        'agent_lines': agent_lines,
        'votes': {
            'buy': buy_v,
            'hold': int(extra.get('hold_agents', 0)),
            'sell': sell_v,
        },
    }


def _agent_one_liner(agent_name: str, ag: Dict[str, Any]) -> str:
    ex = ag.get('extra') or {}
    v = str(ag.get('verdict', 'hold')).lower()
    if agent_name == 'MarketScanner':
        t = ex.get('trend', '')
        if t == 'downtrend':
            return 'Xu hướng giá giảm trên biểu đồ 60 ngày.'
        if t == 'uptrend':
            return 'Xu hướng giá tăng trên biểu đồ 60 ngày.'
        return 'Thị trường chưa rõ xu hướng mạnh.'
    if agent_name == 'TechnicalAnalyst':
        if v == 'sell':
            return 'Chỉ báo kỹ thuật nghiêng về bán.'
        if v == 'buy':
            return 'Chỉ báo kỹ thuật hỗ trợ mua.'
        return 'Chỉ báo kỹ thuật trung tính.'
    if agent_name == 'RiskManagement':
        if v == 'sell':
            return 'Rủi ro/volatility cao — nên thận trọng.'
        return 'Mức rủi ro chấp nhận được.'
    if agent_name == 'BusinessAnalyst':
        if v == 'buy':
            return 'Cơ bản doanh nghiệp ủng hộ.'
        if v == 'sell':
            return 'Lo ngại về định giá / cơ bản.'
        return 'Cơ bản chưa đủ mạnh để mua.'
    if agent_name == 'SentimentAnalysis':
        return 'Tâm lý nhà đầu tư ' + ('tích cực' if v == 'buy' else 'tiêu cực' if v == 'sell' else 'trung lập')
    if agent_name == 'DecisionMaker':
        return str(ag.get('rationale', ''))[:200]
    return str(ag.get('rationale', ''))[:120] or 'Không có nhận xét ngắn.'
