import { Activity, Flame, TrendingDown, TrendingUp, Minus } from 'lucide-react';

export type WatchRow = {
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

export type MoverRow = {
  symbol: string;
  change: number;
  change_pct?: number;
  last_close?: number | null;
  prev_close?: number | null;
  trading_date?: string;
  signal?: string;
  signal_vi?: string;
};

function pct(v: WatchRow | MoverRow) {
  const n = 'change_pct' in v && v.change_pct != null ? v.change_pct : v.change;
  return Number(n) || 0;
}

function SignalIcon({ signal }: { readonly signal?: string }) {
  if (signal === 'bull') return <TrendingUp className="h-4 w-4 text-emerald-400" aria-hidden />;
  if (signal === 'bear') return <TrendingDown className="h-4 w-4 text-rose-400" aria-hidden />;
  return <Minus className="h-4 w-4 text-slate-500" aria-hidden />;
}

/** Nhãn giá theo phiên VN — sau giờ / cuối tuần nhấn mạnh giá đóng cửa gần nhất. */
function priceContextForRow(
  item: WatchRow,
  global: { phase?: string; isTradingHours?: boolean; isTradingDay?: boolean },
): { badge: string; hint: string } {
  const phase = item.market_session?.phase ?? global.phase;
  const hours = item.market_session?.is_trading_hours ?? global.isTradingHours;
  const day = item.market_session?.is_trading_day ?? global.isTradingDay;

  if (phase === 'weekend' || day === false) {
    return {
      badge: 'Đóng cửa',
      hint: 'Cuối tuần — hiển thị giá đóng cửa phiên giao dịch gần nhất trong hệ thống.',
    };
  }
  if (phase === 'after_close') {
    return {
      badge: 'Đóng phiên',
      hint: 'Đã hết giờ HOSE/HNX — mức hiển thị là giá đóng cửa / tham chiếu cuối phiên từ nguồn dữ liệu.',
    };
  }
  if (hours && (phase === 'morning' || phase === 'afternoon')) {
    return {
      badge: 'Trong phiên',
      hint: 'Đang trong giờ khớp lệnh — giá có thể thay đổi theo thị trường.',
    };
  }
  return {
    badge: 'Tham chiếu',
    hint: 'Trước giờ mở cửa hoặc nghỉ trưa — mức tham chiếu / đóng gần nhất.',
  };
}

export default function WatchlistMovers({
  watchlist,
  topGainers,
  topLosers,
  sessionLabel,
  sessionPhase,
  isTradingHours,
  isTradingDay,
}: {
  readonly watchlist: ReadonlyArray<WatchRow>;
  readonly topGainers: ReadonlyArray<MoverRow>;
  readonly topLosers: ReadonlyArray<MoverRow>;
  readonly sessionLabel?: string;
  readonly sessionPhase?: string;
  readonly isTradingHours?: boolean;
  readonly isTradingDay?: boolean;
}) {
  const sessionGlobal = { phase: sessionPhase, isTradingHours, isTradingDay };
  return (
    <div className="space-y-8">
      <section>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-violet-300/90">Watchlist</p>
            <h2 className="mt-1 text-2xl font-bold tracking-tight text-white">Danh mã theo dõi</h2>
            <p className="mt-1 max-w-md text-sm text-slate-400">
              Sau khi hết phiên, bảng hiển thị <span className="text-slate-200">giá đóng cửa / tham chiếu cuối</span> và % so
              với phiên liền trước. Trong giờ giao dịch, giá phản ánh bản ghi mới nhất từ nguồn.
            </p>
          </div>
          {sessionLabel ? (
            <span className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3 py-1.5 text-xs text-cyan-100">
              <Activity className="h-3.5 w-3.5" />
              {sessionLabel}
            </span>
          ) : null}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {watchlist.map((item) => {
            const p = pct(item);
            const up = p >= 0;
            const ctx = priceContextForRow(item, sessionGlobal);
            return (
              <div
                key={item.symbol}
                className="group relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900/95 via-slate-950 to-slate-950 p-4 shadow-lg shadow-black/20 ring-1 ring-white/5 transition hover:border-violet-500/40 hover:ring-violet-500/20"
              >
                <div className="absolute right-0 top-0 h-24 w-24 rounded-full bg-violet-600/10 blur-2xl" />
                <div className="relative flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-mono text-lg font-bold tracking-wide text-white">{item.symbol}</p>
                      <span
                        className={`rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${
                          ctx.badge === 'Trong phiên'
                            ? 'bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-500/30'
                            : ctx.badge === 'Đóng phiên' || ctx.badge === 'Đóng cửa'
                              ? 'bg-amber-500/15 text-amber-100 ring-1 ring-amber-400/25'
                              : 'bg-slate-600/40 text-slate-200 ring-1 ring-white/10'
                        }`}
                      >
                        {ctx.badge}
                      </span>
                    </div>
                    <p className="mt-0.5 text-[11px] leading-snug text-slate-500">{ctx.hint}</p>
                    <p className="mt-2 font-mono text-2xl font-semibold tabular-nums text-slate-100">
                      {(item.price ?? 0).toLocaleString('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </p>
                    {item.trading_date ? (
                      <p className="mt-1 text-[11px] uppercase tracking-wider text-slate-500">Phiên {item.trading_date}</p>
                    ) : null}
                  </div>
                  <div className="text-right">
                    <div className="inline-flex items-center gap-1.5 rounded-lg bg-black/30 px-2 py-1">
                      <SignalIcon signal={item.signal} />
                      <span
                        className={`font-mono text-lg font-bold tabular-nums ${up ? 'text-emerald-400' : 'text-rose-400'}`}
                      >
                        {up ? '+' : ''}
                        {p.toFixed(2)}%
                      </span>
                    </div>
                    {item.signal_vi ? (
                      <p className="mt-2 text-[11px] font-medium text-slate-400">{item.signal_vi}</p>
                    ) : null}
                  </div>
                </div>
                {item.volume != null && item.volume > 0 ? (
                  <p className="relative mt-3 border-t border-white/5 pt-2 text-[11px] text-slate-500">
                    KL: {item.volume.toLocaleString('vi-VN', { maximumFractionDigits: 0 })}
                  </p>
                ) : null}
              </div>
            );
          })}
        </div>
      </section>

      <section>
        <div className="mb-4 flex items-center gap-2">
          <Flame className="h-5 w-5 text-amber-400" />
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-amber-200/80">Signals</p>
            <h2 className="text-xl font-bold text-white">Top movers</h2>
            <p className="text-xs text-slate-500">% so với phiên liền trước trong DB; kèm tín hiệu nhanh</p>
          </div>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <MoverColumn title="Top tăng" accent="emerald" rows={topGainers} />
          <MoverColumn title="Top giảm" accent="rose" rows={topLosers} />
        </div>
      </section>
    </div>
  );
}

function MoverColumn({
  title,
  accent,
  rows,
}: {
  readonly title: string;
  readonly accent: 'emerald' | 'rose';
  readonly rows: ReadonlyArray<MoverRow>;
}) {
  const ring = accent === 'emerald' ? 'ring-emerald-500/20' : 'ring-rose-500/20';
  const bar = accent === 'emerald' ? 'from-emerald-500/80' : 'from-rose-500/80';
  if (!rows.length) {
    return (
      <div className={`rounded-2xl border border-dashed border-slate-700 bg-slate-950/50 p-5 text-left text-sm text-slate-300 ring-1 ${ring}`}>
        <p className="font-medium text-slate-200">Chưa có dữ liệu {title.toLowerCase()}</p>
        <p className="mt-2 text-xs leading-relaxed text-slate-400">
          Top movers lấy từ API backend (giá lịch sử trong DB). Làm lần lượt:
        </p>
        <ol className="mt-2 list-decimal space-y-1.5 pl-4 text-xs text-slate-300">
          <li>
            Mở terminal tại thư mục dự án, chạy:{' '}
            <code className="rounded bg-black/40 px-1.5 py-0.5 font-mono text-[11px] text-violet-200">docker compose up --build</code>
          </li>
          <li>
            Đợi container <strong className="text-slate-200">backend</strong> và <strong className="text-slate-200">postgres</strong> chạy
            (log không báo lỗi kết nối DB).
          </li>
          <li>
            Kiểm tra API:{' '}
            <a
              href="http://localhost:5555/api/v1/market/overview"
              target="_blank"
              rel="noopener noreferrer"
              className="text-violet-300 underline hover:text-violet-200"
            >
              localhost:5555/api/v1/market/overview
            </a>{' '}
            — phải có mảng <code className="font-mono text-[11px]">top_gainers</code> không rỗng.
          </li>
          <li>Tải lại trang frontend (F5). Lần đầu có thể mất 1–2 phút để đồng bộ giá / seed demo.</li>
        </ol>
      </div>
    );
  }
  return (
    <div className={`rounded-2xl border border-white/10 bg-slate-950/80 p-4 ring-1 ${ring}`}>
      <div className={`mb-3 h-1 w-16 rounded-full bg-gradient-to-r ${bar} to-transparent`} />
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-300">{title}</h3>
      <ul className="space-y-2">
        {rows.map((row, idx) => {
          const p = pct(row);
          const up = p >= 0;
          const color = accent === 'emerald' ? (up ? 'text-emerald-400' : 'text-slate-400') : up ? 'text-slate-400' : 'text-rose-400';
          return (
            <li
              key={`${row.symbol}-${idx}`}
              className="flex items-center justify-between gap-3 rounded-xl border border-white/5 bg-black/20 px-3 py-2.5"
            >
              <div className="flex min-w-0 flex-1 items-center gap-3">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/5 font-mono text-xs font-bold text-slate-400">
                  {idx + 1}
                </span>
                <div className="min-w-0">
                  <p className="font-mono font-semibold text-white">{row.symbol}</p>
                  <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-slate-500">
                    {row.last_close != null && row.last_close > 0 ? (
                      <span>Đóng {row.last_close.toFixed(2)}</span>
                    ) : null}
                    {row.prev_close != null && row.prev_close > 0 ? (
                      <span className="text-slate-600">← trước {row.prev_close.toFixed(2)}</span>
                    ) : null}
                    {row.trading_date ? <span className="text-violet-400/80">· {row.trading_date}</span> : null}
                  </div>
                  {row.signal_vi ? (
                    <p className="mt-1 flex items-center gap-1.5 text-[11px] font-medium text-slate-400">
                      <SignalIcon signal={row.signal} />
                      {row.signal_vi}
                    </p>
                  ) : null}
                </div>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-0.5">
                {!row.signal_vi ? <SignalIcon signal={row.signal} /> : null}
                <span className={`font-mono text-sm font-bold tabular-nums ${color}`}>
                  {p >= 0 ? '+' : ''}
                  {p.toFixed(2)}%
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
