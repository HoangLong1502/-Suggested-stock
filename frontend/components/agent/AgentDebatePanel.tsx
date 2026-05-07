'use client';

import { useQuery } from '@tanstack/react-query';
import { getAgentDebate } from '../../lib/api';

interface DebateItem {
  agent: string;
  message: string;
  confidence: number;
}

interface DecisionResult {
  agent: string;
  stock_symbol: string;
  verdict: string;
  score: number;
  rationale: string;
  extra: Record<string, unknown>;
}

interface DebateResponse {
  symbol: string;
  debate: DebateItem[];
  decision: DecisionResult;
}

export default function AgentDebatePanel({ symbol }: { readonly symbol: string }) {
  const { data, isLoading } = useQuery<DebateResponse>({
    queryKey: ['agentDebate', symbol],
    queryFn: () => getAgentDebate(symbol),
  });
  const debate: DebateItem[] = data?.debate ?? [];
  const decision = data?.decision;

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
                {decision ? `${decision.verdict.toUpperCase()} · ${Math.round(decision.score * 100)}%` : 'Chưa có kết luận'}
              </div>
            </div>
          </div>

          {debate.map((item) => (
            <div key={item.agent} className="rounded-3xl border border-slate-800 bg-slate-950/80 p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm uppercase tracking-[0.24em] text-slate-500">{item.agent}</p>
                  <p className="mt-2 text-lg font-semibold">{item.message}</p>
                </div>
                <span className="rounded-full bg-slate-800 px-3 py-1 text-xs uppercase tracking-[0.18em] text-slate-300">
                  {Math.round(item.confidence * 100)}%
                </span>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
