# 🧪 AI Stock Ranking System - Testing Guide

## Quick Verification (2 Minutes)

### Test 1: Best Stock Endpoint
```bash
# In Terminal/PowerShell
curl "http://localhost:8000/api/v1/agents/best-stock"
```

**Expected Response:**
```json
{
  "best_stock": "SSI",
  "recommendation": "buy",
  "confidence": 84.5,
  "consensus_strength": 80.0,
  "reasoning": "Strong consensus among all agents...",
  "analysis_period": "60 days (2 months)",
  "timestamp": "2026-05-12T10:30:00"
}
```

✅ **Pass**: Stock symbol returned + confidence score shown  
❌ **Fail**: Error message or empty response

---

### Test 2: Top Stocks Endpoint
```bash
curl "http://localhost:8000/api/v1/agents/top-stocks?limit=5&min_confidence=0.65"
```

**Expected Response:**
```json
{
  "timestamp": "2026-05-12T10:30:00",
  "analysis_period_days": 60,
  "summary": {
    "total_analyzed": 25,
    "high_confidence": 8,
    "buy_signals": 5,
    "hold_signals": 2,
    "sell_signals": 1
  },
  "best_stock": "SSI",
  "all_ranked": [
    {
      "symbol": "SSI",
      "recommendation": "buy",
      "confidence": 84.5,
      "consensus_strength": 80.0
    },
    ...
  ]
}
```

✅ **Pass**: Multiple stocks returned + ranked by confidence  
❌ **Fail**: Empty list or error

---

### Test 3: Compare Stocks Endpoint
```bash
curl -X POST "http://localhost:8000/api/v1/agents/compare-stocks?symbols=VNM&symbols=SSI&symbols=ACB"
```

**Expected Response:**
```json
{
  "timestamp": "2026-05-12T10:30:00",
  "analysis_period": "60 days (2 months)",
  "best_stock": "SSI",
  "comparison": [
    {
      "symbol": "SSI",
      "recommendation": "buy",
      "confidence": 84.5,
      "consensus_strength": 80.0,
      "agent_votes": {
        "buy": 4,
        "hold": 1,
        "sell": 0
      }
    },
    ...
  ]
}
```

✅ **Pass**: All 3 stocks compared side-by-side  
❌ **Fail**: Error or incomplete comparison

---

### Test 4: Debate View Endpoint
```bash
curl "http://localhost:8000/api/v1/agents/consensus-debate/SSI"
```

**Expected Response:**
```json
{
  "symbol": "SSI",
  "analysis_period": "60 days (2 months)",
  "agents_involved": [
    "MarketScanner (Trend & Momentum)",
    "BusinessAnalyst (Fundamentals)",
    "TechnicalAnalyst (Technical Indicators)",
    "SentimentAnalysis (Market Sentiment)",
    "RiskManagement (Risk Assessment)"
  ],
  "individual_analyses": [
    {
      "agent": "MarketScanner",
      "verdict": "BUY",
      "confidence": 82.0,
      "rationale": "Market trend: uptrend..."
    },
    ...
  ],
  "consensus": {
    "verdict": "BUY",
    "confidence": 84.5,
    "consensus_strength": 80.0,
    "agent_votes": {
      "buy": 4,
      "hold": 1,
      "sell": 0
    }
  }
}
```

✅ **Pass**: Individual agent analysis shown + consensus calculated  
❌ **Fail**: Error or missing agents

---

## Comprehensive Testing (5 Minutes)

### Test 5: Response Times
```bash
# Measure time for all endpoints

# Test best-stock (should be <3 seconds)
time curl "http://localhost:8000/api/v1/agents/best-stock"

# Test top-stocks (should be <15 seconds)
time curl "http://localhost:8000/api/v1/agents/top-stocks?limit=10"

# Test compare (should be <10 seconds)
time curl -X POST "http://localhost:8000/api/v1/agents/compare-stocks?symbols=VNM&symbols=SSI&symbols=ACB"
```

✅ **Pass**: All responses within time limits  
❌ **Fail**: Responses taking >20 seconds

---

### Test 6: Frontend Component
```typescript
// In your React component
import AIStockRanking from '@/components/dashboard/AIStockRanking';

export default function TestPage() {
  return <AIStockRanking />;
}
```

**Visual Checks:**
- ✅ Component loads without errors
- ✅ Shows summary statistics
- ✅ Displays best stock with trophy icon
- ✅ Shows ranked stock list
- ✅ Expandable stock cards work
- ✅ Tabs filter correctly
- ✅ Auto-refresh works (check every 5 min)
- ✅ Colors are correct (Green/Yellow/Red)

---

### Test 7: Confidence Scores
```bash
# Get top stocks and verify confidence distribution
curl "http://localhost:8000/api/v1/agents/top-stocks?limit=20"

# Then check:
# - All confidence scores between 0-100 ✅
# - Sorted by confidence descending ✅
# - Only stocks with ≥65% confidence included ✅
```

✅ **Pass**: Confidence scores valid and properly sorted  
❌ **Fail**: Invalid scores or wrong sorting

---

### Test 8: Agent Agreement
```bash
# Get detailed analysis for a stock
curl "http://localhost:8000/api/v1/agents/consensus-debate/SSI" | jq '.consensus'

# Verify:
# - buy_agents + hold_agents + sell_agents = 5 ✅
# - consensus_strength between 0-100 ✅
# - consensus_strength correlates with verdict ✅
```

✅ **Pass**: Agent counts match + consensus makes sense  
❌ **Fail**: Counts don't add up or consensus illogical

---

## Integration Testing (10 Minutes)

### Test 9: Database Connection
```bash
# Verify watchlist is loaded
curl "http://localhost:8000/api/v1/market/overview"

# Check response includes:
# - watchlist items ✅
# - indices data ✅
# - sector heatmap ✅
```

---

### Test 10: Historical Data
```bash
# Verify 60-day data is available
curl "http://localhost:8000/api/v1/historical/SSI"

# Check response includes:
# - At least 60 days of data ✅
# - Trend analysis ✅
# - Momentum calculation ✅
# - Support/resistance levels ✅
```

---

### Test 11: Fundamental Analysis
```bash
# Verify business data
curl "http://localhost:8000/api/v1/fundamental/SSI"

# Check response includes:
# - PE ratio ✅
# - ROE ✅
# - Growth metrics ✅
# - Quality score ✅
```

---

### Test 12: Technical Indicators
```bash
# Verify indicators calculated
curl "http://localhost:8000/api/v1/technical/SSI"

# Check response includes:
# - RSI ✅
# - MACD ✅
# - Bollinger Bands ✅
# - Volume analysis ✅
```

---

## Edge Case Testing (5 Minutes)

### Test 13: Empty/Invalid Input
```bash
# Test with invalid symbol
curl "http://localhost:8000/api/v1/agents/consensus-debate/INVALID"

# Expected: Error response
{
  "error": "No data available for symbol..."
}

✅ **Pass**: Graceful error handling
```

---

### Test 14: Low Confidence Threshold
```bash
# Request with very low confidence
curl "http://localhost:8000/api/v1/agents/top-stocks?min_confidence=0.1"

# Expected: Many more stocks returned
# Verify: all returned stocks have confidence > 0.1

✅ **Pass**: Threshold filtering works
```

---

### Test 15: High Confidence Threshold
```bash
# Request with very high confidence
curl "http://localhost:8000/api/v1/agents/top-stocks?min_confidence=0.95"

# Expected: Few or no stocks returned
# Verify: all returned stocks have confidence > 0.95

✅ **Pass**: Threshold filtering works
```

---

### Test 16: Parallel Processing
```bash
# Request all stocks analysis
curl "http://localhost:8000/api/v1/agents/top-stocks?limit=20"

# Expected: Returns in <15 seconds
# (If sequential: would take >40 seconds for 20 stocks)

✅ **Pass**: Parallel processing working
❌ **Fail**: Takes >20 seconds
```

---

## Performance Testing (3 Minutes)

### Test 17: Memory Usage
```bash
# Monitor memory while running analysis
# Use system monitor or:
# ps aux | grep python  (on Linux/Mac)
# tasklist (on Windows)

# Expected: Memory usage stays stable (<500MB)
# After 5+ requests: No memory leaks

✅ **Pass**: Stable memory usage
❌ **Fail**: Memory keeps increasing
```

---

### Test 18: Concurrent Requests
```bash
# Send multiple requests simultaneously
# Using curl in parallel or similar tool

# Command (on Linux):
for i in {1..5}; do
  curl "http://localhost:8000/api/v1/agents/best-stock" &
done
wait

# Expected: All requests complete successfully
# No timeouts or errors

✅ **Pass**: Handles concurrent requests
❌ **Fail**: Some requests timeout or error
```

---

## Acceptance Criteria Checklist

### Backend Services
- [ ] `stock_ranker.py` exists and imports correctly
- [ ] `rank_all_stocks()` returns ranked list
- [ ] `get_best_stock()` returns single best stock
- [ ] `compare_stocks()` returns comparison data
- [ ] All functions handle errors gracefully

### API Endpoints
- [ ] `/agents/best-stock` returns valid response
- [ ] `/agents/top-stocks` returns ranked list
- [ ] `/agents/compare-stocks` compares stocks
- [ ] `/agents/consensus-debate/{symbol}` shows debate
- [ ] All endpoints return proper HTTP status codes

### Frontend Component
- [ ] `AIStockRanking.tsx` imports without errors
- [ ] Component renders on page
- [ ] Summary statistics display correctly
- [ ] Stock list populates with data
- [ ] Expandable cards work
- [ ] Tab filtering works
- [ ] Auto-refresh activates every 5 minutes

### Data Quality
- [ ] Confidence scores between 0-100
- [ ] Consensus strength between 0-100
- [ ] All 5 agents represented in debate
- [ ] Agent votes sum to 5 (or 4 if one missing)
- [ ] Recommendations are BUY/HOLD/SELL

### Performance
- [ ] Single stock analysis: <3 seconds
- [ ] Top stocks (10): <15 seconds
- [ ] Compare (3 stocks): <10 seconds
- [ ] Memory stable across requests
- [ ] Handles concurrent requests

---

## Troubleshooting Failed Tests

### If Test 1 Fails (Best Stock)
1. Check backend is running: `http://localhost:8000/docs`
2. Check watchlist has data: `/market/overview`
3. Check logs for agent errors
4. Restart backend service

### If Test 2 Fails (Top Stocks)
1. Verify watchlist populated
2. Check min_confidence value
3. Increase limit to see more stocks
4. Check error logs

### If Frontend Component Fails
1. Check TypeScript compilation
2. Verify imports are correct
3. Check for console errors
4. Verify API endpoints accessible

### If Performance Tests Fail
1. Check system resources (CPU, memory, disk)
2. Reduce number of stocks in watchlist
3. Check network latency
4. Profile with monitoring tools

---

## Sign-Off Checklist

After all tests pass:

- [ ] All 18 tests completed
- [ ] Acceptance criteria met
- [ ] Documentation reviewed
- [ ] No errors in logs
- [ ] Performance acceptable
- [ ] Ready for production

**Status**: ✅ Ready for Production

---

## Next Steps

1. ✅ Run all 18 tests
2. ✅ Fix any failures
3. ✅ Deploy to production
4. ✅ Monitor in production
5. ✅ Gather user feedback
6. ✅ Plan v2.0 enhancements

---

## Support

For test failures, check:
1. `AI_AGENTS_GUIDE.md` - Feature guide
2. `QUICK_START_AI_RANKING.md` - Quick start
3. `IMPLEMENTATION_SUMMARY.md` - Architecture
4. Source code comments in services
5. API documentation at `/docs`

---

**Happy Testing!** 🧪✅🚀
