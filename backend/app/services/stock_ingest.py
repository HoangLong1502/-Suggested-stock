import asyncio
import time as time_module
from datetime import datetime, timedelta, time as dt_time
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select, desc

from app.models.schema import Stock, Watchlist, HistoricalPrice
from app.models.postgres import AsyncSessionLocal


VN_INDEX_SYMBOLS = ['VNINDEX', 'HNX', 'UPCOM']
DEFAULT_WATCHLIST = ['SSI', 'VNM', 'VCB', 'FPT', 'MWG', 'VHM', 'PNJ', 'HPG', 'TPB', 'ACB', 'BVH', 'MSN', 'NVL', 'GAS']

FINFO_STOCK_PRICES = 'https://finfo-api.vndirect.com.vn/v4/stock_prices'

_last_sync_monotonic: float = 0.0
_sync_lock = asyncio.Lock()
SYNC_TTL_SECONDS = 120


def vietnam_market_session(now: Optional[datetime] = None) -> Dict[str, Any]:
    """Rough HoSE / VN market clock (Mon–Fri, ICT). Used for UI copy, not exchange validation."""
    tz = ZoneInfo('Asia/Ho_Chi_Minh')
    now = now or datetime.now(tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    else:
        now = now.astimezone(tz)

    wd = now.weekday()
    if wd >= 5:
        return {
            'phase': 'weekend',
            'is_trading_day': False,
            'is_trading_hours': False,
            'label_vi': 'Cuối tuần — không có phiên giao dịch',
        }

    t = now.time()
    morning_open, morning_close = dt_time(9, 0), dt_time(11, 30)
    afternoon_open, afternoon_close = dt_time(13, 0), dt_time(15, 0)

    if t < morning_open:
        phase = 'pre_open'
        label = 'Trước giờ mở cửa (09:00)'
        hours = False
    elif morning_open <= t <= morning_close:
        phase = 'morning'
        label = 'Phiên sáng đang diễn ra'
        hours = True
    elif morning_close < t < afternoon_open:
        phase = 'lunch_break'
        label = 'Nghỉ trưa (11:30–13:00)'
        hours = False
    elif afternoon_open <= t <= afternoon_close:
        phase = 'afternoon'
        label = 'Phiên chiều đang diễn ra'
        hours = True
    else:
        phase = 'after_close'
        label = 'Đã hết phiên — hiển thị % thay đổi theo bản ghi giao dịch mới nhất từ nguồn dữ liệu'
        hours = False

    return {
        'phase': phase,
        'is_trading_day': True,
        'is_trading_hours': hours,
        'label_vi': label,
        'as_of': now.isoformat(),
    }


def _float_or_none(val: Any) -> Optional[float]:
    if val is None or val == '':
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def extract_change_pct(row: Dict[str, Any], close: float) -> float:
    """Best-effort daily % change from VNDirect finfo row (field names vary)."""
    for key in (
        'pctChange',
        'changePercent',
        'changePc',
        'percentChange',
        'priceChangePercent',
        'rate',
        'changeRatio',
        'deltaRatio',
    ):
        v = _float_or_none(row.get(key))
        if v is not None:
            return round(v, 4)

    change_abs = _float_or_none(row.get('change'))
    ref = _float_or_none(
        row.get('basicPrice')
        or row.get('refPrice')
        or row.get('r')
        or row.get('adPrice')
        or row.get('priorClose')
        or row.get('prevClosePrice')
    )
    if change_abs is not None and ref is not None and ref != 0:
        return round((change_abs / ref) * 100.0, 4)

    prev_close = _float_or_none(
        row.get('priorClose') or row.get('prevClosePrice') or row.get('priorClosePrice')
    )
    if prev_close is not None and prev_close > 0 and close:
        return round(((close - prev_close) / prev_close) * 100.0, 4)

    return 0.0


def _parse_row_to_values(row: Dict[str, Any]) -> Dict[str, Any]:
    close = float(
        row.get('close')
        or row.get('accumulatedPrice')
        or row.get('adClose')
        or row.get('average')
        or 0.0
    )
    change_abs = float(row.get('change') or 0.0)
    change_pct = extract_change_pct(row, close)
    trading_date = row.get('date') or row.get('tradingDate') or row.get('tradeDate')

    meta = {
        **row,
        'change_pct_computed': change_pct,
        'change_abs': change_abs,
        'trading_date': trading_date,
        'quote_synced_at': datetime.now(tz=ZoneInfo('UTC')).isoformat(),
    }
    return {
        'symbol': (row.get('symbol') or row.get('code') or '').upper(),
        'name': row.get('name') or row.get('symbol') or row.get('code'),
        'exchange': row.get('exchange', 'VN'),
        'last_price': close,
        'change': change_pct,
        'volume': float(row.get('totalVolume') or row.get('nmTotalTradedQty') or row.get('volume') or 0.0),
        'stock_metadata': meta,
    }


async def fetch_latest_price_row(client: httpx.AsyncClient, symbol: str) -> Optional[Dict[str, Any]]:
    """Latest finfo row for symbol (walks back calendar days if empty / holiday)."""
    sym = symbol.upper().strip()
    tz = ZoneInfo('Asia/Ho_Chi_Minh')
    for offset in range(0, 20):
        day = (datetime.now(tz) - timedelta(days=offset)).strftime('%Y-%m-%d')
        params = {
            'q': f'code:{sym}~date:gte:{day}~date:lte:{day}',
            'sort': 'date',
            'size': 30,
            'page': 1,
        }
        try:
            response = await client.get(FINFO_STOCK_PRICES, params=params)
            response.raise_for_status()
            payload = response.json()
            rows = payload.get('data') if isinstance(payload, dict) else None
            if isinstance(rows, list) and rows:
                return rows[-1]
        except Exception:
            continue
    return None


async def _fetch_symbol_safe(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    symbol: str,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    async with sem:
        try:
            row = await fetch_latest_price_row(client, symbol)
            return symbol, row
        except Exception:
            return symbol, None


async def sync_market_snapshot_if_stale(ttl_seconds: int = SYNC_TTL_SECONDS) -> bool:
    """Chạy sync VNDirect tối đa mỗi ttl_seconds — tránh overview/SSR chờ hàng chục giây."""
    global _last_sync_monotonic
    now = time_module.monotonic()
    if now - _last_sync_monotonic < ttl_seconds:
        return False
    async with _sync_lock:
        now = time_module.monotonic()
        if now - _last_sync_monotonic < ttl_seconds:
            return False
        await sync_market_snapshot()
        _last_sync_monotonic = time_module.monotonic()
    return True


async def sync_market_snapshot() -> None:
    """
    Refresh prices for indices + watchlist + default liquid names.
    Persists daily % change in Stock.change (UI expects percent), full row in stock_metadata.
    """
    watch = await load_watchlist_symbols()
    symbols = list(dict.fromkeys([*VN_INDEX_SYMBOLS, *watch, *DEFAULT_WATCHLIST]))

    sem = asyncio.Semaphore(12)
    async with httpx.AsyncClient(timeout=30.0) as client:
        pairs = await asyncio.gather(*[_fetch_symbol_safe(client, sem, s) for s in symbols])

    async with AsyncSessionLocal() as session:
        for sym, row in pairs:
            if not row:
                continue
            values = _parse_row_to_values(row)
            code = values['symbol']
            if not code or float(values.get('last_price') or 0) <= 0:
                continue

            res = await session.execute(select(Stock).where(Stock.symbol == code))
            existing = res.scalar_one_or_none()
            payload = {k: v for k, v in values.items() if k != 'symbol'}
            if existing:
                await session.execute(
                    Stock.__table__.update().where(Stock.id == existing.id).values(**payload),
                )
            else:
                session.add(Stock(symbol=code, **payload))
        await session.commit()
    global _last_sync_monotonic
    _last_sync_monotonic = time_module.monotonic()


async def load_watchlist_symbols() -> List[str]:
    async with AsyncSessionLocal() as session:
        watchlist_result = await session.execute(
            select(Watchlist).order_by(Watchlist.created_at.desc()).limit(1)
        )
        watchlist = watchlist_result.scalar_one_or_none()

        if watchlist and isinstance(watchlist.symbols, list):
            cleaned = [str(s).strip().upper() for s in watchlist.symbols if s and str(s).strip()]
            if cleaned:
                return cleaned

        legacy_result = await session.execute(select(Stock).limit(20))
        stocks = legacy_result.scalars().all()
        symbols = [str(s.symbol).strip().upper() for s in stocks if s.symbol]
        return symbols if symbols else list(DEFAULT_WATCHLIST)


async def batch_ohlc_day_pct(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """Hai nến đóng gần nhất / mã — một query, dùng cho watchlist & movers."""
    syms = [str(s).strip().upper() for s in symbols if s]
    if not syms:
        return {}

    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(
                HistoricalPrice.stock_symbol,
                HistoricalPrice.close_price,
                HistoricalPrice.date,
            )
            .where(HistoricalPrice.stock_symbol.in_(syms))
            .order_by(HistoricalPrice.stock_symbol, desc(HistoricalPrice.date)),
        )
        rows = res.all()

    grouped: Dict[str, List[Tuple[float, Any]]] = {}
    for sym, close, dt in rows:
        key = str(sym).strip().upper()
        if key not in grouped:
            grouped[key] = []
        if len(grouped[key]) < 2:
            grouped[key].append((float(close), dt))

    out: Dict[str, Dict[str, Any]] = {}
    for sym, bars in grouped.items():
        c0, d0 = bars[0]
        date_s = d0.isoformat()[:10] if hasattr(d0, 'isoformat') else str(d0)[:10]
        if len(bars) < 2:
            out[sym] = {
                'close': c0,
                'prev_close': None,
                'pct': 0.0,
                'trading_date': date_s,
            }
            continue
        c1, _ = bars[1]
        pct = round(((c0 - c1) / c1) * 100, 4) if c1 > 0 else 0.0
        out[sym] = {
            'close': c0,
            'prev_close': c1,
            'pct': pct,
            'trading_date': date_s,
        }
    return out


async def _fill_prices_from_historical_db(items: List[Dict[str, Any]]) -> None:
    """Batch OHLC: luôn ghi % từ 2 phiên gần nhất khi có trong DB."""
    note = (
        'Giá và % thay đổi lấy từ dữ liệu lịch sử trong DB (bản demo hoặc khi API giá ngoài chưa trả về).'
    )
    symbols = [it['symbol'] for it in items]
    hist = await batch_ohlc_day_pct(symbols)

    for item in items:
        sym = item['symbol']
        row = hist.get(sym)
        if not row:
            continue

        c0 = float(row['close'])
        pct = float(row['pct'])
        if not (item.get('price') and float(item['price']) > 0):
            item['price'] = c0

        item['change'] = pct
        item['change_pct'] = pct
        if not item.get('trading_date'):
            item['trading_date'] = row.get('trading_date')
        item['quote_source_note'] = note


async def load_watchlist_items() -> List[Dict[str, Any]]:
    symbols = await load_watchlist_symbols()
    if not symbols:
        symbols = list(DEFAULT_WATCHLIST)
    session_info = vietnam_market_session()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Stock).where(Stock.symbol.in_(symbols)))
        stocks = result.scalars().all()

    stock_map = {str(stock.symbol).strip().upper(): stock for stock in stocks}
    items: List[Dict[str, Any]] = []
    for symbol in symbols:
        st = stock_map.get(symbol)
        meta: Dict[str, Any] = (st.stock_metadata or {}) if st else {}
        change_pct = float(st.change or 0.0) if st else 0.0
        price = float(st.last_price or 0.0) if st else 0.0
        change_abs = float(meta.get('change_abs') or meta.get('change') or 0.0)
        if change_abs and abs(change_pct) < 1e-9:
            ref = meta.get('basicPrice') or meta.get('refPrice')
            try:
                if ref and float(ref) != 0:
                    change_pct = round((change_abs / float(ref)) * 100.0, 4)
            except (TypeError, ValueError):
                pass

        items.append(
            {
                'symbol': symbol,
                'price': price,
                'change': change_pct,
                'change_pct': change_pct,
                'change_abs': change_abs,
                'reference_price': meta.get('basicPrice') or meta.get('refPrice') or meta.get('r'),
                'trading_date': meta.get('trading_date') or meta.get('date'),
                'volume': float(st.volume or 0.0) if st else 0.0,
                'quote_time': meta.get('quote_synced_at'),
                'market_session': session_info,
            }
        )

    await _fill_prices_from_historical_db(items)

    if any((it.get('price') or 0) <= 0 for it in items):
        from app.services.demo_seed import ensure_demo_historical_data

        if await ensure_demo_historical_data():
            await _fill_prices_from_historical_db(items)

    for it in items:
        ch = float(it.get('change_pct') or it.get('change') or 0)
        if ch > 0.05:
            it['signal'] = 'bull'
            it['signal_vi'] = 'Tích cực'
        elif ch < -0.05:
            it['signal'] = 'bear'
            it['signal_vi'] = 'Tiêu cực'
        else:
            it['signal'] = 'flat'
            it['signal_vi'] = 'Trung lập'

    return items


async def periodic_market_sync() -> None:
    while True:
        try:
            await sync_market_snapshot()
        except Exception:
            pass
        await asyncio.sleep(60)
