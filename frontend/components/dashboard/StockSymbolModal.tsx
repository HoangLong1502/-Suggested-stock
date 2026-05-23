'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, Sparkles, TrendingDown, TrendingUp, X } from 'lucide-react';
import { getStockDetail } from '../../lib/api';
import AgentDebatePanel from '../agent/AgentDebatePanel';

function fmtPrice(v: number | null | undefined) {
  if (v == null || Number.isNaN(v) || v <= 0) return '—';
  return v.toLocaleString('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtPct(v: number | null | undefined) {
  if (v == null || Number.isNaN(v)) return '—';
  const sign = v >= 0 ? '+' : '';
  return `${sign}${v.toFixed(2)}%`;
}

export default function StockSymbolModal({
  symbol,
  onClose,
}: {
  readonly symbol: string;
  readonly onClose: () => void;
}) {
  const [showAi, setShowAi] = useState(false);
  const { data, isLoading, isError } = useQuery({
    queryKey: ['stockDetail', symbol],
    queryFn: () => getStockDetail(symbol),
    staleTime: 15_000,
    refetchOnWindowFocus: false,
  });

  const prices = data?.prices;
  const flow = data?.order_flow;
  const changePct = data?.change_pct ?? 0;
  const up = changePct >= 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-0 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="stock-modal-title"
      onClick={onClose}
      onKeyDown={(e) => {
        if (e.key === 'Escape') onClose();
      }}
    >
      <div
        className="flex max-h-[92vh] w-full max-w-2xl flex-col overflow-hidden rounded-t-3xl border border-white/10 bg-slate-950 shadow-2xl sm:rounded-3xl"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-white/10 px-5 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-violet-300/90">Chi tiết mã</p>
            <h2 id="stock-modal-title" className="mt-1 font-mono text-2xl font-bold text-white">
              {symbol}
            </h2>
            {data?.name && data.name !== symbol ? (
              <p className="mt-0.5 text-sm text-slate-400">{data.name}</p>
            ) : null}
            {data?.organ_name ? <p className="text-xs text-slate-500">{data.organ_name}</p> : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-white/10 bg-white/5 p-2 text-slate-300 hover:bg-white/10"
            aria-label="Đóng"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {isLoading ? (
            <div className="flex items-center justify-center gap-2 py-12 text-slate-400">
              <Loader2 className="h-5 w-5 animate-spin" />
              Đang tải dữ liệu VCI…
            </div>
          ) : isError || !data ? (
            <p className="py-8 text-center text-sm text-rose-300">Không tải được dữ liệu cho {symbol}.</p>
          ) : (
            <div className="space-y-5">
              <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 p-4">
                <div className="flex flex-wrap items-end justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-wider text-slate-500">Giá khớp</p>
                    <p className="font-mono text-3xl font-bold tabular-nums text-white">{fmtPrice(prices?.last)}</p>
                  </div>
                  <span
                    className={`inline-flex items-center gap-1 rounded-lg px-3 py-1.5 font-mono text-lg font-bold tabular-nums ${
                      up ? 'bg-emerald-500/15 text-emerald-400' : 'bg-rose-500/15 text-rose-400'
                    }`}
                  >
                    {up ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                    {fmtPct(changePct)}
                  </span>
                </div>
                {flow?.pressure_label_vi ? (
                  <p
                    className={`mt-3 rounded-lg px-3 py-2 text-sm font-medium ${
                      flow.pressure === 'buy_strong'
                        ? 'bg-emerald-500/10 text-emerald-200'
                        : flow.pressure === 'sell_strong'
                          ? 'bg-rose-500/10 text-rose-200'
                          : 'bg-slate-800/80 text-slate-300'
                    }`}
                  >
                    {flow.pressure_label_vi}
                  </p>
                ) : null}
              </div>

              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {[
                  { label: 'Trần', value: prices?.ceiling },
                  { label: 'Sàn', value: prices?.floor },
                  { label: 'TC', value: prices?.reference },
                  { label: 'Cao', value: prices?.high },
                  { label: 'Thấp', value: prices?.low },
                  { label: 'TB khớp', value: prices?.avg_match },
                ].map((row) => (
                  <div key={row.label} className="rounded-xl border border-white/5 bg-black/25 px-3 py-2.5">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{row.label}</p>
                    <p className="mt-0.5 font-mono text-sm font-semibold text-slate-100">{fmtPrice(row.value)}</p>
                  </div>
                ))}
              </div>

              {data.distance ? (
                <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                  {data.distance.from_reference_pct != null ? (
                    <span>So TC: {fmtPct(data.distance.from_reference_pct)}</span>
                  ) : null}
                  {data.distance.to_ceiling_pct != null ? (
                    <span>→ Trần: {fmtPct(data.distance.to_ceiling_pct)}</span>
                  ) : null}
                  {data.distance.to_floor_pct != null ? (
                    <span>→ Sàn: {fmtPct(data.distance.to_floor_pct)}</span>
                  ) : null}
                </div>
              ) : null}

              {(flow?.bid_levels?.length || flow?.ask_levels?.length) ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  <BookSide title="Dư mua" levels={flow?.bid_levels ?? []} accent="emerald" />
                  <BookSide title="Chào bán" levels={flow?.ask_levels ?? []} accent="rose" />
                </div>
              ) : null}

              {data.foreign?.label_vi ? (
                <p className="rounded-xl border border-cyan-500/20 bg-cyan-950/30 px-3 py-2 text-sm text-cyan-100">
                  {data.foreign.label_vi}
                </p>
              ) : null}

              {data.volume != null && data.volume > 0 ? (
                <p className="text-xs text-slate-500">
                  Khối lượng: {data.volume.toLocaleString('vi-VN', { maximumFractionDigits: 0 })}
                </p>
              ) : null}

              <button
                type="button"
                onClick={() => setShowAi((v) => !v)}
                className="flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-violet-600 to-fuchsia-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-violet-900/40 transition hover:from-violet-500 hover:to-fuchsia-500"
              >
                <Sparkles className="h-4 w-4" />
                {showAi ? 'Ẩn phân tích AI' : 'AI phân tích'}
              </button>

              {showAi ? (
                <div className="border-t border-white/10 pt-2">
                  <AgentDebatePanel symbol={symbol} enabled={showAi} />
                </div>
              ) : null}
            </div>
          )}
        </div>

        {data?.quote_source ? (
          <p className="border-t border-white/5 px-5 py-2 text-[10px] text-slate-600">{data.quote_source}</p>
        ) : null}
      </div>
    </div>
  );
}

function BookSide({
  title,
  levels,
  accent,
}: {
  readonly title: string;
  readonly levels: ReadonlyArray<{ price: number; volume: number }>;
  readonly accent: 'emerald' | 'rose';
}) {
  const color = accent === 'emerald' ? 'text-emerald-300' : 'text-rose-300';
  return (
    <div className="rounded-xl border border-white/5 bg-slate-900/50 p-3">
      <p className={`mb-2 text-xs font-semibold uppercase tracking-wider ${color}`}>{title}</p>
      <ul className="space-y-1 text-xs">
        {levels.slice(0, 5).map((lv, i) => (
          <li key={`${lv.price}-${i}`} className="flex justify-between font-mono tabular-nums text-slate-300">
            <span>{fmtPrice(lv.price)}</span>
            <span className="text-slate-500">{lv.volume.toLocaleString('vi-VN')}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
