# 🤖 AI Multi-Agent Stock Analysis Platform - Updated Architecture

## ✨ Mới: Real-time AI Analysis với Buy/Sell Timing

### Tính năng chính

✅ **Historical Data Analysis** - AI phân tích từ dữ liệu quá khứ (60 ngày)
✅ **Business Analyzer Bot** - Phân tích doanh nghiệp thực sự (PE, ROE, Growth)
✅ **Technical Indicators** - Tính toán RSI, MACD, EMA, Bollinger Bands
✅ **Entry/Exit Points** - Đề xuất thời gian mua, giá mua, stop loss, take profit
✅ **Multi-Agent Debate** - 5 agents tương tác để ra quyết định
✅ **Real-time Watchlist** - Track múmã cổ phiếu với phân tích liên tục

---

## 🏗️ Architecture

### 6 AI Agents

1. **Market Scanner Agent** - Phân tích xu hướng + momentum từ dữ liệu lịch sử
2. **Business Analyst Agent** - ⭐ MỚI: Phân tích doanh nghiệp (PE, ROE, Growth, Debt)
3. **Technical Analyst Agent** - Tính toán RSI, MACD, EMA, Bollinger Bands
4. **Sentiment Analysis Agent** - Phân tích tâm lý thị trường từ volatility
5. **Risk Management Agent** - Tính stop loss, take profit, position size
6. **Decision Maker Agent** - Tổng hợp tất cả ý kiến → quyết định cuối

### Services

```
backend/app/services/
├── historical_analyzer.py       : Phân tích dữ liệu lịch sử
├── fundamental_analyzer.py      : Bot phân tích doanh nghiệp
├── technical_calculator.py      : Tính toán technical indicators
├── recommendation_engine.py     : Đề xuất entry/exit points
├── agent_orchestrator.py        ✅ IMPROVED: 6 agents thực sự
├── stock_ingest.py
├── pubsub.py
└── llm_provider.py
```

---

## 📊 API Endpoints

### 1. Market Overview
```
GET /api/v1/market/overview
```
Kết quả:
- VNINDEX, HNX, UPCOM
- Watchlist items
- Top gainers/losers
- Sector heatmap

### 2. Stock Detail (NEW!)
```
GET /api/v1/stock/{symbol}
```
Kết quả:
- Historical analysis (trend, volatility, momentum)
- Business analysis (PE, ROE, Growth scores)
- Technical indicators (RSI, MACD, EMA, Bollinger)

### 3. AI Recommendation (ENHANCED!)
```
GET /api/v1/agents/{symbol}/recommendation
```
Kết quả:
```json
{
  "symbol": "SSI",
  "recommendation": "buy",
  "confidence": 78.5,
  "current_price": 52.30,
  "entry_points": {
    "recommended_entry": 51.50,
    "entry_type": "Moderate (Near Support)",
    "breakout_entry": 53.45,
    "alternative_entries": [...]
  },
  "exit_points": {
    "stop_loss": 50.25,
    "stop_loss_pct": 3.92,
    "take_profit": 55.80,
    "tp_pct": 6.68,
    "suggested_exit_strategy": "Exit 1/3 at 2.8% gains, 1/3 at 6.7%, 1/3 at 11.2%"
  },
  "buy_timing": {
    "timing": "BUY NOW",
    "urgency": "High",
    "buy_signals": ["RSI oversold", "MACD bullish crossover"],
    "next_check_hours": 4
  },
  "sell_timing": {
    "timing": "HOLD",
    "urgency": "Low",
    "sell_signals": []
  },
  "risk_reward": 1.71
}
```

### 4. Detailed Analysis (AI Debate Room)
```
GET /api/v1/agents/debate/{symbol}
```
Kết quả:
```json
{
  "symbol": "SSI",
  "debate": [
    {
      "agent": "MarketScanner",
      "verdict": "buy",
      "confidence": 75.3,
      "rationale": "Uptrend with strong momentum...",
      "details": {
        "trend": "uptrend",
        "momentum": "strong_bullish"
      }
    },
    {
      "agent": "BusinessAnalyst",
      "verdict": "buy",
      "confidence": 82.1,
      "rationale": "Business Quality: Good...",
      "details": {
        "pe_ratio": 12.4,
        "roe": 18.2,
        "growth_profit": 15.3
      }
    },
    ...
  ],
  "consensus": {
    "verdict": "buy",
    "confidence": 78.5,
    "consensus_strength": 80
  }
}
```

### 5. Top Suggestions
```
GET /api/v1/agents/suggest
```
Kết quả:
```json
{
  "suggestions": [
    {
      "symbol": "SSI",
      "verdict": "buy",
      "confidence": 78.5,
      "rationale": "..."
    },
    ...
  ],
  "count": 5
}
```

### 6. Technical Analysis (NEW!)
```
GET /api/v1/technical/{symbol}
```

### 7. Fundamental Analysis (NEW!)
```
GET /api/v1/fundamental/{symbol}
```

### 8. Historical Analysis (NEW!)
```
GET /api/v1/historical/{symbol}
```

---

## 🚀 Khởi chạy

### 1. Start Docker containers
```bash
cd f:\Bot_Trading
docker-compose up --build
```

### 2. Initialize data (optional - với sample data)
```bash
docker-compose exec backend python -m scripts.init_data
```

### 3. Access ứng dụng
- Frontend: http://localhost:3010
- Backend API: http://localhost:5555
- Swagger Docs: http://localhost:5555/docs

---

## 📈 Workflow Phân tích

### Khi bạn yêu cầu recommendation cho mã SSI:

1. **Market Scanner Agent** (30ms)
   - Lấy 60 ngày historical prices
   - Tính trend, momentum, volatility
   - Phát hiện support/resistance
   - → Verdict: BUY (score: 0.75)

2. **Business Analyst Agent** (200ms) ⭐ NEW
   - Gọi vnstock API lấy fundamentals
   - Tính PE, ROE, Revenue Growth
   - Scoring doanh nghiệp (Excellent/Good/Fair/Poor)
   - → Verdict: BUY (score: 0.82)

3. **Technical Analyst Agent** (50ms)
   - Tính RSI, MACD, EMA, Bollinger Bands
   - Phân tích volume profile
   - Tìm entry signals
   - → Verdict: BUY (score: 0.80)

4. **Sentiment Agent** (30ms)
   - Phân tích tâm lý từ momentum
   - Kiểm tra overbought/oversold
   - → Verdict: HOLD (score: 0.60)

5. **Risk Manager Agent** (40ms)
   - Tính volatility (ATR)
   - Xác định stop loss từ support
   - Tính take profit từ resistance
   - Đề xuất position size
   - → Verdict: BUY (score: 0.70)

6. **Decision Maker Agent** (20ms)
   - Tổng hợp: 4 votes BUY, 1 vote HOLD
   - Avg confidence: 0.734
   - Consensus strength: 80%
   - → Final Verdict: **BUY** ✓

7. **Recommendation Engine** (100ms) ⭐ NEW
   - Calculate entry points:
     - Recommended: 51.50 (Moderate - Near Support)
     - Breakout: 53.45
   - Calculate exit points:
     - Stop Loss: 50.25 (3.92% below)
     - Take Profit: 55.80 (6.68% above)
   - Determine timing:
     - Buy Timing: **BUY NOW** (RSI < 30 + MACD bullish)
     - Sell Timing: **HOLD** (not overbought)

**Total time: ~500ms** ⚡

---

## 🎯 Key Improvements

| Trước | Sau |
|------|-----|
| Mock data | ✓ Real historical analysis |
| Stub agents | ✓ 6 thực agents với logic |
| Không buy/sell timing | ✓ Entry/exit points + timing |
| Không business analysis | ✓ Business Analyst Bot |
| Không technical calc | ✓ Real RSI, MACD, EMA, Bollinger |
| ~30% hoàn thiện | ✓ ~75% hoàn thiện |

---

## 📝 Yêu cầu dữ liệu

Tất cả dữ liệu đến từ:
- ✅ vnstock library (free Vietnamese stock data)
- ✅ VNDirect API (public market data)
- ✅ Local historical prices (database)
- ✅ không cần API keys

---

## 🔧 Development

### Thêm stock vào watchlist
1. Cập nhật `backend/app/services/stock_ingest.py` → `DEFAULT_WATCHLIST`
2. Restart backend

### Tuning confidence weights
1. Edit `backend/app/services/agent_orchestrator.py`
2. Adjust scores trong mỗi agent

### Thay đổi technical indicators
1. Edit `backend/app/services/technical_calculator.py`
2. Add new indicators hoặc adjust periods

---

## 🐛 Troubleshooting

### "No data available"
- Chạy `init_data.py` để seed sample data
- Kiểm tra database connection

### "vnstock not available"
- Cài: `pip install vnstock>=4.0.2`
- Kiểm tra version

### LLM errors
- Start Ollama: `ollama serve`
- Pull model: `ollama pull llama3:8b`

---

## 🎨 Next Steps

1. Real-time WebSocket streaming (mỗi 10s update)
2. Notification system (Telegram/Discord)
3. Portfolio tracking
4. Backtesting engine
5. Advanced pattern recognition

---

**Platform hoàn thiện: ~75%** ✅
