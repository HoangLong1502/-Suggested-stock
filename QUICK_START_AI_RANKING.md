# Quick Start: Using AI Stock Ranking

## 🚀 3-Minute Setup

### Step 1: Import New Service (Already Done ✅)
The `stock_ranker.py` service is already integrated into the API routes.

### Step 2: Call the New Endpoints

#### Get Best Stock Right Now
```bash
curl http://localhost:8000/api/v1/agents/best-stock
```

**Response:**
```json
{
  "best_stock": "SSI",
  "recommendation": "buy",
  "confidence": 84.5,
  "consensus_strength": 80.0,
  "analysis_period": "60 days (2 months)"
}
```

#### Get Top 5 Stocks (All Filtered by Confidence)
```bash
curl "http://localhost:8000/api/v1/agents/top-stocks?limit=5&min_confidence=0.65"
```

#### Compare 3 Stocks
```bash
curl "http://localhost:8000/api/v1/agents/compare-stocks?symbols=VNM&symbols=SSI&symbols=ACB"
```

#### See How Agents Debated a Stock
```bash
curl "http://localhost:8000/api/v1/agents/consensus-debate/SSI"
```

---

## 📊 Frontend Integration

### Add Component to Dashboard
```tsx
// pages/dashboard.tsx or app/page.tsx
import AIStockRanking from '@/components/dashboard/AIStockRanking';

export default function DashboardPage() {
  return (
    <div className="p-6">
      <AIStockRanking />
    </div>
  );
}
```

### Component Features
- ✅ Auto-fetches top stocks from `/api/v1/agents/top-stocks`
- ✅ Shows summary statistics
- ✅ Highlights best stock with trophy 🏆
- ✅ Expandable stock cards with agent details
- ✅ Color-coded verdicts (Green/Yellow/Red)
- ✅ Auto-refreshes every 5 minutes
- ✅ Manual refresh button

---

## 🔧 Python/Backend Usage

### Use in Your Scripts
```python
from app.services.stock_ranker import stock_ranker
import asyncio

# Get best stock
result = asyncio.run(stock_ranker.get_best_stock())
print(f"Best stock: {result['best_stock']}")
print(f"Confidence: {result['confidence']}%")

# Rank all stocks
ranking = asyncio.run(stock_ranker.rank_all_stocks(min_confidence=0.65))
for stock in ranking['top_buy_stocks']:
    print(f"{stock['symbol']}: {stock['confidence']}% confidence")

# Compare specific stocks
comparison = asyncio.run(stock_ranker.compare_stocks(['VNM', 'SSI', 'ACB']))
for stock in comparison['comparison']:
    print(f"{stock['symbol']}: {stock['recommendation']}")
```

---

## 📈 Understanding Results

### Confidence Scores
- **80-100%**: Excellent - Strong signals, high conviction
- **65-79%**: Good - Clear signals, moderate conviction
- **50-64%**: Fair - Mixed signals, proceed cautiously
- **<50%**: Weak - No clear signals, skip this stock

### Consensus Strength
- **80-100%**: All agents strongly agree
- **60-79%**: Most agents agree (4 out of 5)
- **40-59%**: Split opinions (2-3 agents each side)
- **<40%**: Highly conflicted - investigate further

---

## 🎯 Example Workflows

### Workflow 1: Find the Best Stock Quickly
```javascript
// Fetch best stock
const response = await fetch('/api/v1/agents/best-stock');
const best = await response.json();

console.log(`💡 Best stock to trade: ${best.best_stock}`);
console.log(`📊 Confidence: ${best.confidence}%`);
console.log(`🎯 Recommendation: ${best.recommendation}`);
console.log(`📝 Reasoning: ${best.reasoning}`);
```

### Workflow 2: Review Top 5 Stocks
```javascript
// Fetch ranked list
const response = await fetch('/api/v1/agents/top-stocks?limit=5');
const ranking = await response.json();

console.log(`Total analyzed: ${ranking.summary.total_analyzed}`);
console.log(`High confidence: ${ranking.summary.high_confidence}`);
console.log(`Buy signals: ${ranking.summary.buy_signals}`);

ranking.all_ranked.forEach((stock, i) => {
  console.log(`${i + 1}. ${stock.symbol} - ${stock.confidence}% confidence`);
});
```

### Workflow 3: Deep Dive on Disagreement
```javascript
// When agents disagree, see why
const response = await fetch('/api/v1/agents/consensus-debate/ACB');
const debate = await response.json();

console.log(`Agent Votes: Buy=${debate.consensus.agent_votes.buy}, Hold=${debate.consensus.agent_votes.hold}, Sell=${debate.consensus.agent_votes.sell}`);

debate.individual_analyses.forEach(agent => {
  console.log(`${agent.agent}: ${agent.verdict} (${agent.confidence}%)`);
});
```

---

## ⚙️ Configuration

### Change Minimum Confidence Threshold
Edit `/backend/app/api/v1/routes.py` line where `min_confidence` is defined:

```python
# Default: 0.65 (65%)
min_confidence: float = Query(0.70, ge=0.0, le=1.0)  # Change to 70%
```

### Adjust Agent Weights
Edit `/backend/app/services/agent_orchestrator.py` in `DecisionMakerAgent.evaluate()`:

```python
# Currently:
if agent_name in ['BusinessAnalyst', 'TechnicalAnalyst']:
    weight = 1.2  # 20% more important
elif agent_name == 'RiskManagement':
    weight = 0.8  # 20% less important

# Adjust weights as needed for your strategy
```

---

## 🐛 Troubleshooting

### No stocks returned?
1. Check watchlist has symbols: `/api/v1/market/overview`
2. Increase minimum confidence: Add `&min_confidence=0.50` to URL
3. Check API logs for errors

### Slow response?
1. Analyze running for first time? May take 30-60 seconds
2. Try smaller limit: `?limit=3` instead of `?limit=10`
3. Check server resources

### Unexpected recommendation?
1. Check agent breakdown: `/api/v1/agents/consensus-debate/{symbol}`
2. Review individual agent reasoning
3. Consider counter-signals from dissenting agents

---

## 📚 Full API Reference

### Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/agents/best-stock` | Single best stock |
| GET | `/agents/top-stocks` | Ranked list of stocks |
| POST | `/agents/compare-stocks` | Compare specific stocks |
| GET | `/agents/consensus-debate/{symbol}` | See agent debate |
| GET | `/agents/debate/{symbol}` | Old format (still works) |
| GET | `/agents/{symbol}/recommendation` | Get recommendation |
| GET | `/agents/{symbol}/detailed-analysis` | Detailed analysis |

---

## ✨ Tips & Tricks

### Tip 1: Use for Watchlist Screening
Run `/agents/top-stocks` daily to screen watchlist for opportunities.

### Tip 2: Monitor Confidence Trends
Track how stock confidence changes over time - rising confidence = improving sentiment.

### Tip 3: Combine with Price Action
Use AI rankings + chart patterns for higher accuracy.

### Tip 4: Check Disagreement
When agents disagree (low consensus), look for breakout opportunities.

### Tip 5: Risk Management
High confidence ≠ No risk. Always check RiskManagement agent's stop-loss recommendations.

---

## 🎓 Learning More

- Read full guide: [AI_AGENTS_GUIDE.md](AI_AGENTS_GUIDE.md)
- Check source: [backend/app/services/stock_ranker.py](backend/app/services/stock_ranker.py)
- Review agents: [backend/app/services/agent_orchestrator.py](backend/app/services/agent_orchestrator.py)

---

## 🚀 Ready to Trade with AI!

Your system now has AI agents that can:
- Analyze stocks from 5 different angles
- Collaborate and debate recommendations
- Rank all your watched stocks
- Provide detailed reasoning

**Start using the new endpoints today!** 💰📊🤖
