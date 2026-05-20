'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { AlertCircle, Trophy, Users, Target } from 'lucide-react';
import { apiUrl, getBestStock } from '../../lib/api';

interface StockRanking {
  symbol: string;
  recommendation: string;
  confidence: number;
  consensus_strength: number;
  reasoning: string;
  agents_buy: number;
  agents_sell: number;
  agents_hold: number;
  when_to_buy?: {
    summary_vi?: string;
    timing?: string;
    urgency?: string;
    buy_signals?: string[];
    recommended_entry_price?: number;
    next_check_hours?: number;
  };
  why_this_stock?: string;
  agent_details: Array<{
    agent: string;
    verdict: string;
    confidence: number;
    rationale: string;
  }>;
}

interface BestStockData {
  best_stock?: string;
  symbol?: string;
  recommendation: string;
  confidence: number;
  consensus_strength: number;
  reasoning: string;
  why_this_stock?: string;
  buy_timing?: {
    timing: string;
    urgency: string;
    buy_signals?: string[];
    wait_reasons?: string[];
    next_check_hours?: number;
  };
  recommended_entry?: number;
  current_price?: number;
  timestamp?: string;
}

interface TopStocksData {
  timestamp: string;
  analysis_period_days: number;
  status?: string;
  server_message?: string;
  summary: {
    total_analyzed: number;
    high_confidence: number;
    buy_signals: number;
    hold_signals: number;
    sell_signals: number;
  };
  best_stock: string | null;
  buy_recommendations: StockRanking[];
  all_ranked: StockRanking[];
}

export default function AIStockRanking() {
  const [topStocks, setTopStocks] = useState<TopStocksData | null>(null);
  const [bestStock, setBestStock] = useState<BestStockData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedStock, setExpandedStock] = useState<string | null>(null);
  const [selectedTab, setSelectedTab] = useState<'all' | 'buy' | 'analysis'>('all');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    await Promise.allSettled([fetchTopStocks(), fetchBestStock()]);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10 * 60 * 1000); // Mỗi phân tích rất nặng — refresh 10 phút
    return () => clearInterval(interval);
  }, [fetchData]);

  const fetchTopStocks = async () => {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 900_000);
    try {
      const response = await fetch(`${apiUrl}/agents/top-stocks?limit=10&min_confidence=0.4`, {
        cache: 'no-store',
        signal: ctrl.signal,
      });
      const text = await response.text();
      if (!response.ok) {
        let msg = text.slice(0, 400);
        try {
          const j = JSON.parse(text) as { detail?: string; error?: string; message?: string };
          msg = (typeof j.detail === 'string' && j.detail) || j.error || j.message || msg;
        } catch {
          /* keep slice */
        }
        throw new Error(msg || `HTTP ${response.status}`);
      }
      const data = JSON.parse(text) as TopStocksData;
      setTopStocks(data);
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        setError('Hết thời gian chờ (15 phút). Backend đang phân tích quá lâu — thử Refresh hoặc giảm số mã watchlist.');
      } else {
        setError(err instanceof Error ? err.message : 'An error occurred');
      }
    } finally {
      clearTimeout(t);
    }
  };

  const fetchBestStock = async () => {
    try {
      const data = await getBestStock();
      if (data && data.best_stock) {
        setBestStock(data as BestStockData);
      }
    } catch {
      // ignore best stock failures
    }
  };

  const getRecommendationColor = (recommendation: string) => {
    switch (recommendation.toLowerCase()) {
      case 'buy':
        return 'border-emerald-500/25 bg-emerald-950/35 hover:border-emerald-400/40';
      case 'sell':
        return 'border-rose-500/25 bg-rose-950/35 hover:border-rose-400/40';
      case 'hold':
        return 'border-amber-500/25 bg-amber-950/25 hover:border-amber-400/35';
      default:
        return 'border-slate-600/50 bg-slate-900/50 hover:border-slate-500/50';
    }
  };

  const getVerdictBadge = (verdict: string) => {
    switch (verdict.toLowerCase()) {
      case 'buy':
        return 'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30';
      case 'sell':
        return 'bg-rose-500/15 text-rose-300 ring-1 ring-rose-500/30';
      case 'hold':
        return 'bg-amber-500/15 text-amber-200 ring-1 ring-amber-500/30';
      default:
        return 'bg-slate-600/40 text-slate-200 ring-1 ring-white/10';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'text-emerald-400';
    if (confidence >= 65) return 'text-sky-400';
    if (confidence >= 50) return 'text-amber-300';
    return 'text-rose-400';
  };

  const bestHighlight = bestStock || (topStocks?.all_ranked?.[0] as BestStockData | undefined);

  if (loading && !topStocks) {
    return (
      <div className="flex h-52 items-center justify-center rounded-2xl border border-violet-500/20 bg-slate-950/60">
        <div className="text-center">
          <Trophy className="mx-auto mb-3 h-9 w-9 animate-pulse text-violet-400" />
          <p className="text-sm font-medium text-slate-200">Đang phân tích watchlist với AI agents…</p>
        </div>
      </div>
    );
  }

  const bestSymbol =
    bestHighlight && 'best_stock' in bestHighlight && bestHighlight.best_stock
      ? bestHighlight.best_stock
      : bestHighlight?.symbol ?? '';

  const whyText = bestStock?.why_this_stock ?? bestHighlight?.reasoning ?? '';

  return (
    <div className="space-y-5 text-slate-200">
      <div className="relative overflow-hidden rounded-2xl border border-violet-500/25 bg-gradient-to-br from-violet-950/80 via-slate-900 to-slate-950 p-5 ring-1 ring-violet-500/15">
        <div className="pointer-events-none absolute -right-16 -top-20 h-48 w-48 rounded-full bg-violet-600/20 blur-3xl" />
        <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-xl font-bold tracking-tight text-white">
              <Trophy className="h-6 w-6 text-amber-400" />
              AI ranking & best pick
            </h2>
            <p className="mt-1.5 max-w-2xl text-base font-normal leading-relaxed text-slate-100">
              60 ngày dữ liệu, tổng hợp từ nhiều agent — giao diện tối đồng bộ với dashboard.
            </p>
          </div>
          <button
            type="button"
            onClick={fetchData}
            className="shrink-0 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-white/10"
          >
            Làm mới
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-500/30 bg-rose-950/40 p-4 text-sm text-rose-100">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
          <p>{error}</p>
        </div>
      )}

      {topStocks?.status === 'degraded' && topStocks.server_message && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-950/35 p-4 text-sm text-amber-100">
          Phân tích ranking tạm không chạy xong: {topStocks.server_message}
        </div>
      )}

      {topStocks && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            <div className="rounded-xl border border-white/10 bg-slate-900/60 p-4 ring-1 ring-white/5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-300">Tổng mã</p>
              <p className="mt-1 font-mono text-2xl font-bold text-white">{topStocks.summary.total_analyzed}</p>
            </div>
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/30 p-4 ring-1 ring-emerald-500/15">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-200">Mua</p>
              <p className="mt-1 font-mono text-2xl font-bold text-emerald-300">{topStocks.summary.buy_signals}</p>
            </div>
            <div className="rounded-xl border border-amber-500/20 bg-amber-950/25 p-4 ring-1 ring-amber-500/15">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-200">Giữ</p>
              <p className="mt-1 font-mono text-2xl font-bold text-amber-200">{topStocks.summary.hold_signals}</p>
            </div>
            <div className="rounded-xl border border-rose-500/20 bg-rose-950/30 p-4 ring-1 ring-rose-500/15">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-rose-200">Bán</p>
              <p className="mt-1 font-mono text-2xl font-bold text-rose-300">{topStocks.summary.sell_signals}</p>
            </div>
            <div className="col-span-2 rounded-xl border border-violet-500/25 bg-violet-950/30 p-4 ring-1 ring-violet-500/15 md:col-span-1">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-violet-200">Tự tin cao</p>
              <p className="mt-1 font-mono text-2xl font-bold text-violet-200">{topStocks.summary.high_confidence}</p>
            </div>
          </div>

          {bestHighlight && (
            <div className="relative overflow-hidden rounded-2xl border border-amber-500/35 bg-gradient-to-r from-amber-950/50 via-slate-900 to-slate-950 p-5 ring-1 ring-amber-500/20">
              <div className="pointer-events-none absolute right-0 top-0 h-32 w-32 rounded-full bg-amber-500/10 blur-2xl" />
              {/* Hàng 1: mã + lý do (không còn cột giá bên phải) */}
              <div className="relative flex flex-col gap-5 lg:flex-row lg:items-start lg:gap-6">
                <div className="flex shrink-0 flex-row items-center gap-4">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-orange-600 text-slate-900 shadow-lg shadow-amber-900/40">
                    <Target className="h-7 w-7" />
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-amber-50">
                      Best pick hôm nay
                    </p>
                    <h3 className="mt-1 font-mono text-3xl font-bold tracking-tight text-white">{bestSymbol}</h3>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <span className={`rounded-lg px-2.5 py-1 text-xs font-bold ${getVerdictBadge(bestHighlight.recommendation)}`}>
                        {bestHighlight.recommendation.toUpperCase()}
                      </span>
                      <span className={`text-sm font-bold tabular-nums ${getConfidenceColor(bestHighlight.confidence)}`}>
                        {bestHighlight.confidence}% tin cậy
                      </span>
                      <span className="rounded-md bg-white/10 px-2 py-1 text-xs font-medium text-slate-100 ring-1 ring-white/15">
                        Đồng thuận {bestHighlight.consensus_strength}%
                      </span>
                    </div>
                  </div>
                </div>

                <div className="min-h-0 min-w-0 flex-1 rounded-xl border border-white/10 bg-black/30 px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-300">Tại sao chọn mã này</p>
                  <p className="mt-2 text-base leading-relaxed text-slate-100 lg:line-clamp-6">{whyText}</p>
                </div>
              </div>

              {/* Hàng 2: thời điểm / tín hiệu (vùng “đồ thị” nội dung chính) */}
              {bestStock?.buy_timing?.timing && (
                <div className="relative mt-4 rounded-xl border border-amber-500/30 bg-amber-950/40 px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-100">Thời điểm nên mua</p>
                  <p className="mt-1 text-base font-semibold text-white">
                    {bestStock.buy_timing.timing} · {bestStock.buy_timing.urgency}
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-amber-50">
                    {bestStock.buy_timing.buy_signals?.join(' · ') || 'Dựa trên RSI, MACD và khối lượng.'}
                  </p>
                </div>
              )}

              {/* Hàng 3: giá — entry — xem lại (một hàng ngang ngay dưới khối trên) */}
              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="rounded-xl border border-white/10 bg-slate-950/80 px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-300">Giá hiện tại</p>
                  <p className="mt-1 font-mono text-xl font-semibold tabular-nums text-white">
                    {bestStock?.current_price != null ? bestStock.current_price.toFixed(2) : '—'}
                  </p>
                </div>
                <div className="rounded-xl border border-white/10 bg-slate-950/80 px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-300">Entry gợi ý</p>
                  <p className="mt-1 font-mono text-xl font-semibold tabular-nums text-emerald-300">
                    {bestStock?.recommended_entry != null ? bestStock.recommended_entry.toFixed(2) : '—'}
                  </p>
                </div>
                <div className="rounded-xl border border-amber-500/25 bg-amber-950/40 px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-100">Xem lại sau</p>
                  <p className="mt-1 font-mono text-xl font-semibold tabular-nums text-amber-100">
                    {bestStock?.buy_timing?.next_check_hours ?? 4} giờ
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-1 border-b border-white/10 pb-px">
            {(
              [
                ['all', 'Tất cả', 'violet'],
                ['buy', 'Chỉ mua', 'emerald'],
                ['analysis', 'Chi tiết', 'sky'],
              ] as const
            ).map(([id, label, hue]) => (
              <button
                key={id}
                type="button"
                onClick={() => setSelectedTab(id)}
                className={`rounded-t-lg px-4 py-2.5 text-sm font-medium transition ${
                  selectedTab === id
                    ? hue === 'violet'
                      ? 'border-b-2 border-violet-400 text-violet-300'
                      : hue === 'emerald'
                        ? 'border-b-2 border-emerald-400 text-emerald-300'
                        : 'border-b-2 border-sky-400 text-sky-300'
                    : 'border-b-2 border-transparent text-slate-400 hover:text-slate-100'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="space-y-2.5">
            {(selectedTab === 'buy' ? topStocks.buy_recommendations : topStocks.all_ranked).map((stock) => (
              <div
                key={stock.symbol}
                role="button"
                tabIndex={0}
                className={`cursor-pointer rounded-xl border p-4 transition-all ${getRecommendationColor(stock.recommendation)} ${
                  expandedStock === stock.symbol ? 'ring-2 ring-violet-400/60' : ''
                }`}
                onClick={() => setExpandedStock(expandedStock === stock.symbol ? null : stock.symbol)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setExpandedStock(expandedStock === stock.symbol ? null : stock.symbol);
                  }
                }}
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0 flex-1">
                    <h4 className="font-mono text-lg font-bold text-white">{stock.symbol}</h4>
                    <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-slate-200">
                      {(stock.reasoning ?? '').length > 140 ? `${(stock.reasoning ?? '').slice(0, 140)}…` : stock.reasoning ?? '—'}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-row flex-wrap items-center gap-3 sm:justify-end">
                    <span className={`rounded-lg px-2.5 py-1 text-xs font-bold ${getVerdictBadge(stock.recommendation)}`}>
                      {stock.recommendation.toUpperCase()}
                    </span>
                    <div className="text-right">
                      <p className={`font-mono text-lg font-bold tabular-nums ${getConfidenceColor(stock.confidence)}`}>
                        {stock.confidence}%
                      </p>
                      <p className="text-[11px] font-medium text-slate-300">Đồng thuận {stock.consensus_strength}%</p>
                    </div>
                  </div>
                </div>

                {expandedStock === stock.symbol && (
                  <div className="mt-4 space-y-4 border-t border-white/10 pt-4">
                    <div>
                      <h5 className="mb-2 flex items-center gap-2 text-sm font-semibold text-white">
                        <Users className="h-4 w-4 text-violet-400" />
                        Phiếu bầu agent
                      </h5>
                      <div className="grid grid-cols-3 gap-2">
                        <div className="rounded-lg border border-emerald-500/20 bg-emerald-950/40 p-2 text-center">
                          <p className="text-2xl font-bold text-emerald-300">{stock.agents_buy}</p>
                          <p className="text-[10px] uppercase text-emerald-400/80">Mua</p>
                        </div>
                        <div className="rounded-lg border border-amber-500/20 bg-amber-950/35 p-2 text-center">
                          <p className="text-2xl font-bold text-amber-200">{stock.agents_hold}</p>
                          <p className="text-[10px] uppercase text-amber-300/80">Giữ</p>
                        </div>
                        <div className="rounded-lg border border-rose-500/20 bg-rose-950/40 p-2 text-center">
                          <p className="text-2xl font-bold text-rose-300">{stock.agents_sell}</p>
                          <p className="text-[10px] uppercase text-rose-300/80">Bán</p>
                        </div>
                      </div>
                    </div>

                    {stock.recommendation === 'buy' && (stock.when_to_buy || stock.why_this_stock) && (
                      <div className="rounded-xl border border-emerald-500/25 bg-emerald-950/25 p-3 text-sm text-slate-200">
                        <h5 className="mb-2 font-semibold text-emerald-200">Thời điểm mua & lý do</h5>
                        {stock.when_to_buy?.summary_vi && (
                          <p className="mb-2 text-slate-100">
                            <span className="font-medium text-emerald-300">Khi nào nên mua: </span>
                            {stock.when_to_buy.summary_vi}
                          </p>
                        )}
                        {stock.when_to_buy?.recommended_entry_price != null && (
                          <p className="text-xs leading-relaxed text-slate-200">
                            Entry tham chiếu:{' '}
                            <span className="font-mono font-semibold text-white">{stock.when_to_buy.recommended_entry_price}</span>
                            {stock.when_to_buy.next_check_hours != null && (
                              <> — xem lại sau ~{stock.when_to_buy.next_check_hours} giờ</>
                            )}
                          </p>
                        )}
                        {stock.why_this_stock && (
                          <p className="mt-2 whitespace-pre-line text-slate-100">{stock.why_this_stock}</p>
                        )}
                      </div>
                    )}

                    <div>
                      <h5 className="mb-2 text-sm font-semibold text-white">Phân tích từng agent</h5>
                      <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
                        {stock.agent_details.map((agent) => (
                          <div key={agent.agent} className="rounded-lg border border-white/10 bg-black/25 p-3 text-sm">
                            <div className="mb-1 flex items-center justify-between gap-2">
                              <span className="font-medium text-slate-200">{agent.agent}</span>
                              <span className={`rounded px-2 py-0.5 text-[10px] font-bold ${getVerdictBadge(agent.verdict)}`}>
                                {agent.verdict.toUpperCase()}
                              </span>
                            </div>
                            <p className="text-xs leading-relaxed text-slate-200">{agent.rationale}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          <p className="text-center text-xs font-medium text-slate-300">
            Cập nhật: {new Date(topStocks.timestamp).toLocaleString('vi-VN')}
          </p>
        </>
      )}
    </div>
  );
}
