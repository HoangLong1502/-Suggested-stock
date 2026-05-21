'use client';

import { useCallback, useEffect, useState } from 'react';
import { ArrowDownRight, ArrowUpRight, Loader2, Minus, RefreshCw, TrendingDown, TrendingUp } from 'lucide-react';
import { getSectorAnalysis, type SectorAnalysisData } from '../../lib/api';

function momentumStyle(id: string) {
  if (id === 'tang_manh' || id === 'tang') return 'text-emerald-400 bg-emerald-500/15 ring-emerald-500/30';
  if (id === 'giam_manh' || id === 'giam') return 'text-rose-400 bg-rose-500/15 ring-rose-500/30';
  return 'text-slate-300 bg-slate-600/30 ring-white/10';
}

function MomentumIcon({ id }: { readonly id: string }) {
  if (id.startsWith('tang')) return <TrendingUp className="h-4 w-4" aria-hidden />;
  if (id.startsWith('giam')) return <TrendingDown className="h-4 w-4" aria-hidden />;
  return <Minus className="h-4 w-4" aria-hidden />;
}

export default function SectorAnalysis() {
  const [data, setData] = useState<SectorAnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getSectorAnalysis());
    } catch {
      setError('Không tải được dữ liệu ngành. Kiểm tra backend (port 5555).');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 90_000);
    return () => clearInterval(t);
  }, [load]);

  return (
    <main className="px-6 py-8 text-slate-100">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-violet-300/90">Sector intelligence</p>
          <h1 className="text-3xl font-bold tracking-tight">Phân tích theo ngành</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-300">
            So sánh xu hướng các nhóm: công nghệ, dầu khí, bất động sản, ngân hàng… % thay đổi lấy từ giá đóng cửa các mã
            đại diện trong hệ thống (DB + VNDirect khi sync).
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-medium hover:bg-white/10 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          Làm mới
        </button>
      </div>

      {error ? (
        <p className="mb-6 rounded-xl border border-rose-500/30 bg-rose-950/40 px-4 py-3 text-sm text-rose-100">{error}</p>
      ) : null}

      {loading && !data ? (
        <div className="flex h-48 items-center justify-center text-slate-400">
          <Loader2 className="mr-2 h-6 w-6 animate-spin text-violet-400" />
          Đang tổng hợp theo ngành…
        </div>
      ) : null}

      {data ? (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-slate-950/80 p-4 ring-1 ring-white/5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">TB thị trường (các nhóm)</p>
              <p
                className={`mt-1 font-mono text-2xl font-bold tabular-nums ${
                  data.market_avg_change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {data.market_avg_change_pct >= 0 ? '+' : ''}
                {data.market_avg_change_pct.toFixed(2)}%
              </p>
            </div>
            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-950/30 p-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-300/80">Ngành dẫn dắt</p>
              <p className="mt-1 text-lg font-semibold text-white">
                {data.sectors[0]?.name_vi ?? '—'}
                <span className="ml-2 font-mono text-emerald-400">
                  {data.sectors[0] ? `${data.sectors[0].change_pct_avg >= 0 ? '+' : ''}${data.sectors[0].change_pct_avg.toFixed(2)}%` : ''}
                </span>
              </p>
            </div>
            <div className="rounded-2xl border border-rose-500/20 bg-rose-950/30 p-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-rose-300/80">Ngành yếu nhất</p>
              <p className="mt-1 text-lg font-semibold text-white">
                {data.sectors[data.sectors.length - 1]?.name_vi ?? '—'}
                <span className="ml-2 font-mono text-rose-400">
                  {data.sectors.length
                    ? `${data.sectors[data.sectors.length - 1].change_pct_avg >= 0 ? '+' : ''}${data.sectors[data.sectors.length - 1].change_pct_avg.toFixed(2)}%`
                    : ''}
                </span>
              </p>
            </div>
          </div>

          <p className="mb-4 text-xs text-slate-500">{data.data_source}</p>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.sectors.map((sector) => {
              const up = sector.change_pct_avg >= 0;
              const open = expanded === sector.id;
              return (
                <article
                  key={sector.id}
                  className="overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900/90 to-slate-950 ring-1 ring-white/5 transition hover:border-violet-500/30"
                >
                  <button
                    type="button"
                    className="w-full p-5 text-left"
                    onClick={() => setExpanded(open ? null : sector.id)}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h2 className="text-lg font-bold text-white">{sector.name_vi}</h2>
                        <p className="text-xs text-slate-500">{sector.name_en}</p>
                      </div>
                      <span
                        className={`inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-semibold ring-1 ${momentumStyle(sector.momentum)}`}
                      >
                        <MomentumIcon id={sector.momentum} />
                        {sector.momentum_vi}
                      </span>
                    </div>

                    <div className="mt-4 flex items-end justify-between">
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-slate-500">% TB ngành</p>
                        <p className={`font-mono text-3xl font-bold tabular-nums ${up ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {up ? '+' : ''}
                          {sector.change_pct_avg.toFixed(2)}%
                        </p>
                      </div>
                      <div className="text-right text-[11px] text-slate-400">
                        <p className="flex items-center justify-end gap-1 text-emerald-400">
                          <ArrowUpRight className="h-3 w-3" /> {sector.gainers} tăng
                        </p>
                        <p className="flex items-center justify-end gap-1 text-rose-400">
                          <ArrowDownRight className="h-3 w-3" /> {sector.losers} giảm
                        </p>
                        <p className="text-slate-500">
                          {sector.stocks_with_data}/{sector.stocks_total} mã có dữ liệu
                        </p>
                      </div>
                    </div>

                    {sector.leader_symbol ? (
                      <p className="mt-3 rounded-lg bg-black/25 px-3 py-2 text-xs text-slate-300">
                        Mã dẫn: <span className="font-mono font-bold text-white">{sector.leader_symbol}</span>{' '}
                        <span className={sector.leader_change_pct! >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                          {sector.leader_change_pct! >= 0 ? '+' : ''}
                          {sector.leader_change_pct!.toFixed(2)}%
                        </span>
                      </p>
                    ) : null}
                  </button>

                  {open && sector.stocks.length > 0 ? (
                    <ul className="border-t border-white/10 bg-black/20 px-4 py-3">
                      {sector.stocks.map((st) => (
                        <li
                          key={st.symbol}
                          className="flex items-center justify-between border-b border-white/5 py-2 last:border-0"
                        >
                          <span className="font-mono font-semibold text-white">{st.symbol}</span>
                          <span
                            className={`font-mono text-sm font-bold tabular-nums ${
                              st.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                          >
                            {st.change_pct >= 0 ? '+' : ''}
                            {st.change_pct.toFixed(2)}%
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </article>
              );
            })}
          </div>
        </>
      ) : null}
    </main>
  );
}
