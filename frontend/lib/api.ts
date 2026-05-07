const apiUrl = (() => {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL ?? 'http://backend:8000/api/v1';
  }
  return process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:5555/api/v1';
})();

export async function getDashboardData() {
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
}

export async function getAgentDebate(symbol: string) {
  const res = await fetch(`${apiUrl}/agents/debate/${symbol}`);
  if (!res.ok) {
    return { symbol, debate: [] };
  }
  return res.json();
}
