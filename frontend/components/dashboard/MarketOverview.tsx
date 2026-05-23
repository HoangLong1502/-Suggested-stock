'use client';

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

interface MarketOverviewProps {
  readonly overview: {
    readonly indices: ReadonlyArray<{ symbol: string; price: number; change: number }>;
    /** API có thể trả chuỗi mã hoặc object — component chỉ dùng indices/chart/sector. */
    readonly watchlist: ReadonlyArray<string | { symbol: string; price: number; change: number }>;
    readonly top_gainers: ReadonlyArray<{ symbol: string; change: number }>;
    readonly top_losers: ReadonlyArray<{ symbol: string; change: number }>;
    readonly sector_heatmap: ReadonlyArray<{ sector: string; strength: number }>;
    readonly chart_preview?: ReadonlyArray<{ name: string; value: number }>;
  };
}

const staticChart = [
  { name: '09:00', value: 1180 },
  { name: '10:00', value: 1192 },
  { name: '11:00', value: 1188 },
  { name: '12:00', value: 1200 },
  { name: '13:00', value: 1206 },
  { name: '14:00', value: 1212 },
  { name: '15:00', value: 1200 },
];

export default function MarketOverview({ overview }: MarketOverviewProps) {
  const chartData =
    overview.chart_preview && overview.chart_preview.length >= 2 ? [...overview.chart_preview] : staticChart;
  const liveHint =
    overview.chart_preview && overview.chart_preview.length >= 2
      ? 'Đường giá gần đây (VNINDEX, các nến đóng cửa trong DB).'
      : 'Biểu đồ minh họa — chưa có đủ dữ liệu VNINDEX để vẽ đường thật.';

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        {overview.indices.map((index) => {
          const up = index.change >= 0;
          return (
            <div
              key={index.symbol}
              className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 p-4 shadow-lg ring-1 ring-white/5"
            >
              <div className="absolute -right-4 -top-4 h-20 w-20 rounded-full bg-violet-600/15 blur-2xl" />
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-200">{index.symbol}</p>
              <p className="relative mt-2 font-mono text-2xl font-bold text-white">{index.price.toFixed(2)}</p>
              <p className={`relative mt-1 font-mono text-sm font-semibold ${up ? 'text-emerald-400' : 'text-rose-400'}`}>
                {up ? '+' : ''}
                {index.change.toFixed(2)}%
              </p>
            </div>
          );
        })}
      </div>

      <div className="rounded-2xl border border-white/10 bg-slate-950/80 p-5 ring-1 ring-white/5">
        <div className="mb-3 rounded-xl border border-amber-500/25 bg-amber-950/35 px-3 py-2 text-sm text-amber-50">{liveHint}</div>
        <div className="mb-4 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-200">Xu hướng gần đây</p>
          <span className="text-xs text-slate-300">VNINDEX · preview</span>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <XAxis dataKey="name" tick={{ fill: '#cbd5e1', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#cbd5e1', fontSize: 12 }} axisLine={false} tickLine={false} domain={['auto', 'auto']} />
              <Tooltip contentStyle={{ background: '#0f172a', borderColor: '#334155', borderRadius: '12px' }} />
              <Line
                type="monotone"
                dataKey="value"
                stroke={overview.chart_preview && overview.chart_preview.length >= 2 ? '#34d399' : '#a78bfa'}
                strokeWidth={2.5}
                dot={{ r: 3, fill: '#1e293b', strokeWidth: 2 }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {overview.sector_heatmap?.length ? (
          <div className="mt-5 border-t border-white/5 pt-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200">Bản đồ ngành</p>
            <div className="flex flex-wrap gap-2">
              {overview.sector_heatmap.map((s) => (
                <span
                  key={s.sector}
                  className="rounded-lg border border-white/15 bg-white/10 px-3 py-1.5 text-sm text-slate-100"
                >
                  {s.sector}{' '}
                  <span className="font-mono text-violet-300">{Math.round(s.strength * 100)}%</span>
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
