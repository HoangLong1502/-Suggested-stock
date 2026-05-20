export const apiUrl = (() => {
  if (typeof window === 'undefined') {
    return process.env.INTERNAL_API_URL ?? 'http://backend:8000/api/v1';
  }
  return process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';
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

export const WATCHLIST_FALLBACK_SYMBOLS = [
  'SSI', 'VNM', 'VCB', 'FPT', 'MWG', 'VHM', 'PNJ', 'HPG', 'TPB', 'ACB', 'BVH', 'MSN', 'NVL', 'GAS', 'PXL',
] as const;

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
