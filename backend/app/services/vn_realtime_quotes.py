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
    try:
        v = float(raw or 0)
    except (TypeError, ValueError):
        return 0.0
    if v <= 0:
        return 0.0
    return round(v / PRICE_SCALE, 2)


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
    meta = {
        'refPrice': ref,
        'basicPrice': ref,
        'change_abs': change_abs,
        'change_pct_computed': change_pct,
        'trading_date': trading_date,
        'quote_synced_at': now_iso,
        'quote_source': 'vnstock_vci',
        'vci_received_time': match.get('receivedTime') or listing.get('receivedTime'),
        'demo': False,
        'match_raw': match,
        'listing_raw': listing,
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
