'use client';

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

interface MarketOverviewProps {
  readonly overview: {
    readonly indices: ReadonlyArray<{ symbol: string; price: number; change: number }>;
    readonly watchlist: readonly string[];
    readonly top_gainers: ReadonlyArray<{ symbol: string; change: number }>;
    readonly top_losers: ReadonlyArray<{ symbol: string; change: number }>;
    readonly sector_heatmap: ReadonlyArray<{ sector: string; strength: number }>;
  };
}

const chartData = [
  { name: '09:00', value: 1180 },
  { name: '10:00', value: 1192 },
  { name: '11:00', value: 1188 },
  { name: '12:00', value: 1200 },
  { name: '13:00', value: 1206 },
  { name: '14:00', value: 1212 },
  { name: '15:00', value: 1200 },
];

export default function MarketOverview({ overview }: MarketOverviewProps) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        {overview.indices.map((index) => (
          <div key={index.symbol} className="rounded-3xl border border-slate-800 bg-slate-900/80 p-4">
            <p className="text-sm uppercase tracking-[0.24em] text-slate-400">{index.symbol}</p>
            <p className="mt-3 text-2xl font-semibold">{index.price.toFixed(2)}</p>
            <p className={index.change >= 0 ? 'text-emerald-400' : 'text-rose-400'}>{index.change.toFixed(2)}%</p>
          </div>
        ))}
      </div>

      <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm uppercase tracking-[0.24em] text-slate-400">Intraday trend</p>
          <span className="text-xs text-slate-500">VNINDEX trend preview</span>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: '#0f172a', borderColor: '#334155' }} />
              <Line type="monotone" dataKey="value" stroke="#8b5cf6" strokeWidth={3} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
