import { ArrowUpRight, Sparkles, TrendingUp } from 'lucide-react';
import MarketOverview from '../components/dashboard/MarketOverview';
import AgentDebatePanel from '../components/agent/AgentDebatePanel';
import { getDashboardData, getSuggestedStock } from '../lib/api';

type DashboardData = {
  indices: Array<{ symbol: string; price: number; change: number }>;
  watchlist: Array<{ symbol: string; price: number; change: number }>;
  top_gainers: Array<{ symbol: string; change: number }>;
  top_losers: Array<{ symbol: string; change: number }>;
  sector_heatmap: Array<{ sector: string; strength: number }>;
};

export default async function Home() {
  const data = (await getDashboardData()) as DashboardData;
  const suggestion = await getSuggestedStock();
  const watchlist = data.watchlist.map((item) =>
    typeof item === 'string'
      ? { symbol: item, price: 0, change: 0 }
      : item,
  );
  const suggestedSymbol =
    suggestion?.suggested?.symbol ?? watchlist[0]?.symbol ?? 'SSI';

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
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.24em] text-slate-400">Watchlist</p>
                <h2 className="text-2xl font-semibold">Top Vietnamese symbols</h2>
              </div>
            </div>
            <div className="space-y-3">
              {watchlist.map((item) => (
                <div key={item.symbol} className="flex items-center justify-between rounded-3xl border border-slate-800 bg-slate-900/70 px-4 py-3">
                  <div>
                    <p className="font-semibold">{item.symbol}</p>
                    <p className="text-xs text-slate-500">{item.price.toFixed(2)}</p>
                  </div>
                  <span className={item.change >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                    {item.change >= 0 ? '+' : ''}{item.change.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section className="section-card">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.24em] text-slate-400">Signals</p>
                <h2 className="text-2xl font-semibold">Top movers</h2>
              </div>
            </div>
            <div className="grid gap-3">
              {data.top_gainers.map((item) => (
                <div key={item.symbol} className="rounded-3xl border border-slate-800 bg-slate-900/70 px-4 py-3">
                  <div className="flex items-center justify-between">
                    <span>{item.symbol}</span>
                    <span className="text-emerald-400">+{item.change}%</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </main>
  );
}
