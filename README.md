# Bot Trading — AI Multi-Agent Stock Analysis (VN)

Nền tảng phân tích cổ phiếu Việt Nam: dashboard thị trường, watchlist, top movers, phòng tranh luận đa agent và xếp hạng AI (best pick / top stocks). Chạy local bằng Docker, stack mã nguồn mở.

## Tính năng chính

| Khu vực | Mô tả |
|--------|--------|
| **Market overview** | VNINDEX / HNX / UPCOM, biểu đồ preview, sector heatmap |
| **Watchlist** | Giá & % theo phiên; sau giờ đóng cửa hiển thị **giá đóng / tham chiếu** cuối; badge trạng thái phiên |
| **Top movers** | Top tăng / giảm từ DB hoặc quote (VNDirect finho + OHLC fallback) |
| **AI Debate** | Nhiều agent bàn luận theo mã (HOLD / BUY / SELL, % = độ tin cậy) |
| **AI ranking** | Best pick, thống kê tín hiệu, danh sách xếp hạng; entry / thời điểm mua (khi API trả đủ) |

Dữ liệu: ưu tiên **VNDirect finho**; nếu thiếu thì **OHLC trong PostgreSQL**; DB trống có thể **seed demo** để UI và agent hoạt động offline.

## Kiến trúc

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Next.js    │────▶│   FastAPI    │────▶│ PostgreSQL  │
│  (3000)     │     │   (5555)     │     │  + Redis    │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    Ollama (tùy chọn)
                    Multi-agent services
```

- **Frontend:** Next.js 14, TypeScript, Tailwind CSS, Recharts, React Query, Zustand  
- **Backend:** FastAPI, SQLAlchemy (async), Celery worker (tùy cấu hình)  
- **AI:** orchestrator + ranking (`stock_ranker`, `agent_orchestrator`, `recommendation_engine`)  
- **Dữ liệu:** `stock_ingest`, `historical_analyzer`, `technical_calculator`, `fundamental_analyzer`

Chi tiết kiến trúc agent: [ARCHITECTURE.md](./ARCHITECTURE.md) · Hướng dẫn agent: [AI_AGENTS_GUIDE.md](./AI_AGENTS_GUIDE.md) · Ranking API: [AI_STOCK_RANKING_README.md](./AI_STOCK_RANKING_README.md) · Quick start ranking: [QUICK_START_AI_RANKING.md](./QUICK_START_AI_RANKING.md)

## Yêu cầu

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Compose v2)
- RAM đủ cho Postgres + Redis + Next dev (khuyến nghị ≥ 8 GB)
- **Tùy chọn:** [Ollama](https://ollama.com/) chạy trên máy host nếu muốn LLM local (xem mục Ollama bên dưới)

## Chạy bằng Docker (khuyến nghị)

Tại thư mục gốc dự án:

```powershell
docker compose up --build
```

Lần đầu container **frontend** chạy `npm install` (volume `node_modules` riêng trong Linux — tránh lỗi UI chỉ trắng/đen trên Windows).

### Truy cập

| Dịch vụ | URL |
|---------|-----|
| **Giao diện** | http://localhost:3000 |
| **API** | http://localhost:5555/api/v1 |
| **Swagger** | http://localhost:5555/docs |
| PostgreSQL | `localhost:5432` (user/pass/db: `bottrader` / `bottrader` / `bottrading`) |
| Redis | `localhost:6379` |

### Dừng

```powershell
docker compose down
```

Xóa volume DB (cẩn thận — mất dữ liệu Postgres):

```powershell
docker compose down -v
```

## Biến môi trường

Đã khai báo trong `docker-compose.yml`:

| Biến | Mặc định (Docker) | Ghi chú |
|------|-------------------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:5555/api/v1` | Browser gọi API |
| `INTERNAL_API_URL` | `http://backend:8000/api/v1` | SSR Next trong mạng Docker |
| `DATABASE_URL` | Postgres service | Backend |
| `REDIS_URL` | Redis service | Pub/sub, cache |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Trong container cần đổi nếu Ollama chạy trên host |

**Ollama trên Windows/Mac (Docker Desktop):** backend trong container không truy cập `127.0.0.1` của host. Sửa trong `docker-compose.yml`:

```yaml
OLLAMA_URL=http://host.docker.internal:11434
```

## API tiêu biểu

```http
GET  /api/v1/market/overview          # indices, watchlist, gainers/losers, chart_preview
GET  /api/v1/stock/{symbol}           # phân tích lịch sử + fundamental + technical
GET  /api/v1/agents/debate/{symbol}   # tranh luận đa agent
GET  /api/v1/agents/best-stock        # mã AI chọn (có thể chạy lâu)
GET  /api/v1/agents/top-stocks        # xếp hạng watchlist (?limit=10&min_confidence=0.4)
GET  /api/v1/agents/suggest           # gợi ý mã (nặng — không gọi SSR dashboard)
```

Phân tích ranking / best-stock có thể **vài phút** tùy số mã và Ollama.

## Cấu trúc thư mục

```
Bot_Trading/
├── backend/          # FastAPI, services, models, scripts/init_data.py
├── frontend/         # Next.js app, components/dashboard, lib/api.ts
├── docker-compose.yml
├── ARCHITECTURE.md
├── AI_AGENTS_GUIDE.md
└── TESTING_GUIDE.md
```

## Chạy local không Docker (tùy chọn)

**Backend**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Postgres + Redis phải đang chạy, DATABASE_URL/REDIS_URL đúng
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_API_URL="http://localhost:8000/api/v1"
npm run dev
```

Mở http://localhost:3000 (Next mặc định port 3000).

## Xử lý sự cố

### Giao diện chỉ nền trắng, chữ đen

- Do Tailwind/PostCSS không build trong container (thường gặp khi mount `./frontend` đè `node_modules` trên Windows).  
- **Cách xử lý:** dùng `docker-compose.yml` hiện tại (volume `frontend_node_modules`) rồi `docker compose up --build`.  
- Hoặc chạy frontend trên host: `cd frontend && npm install && npm run dev`.

### Watchlist / % = 0

- Đợi backend sync (`stock_ingest`) hoặc seed: DB trống sẽ tự seed OHLC demo lúc startup.  
- Kiểm tra http://localhost:5555/api/v1/market/overview

### AI ranking / best-stock treo hoặc timeout

- Endpoint nặng; UI timeout ~15 phút. Giảm mã watchlist hoặc bật Ollama ổn định.  
- Tab **degraded** vẫn có thể hiện thông báo từ server khi ranking không chạy xong.

### Cổng 3000 bận

Đổi mapping trong `docker-compose.yml`, ví dụ `'3010:3000'`, và truy cập http://localhost:3010.

## Tài liệu thêm

- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) — tóm tắt triển khai  
- [TESTING_GUIDE.md](./TESTING_GUIDE.md) — kiểm thử  

## Lưu ý pháp lý

Công cụ hỗ trợ nghiên cứu / học tập, **không phải** lời khuyên đầu tư. Kiểm tra dữ liệu và rủi ro trước khi giao dịch thật.

## Repository

https://github.com/HoangLong1502/-Suggested-stock.git
