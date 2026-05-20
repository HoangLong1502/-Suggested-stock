import { ArrowUpRight, Sparkles, TrendingUp } from 'lucide-react';
import MarketOverview from '../components/dashboard/MarketOverview';
import WatchlistMovers from '../components/dashboard/WatchlistMovers';
import AgentDebatePanel from '../components/agent/AgentDebatePanel';
import AIStockRanking from '../components/dashboard/AIStockRanking';
import { getDashboardData } from '../lib/api';

type WatchlistRow = {
  symbol: string;
  price: number;
  change: number;
  change_pct?: number;
  trading_date?: string;
  signal?: string;
  signal_vi?: string;
  volume?: number;
  quote_source_note?: string;
  market_session?: { label_vi?: string; phase?: string; is_trading_hours?: boolean };
};

type DashboardData = {
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
  market_session?: { label_vi?: string; phase?: string };
  chart_preview?: Array<{ name: string; value: number }>;
};

export default async function Home() {
  const data = (await getDashboardData()) as DashboardData;
  const watchlist = data.watchlist.map((item) =>
    typeof item === 'string'
      ? { symbol: item, price: 0, change: 0 }
      : item,
  );
  /** Không gọi /agents/suggest ở SSR — endpoint đó chạy nhiều agent/ mã, dễ làm tab quay vòng vài phút. */
  const suggestedSymbol = watchlist[0]?.symbol ?? 'SSI';

  return (
    <main className="min-h-screen px-6 py-8 text-slate-100">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-slate-400">AI multi-agent stock platform</p>
          <h1 className="text-4xl font-semibold">Vietnam market intelligence</h1>
        </div>
        <div className="flex items-center gap-3 text-slate-300">
          <Sparkles className="h-5 w-5" />
          <span>Realtime ideas, AI debate, watchlists.</span>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.8fr_1fr]">
        <div className="space-y-5">
          <section className="section-card">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.24em] text-slate-400">Market Overview</p>
                <h2 className="text-2xl font-semibold">VNINDEX & Market pulse</h2>
              </div>
              <ArrowUpRight className="h-5 w-5 text-slate-300" />
            </div>
            <MarketOverview overview={data} />
          </section>

          <section className="section-card">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.24em] text-slate-400">AI Debate Room</p>
                <h2 className="text-2xl font-semibold">Agent recommendation chain</h2>
              </div>
              <TrendingUp className="h-5 w-5 text-slate-300" />
            </div>
            <AgentDebatePanel symbol={suggestedSymbol} />
          </section>
        </div>

        <aside className="space-y-5">
          <section className="section-card">
            <WatchlistMovers
              watchlist={watchlist as WatchlistRow[]}
              topGainers={data.top_gainers ?? []}
              topLosers={data.top_losers ?? []}
              sessionLabel={data.market_session?.label_vi}
            />
          </section>

          <AIStockRanking />

        </aside>
      </div>
    </main>
  );
}
