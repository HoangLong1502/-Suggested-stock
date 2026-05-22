'use client';

import { useQuery } from '@tanstack/react-query';
import { getBestStock } from '../lib/api';
import type { CommitteeReport } from '../types/committee';

/** Một request /agents/best-stock dùng chung (debate + ranking). */
export const COMMITTEE_QUERY_KEY = ['committee-report'] as const;

const STALE_MS = 10 * 60 * 1000;

export function useCommitteeReport() {
  return useQuery<CommitteeReport>({
    queryKey: COMMITTEE_QUERY_KEY,
    queryFn: () => getBestStock() as Promise<CommitteeReport>,
    staleTime: STALE_MS,
    gcTime: STALE_MS * 2,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    retry: 1,
  });
}
