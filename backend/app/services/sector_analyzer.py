"""
Phân tích ngành / lĩnh vực — gom mã VN theo nhóm, tính % thay đổi từ OHLC trong DB.
Nguồn giá: historical_prices (demo seed hoặc sync VNDirect). Có thể bổ sung mapping từ finfo stocks.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import httpx

from app.services.stock_ingest import batch_ohlc_day_pct

FINFO_STOCKS = 'https://finfo-api.vndirect.com.vn/v4/stocks'

# Nhóm ngành tiếng Việt — mã thanh khoản đại diện (có thể mở rộng)
VN_SECTOR_GROUPS: Dict[str, Dict[str, Any]] = {
    'ngan_hang': {
        'name_vi': 'Ngân hàng',
        'name_en': 'Banking',
        'symbols': ['VCB', 'TCB', 'BID', 'CTG', 'MBB', 'ACB', 'TPB', 'VPB', 'STB', 'HDB', 'LPB', 'EIB', 'MSB'],
    },
    'bat_dong_san': {
        'name_vi': 'Bất động sản',
        'name_en': 'Real Estate',
        'symbols': ['VHM', 'VIC', 'NVL', 'KDH', 'DXG', 'NLG', 'PDR', 'CEO', 'HDG', 'DIG'],
    },
    'cong_nghe': {
        'name_vi': 'Công nghệ',
        'name_en': 'Technology',
        'symbols': ['FPT', 'CMG', 'FOX', 'ELC', 'SGT'],
    },
    'dau_khi': {
        'name_vi': 'Dầu khí & năng lượng',
        'name_en': 'Oil & Gas',
        'symbols': ['GAS', 'PLX', 'PVD', 'PVS', 'OIL', 'BSR', 'PVC'],
    },
    'ban_le_tieu_dung': {
        'name_vi': 'Bán lẻ & tiêu dùng',
        'name_en': 'Consumer & Retail',
        'symbols': ['MWG', 'FRT', 'VNM', 'MSN', 'SAB', 'BHN', 'KDC', 'PNJ'],
    },
    'thep_xay_dung': {
        'name_vi': 'Thép & xây dựng',
        'name_en': 'Steel & Construction',
        'symbols': ['HPG', 'HSG', 'NKG', 'CTD', 'VCG', 'HHV'],
    },
    'chung_khoan': {
        'name_vi': 'Chứng khoán',
        'name_en': 'Securities',
        'symbols': ['SSI', 'VCI', 'VND', 'SHS', 'HCM', 'BSI', 'FTS'],
    },
    'bao_hiem': {
        'name_vi': 'Bảo hiểm',
        'name_en': 'Insurance',
        'symbols': ['BVH', 'PVI', 'MIG', 'BMI'],
    },
    'dien_cong_nghiep': {
        'name_vi': 'Điện & công nghiệp',
        'name_en': 'Utilities & Industrials',
        'symbols': ['POW', 'REE', 'GEG', 'GEX', 'PC1'],
    },
    'van_tai': {
        'name_vi': 'Vận tải & logistics',
        'name_en': 'Transport & Logistics',
        'symbols': ['GMD', 'VSC', 'VTP', 'HAH', 'SCS'],
    },
}


def _momentum_label(avg_pct: float) -> Tuple[str, str]:
    if avg_pct > 0.15:
        return 'tang_manh', 'Tăng mạnh'
    if avg_pct > 0.05:
        return 'tang', 'Đang tăng'
    if avg_pct < -0.15:
        return 'giam_manh', 'Giảm mạnh'
    if avg_pct < -0.05:
        return 'giam', 'Đang giảm'
    return 'di_ngang', 'Đi ngang'


async def _fetch_finfo_symbol_industry_map() -> Dict[str, str]:
    """Best-effort: lấy industry/ICB từ finfo stocks (không bắt buộc)."""
    out: Dict[str, str] = {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(
                FINFO_STOCKS,
                params={'size': 200, 'page': 1, 'q': 'type:STOCK'},
            )
            if res.status_code != 200:
                return out
            payload = res.json()
            rows = payload.get('data') if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                return out
            for row in rows:
                if not isinstance(row, dict):
                    continue
                code = (row.get('code') or row.get('symbol') or '').upper().strip()
                ind = (
                    row.get('icbName')
                    or row.get('industryName')
                    or row.get('industry')
                    or row.get('sector')
                    or ''
                )
                if code and ind:
                    out[code] = str(ind).strip()
    except Exception:
        pass
    return out


async def build_sector_analysis(*, include_finfo: bool = False) -> Dict[str, Any]:
    all_symbols: List[str] = []
    for meta in VN_SECTOR_GROUPS.values():
        all_symbols.extend(meta['symbols'])
    all_symbols = list(dict.fromkeys(all_symbols))

    hist = await batch_ohlc_day_pct(all_symbols)
    finfo_map: Dict[str, str] = {}
    if include_finfo:
        try:
            finfo_map = await asyncio.wait_for(_fetch_finfo_symbol_industry_map(), timeout=6.0)
        except (asyncio.TimeoutError, Exception):
            finfo_map = {}

    sectors_out: List[Dict[str, Any]] = []

    for sector_id, meta in VN_SECTOR_GROUPS.items():
        stocks_detail: List[Dict[str, Any]] = []
        changes: List[float] = []
        up = down = flat = 0

        for sym in meta['symbols']:
            row = hist.get(sym)
            if not row:
                continue
            pct = float(row.get('pct') or 0)
            price = float(row.get('close') or 0)
            changes.append(pct)
            if pct > 0.05:
                up += 1
            elif pct < -0.05:
                down += 1
            else:
                flat += 1
            stocks_detail.append(
                {
                    'symbol': sym,
                    'change_pct': pct,
                    'price': price,
                    'trading_date': row.get('trading_date'),
                    'finfo_industry': finfo_map.get(sym),
                }
            )

        stocks_detail.sort(key=lambda x: x['change_pct'], reverse=True)
        avg_pct = round(sum(changes) / len(changes), 4) if changes else 0.0
        mom_id, mom_vi = _momentum_label(avg_pct)
        leader = stocks_detail[0] if stocks_detail else None

        sectors_out.append(
            {
                'id': sector_id,
                'name_vi': meta['name_vi'],
                'name_en': meta['name_en'],
                'change_pct_avg': avg_pct,
                'stocks_with_data': len(stocks_detail),
                'stocks_total': len(meta['symbols']),
                'gainers': up,
                'losers': down,
                'flat': flat,
                'momentum': mom_id,
                'momentum_vi': mom_vi,
                'leader_symbol': leader['symbol'] if leader else None,
                'leader_change_pct': leader['change_pct'] if leader else None,
                'stocks': stocks_detail[:12],
            }
        )

    sectors_out.sort(key=lambda s: s['change_pct_avg'], reverse=True)

    market_avg = (
        round(sum(s['change_pct_avg'] for s in sectors_out) / len(sectors_out), 4) if sectors_out else 0.0
    )

    return {
        'as_of': datetime.now(timezone.utc).isoformat(),
        'market_avg_change_pct': market_avg,
        'sectors': sectors_out,
        'data_source': (
            'Tỷ lệ % = trung bình % ngày (2 nến đóng gần nhất) của các mã đại diện trong nhóm, '
            'lấy từ historical_prices trong DB. Mapping ngành nội bộ; có thể bổ sung nhãn industry từ VNDirect finfo.'
        ),
        'top_sectors': [s['id'] for s in sectors_out[:3]],
        'bottom_sectors': [s['id'] for s in sectors_out[-3:][::-1]] if len(sectors_out) >= 3 else [],
    }


class SectorAnalyzer:
    build_sector_analysis = staticmethod(build_sector_analysis)


sector_analyzer = SectorAnalyzer()
