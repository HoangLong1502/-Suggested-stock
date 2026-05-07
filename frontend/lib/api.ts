const apiUrl = (() => {
  if (typeof window === 'undefined') {
    return process.env.INTERNAL_API_URL ?? 'http://backend:8000/api/v1';
  }
  return process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:5555/api/v1';
})();

export async function getDashboardData() {
  try {
    const res = await fetch(`${apiUrl}/market/overview`, { cache: 'no-store' });
    if (!res.ok) {
      return {
        indices: [],
        watchlist: [],
        top_gainers: [],
        top_losers: [],
        sector_heatmap: [],
      };
    }
    return res.json();
  } catch {
    return {
      indices: [],
      watchlist: [],
      top_gainers: [],
      top_losers: [],
      sector_heatmap: [],
    };
  }
}

export async function getAgentDebate(symbol: string) {
  try {
    const res = await fetch(`${apiUrl}/agents/debate/${symbol}`);
    if (!res.ok) {
      return { symbol, debate: [], decision: null };
    }
    return res.json();
  } catch {
    return { symbol, debate: [], decision: null };
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
