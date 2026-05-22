/** Response từ GET /agents/best-stock (hội đồng đầu tư). */
export type CommitteePick = {
  symbol: string;
  recommendation?: string;
  confidence?: number;
  consensus_strength?: number;
  why_vi?: string;
  reasoning?: string;
  scan_case_label_vi?: string;
  buy_timing?: {
    timing: string;
    urgency: string;
    buy_signals?: string[];
    next_check_hours?: number;
  };
  sell_timing?: {
    timing: string;
    urgency: string;
    sell_signals?: string[];
    early_downtrend?: boolean;
  };
  recommended_entry?: number;
  recommended_exit_price?: number;
  current_price?: number;
  stop_loss?: number;
  downtrend_risk?: string;
  exit_strategy?: string;
  early_sell_alert?: {
    urgency: string;
    reason_vi?: string;
    signals?: string[];
  };
};

export type EarlySellAlert = {
  symbol: string;
  urgency: string;
  action?: string;
  reason_vi?: string;
  signals?: string[];
  risk_score?: number;
};

export type CommitteeReport = {
  status?: string;
  message?: string;
  best_stock?: string | null;
  worst_stock?: string | null;
  symbol?: string;
  recommendation?: string;
  confidence?: number;
  consensus_strength?: number;
  reasoning?: string;
  why_this_stock?: string;
  why_vi?: string;
  best_pick?: CommitteePick;
  worst_pick?: CommitteePick;
  early_sell_alerts?: EarlySellAlert[];
  workflow?: {
    title_vi?: string;
    steps_vi?: string[];
    agents?: { id: string; role_vi: string }[];
  };
  buy_timing?: CommitteePick['buy_timing'];
  recommended_entry?: number;
  current_price?: number;
  timestamp?: string;
  pipeline?: Record<string, unknown>;
  scan_passed?: unknown[];
  sell_top_candidates?: unknown[];
  excluded_stocks?: unknown[];
  deep_candidates?: unknown[];
  summary?: Record<string, unknown>;
};

export function resolveDebateSymbol(report: CommitteeReport | null | undefined): string | null {
  if (!report || report.status === 'error') return null;
  const raw = report.best_stock ?? report.best_pick?.symbol ?? report.symbol;
  if (typeof raw === 'string' && raw.trim().length > 0) {
    return raw.trim().toUpperCase();
  }
  return null;
}
