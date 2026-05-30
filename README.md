# Bot Trading — AI Multi-Agent Stock Analysis (VN)

Nền tảng phân tích cổ phiếu Việt Nam: dashboard thị trường, watchlist, top movers, chi tiết mã + AI phân tích, phòng tranh luận đa agent và xếp hạng AI (best pick / top stocks).

> **Chạy lần đầu?** Đọc **[HOW_TO_RUN.md](./HOW_TO_RUN.md)** — hướng dẫn từng bước, xử lý lỗi, không cần hỏi maintainer.

## Quick start

```powershell
git clone <repo-url> Bot_Trading
cd Bot_Trading
docker compose up --build
```

| Dịch vụ | URL |
|---------|-----|
| **Giao diện** | http://localhost:3000 |
| **Phân tích ngành** | http://localhost:3000/sectors |
| **API** | http://localhost:5555/api/v1 |
| **Swagger** | http://localhost:5555/docs |

Chi tiết: [HOW_TO_RUN.md](./HOW_TO_RUN.md)

## Tính năng chính

| Khu vực | Mô tả |
|--------|--------|
| **Market overview** | VNINDEX / HNX / UPCOM, watchlist 30 mã, top movers, biểu đồ preview |
| **Giá realtime** | VCI (vnstock) sync ~8s; WebSocket `/ws/market` — không reload trang |
| **Chi tiết mã** | Bấm mã → trần/sàn/TC, sổ lệnh, nút **AI phân tích** |
| **Phân tích ngành** | `/sectors` — nhóm ngành VN, % TB từ OHLC DB |
| **AI Debate** | 5 agent bàn luận theo mã; tóm tắt tiếng Việt dễ đọc |
| **AI ranking** | Best pick, worst, cảnh báo SELL sớm, entry gợi ý |

**Nguồn giá:** ưu tiên **VCI / vnstock**; fallback VNDirect finfo hoặc OHLC trong PostgreSQL; DB trống có thể **seed demo**.

**Đơn vị giá trên UI:** nghìn VNĐ (vd `27,55` = 27.550 đ/cp).

## Kiến trúc

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Next.js    │────▶│   FastAPI    │────▶│ PostgreSQL  │
│  (3000)     │     │   (5555)     │     │  (dữ liệu)  │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    Redis (pub/sub agent)
                    VCI / vnstock (giá)
                    Ollama (tùy chọn)
```

- **Frontend:** Next.js 14, TypeScript, Tailwind, Recharts, React Query  
- **Backend:** FastAPI, SQLAlchemy (async)  
- **AI:** `agent_orchestrator`, `investment_committee`, `recommendation_engine`, `stock_ranker`  
- **Dữ liệu:** `stock_ingest`, `vn_realtime_quotes`, `historical_analyzer`, `sector_analyzer`

Tài liệu sâu: [ARCHITECTURE.md](./ARCHITECTURE.md) · [AI_AGENTS_GUIDE.md](./AI_AGENTS_GUIDE.md) · [AI_STOCK_RANKING_README.md](./AI_STOCK_RANKING_README.md)

## Yêu cầu

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Compose v2) — **khuyên dùng**
- RAM ≥ 8 GB
- **Tùy chọn:** [Ollama](https://ollama.com/) cho LLM local

## API tiêu biểu

```http
GET  /api/v1/market/overview?fast=true
GET  /api/v1/market/stock/{symbol}
GET  /api/v1/market/sectors?fast=true
GET  /api/v1/agents/debate/{symbol}
GET  /api/v1/agents/best-stock
GET  /api/v1/agents/top-stocks?limit=10
WS   ws://localhost:5555/ws/market
```

| Endpoint | Thời gian gợi ý |
|----------|------------------|
| `market/overview?fast=true` | &lt; 1s (cache) |
| `market/stock/FPT` | vài giây |
| `agents/debate/{symbol}` | 1–2 phút |
| `agents/best-stock` | 2–5 phút (lần đầu, có cache) |

## Cấu trúc thư mục

```
Bot_Trading/
├── HOW_TO_RUN.md      ← hướng dẫn chạy chi tiết
├── backend/           # FastAPI, services, models
├── frontend/          # Next.js dashboard
├── docker-compose.yml
└── docs: ARCHITECTURE.md, AI_AGENTS_GUIDE.md, TESTING_GUIDE.md, ...
```

## Xử lý sự cố (tóm tắt)

| Triệu chứng | Xem |
|-------------|-----|
| `npm ENOENT package.json` | [HOW_TO_RUN §10](./HOW_TO_RUN.md#10-xử-lý-lỗi-thường-gặp) |
| Backend không kết nối Postgres | Restart compose; đợi postgres Healthy |
| UI trắng / không CSS | Rebuild frontend container |
| Giá = 0, movers trống | Đợi sync VCI 1–2 phút |
| AI ranking timeout | Bình thường lần đầu; đợi cache |

Đầy đủ: **[HOW_TO_RUN.md — mục 10](./HOW_TO_RUN.md#10-xử-lý-lỗi-thường-gặp)**

## Tài liệu thêm

- [HOW_TO_RUN.md](./HOW_TO_RUN.md) — **chạy project từ A–Z**
- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
- [TESTING_GUIDE.md](./TESTING_GUIDE.md)

## Lưu ý pháp lý

Công cụ hỗ trợ nghiên cứu / học tập, **không phải** lời khuyên đầu tư.

## Repository

https://github.com/HoangLong1502/-Suggested-stock.git
