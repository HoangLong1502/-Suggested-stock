"""
Giá realtime / trễ ~8–10s — cùng nguồn vnstock Trading (VCI Vietcap).
POST https://trading.vietcap.com.vn/api/price/symbols/getList
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import httpx

VCI_PRICE_URL = 'https://trading.vietcap.com.vn/api/price/symbols/getList'
# VCI trả giá ×1000 (vd 27650 → 27.65 nghìn VND)
PRICE_SCALE = 1000.0
CHUNK_SIZE = 40


def _vci_headers() -> Dict[str, str]:
    from vnstock.core.utils.user_agent import get_headers

    return get_headers(data_source='VCI')


def _scaled_price(raw: Any) -> float:
    """
    VCI: giá thô thường ×1000 (vd 13000 → 13.00 nghìn VNĐ).
    Nếu API đã trả đơn vị nghìn (vd 12.7), giữ nguyên.
    """
    try:
        v = float(raw or 0)
    except (TypeError, ValueError):
        return 0.0
    if v <= 0:
        return 0.0
    if v >= 500:
        return round(v / PRICE_SCALE, 2)
    return round(v, 2)


def parse_vci_board_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    listing = item.get('listingInfo') or {}
    match = item.get('matchPrice') or {}
    sym = str(listing.get('symbol') or match.get('symbol') or '').strip().upper()
    if not sym:
        return None

    ref = _scaled_price(listing.get('refPrice') or match.get('referencePrice'))
    last = _scaled_price(match.get('matchPrice') or match.get('openPrice'))
    if last <= 0:
        last = ref
    if last <= 0:
        return None

    change_abs = round(last - ref, 2) if ref > 0 else 0.0
    change_pct = round((change_abs / ref) * 100.0, 4) if ref > 0 else 0.0
    vol = float(match.get('accumulatedVolume') or match.get('accumulatedVolumeG1') or 0.0)
    trading_date = listing.get('tradingDate') or match.get('time')
    if isinstance(trading_date, str) and 'T' in trading_date:
        trading_date = trading_date[:10]

    now_iso = datetime.now(tz=ZoneInfo('UTC')).isoformat()
    board = str(listing.get('board') or 'VN').upper()
    meta = {
        'refPrice': ref,
        'basicPrice': ref,
        'change_abs': change_abs,
        'change_pct_computed': change_pct,
        'trading_date': trading_date,
        'quote_synced_at': now_iso,
        'quote_source': 'vnstock_vci',
        'exchange': board,
        'organShortName': listing.get('organShortName') or listing.get('enOrganShortName'),
        'vci_received_time': match.get('receivedTime') or listing.get('receivedTime'),
        'demo': False,
        'match_raw': match,
        'listing_raw': listing,
        'bid_ask_raw': item.get('bidAsk') or {},
    }
    return {
        'symbol': sym,
        'name': listing.get('organShortName') or listing.get('enOrganShortName') or sym,
        'exchange': listing.get('board') or 'VN',
        'last_price': last,
        'change': change_pct,
        'volume': vol,
        'stock_metadata': meta,
    }


def _sum_book_side(levels: Any) -> tuple[float, List[Dict[str, float]]]:
    out: List[Dict[str, float]] = []
    total = 0.0
    if not isinstance(levels, list):
        return 0.0, out
    for lv in levels[:5]:
        if not isinstance(lv, dict):
            continue
        p = _scaled_price(lv.get('price'))
        v = float(lv.get('volume') or 0)
        if p > 0 and v > 0:
            out.append({'price': p, 'volume': v})
            total += v
    return total, out


def parse_vci_symbol_detail(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Chi tiết 1 mã: trần/sàn/TC, sổ lệnh, áp lực mua-bán."""
    base = parse_vci_board_item(item)
    if not base:
        return None

    listing = item.get('listingInfo') or {}
    match = item.get('matchPrice') or {}
    bid_ask = item.get('bidAsk') or {}

    ref = _scaled_price(listing.get('refPrice') or match.get('referencePrice'))
    last = float(base['last_price'])
    ceiling = _scaled_price(listing.get('ceiling') or match.get('ceilingPrice'))
    floor = _scaled_price(listing.get('floor') or match.get('floorPrice'))
    high = _scaled_price(match.get('highest'))
    low = _scaled_price(match.get('lowest'))
    open_p = _scaled_price(match.get('openPrice'))
    avg_match = _scaled_price(match.get('avgMatchPrice'))

    bid_total, bid_levels = _sum_book_side(bid_ask.get('bidPrices'))
    ask_total, ask_levels = _sum_book_side(bid_ask.get('askPrices'))

    if bid_total > ask_total * 1.15:
        pressure = 'buy_strong'
        pressure_vi = 'Lực mua mạnh hơn (tổng dư mua)'
    elif ask_total > bid_total * 1.15:
        pressure = 'sell_strong'
        pressure_vi = 'Lực bán mạnh hơn (tổng chào bán)'
    else:
        pressure = 'balanced'
        pressure_vi = 'Cân bằng mua / bán'

    dist_ceiling = round(((ceiling - last) / last) * 100, 2) if ceiling > 0 and last > 0 else None
    dist_floor = round(((last - floor) / last) * 100, 2) if floor > 0 and last > 0 else None
    dist_ref = round(((last - ref) / ref) * 100, 2) if ref > 0 else float(base['stock_metadata'].get('change_pct_computed', 0))

    f_buy = float(match.get('foreignBuyVolume') or 0)
    f_sell = float(match.get('foreignSellVolume') or 0)
    if f_buy > f_sell * 1.1:
        foreign_vi = 'Khối ngoại mua ròng (theo khối lượng)'
    elif f_sell > f_buy * 1.1:
        foreign_vi = 'Khối ngoại bán ròng (theo khối lượng)'
    else:
        foreign_vi = 'Khối ngoại tương đối cân bằng'

    return {
        **base,
        'prices': {
            'last': last,
            'reference': ref,
            'ceiling': ceiling,
            'floor': floor,
            'high': high,
            'low': low,
            'open': open_p,
            'avg_match': avg_match,
        },
        'change_pct': float(base['change']),
        'change_abs': float(base['stock_metadata'].get('change_abs', 0)),
        'distance': {
            'to_ceiling_pct': dist_ceiling,
            'to_floor_pct': dist_floor,
            'from_reference_pct': dist_ref,
        },
        'order_flow': {
            'bid_volume_total': bid_total,
            'ask_volume_total': ask_total,
            'pressure': pressure,
            'pressure_label_vi': pressure_vi,
            'bid_levels': bid_levels,
            'ask_levels': ask_levels,
        },
        'foreign': {
            'buy_volume': f_buy,
            'sell_volume': f_sell,
            'label_vi': foreign_vi,
        },
        'organ_name': listing.get('organShortName') or listing.get('organName'),
        'exchange': listing.get('board') or base.get('exchange'),
    }


async def fetch_vci_symbol_detail(symbol: str) -> Optional[Dict[str, Any]]:
    sym = str(symbol).strip().upper()
    if not sym:
        return None
    headers = _vci_headers()
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                VCI_PRICE_URL,
                headers=headers,
                json={'symbols': [sym]},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None
    if not isinstance(data, list) or not data:
        return None
    item = data[0]
    if not isinstance(item, dict):
        return None
    return parse_vci_symbol_detail(item)


async def fetch_vci_price_board(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """Một hoặc vài request POST — trả map symbol → giá parse."""
    syms = list(dict.fromkeys(str(s).strip().upper() for s in symbols if s and str(s).strip()))
    if not syms:
        return {}

    headers = _vci_headers()
    out: Dict[str, Dict[str, Any]] = {}

    async with httpx.AsyncClient(timeout=25.0) as client:
        for i in range(0, len(syms), CHUNK_SIZE):
            chunk = syms[i : i + CHUNK_SIZE]
            try:
                resp = await client.post(
                    VCI_PRICE_URL,
                    headers=headers,
                    json={'symbols': chunk},
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                continue
            if not isinstance(data, list):
                continue
            for item in data:
                if not isinstance(item, dict):
                    continue
                parsed = parse_vci_board_item(item)
                if parsed:
                    out[parsed['symbol']] = parsed

    return out
