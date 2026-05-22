'use client';

import { useQuery } from '@tanstack/react-query';
import { getAgentDebate } from '../../lib/api';

interface DebateItem {
  agent: string;
  verdict: string;
  rationale: string;
  confidence: number;
}

interface ConsensusResult {
  verdict: string;
  confidence: number;
  consensus_strength: number;
  overall_reasoning?: string;
  reasoning?: string;
  agent_votes: {
    buy: number;
    hold: number;
    sell: number;
  };
}

interface BuyTiming {
  timing: string;
  urgency: string;
  buy_signals?: string[];
  wait_reasons?: string[];
  next_check_hours?: number;
}

interface DebateResponse {
  symbol: string;
  debate: DebateItem[];
  consensus: ConsensusResult | null;
  buy_timing?: BuyTiming;
  recommended_entry?: number;
  current_price?: number;
}

function formatAgentConfidencePct(value: number): string {
  if (value == null || Number.isNaN(value)) {
    return '—';
  }
  // API sends 0–100; older bugs might send 0–1
  const pct = value <= 1 && value >= 0 ? value * 100 : Math.min(100, value);
  return `${Math.round(pct)}%`;
}

export default function AgentDebatePanel({
  symbol,
  enabled = true,
}: {
  readonly symbol: string;
  readonly enabled?: boolean;
}) {
  const { data, isLoading } = useQuery<DebateResponse>({
    queryKey: ['agentDebate', symbol],
    queryFn: () => getAgentDebate(symbol),
    enabled: enabled && symbol.length > 0,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
  const debate: DebateItem[] = data?.debate ?? [];
  const consensus = data?.consensus;
  const buyTiming = data?.buy_timing;

  return (
    <div className="space-y-4">
      {isLoading ? (
        <p className="text-slate-400">Loading debate...</p>
      ) : (
        <>
          <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Mã cổ phiếu đề xuất</p>
                <p className="mt-1 text-2xl font-semibold">{data?.symbol ?? symbol}</p>
              </div>
              <div className="rounded-3xl bg-slate-800 px-4 py-2 text-xs uppercase tracking-[0.18em] text-slate-300">
                {consensus ? `${consensus.verdict.toUpperCase()} · ${formatAgentConfidencePct(consensus.confidence)}` : 'Chưa có kết luận'}
              </div>
            </div>
            {consensus && (
              <div className="mt-4 text-sm text-slate-300">
                <p className="font-semibold text-slate-200">Lý do mua của AI</p>
                <p className="mt-2 text-slate-300">
                  {consensus.overall_reasoning ||
                    consensus.reasoning ||
                    'Chưa có tóm tắt đồng thuận — kiểm tra backend / dữ liệu lịch sử giá.'}
                </p>
                {buyTiming?.timing && (
                  <p className="mt-3 text-sm text-amber-200">
                    Thời điểm nên mua: <span className="font-semibold">{buyTiming.timing}</span> · {buyTiming.urgency}
                  </p>
                )}
              </div>
            )}
          </div>

          {debate.map((item) => (
            <div key={item.agent} className="rounded-3xl border border-slate-800 bg-slate-950/80 p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm uppercase tracking-[0.24em] text-slate-500">{item.agent}</p>
                  <p className="mt-2 text-lg font-semibold">{item.verdict}</p>
                  <p className="mt-1 text-sm text-slate-300">{item.rationale}</p>
                </div>
                <span className="rounded-full bg-slate-800 px-3 py-1 text-xs uppercase tracking-[0.18em] text-slate-300">
                  {formatAgentConfidencePct(item.confidence)}
                </span>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
