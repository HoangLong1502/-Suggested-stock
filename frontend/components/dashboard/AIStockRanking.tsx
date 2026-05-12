import React, { useState, useEffect } from 'react';
import { AlertCircle, TrendingUp, Trophy, Users, Target } from 'lucide-react';

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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedStock, setExpandedStock] = useState<string | null>(null);
  const [selectedTab, setSelectedTab] = useState<'all' | 'buy' | 'analysis'>('all');

  useEffect(() => {
    fetchTopStocks();
    const interval = setInterval(fetchTopStocks, 5 * 60 * 1000); // Refresh every 5 minutes
    return () => clearInterval(interval);
  }, []);

  const fetchTopStocks = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/v1/agents/top-stocks?limit=10&min_confidence=0.65');
      if (!response.ok) throw new Error('Failed to fetch top stocks');
      const data = await response.json();
      setTopStocks(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
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
            onClick={fetchTopStocks}
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
          {topStocks.all_ranked.length > 0 && (
            <div className="bg-gradient-to-r from-yellow-50 to-orange-50 border-2 border-yellow-300 p-6 rounded-lg">
              <div className="flex items-start gap-4">
                <div className="bg-yellow-400 text-white rounded-full p-3">
                  <Target className="w-6 h-6" />
                </div>
                <div className="flex-1">
                  <p className="text-sm text-gray-600">🏆 Best Stock (Highest Confidence)</p>
                  <h3 className="text-3xl font-bold text-gray-900">
                    {topStocks.all_ranked[0].symbol}
                  </h3>
                  <div className="mt-2 flex items-center gap-4">
                    <span className={`badge ${getVerdictBadge(topStocks.all_ranked[0].recommendation)}`}>
                      {topStocks.all_ranked[0].recommendation.toUpperCase()}
                    </span>
                    <span className={`text-lg font-bold ${getConfidenceColor(topStocks.all_ranked[0].confidence)}`}>
                      {topStocks.all_ranked[0].confidence}% Confidence
                    </span>
                    <span className="text-gray-600">
                      Consensus: {topStocks.all_ranked[0].consensus_strength}%
                    </span>
                  </div>
                  <p className="text-gray-700 mt-3">{topStocks.all_ranked[0].reasoning}</p>
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
            {(selectedTab === 'all' ? topStocks.all_ranked : topStocks.buy_recommendations).map((stock) => (
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
