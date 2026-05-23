import asyncio
import time as time_module
from datetime import datetime, timedelta, time as dt_time
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select, desc

from app.core.config import settings
from app.models.schema import Stock, Watchlist, HistoricalPrice
from app.models.postgres import AsyncSessionLocal
from app.services.vn_realtime_quotes import fetch_vci_price_board


VN_INDEX_SYMBOLS = ['VNINDEX', 'HNX', 'UPCOM']

# Watchlist cố định (user) + 5 bluechip nổi tiếng: FPT, VHM, GAS, PLX, BID
DEFAULT_WATCHLIST: List[str] = list(
    dict.fromkeys(
        [
            'OIL', 'PXL', 'SSI', 'CII', 'MBB', 'BSR', 'DPM', 'HAG', 'MSN', 'MSR', 'SGP',
            'DCM', 'HPG', 'FPR', 'MCH', 'VTP', 'VTB', 'ACV', 'MWG', 'POW', 'SAB', 'TCB',
            'VCB', 'VIC', 'VJC', 'VNM',
            'FPT', 'VHM', 'GAS', 'PLX', 'BID',
        ],
    ),
)

FINFO_STOCK_PRICES = 'https://finfo-api.vndirect.com.vn/v4/stock_prices'

_last_sync_monotonic: float = 0.0
_sync_lock = asyncio.Lock()
SYNC_TTL_SECONDS = max(2, int(getattr(settings, 'quote_sync_interval_seconds', 8) or 8))
QUOTE_MAX_DELAY_SECONDS = max(SYNC_TTL_SECONDS, int(getattr(settings, 'quote_max_delay_seconds', 10) or 10))


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
        'quote_source': 'vndirect_finfo',
        'demo': False,
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


async def fetch_latest_price_row(
    client: httpx.AsyncClient,
    symbol: str,
    *,
    max_lookback_days: int = 20,
) -> Optional[Dict[str, Any]]:
    """Latest finfo row for symbol (walks back calendar days if empty / holiday)."""
    sym = symbol.upper().strip()
    tz = ZoneInfo('Asia/Ho_Chi_Minh')
    for offset in range(0, max(1, max_lookback_days)):
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


async def _persist_stock_quotes(quotes: Dict[str, Dict[str, Any]]) -> None:
    if not quotes:
        return
    async with AsyncSessionLocal() as session:
        for code, values in quotes.items():
            sym = str(code).strip().upper()
            if not sym or float(values.get('last_price') or 0) <= 0:
                continue
            res = await session.execute(select(Stock).where(Stock.symbol == sym))
            existing = res.scalar_one_or_none()
            payload = {k: v for k, v in values.items() if k != 'symbol'}
            if existing:
                await session.execute(
                    Stock.__table__.update().where(Stock.id == existing.id).values(**payload),
                )
            else:
                session.add(Stock(symbol=sym, **payload))
        await session.commit()


async def _sync_market_snapshot_impl() -> None:
    """
    Refresh giá watchlist + chỉ số: ưu tiên VCI (vnstock Trading), fallback VNDirect finfo.
    Một batch ~30 mã ≈ vài giây; lặp mỗi SYNC_TTL_SECONDS (mặc định 8s).
    """
    watch = await load_watchlist_symbols()
    symbols = list(dict.fromkeys([*VN_INDEX_SYMBOLS, *watch, *DEFAULT_WATCHLIST]))

    vci_quotes = await fetch_vci_price_board(symbols)
    await _persist_stock_quotes(vci_quotes)

    missing = [s for s in symbols if s not in vci_quotes]
    # Chỉ finfo fallback mã lẻ (tối đa 5 ngày) — tránh treo request overview
    finfo_candidates = [s for s in missing if s not in VN_INDEX_SYMBOLS][:6]
    if finfo_candidates:
        sem = asyncio.Semaphore(4)

        async def _finfo_one(sym: str) -> Tuple[str, Optional[Dict[str, Any]]]:
            async with sem:
                try:
                    async with httpx.AsyncClient(timeout=12.0) as client:
                        row = await fetch_latest_price_row(client, sym, max_lookback_days=5)
                    return sym, row
                except Exception:
                    return sym, None

        try:
            pairs = await asyncio.wait_for(
                asyncio.gather(*[_finfo_one(s) for s in finfo_candidates]),
                timeout=8.0,
            )
        except asyncio.TimeoutError:
            pairs = []
        finfo_quotes: Dict[str, Dict[str, Any]] = {}
        for sym, row in pairs:
            if not row:
                continue
            values = _parse_row_to_values(row)
            code = values.get('symbol')
            if code:
                finfo_quotes[code] = values
        await _persist_stock_quotes(finfo_quotes)

    global _last_sync_monotonic
    _last_sync_monotonic = time_module.monotonic()

    from app.services.market_ws import notify_market_update

    asyncio.create_task(notify_market_update())


async def sync_market_snapshot() -> None:
    async with _sync_lock:
        await _sync_market_snapshot_impl()


async def sync_market_snapshot_if_stale(ttl_seconds: int = SYNC_TTL_SECONDS) -> bool:
    """Chạy sync tối đa mỗi ttl_seconds (mặc định 8s, trễ mục tiêu ≤10s so với vnstock/VCI)."""
    global _last_sync_monotonic
    now = time_module.monotonic()
    if now - _last_sync_monotonic < ttl_seconds:
        return False
    async with _sync_lock:
        now = time_module.monotonic()
        if now - _last_sync_monotonic < ttl_seconds:
            return False
        await _sync_market_snapshot_impl()
        _last_sync_monotonic = time_module.monotonic()
    return True


async def ensure_default_watchlist() -> None:
    """Ghi watchlist mặc định vào DB — luôn đúng danh sách DEFAULT_WATCHLIST (không gộp mã cũ)."""
    target = list(DEFAULT_WATCHLIST)
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Watchlist).order_by(Watchlist.created_at.desc()).limit(1))
        wl = res.scalar_one_or_none()
        if wl is None:
            session.add(Watchlist(user_id='default', symbols=target))
        else:
            wl.symbols = target
        await session.commit()


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

    return list(DEFAULT_WATCHLIST)


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


def _has_live_market_quote(meta: Dict[str, Any]) -> bool:
    """Giá live: vnstock VCI hoặc VNDirect finfo — không dùng demo."""
    if not meta.get('quote_synced_at'):
        return False
    if meta.get('demo') is True:
        return False
    if meta.get('quote_source') == 'demo_seed':
        return False
    return meta.get('quote_source') in (None, 'vndirect_finfo', 'vnstock_vci')


def _quote_is_fresh(meta: Dict[str, Any], max_age_seconds: int = QUOTE_MAX_DELAY_SECONDS) -> bool:
    if not _has_live_market_quote(meta):
        return False
    synced = meta.get('quote_synced_at')
    if not synced:
        return False
    try:
        ts = datetime.fromisoformat(str(synced).replace('Z', '+00:00'))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=ZoneInfo('UTC'))
        age = (datetime.now(tz=ZoneInfo('UTC')) - ts.astimezone(ZoneInfo('UTC'))).total_seconds()
        return age <= max_age_seconds
    except (TypeError, ValueError):
        return True


async def _fill_prices_from_historical_db(items: List[Dict[str, Any]]) -> None:
    """OHLC DB chỉ fallback mã chưa có quote live."""
    live_sources = ('vndirect_finfo', 'vnstock_vci')
    fallback_items = [it for it in items if it.get('quote_source') not in live_sources]
    if not fallback_items:
        return

    note = (
        'Giá demo từ DB (chưa sync VCI/vnstock). Đợi tối đa ~10s hoặc bấm Làm mới giá.'
    )
    symbols = [it['symbol'] for it in fallback_items]
    hist = await batch_ohlc_day_pct(symbols)

    for item in fallback_items:
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
        item['quote_source'] = 'demo_db'
        item['quote_source_note'] = note


async def load_watchlist_items(*, skip_sync: bool = False) -> List[Dict[str, Any]]:
    """Đọc watchlist từ DB. skip_sync=True: không gọi API (chỉ dùng cache DB)."""
    if not skip_sync:
        try:
            await sync_market_snapshot_if_stale(ttl_seconds=SYNC_TTL_SECONDS)
        except Exception:
            pass

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

        live = _has_live_market_quote(meta)
        fresh = _quote_is_fresh(meta)
        src = str(meta.get('quote_source') or '')
        if src == 'vnstock_vci':
            note = (
                f'Giá VCI (vnstock Trading) — cập nhật ~{SYNC_TTL_SECONDS}s/lần, trễ mục tiêu ≤{QUOTE_MAX_DELAY_SECONDS}s.'
                if fresh
                else 'Giá VCI — đang chờ sync nền…'
            )
            qsrc = 'vnstock_vci'
        elif live:
            note = 'Giá VNDirect finho (fallback).'
            qsrc = 'vndirect_finfo'
        else:
            note = None
            qsrc = 'demo_db'
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
                'quote_source': qsrc,
                'quote_fresh': fresh,
                'quote_source_note': note,
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
            await sync_market_snapshot_if_stale(ttl_seconds=0)
        except Exception:
            pass
        await asyncio.sleep(SYNC_TTL_SECONDS)
