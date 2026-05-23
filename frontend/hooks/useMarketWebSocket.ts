'use client';

import { useEffect, useRef, useState } from 'react';
import { marketWsUrl } from '../lib/api';
import type { DashboardData, WatchlistRow } from '../components/dashboard/DashboardHome';

export type MarketWsMessage = {
  type: string;
  timestamp?: string;
  watchlist?: DashboardData['watchlist'];
  indices?: DashboardData['indices'];
  top_gainers?: DashboardData['top_gainers'];
  top_losers?: DashboardData['top_losers'];
  market_session?: DashboardData['market_session'];
};

function patchWatchlist(
  prev: DashboardData['watchlist'],
  incoming: DashboardData['watchlist'] | undefined,
): DashboardData['watchlist'] {
  if (!incoming?.length) return prev;
  const bySym = new Map<string, WatchlistRow>();
  for (const row of incoming) {
    if (typeof row === 'object' && row && 'symbol' in row) {
      bySym.set(String(row.symbol).toUpperCase(), row as WatchlistRow);
    }
  }
  return (prev ?? []).map((item) => {
    const sym = typeof item === 'string' ? item : item.symbol;
    const upd = bySym.get(String(sym).toUpperCase());
    if (!upd) {
      return typeof item === 'string' ? { symbol: item, price: 0, change: 0 } : item;
    }
    return typeof item === 'string' ? { symbol: item, ...upd } : { ...item, ...upd };
  });
}

/** Chỉ cập nhật giá — không đổi top gainers/losers mỗi 8s (tránh list nhảy). */
function mergeLiveQuotes(prev: DashboardData, msg: MarketWsMessage): DashboardData {
  return {
    ...prev,
    watchlist: patchWatchlist(prev.watchlist, msg.watchlist),
    indices: msg.indices?.length ? msg.indices : prev.indices,
    market_session: msg.market_session ?? prev.market_session,
  };
}

function snapshotKey(d: DashboardData): string {
  const wl = (d.watchlist ?? [])
    .map((it) => {
      if (typeof it === 'string') return `${it}:0:0`;
      return `${it.symbol}:${it.price}:${it.change_pct ?? it.change}`;
    })
    .join('|');
  const idx = (d.indices ?? []).map((i) => `${i.symbol}:${i.price}:${i.change}`).join('|');
  return `${wl}#${idx}`;
}

export function useMarketWebSocket(
  data: DashboardData | null,
  setData: React.Dispatch<React.SetStateAction<DashboardData | null>>,
) {
  const [connected, setConnected] = useState(false);
  const dataRef = useRef(data);
  dataRef.current = data;
  const lastKeyRef = useRef('');

  useEffect(() => {
    let ws: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let closed = false;

    const applyMessage = (msg: MarketWsMessage) => {
      if (msg.type !== 'market_update') return;
      const prev = dataRef.current;
      if (!prev) {
        const initial: DashboardData = {
          indices: msg.indices ?? [],
          watchlist: msg.watchlist ?? [],
          top_gainers: msg.top_gainers ?? [],
          top_losers: msg.top_losers ?? [],
          sector_heatmap: [],
          market_session: msg.market_session,
          chart_preview: [],
        };
        lastKeyRef.current = snapshotKey(initial);
        setData(initial);
        return;
      }
      const next = mergeLiveQuotes(prev, msg);
      const key = snapshotKey(next);
      if (key === lastKeyRef.current) return;
      lastKeyRef.current = key;
      setData(next);
    };

    const connect = () => {
      if (closed) return;
      try {
        ws = new WebSocket(marketWsUrl());
      } catch {
        retryTimer = setTimeout(connect, 5000);
        return;
      }

      ws.onopen = () => {
        setConnected(true);
        ws?.send('ping');
      };

      ws.onmessage = (ev) => {
        try {
          applyMessage(JSON.parse(ev.data as string) as MarketWsMessage);
        } catch {
          /* ignore */
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (!closed) retryTimer = setTimeout(connect, 4000);
      };

      ws.onerror = () => ws?.close();
    };

    connect();

    return () => {
      closed = true;
      if (retryTimer) clearTimeout(retryTimer);
      ws?.close();
      setConnected(false);
    };
  }, [setData]);

  return { wsConnected: connected };
}
