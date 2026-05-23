'use client';

import { useEffect, useRef, useState } from 'react';
import { marketWsUrl } from '../lib/api';
import type { DashboardData } from '../components/dashboard/DashboardHome';

export type MarketWsMessage = {
  type: string;
  timestamp?: string;
  watchlist?: DashboardData['watchlist'];
  indices?: DashboardData['indices'];
  top_gainers?: DashboardData['top_gainers'];
  top_losers?: DashboardData['top_losers'];
  market_session?: DashboardData['market_session'];
};

function mergeDashboard(prev: DashboardData, msg: MarketWsMessage): DashboardData {
  const bySym = new Map<string, Record<string, unknown>>();
  for (const row of msg.watchlist ?? []) {
    if (typeof row === 'object' && row && 'symbol' in row) {
      bySym.set(String(row.symbol).toUpperCase(), row as Record<string, unknown>);
    }
  }

  const watchlist = (prev.watchlist ?? []).map((item) => {
    const sym = typeof item === 'string' ? item : item.symbol;
    const upd = bySym.get(String(sym).toUpperCase());
    if (!upd) {
      return typeof item === 'string' ? { symbol: item, price: 0, change: 0 } : item;
    }
    return typeof item === 'string'
      ? { symbol: item, ...(upd as object) }
      : { ...item, ...(upd as object) };
  });

  return {
    ...prev,
    watchlist,
    indices: msg.indices?.length ? msg.indices : prev.indices,
    top_gainers: msg.top_gainers?.length ? msg.top_gainers : prev.top_gainers,
    top_losers: msg.top_losers?.length ? msg.top_losers : prev.top_losers,
    market_session: msg.market_session ?? prev.market_session,
  };
}

export function useMarketWebSocket(
  data: DashboardData | null,
  setData: React.Dispatch<React.SetStateAction<DashboardData | null>>,
) {
  const [connected, setConnected] = useState(false);
  const dataRef = useRef(data);
  dataRef.current = data;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let closed = false;

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
          const msg = JSON.parse(ev.data as string) as MarketWsMessage;
          if (msg.type !== 'market_update') return;
          const prev = dataRef.current;
          if (!prev) {
            setData({
              indices: msg.indices ?? [],
              watchlist: msg.watchlist ?? [],
              top_gainers: msg.top_gainers ?? [],
              top_losers: msg.top_losers ?? [],
              sector_heatmap: [],
              market_session: msg.market_session,
              chart_preview: [],
            });
            return;
          }
          setData(mergeDashboard(prev, msg));
        } catch {
          /* ignore parse errors */
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (!closed) {
          retryTimer = setTimeout(connect, 4000);
        }
      };

      ws.onerror = () => {
        ws?.close();
      };
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
