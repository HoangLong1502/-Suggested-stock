'use client';

import { create } from 'zustand';

interface MarketState {
  selectedSymbol: string;
  setSelectedSymbol: (symbol: string) => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  selectedSymbol: '',
  setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol.trim().toUpperCase() }),
}));
