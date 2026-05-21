export const apiUrl = (() => {
  if (typeof window === 'undefined') {
    return process.env.INTERNAL_API_URL ?? 'http://backend:8000/api/v1';
  }
  return process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:5555/api/v1';
})();

const SSR_FETCH_MS = 70_000;

async function fetchWithTimeout(url: string, ms: number): Promise<Response> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), ms);
  try {
    return await fetch(url, { cache: 'no-store', signal: ctrl.signal });
  } finally {
    clearTimeout(t);
  }
}

export { WATCHLIST_FALLBACK_SYMBOLS } from './watchlist-symbols';

export async function getDashboardData() {
  try {
    const res = await fetchWithTimeout(`${apiUrl}/market/overview`, SSR_FETCH_MS);
    if (!res.ok) {
      return {
        indices: [],
        watchlist: WATCHLIST_FALLBACK_SYMBOLS.map((symbol) => ({ symbol, price: 0, change: 0 })),
        top_gainers: [],
        top_losers: [],
        sector_heatmap: [],
        chart_preview: [],
      };
    }
    const data = await res.json();
    if (!Array.isArray(data.watchlist) || data.watchlist.length === 0) {
      return {
        ...data,
        watchlist: WATCHLIST_FALLBACK_SYMBOLS.map((symbol) => ({ symbol, price: 0, change: 0 })),
      };
    }
    return data;
  } catch {
    return {
      indices: [],
      watchlist: WATCHLIST_FALLBACK_SYMBOLS.map((symbol) => ({ symbol, price: 0, change: 0 })),
      top_gainers: [],
      top_losers: [],
      sector_heatmap: [],
      chart_preview: [],
    };
  }
}

const AGENT_LONG_FETCH_MS = 900_000;

export async function getBestStock() {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), AGENT_LONG_FETCH_MS);
  try {
    const res = await fetch(`${apiUrl}/agents/best-stock`, {
      cache: 'no-store',
      signal: ctrl.signal,
    });
    if (!res.ok) return { best_stock: null };
    return res.json();
  } catch {
    return { best_stock: null };
  } finally {
    clearTimeout(t);
  }
}

export async function getAgentDebate(symbol: string) {
  try {
    const res = await fetch(`${apiUrl}/agents/debate/${symbol}`, { cache: 'no-store' });
    if (!res.ok) {
      return { symbol, debate: [], consensus: null };
    }
    return res.json();
  } catch {
    return { symbol, debate: [], consensus: null };
  }
}

export type SectorStockRow = {
  symbol: string;
  change_pct: number;
  price: number;
  trading_date?: string;
  finfo_industry?: string;
};

export type SectorRow = {
  id: string;
  name_vi: string;
  name_en: string;
  change_pct_avg: number;
  stocks_with_data: number;
  stocks_total: number;
  gainers: number;
  losers: number;
  flat: number;
  momentum: string;
  momentum_vi: string;
  leader_symbol: string | null;
  leader_change_pct: number | null;
  stocks: SectorStockRow[];
};

export type SectorAnalysisData = {
  as_of: string;
  market_avg_change_pct: number;
  sectors: SectorRow[];
  data_source: string;
  top_sectors: string[];
  bottom_sectors: string[];
};

export async function getSectorAnalysis(): Promise<SectorAnalysisData> {
  const res = await fetchWithTimeout(`${apiUrl}/market/sectors?fast=true`, 60_000);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<SectorAnalysisData>;
}

export async function getSuggestedStock() {
  try {
    const res = await fetch(`${apiUrl}/agents/suggest`, { cache: 'no-store' });
    if (!res.ok) {
      return { suggested: null };
    }
    return res.json();
  } catch {
    return { suggested: null };
  }
}
