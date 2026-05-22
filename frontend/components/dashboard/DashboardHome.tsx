'use client';

import { useCallback, useEffect, useState } from 'react';
import { ArrowUpRight, Loader2, Sparkles, TrendingUp } from 'lucide-react';
import MarketOverview from './MarketOverview';
import WatchlistMovers from './WatchlistMovers';
import AgentDebatePanel from '../agent/AgentDebatePanel';
import AIStockRanking from './AIStockRanking';
import { apiUrl, WATCHLIST_FALLBACK_SYMBOLS } from '../../lib/api';
import { useCommitteeReport } from '../../hooks/useCommitteeReport';
import { resolveDebateSymbol } from '../../types/committee';

export type WatchlistRow = {
  symbol: string;
  price: number;
  change: number;
  change_pct?: number;
  trading_date?: string;
  signal?: string;
  signal_vi?: string;
  volume?: number;
  quote_source_note?: string;
  market_session?: {
    label_vi?: string;
    phase?: string;
    is_trading_hours?: boolean;
    is_trading_day?: boolean;
  };
};

export type DashboardData = {
  indices: Array<{ symbol: string; price: number; change: number }>;
  watchlist: Array<WatchlistRow | string>;
  top_gainers: Array<{
    symbol: string;
    change: number;
    change_pct?: number;
    last_close?: number | null;
    prev_close?: number | null;
    trading_date?: string;
    signal?: string;
    signal_vi?: string;
  }>;
  top_losers: Array<{
    symbol: string;
    change: number;
    change_pct?: number;
    last_close?: number | null;
    prev_close?: number | null;
    trading_date?: string;
    signal?: string;
    signal_vi?: string;
  }>;
  sector_heatmap: Array<{ sector: string; strength: number }>;
  market_session?: {
    label_vi?: string;
    phase?: string;
    is_trading_hours?: boolean;
    is_trading_day?: boolean;
  };
  chart_preview?: Array<{ name: string; value: number }>;
};

const CLIENT_FETCH_MS = 25_000;
const MARKET_REFRESH_MS = 12_000;

function emptyDashboard(): DashboardData {
  return {
    indices: [],
    watchlist: WATCHLIST_FALLBACK_SYMBOLS.map((symbol) => ({ symbol, price: 0, change: 0 })),
    top_gainers: [],
    top_losers: [],
    sector_heatmap: [],
    chart_preview: [],
  };
}

async function fetchOverview(): Promise<DashboardData> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), CLIENT_FETCH_MS);
  try {
    const res = await fetch(`${apiUrl}/market/overview?fast=true`, {
      cache: 'no-store',
      signal: ctrl.signal,
    });
    if (!res.ok) return emptyDashboard();
    const data = (await res.json()) as DashboardData;
    if (!Array.isArray(data.watchlist) || data.watchlist.length === 0) {
      return {
        ...data,
        watchlist: WATCHLIST_FALLBACK_SYMBOLS.map((symbol) => ({ symbol, price: 0, change: 0 })),
      };
    }
    return data;
  } catch {
    return emptyDashboard();
  } finally {
    clearTimeout(t);
  }
}

function MarketSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 rounded-2xl bg-slate-800/80" />
        ))}
      </div>
      <div className="h-64 rounded-2xl bg-slate-800/60" />
    </div>
  );
}

function WatchlistSkeleton() {
  return (
    <div className="animate-pulse space-y-8">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
          <div key={i} className="h-28 rounded-2xl bg-slate-800/80" />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="h-48 rounded-2xl bg-slate-800/60" />
        <div className="h-48 rounded-2xl bg-slate-800/60" />
      </div>
    </div>
  );
}

export default function DashboardHome() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const {
    data: committeeReport,
    isLoading: committeeLoading,
    isFetching: committeeFetching,
  } = useCommitteeReport();
  const debateSymbol = resolveDebateSymbol(committeeReport);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await fetchOverview();
      setData(next);
    } catch {
      setError('Không tải được dữ liệu thị trường. Kiểm tra backend đang chạy.');
      setData(emptyDashboard());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, MARKET_REFRESH_MS);
    return () => clearInterval(id);
  }, [load]);

  const session = data?.market_session;
  const watchlist = (data?.watchlist ?? []).map((item) =>
    typeof item === 'string'
      ? { symbol: item, price: 0, change: 0, market_session: session }
      : { ...item, market_session: item.market_session ?? session },
  );
  const debatePending = committeeLoading || committeeFetching;
  const debateReady = Boolean(debateSymbol);

  return (
    <main className="min-h-screen px-6 py-8 text-slate-100">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-slate-400">AI multi-agent stock platform</p>
          <h1 className="text-4xl font-semibold">Vietnam market intelligence</h1>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-slate-300">
          <Sparkles className="h-5 w-5" />
          <span>Realtime ideas, AI debate, watchlists.</span>
          {loading ? (
            <span className="inline-flex items-center gap-1.5 text-xs text-violet-300">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Đang tải giá…
            </span>
          ) : (
            <button
              type="button"
              onClick={load}
              className="rounded-lg border border-white/15 px-3 py-1 text-xs text-slate-200 hover:bg-white/10"
            >
              Làm mới giá
            </button>
          )}
        </div>
      </div>

      {error ? (
        <p className="mb-4 rounded-xl border border-amber-500/30 bg-amber-950/40 px-4 py-2 text-sm text-amber-100">
          {error}
        </p>
      ) : null}

      <div className="space-y-5">
        <section className="section-card w-full">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-slate-400">Market Overview</p>
              <h2 className="text-2xl font-semibold">VNINDEX & Market pulse</h2>
            </div>
            <ArrowUpRight className="h-5 w-5 text-slate-300" />
          </div>
          {loading || !data ? <MarketSkeleton /> : <MarketOverview overview={data} />}
        </section>

        <section className="section-card w-full">
          {loading || !data ? (
            <WatchlistSkeleton />
          ) : (
            <WatchlistMovers
              watchlist={watchlist as WatchlistRow[]}
              topGainers={data.top_gainers ?? []}
              topLosers={data.top_losers ?? []}
              sessionLabel={session?.label_vi}
              sessionPhase={session?.phase}
              isTradingHours={session?.is_trading_hours}
              isTradingDay={session?.is_trading_day}
            />
          )}
        </section>

        <section className="section-card w-full">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-slate-400">AI Debate Room</p>
              <h2 className="text-2xl font-semibold">Agent recommendation chain</h2>
              <p className="mt-1 text-sm text-slate-400">
                {debateReady ? (
                  <>
                    Phân tích sâu mã{' '}
                    <span className="font-mono text-violet-300">{debateSymbol}</span> (best pick hội đồng)
                  </>
                ) : debatePending ? (
                  'Đang chờ hội đồng chọn best pick…'
                ) : (
                  'Chưa có best pick — xem AI ranking bên dưới'
                )}
              </p>
            </div>
            <TrendingUp className="h-5 w-5 text-slate-300" />
          </div>
          {debateReady ? (
            <AgentDebatePanel symbol={debateSymbol!} />
          ) : debatePending ? (
            <div className="flex items-center gap-2 rounded-2xl border border-violet-500/20 bg-slate-950/60 px-4 py-8 text-sm text-slate-300">
              <Loader2 className="h-5 w-5 animate-spin text-violet-400" />
              Đang tải best pick (một lần cho cả trang)…
            </div>
          ) : (
            <p className="rounded-2xl border border-amber-500/25 bg-amber-950/30 px-4 py-6 text-sm text-amber-100">
              Hội đồng chưa chốt mã mua. Kiểm tra backend hoặc bấm Làm mới ở AI ranking.
            </p>
          )}
        </section>

        <section className="section-card w-full">
          <AIStockRanking />
        </section>
      </div>
    </main>
  );
}
