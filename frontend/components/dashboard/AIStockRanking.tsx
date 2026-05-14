'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { AlertCircle, Trophy, Users, Target } from 'lucide-react';
import { apiUrl, getBestStock } from '../../lib/api';

interface StockRanking {
  symbol: string;
  recommendation: string;
  confidence: number;
  consensus_strength: number;
  reasoning: string;
  agents_buy: number;
  agents_sell: number;
  agents_hold: number;
  agent_details: Array<{
    agent: string;
    verdict: string;
    confidence: number;
    rationale: string;
  }>;
}

interface BestStockData {
  best_stock: string;
  recommendation: string;
  confidence: number;
  consensus_strength: number;
  reasoning: string;
  buy_timing: {
    timing: string;
    urgency: string;
    buy_signals?: string[];
    wait_reasons?: string[];
    next_check_hours?: number;
  };
  recommended_entry?: number;
  current_price?: number;
  timestamp?: string;
}

interface TopStocksData {
  timestamp: string;
  analysis_period_days: number;
  summary: {
    total_analyzed: number;
    high_confidence: number;
    buy_signals: number;
    hold_signals: number;
    sell_signals: number;
  };
  best_stock: string;
  buy_recommendations: StockRanking[];
  all_ranked: StockRanking[];
}

export default function AIStockRanking() {
  const [topStocks, setTopStocks] = useState<TopStocksData | null>(null);
  const [bestStock, setBestStock] = useState<BestStockData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedStock, setExpandedStock] = useState<string | null>(null);
  const [selectedTab, setSelectedTab] = useState<'all' | 'buy' | 'analysis'>('all');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    await Promise.allSettled([fetchTopStocks(), fetchBestStock()]);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5 * 60 * 1000); // Refresh every 5 minutes
    return () => clearInterval(interval);
  }, [fetchData]);

  const fetchTopStocks = async () => {
    try {
      const response = await fetch(`${apiUrl}/agents/top-stocks?limit=10&min_confidence=0.65`, {
        cache: 'no-store',
      });
      if (!response.ok) throw new Error('Failed to fetch top stocks');
      const data = await response.json();
      setTopStocks(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    }
  };

  const fetchBestStock = async () => {
    try {
      const data = await getBestStock();
      if (data && data.best_stock) {
        setBestStock(data as BestStockData);
      }
    } catch {
      // ignore best stock failures
    }
  };

  const getRecommendationColor = (recommendation: string) => {
    switch (recommendation.toLowerCase()) {
      case 'buy':
        return 'bg-green-50 border-green-200';
      case 'sell':
        return 'bg-red-50 border-red-200';
      case 'hold':
        return 'bg-yellow-50 border-yellow-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const getVerdictBadge = (verdict: string) => {
    switch (verdict.toLowerCase()) {
      case 'buy':
        return 'bg-green-100 text-green-800';
      case 'sell':
        return 'bg-red-100 text-red-800';
      case 'hold':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'text-green-600';
    if (confidence >= 65) return 'text-blue-600';
    if (confidence >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  const bestHighlight = bestStock || (topStocks?.all_ranked?.[0] as BestStockData | undefined);

  if (loading && !topStocks) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-center">
          <div className="animate-spin mb-4">
            <Trophy className="w-8 h-8 text-blue-500" />
          </div>
          <p className="text-gray-600">Analyzing stocks with AI agents...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 text-white p-6 rounded-lg">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <Trophy className="w-6 h-6" />
              AI Agent Stock Ranking
            </h2>
            <p className="text-blue-100 mt-2">
              Based on 60 days (2 months) of comprehensive analysis from 5 AI agents
            </p>
          </div>
          <button
            onClick={fetchData}
            className="bg-blue-700 hover:bg-blue-800 px-4 py-2 rounded text-sm"
          >
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 p-4 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {topStocks && (
        <>
          {/* Summary Stats */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <p className="text-xs text-gray-600 uppercase">Total Analyzed</p>
              <p className="text-2xl font-bold text-gray-900">
                {topStocks.summary.total_analyzed}
              </p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg border border-green-200">
              <p className="text-xs text-green-600 uppercase">Buy Signals</p>
              <p className="text-2xl font-bold text-green-700">
                {topStocks.summary.buy_signals}
              </p>
            </div>
            <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
              <p className="text-xs text-yellow-600 uppercase">Hold Signals</p>
              <p className="text-2xl font-bold text-yellow-700">
                {topStocks.summary.hold_signals}
              </p>
            </div>
            <div className="bg-red-50 p-4 rounded-lg border border-red-200">
              <p className="text-xs text-red-600 uppercase">Sell Signals</p>
              <p className="text-2xl font-bold text-red-700">
                {topStocks.summary.sell_signals}
              </p>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
              <p className="text-xs text-purple-600 uppercase">High Confidence</p>
              <p className="text-2xl font-bold text-purple-700">
                {topStocks.summary.high_confidence}
              </p>
            </div>
          </div>

          {/* Best Stock Highlight */}
          {bestHighlight && (
            <div className="bg-gradient-to-r from-yellow-50 to-orange-50 border-2 border-yellow-300 p-6 rounded-lg">
              <div className="flex flex-col gap-4 md:flex-row md:items-start">
                <div className="bg-yellow-400 text-white rounded-full p-3">
                  <Target className="w-6 h-6" />
                </div>
                <div className="flex-1">
                  <p className="text-sm text-gray-600">🏆 Best AI stock pick hôm nay</p>
                  <h3 className="text-3xl font-bold text-gray-900">
                    {bestHighlight.best_stock}
                  </h3>
                  <div className="mt-3 flex flex-wrap items-center gap-3">
                    <span className={`badge ${getVerdictBadge(bestHighlight.recommendation)}`}>
                      {bestHighlight.recommendation.toUpperCase()}
                    </span>
                    <span className={`text-lg font-bold ${getConfidenceColor(bestHighlight.confidence)}`}>
                      {bestHighlight.confidence}% Confidence
                    </span>
                    <span className="text-gray-600">
                      Consensus: {bestHighlight.consensus_strength}%
                    </span>
                  </div>
                  <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                    <p className="font-semibold text-slate-900">Tại sao AI chọn mã này</p>
                    <p className="mt-2">{bestHighlight.reasoning}</p>
                  </div>

                  {bestStock?.buy_timing?.timing && (
                    <div className="mt-4 rounded-3xl border border-yellow-300 bg-yellow-100 p-4">
                      <p className="text-sm text-yellow-800 uppercase tracking-[0.24em]">Thời điểm nên mua</p>
                      <p className="mt-2 text-xl font-semibold text-yellow-900">
                        {bestStock.buy_timing.timing} · {bestStock.buy_timing.urgency}
                      </p>
                      <p className="mt-2 text-sm text-gray-700">
                        {bestStock.buy_timing.buy_signals?.join(', ') || 'Dựa trên tín hiệu RSI, MACD và khối lượng.'}
                      </p>
                    </div>
                  )}

                  {(bestStock?.recommended_entry || bestStock?.current_price) && (
                    <div className="mt-4 grid gap-2 sm:grid-cols-3">
                      <div className="rounded-3xl bg-white p-4 text-sm text-slate-700 border border-slate-200">
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Giá hiện tại</p>
                        <p className="mt-1 text-xl font-semibold text-slate-900">
                          {bestStock?.current_price?.toFixed(2) ?? 'N/A'}
                        </p>
                      </div>
                      <div className="rounded-3xl bg-white p-4 text-sm text-slate-700 border border-slate-200">
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Entry đề xuất</p>
                        <p className="mt-1 text-xl font-semibold text-slate-900">
                          {bestStock?.recommended_entry?.toFixed(2) ?? 'N/A'}
                        </p>
                      </div>
                      <div className="rounded-3xl bg-white p-4 text-sm text-slate-700 border border-slate-200">
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Kiểm tra lại sau</p>
                        <p className="mt-1 text-xl font-semibold text-slate-900">
                          {bestStock?.buy_timing?.next_check_hours ?? 4} giờ
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Tabs */}
          <div className="flex gap-2 border-b border-gray-200">
            <button
              onClick={() => setSelectedTab('all')}
              className={`px-4 py-2 font-medium border-b-2 ${
                selectedTab === 'all'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              All Stocks
            </button>
            <button
              onClick={() => setSelectedTab('buy')}
              className={`px-4 py-2 font-medium border-b-2 ${
                selectedTab === 'buy'
                  ? 'border-green-600 text-green-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Buy Only
            </button>
            <button
              onClick={() => setSelectedTab('analysis')}
              className={`px-4 py-2 font-medium border-b-2 ${
                selectedTab === 'analysis'
                  ? 'border-purple-600 text-purple-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Analysis Details
            </button>
          </div>

          {/* Stocks List */}
          <div className="space-y-3">
            {(selectedTab === 'buy' ? topStocks.buy_recommendations : topStocks.all_ranked).map((stock) => (
              <div
                key={stock.symbol}
                className={`border rounded-lg p-4 cursor-pointer transition-all ${
                  getRecommendationColor(stock.recommendation)
                } ${expandedStock === stock.symbol ? 'ring-2 ring-blue-400' : ''}`}
                onClick={() =>
                  setExpandedStock(expandedStock === stock.symbol ? null : stock.symbol)
                }
              >
                {/* Collapsed View */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 flex-1">
                    <div>
                      <h4 className="text-lg font-bold text-gray-900">{stock.symbol}</h4>
                      <p className="text-sm text-gray-600">{stock.reasoning.substring(0, 100)}...</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className={`badge ${getVerdictBadge(stock.recommendation)}`}>
                      {stock.recommendation.toUpperCase()}
                    </span>
                    <div className="text-right">
                      <p className={`text-lg font-bold ${getConfidenceColor(stock.confidence)}`}>
                        {stock.confidence}%
                      </p>
                      <p className="text-xs text-gray-600">
                        Consensus: {stock.consensus_strength}%
                      </p>
                    </div>
                  </div>
                </div>

                {/* Expanded View */}
                {expandedStock === stock.symbol && (
                  <div className="mt-4 pt-4 border-t border-gray-300 space-y-4">
                    <div>
                      <h5 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                        <Users className="w-4 h-4" />
                        Agent Votes
                      </h5>
                      <div className="grid grid-cols-3 gap-2">
                        <div className="bg-green-100 p-2 rounded text-center">
                          <p className="text-2xl font-bold text-green-700">{stock.agents_buy}</p>
                          <p className="text-xs text-green-600">Buy</p>
                        </div>
                        <div className="bg-yellow-100 p-2 rounded text-center">
                          <p className="text-2xl font-bold text-yellow-700">{stock.agents_hold}</p>
                          <p className="text-xs text-yellow-600">Hold</p>
                        </div>
                        <div className="bg-red-100 p-2 rounded text-center">
                          <p className="text-2xl font-bold text-red-700">{stock.agents_sell}</p>
                          <p className="text-xs text-red-600">Sell</p>
                        </div>
                      </div>
                    </div>

                    <div>
                      <h5 className="font-semibold text-gray-900 mb-2">Agent Analysis</h5>
                      <div className="space-y-2 max-h-64 overflow-y-auto">
                        {stock.agent_details.map((agent) => (
                          <div key={agent.agent} className="bg-white bg-opacity-60 p-2 rounded text-sm">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-semibold text-gray-800">{agent.agent}</span>
                              <span className={`badge ${getVerdictBadge(agent.verdict)}`}>
                                {agent.verdict.toUpperCase()}
                              </span>
                            </div>
                            <p className="text-xs text-gray-700">{agent.rationale}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Last Updated */}
          <p className="text-xs text-gray-500 text-center">
            Last updated: {new Date(topStocks.timestamp).toLocaleString()}
          </p>
        </>
      )}
    </div>
  );
}
