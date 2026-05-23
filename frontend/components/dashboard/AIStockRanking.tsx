'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { AlertCircle, Trophy, Users, Target, TrendingDown, ShieldAlert } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { useCommitteeReport } from '../../hooks/useCommitteeReport';
import type { CommitteePick, CommitteeReport, EarlySellAlert } from '../../types/committee';

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

type BestStockData = CommitteeReport & {
  recommendation?: string;
  confidence?: number;
  consensus_strength?: number;
  reasoning?: string;
};

type ScanRow = {
  symbol: string;
  potential_score?: number;
  case_id?: string;
  case_label_vi?: string;
  filter_reason_vi?: string;
  signals?: string[];
  trend?: string;
  momentum?: string;
  volume_trend?: string;
  action_hint?: string;
  support?: number;
  resistance?: number;
};

type CaseCatalogItem = { id: string; label_vi: string; default_pass: boolean };

type PipelineInfo = {
  watchlist_total?: number;
  scan_passed?: number;
  scan_excluded?: number;
  deep_analyzed?: number;
  deep_symbols?: string[];
};

interface TopStocksData {
  timestamp: string;
  analysis_period_days: number;
  status?: string;
  server_message?: string;
  pipeline?: PipelineInfo;
  scan_passed?: ScanRow[];
  sell_top_candidates?: ScanRow[];
  excluded_stocks?: ScanRow[];
  case_catalog?: CaseCatalogItem[];
  summary: {
    total_analyzed: number;
    watchlist_total?: number;
    scan_passed?: number;
    scan_excluded?: number;
    high_confidence: number;
    buy_signals: number;
    hold_signals: number;
    sell_signals: number;
  };
  best_stock: string | null;
  worst_stock?: string | null;
  workflow?: BestStockData['workflow'];
  best_pick?: CommitteePick;
  worst_pick?: CommitteePick;
  early_sell_alerts?: EarlySellAlert[];
  buy_recommendations: StockRanking[];
  all_ranked: StockRanking[];
}

export default function AIStockRanking() {
  const { data: committeeReport } = useCommitteeReport();
  const bestStock = (committeeReport as BestStockData | undefined) ?? null;
  const [topStocks, setTopStocks] = useState<TopStocksData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedStock, setExpandedStock] = useState<string | null>(null);
  const [selectedTab, setSelectedTab] = useState<'all' | 'buy' | 'scan' | 'analysis'>('all');
  const hasRankingOnce = useRef(false);

  const fetchData = useCallback(async (silent = false) => {
    if (!silent && !hasRankingOnce.current) setLoading(true);
    setError(null);
    await fetchTopStocks();
    hasRankingOnce.current = true;
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData(false);
    const interval = setInterval(() => fetchData(true), 10 * 60 * 1000);
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

  const bestPick = bestStock?.best_pick;
  const worstPick = bestStock?.worst_pick ?? topStocks?.worst_pick;
  const earlyAlerts =
    (bestStock?.early_sell_alerts?.length ? bestStock.early_sell_alerts : topStocks?.early_sell_alerts) ?? [];
  const workflow = bestStock?.workflow ?? topStocks?.workflow;

  const bestHighlight =
    bestPick ||
    bestStock ||
    (topStocks?.all_ranked?.[0] as BestStockData | undefined);

  if (loading && !topStocks) {
    return (
      <div className="flex h-52 items-center justify-center rounded-2xl border border-violet-500/20 bg-slate-950/60">
        <div className="text-center">
          <Trophy className="mx-auto mb-3 h-9 w-9 animate-pulse text-violet-400" />
          <p className="text-sm font-medium text-slate-200">Quét watchlist → lọc tiềm năng → phân tích sâu 5 agent…</p>
        </div>
      </div>
    );
  }

  const bestSymbol =
    bestStock?.best_stock ??
    (bestHighlight && 'best_stock' in bestHighlight && bestHighlight.best_stock
      ? bestHighlight.best_stock
      : bestHighlight?.symbol ?? '');

  const whyText =
    bestPick?.why_vi ??
    bestStock?.why_vi ??
    bestStock?.why_this_stock ??
    bestHighlight?.reasoning ??
    '';

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
              Mô phỏng phòng phân tích: 5 agent + Chủ tịch → best mua giá tốt, worst downtrend, SELL sớm nếu đảo chiều.
            </p>
          </div>
          <button
            type="button"
            onClick={() => fetchData(false)}
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

      {workflow?.steps_vi && workflow.steps_vi.length > 0 && (
        <div className="rounded-xl border border-violet-500/25 bg-violet-950/30 p-4 text-sm text-slate-200">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-violet-200">
            {workflow.title_vi ?? 'Quy trình hội đồng đầu tư'}
          </p>
          <ol className="mt-2 list-decimal space-y-1 pl-5 leading-relaxed">
            {workflow.steps_vi.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
          {workflow.agents && workflow.agents.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {workflow.agents.map((a) => (
                <span
                  key={a.id}
                  className="rounded-md bg-white/5 px-2 py-0.5 text-xs text-slate-300 ring-1 ring-white/10"
                  title={a.role_vi}
                >
                  {a.id}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {topStocks && (
        <>
          {topStocks.pipeline && (
            <div className="rounded-xl border border-cyan-500/25 bg-cyan-950/25 p-4 text-sm text-slate-200">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-cyan-200">Pipeline 2 bước</p>
              <p className="mt-2 leading-relaxed">
                Watchlist <span className="font-mono font-bold text-white">{topStocks.pipeline.watchlist_total ?? '—'}</span>
                {' → '}
                qua lọc <span className="font-mono font-bold text-emerald-300">{topStocks.pipeline.scan_passed ?? '—'}</span>
                {' → '}
                loại <span className="font-mono font-bold text-rose-300">{topStocks.pipeline.scan_excluded ?? '—'}</span>
                {' → '}
                phân tích sâu <span className="font-mono font-bold text-violet-300">{topStocks.pipeline.deep_analyzed ?? '—'}</span>
                {topStocks.pipeline.deep_symbols?.length ? (
                  <span className="mt-2 block font-mono text-xs text-slate-400">
                    {topStocks.pipeline.deep_symbols.join(', ')}
                  </span>
                ) : null}
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            <div className="rounded-xl border border-white/10 bg-slate-900/60 p-4 ring-1 ring-white/5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-300">Watchlist</p>
              <p className="mt-1 font-mono text-2xl font-bold text-white">
                {topStocks.summary.watchlist_total ?? topStocks.pipeline?.watchlist_total ?? '—'}
              </p>
            </div>
            <div className="rounded-xl border border-cyan-500/20 bg-cyan-950/30 p-4 ring-1 ring-cyan-500/15">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-cyan-200">Phân tích sâu</p>
              <p className="mt-1 font-mono text-2xl font-bold text-cyan-200">{topStocks.summary.total_analyzed}</p>
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
                      <span
                        className={`rounded-lg px-2.5 py-1 text-xs font-bold ${getVerdictBadge(bestHighlight.recommendation ?? 'hold')}`}
                      >
                        {(bestHighlight.recommendation ?? 'hold').toUpperCase()}
                      </span>
                      <span
                        className={`text-sm font-bold tabular-nums ${getConfidenceColor(bestHighlight.confidence ?? 0)}`}
                      >
                        {bestHighlight.confidence ?? 0}% tin cậy
                      </span>
                      <span className="rounded-md bg-white/10 px-2 py-1 text-xs font-medium text-slate-100 ring-1 ring-white/15">
                        Đồng thuận {bestHighlight.consensus_strength ?? 0}%
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
              {(bestPick?.buy_timing?.timing || bestStock?.buy_timing?.timing) && (
                <div className="relative mt-4 rounded-xl border border-amber-500/30 bg-amber-950/40 px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-100">Thời điểm nên mua</p>
                  <p className="mt-1 text-base font-semibold text-white">
                    {(bestPick?.buy_timing ?? bestStock?.buy_timing)?.timing} ·{' '}
                    {(bestPick?.buy_timing ?? bestStock?.buy_timing)?.urgency}
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-amber-50">
                    {(bestPick?.buy_timing ?? bestStock?.buy_timing)?.buy_signals?.join(' · ') ||
                      'Dựa trên RSI, MACD và khối lượng.'}
                  </p>
                </div>
              )}

              {/* Hàng 3: giá — entry — xem lại (một hàng ngang ngay dưới khối trên) */}
              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="rounded-xl border border-white/10 bg-slate-950/80 px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-300">Giá hiện tại</p>
                  <p className="mt-1 font-mono text-xl font-semibold tabular-nums text-white">
                    {(bestPick?.current_price ?? bestStock?.current_price) != null
                      ? Number(bestPick?.current_price ?? bestStock?.current_price).toFixed(2)
                      : '—'}
                  </p>
                </div>
                <div className="rounded-xl border border-white/10 bg-slate-950/80 px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-300">Entry gợi ý</p>
                  <p className="mt-1 font-mono text-xl font-semibold tabular-nums text-emerald-300">
                    {(bestPick?.recommended_entry ?? bestStock?.recommended_entry) != null
                      ? Number(bestPick?.recommended_entry ?? bestStock?.recommended_entry).toFixed(2)
                      : '—'}
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

          {worstPick?.symbol && (
            <div className="relative overflow-hidden rounded-2xl border border-rose-500/35 bg-gradient-to-r from-rose-950/50 via-slate-900 to-slate-950 p-5 ring-1 ring-rose-500/20">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
                <div className="flex shrink-0 items-center gap-4">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-rose-500 to-red-800 text-white shadow-lg shadow-rose-900/40">
                    <TrendingDown className="h-7 w-7" />
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-rose-100">
                      Worst — tránh / thoát
                    </p>
                    <h3 className="mt-1 font-mono text-3xl font-bold text-white">{worstPick.symbol}</h3>
                    <p className="mt-1 text-xs text-rose-200">
                      Rủi ro downtrend: {worstPick.downtrend_risk ?? '—'}
                      {worstPick.scan_case_label_vi ? ` · ${worstPick.scan_case_label_vi}` : ''}
                    </p>
                  </div>
                </div>
                <div className="min-w-0 flex-1 rounded-xl border border-white/10 bg-black/30 px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-300">Lý do hội đồng</p>
                  <p className="mt-2 text-sm leading-relaxed text-slate-100 line-clamp-5">{worstPick.why_vi ?? '—'}</p>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="rounded-xl border border-white/10 bg-slate-950/80 px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-300">Giá hiện tại</p>
                  <p className="mt-1 font-mono text-xl font-semibold text-white tabular-nums">
                    {worstPick.current_price != null ? worstPick.current_price.toFixed(2) : '—'}
                  </p>
                </div>
                <div className="rounded-xl border border-rose-500/25 bg-rose-950/40 px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-rose-100">Giá nên bán (tham chiếu)</p>
                  <p className="mt-1 font-mono text-xl font-semibold text-rose-200 tabular-nums">
                    {worstPick.recommended_exit_price != null
                      ? Number(worstPick.recommended_exit_price).toFixed(2)
                      : '—'}
                  </p>
                </div>
                <div className="rounded-xl border border-white/10 bg-slate-950/80 px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-300">Stop-loss</p>
                  <p className="mt-1 font-mono text-xl font-semibold text-amber-200 tabular-nums">
                    {worstPick.stop_loss != null ? Number(worstPick.stop_loss).toFixed(2) : '—'}
                  </p>
                </div>
              </div>
              {worstPick.sell_timing?.timing && (
                <div className="mt-3 rounded-xl border border-rose-500/30 bg-rose-950/40 px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-rose-100">Thời điểm bán</p>
                  <p className="mt-1 font-semibold text-white">
                    {worstPick.sell_timing.timing} · {worstPick.sell_timing.urgency}
                  </p>
                  {worstPick.early_sell_alert?.urgency && (
                    <p className="mt-2 text-sm font-medium text-rose-200">
                      SELL sớm: {worstPick.early_sell_alert.urgency} — {worstPick.early_sell_alert.reason_vi}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {earlyAlerts.length > 0 && (
            <div className="rounded-2xl border border-orange-500/30 bg-orange-950/25 p-4 ring-1 ring-orange-500/15">
              <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-orange-200">
                <ShieldAlert className="h-4 w-4" />
                Cảnh báo SELL sớm (downtrend trước khi lỡ giá thoát)
              </p>
              <div className="mt-3 space-y-2">
                {earlyAlerts.slice(0, 8).map((a) => (
                  <div
                    key={a.symbol}
                    className="flex flex-wrap items-start justify-between gap-2 rounded-xl border border-orange-500/20 bg-black/25 px-3 py-2.5"
                  >
                    <div>
                      <span className="font-mono text-lg font-bold text-white">{a.symbol}</span>
                      <span className="ml-2 rounded-md bg-rose-500/20 px-2 py-0.5 text-xs font-bold text-rose-200 ring-1 ring-rose-500/30">
                        {a.urgency}
                      </span>
                      <p className="mt-1 text-xs text-slate-300">{a.reason_vi}</p>
                      {a.signals?.length ? (
                        <p className="mt-0.5 text-[11px] text-orange-200/90">{a.signals.join(' · ')}</p>
                      ) : null}
                    </div>
                    {a.risk_score != null && (
                      <span className="text-xs font-mono text-orange-300">risk {a.risk_score}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-1 border-b border-white/10 pb-px">
            {(
              [
                ['all', 'Sau lọc (AI)', 'violet'],
                ['buy', 'Chỉ mua', 'emerald'],
                ['scan', 'Lọc sơ bộ', 'cyan'],
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
                        : hue === 'cyan'
                          ? 'border-b-2 border-cyan-400 text-cyan-300'
                          : 'border-b-2 border-sky-400 text-sky-300'
                    : 'border-b-2 border-transparent text-slate-400 hover:text-slate-100'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="space-y-2.5">
            {selectedTab === 'scan' && (
              <>
                {topStocks.case_catalog && topStocks.case_catalog.length > 0 && (
                  <div className="rounded-xl border border-white/10 bg-slate-900/50 p-3 text-xs text-slate-300">
                    <p className="mb-2 font-semibold uppercase tracking-wider text-slate-200">Các kịch bản hệ thống nhận diện</p>
                    <div className="flex flex-wrap gap-1.5">
                      {topStocks.case_catalog.map((c) => (
                        <span
                          key={c.id}
                          className={`rounded-md px-2 py-0.5 ring-1 ${
                            c.default_pass
                              ? 'bg-emerald-950/50 text-emerald-200 ring-emerald-500/25'
                              : 'bg-rose-950/40 text-rose-200 ring-rose-500/20'
                          }`}
                          title={c.id}
                        >
                          {c.label_vi}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                <p className="text-xs font-semibold uppercase tracking-wider text-emerald-300">Đủ tiềm năng — phân tích sâu (top)</p>
                {(topStocks.scan_passed ?? []).slice(0, 15).map((row) => (
                  <div
                    key={`pass-${row.symbol}`}
                    className="rounded-xl border border-emerald-500/20 bg-emerald-950/20 px-4 py-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-mono text-lg font-bold text-white">{row.symbol}</span>
                      <span className="text-sm font-bold text-emerald-300">{row.potential_score ?? '—'} điểm</span>
                    </div>
                    {row.case_label_vi && (
                      <p className="mt-1 text-xs font-medium text-cyan-200">{row.case_label_vi}</p>
                    )}
                    <p className="mt-1 text-xs text-slate-400">{row.signals?.join(' · ')}</p>
                  </div>
                ))}
                <p className="pt-2 text-xs font-semibold uppercase tracking-wider text-amber-300">Bán đỉnh / chốt lời (gần kháng cự)</p>
                {(topStocks.sell_top_candidates ?? []).slice(0, 12).map((row) => (
                  <div
                    key={`sell-${row.symbol}`}
                    className="rounded-xl border border-amber-500/25 bg-amber-950/25 px-4 py-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-mono text-lg font-bold text-amber-100">{row.symbol}</span>
                      <span className="text-xs font-semibold uppercase text-amber-200">Gợi ý BÁN / chốt</span>
                    </div>
                    {row.case_label_vi && <p className="mt-1 text-xs text-amber-100/90">{row.case_label_vi}</p>}
                    <p className="mt-1 text-[11px] text-slate-400">
                      Hỗ trợ {row.support ?? '—'} · Kháng cự {row.resistance ?? '—'}
                    </p>
                  </div>
                ))}
                <p className="pt-2 text-xs font-semibold uppercase tracking-wider text-rose-300">Đã loại — tránh mua (mẫu)</p>
                {(topStocks.excluded_stocks ?? []).slice(0, 12).map((row) => (
                  <div
                    key={`ex-${row.symbol}`}
                    className="rounded-xl border border-rose-500/15 bg-rose-950/15 px-4 py-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-mono font-semibold text-slate-300">{row.symbol}</span>
                      <span className="text-xs text-rose-200">{row.case_label_vi ?? row.filter_reason_vi}</span>
                    </div>
                    <p className="mt-1 text-[11px] text-slate-500">{row.potential_score ?? 0} điểm · {row.trend}</p>
                  </div>
                ))}
              </>
            )}
            {selectedTab !== 'scan' &&
              (selectedTab === 'buy' ? topStocks.buy_recommendations : topStocks.all_ranked).map((stock) => (
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
