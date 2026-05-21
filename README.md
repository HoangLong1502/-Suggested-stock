# Bot Trading — AI Multi-Agent Stock Analysis (VN)

Nền tảng phân tích cổ phiếu Việt Nam: dashboard thị trường, watchlist, top movers, phòng tranh luận đa agent và xếp hạng AI (best pick / top stocks). Chạy local bằng Docker, stack mã nguồn mở.

## Tính năng chính

| Khu vực | Mô tả |
|--------|--------|
| **Market overview** | VNINDEX / HNX / UPCOM, watchlist, top movers, biểu đồ preview; `?fast=true` đọc DB nhanh (cache ~25s) |
| **Phân tích ngành** | Trang `/sectors` — 10 nhóm VN (ngân hàng, BĐS, công nghệ…), % TB từ OHLC DB, mã dẫn dắt |
| **Watchlist** | Giá & % theo phiên (2 nến đóng gần nhất); badge trạng thái phiên |
| **Top movers** | Top tăng / giảm từ DB (batch OHLC, không quét full DB) |
| **AI Debate** | Nhiều agent bàn luận theo mã (HOLD / BUY / SELL, % = độ tin cậy) |
| **AI ranking** | Best pick, top stocks; entry / thời điểm mua; cache ranking; lỗi trả **degraded** (200) thay vì 500 |

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
- **Dữ liệu:** `stock_ingest`, `historical_analyzer`, `technical_calculator`, `fundamental_analyzer`, `sector_analyzer`

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
| **Phân tích ngành** | http://localhost:3000/sectors |
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
GET  /api/v1/market/overview?fast=true   # overview nhanh (cache ~25s, không sync VNDirect mỗi request)
GET  /api/v1/market/sectors?fast=true    # phân tích 10 ngành từ OHLC DB (cache ~120s; fast=bỏ finfo)
GET  /api/v1/stock/{symbol}              # phân tích lịch sử + fundamental + technical
GET  /api/v1/agents/debate/{symbol}      # tranh luận đa agent
GET  /api/v1/agents/best-stock           # mã AI chọn + buy_timing (cache ~10 phút; có thể vài phút lần đầu)
GET  /api/v1/agents/top-stocks           # xếp hạng (?limit=10&min_confidence=0.4; dùng chung cache ranking)
GET  /api/v1/agents/suggest              # gợi ý mã (nặng — không gọi SSR dashboard)
```

| Endpoint | Thời gian gợi ý | Ghi chú |
|----------|------------------|---------|
| `market/overview?fast=true` | &lt; 1s (cache) | Sync giá nền qua `periodic_market_sync` |
| `market/sectors?fast=true` | &lt; 1s (cache) | `fast=false` gọi thêm VNDirect finfo (chậm hơn) |
| `agents/best-stock` | 2–5 phút (lần đầu) | Tối đa 10 mã watchlist; lần sau dùng cache |
| `agents/top-stocks` | như ranking | Lỗi ranking → JSON `status: degraded`, HTTP 200 |

## Cấu trúc thư mục

```
Bot_Trading/
├── backend/          # FastAPI, services, models, scripts/init_data.py
├── frontend/         # Next.js: dashboard, sectors, lib/api.ts, AppNavbar
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
$env:NEXT_PUBLIC_API_URL="http://localhost:8000/api/v1"   # hoặc 5555 nếu backend map cổng Docker
npm run dev
```

Mở http://localhost:3000 (Next mặc định port 3000). Trang ngành: http://localhost:3000/sectors

## Xử lý sự cố

### Giao diện chỉ nền trắng, chữ đen

- Do Tailwind/PostCSS không build trong container (thường gặp khi mount `./frontend` đè `node_modules` trên Windows).  
- **Cách xử lý:** dùng `docker-compose.yml` hiện tại (volume `frontend_node_modules`) rồi `docker compose up --build`.  
- Hoặc chạy frontend trên host: `cd frontend && npm install && npm run dev`.

### Watchlist / % = 0

- Đợi backend sync (`stock_ingest`) hoặc seed: DB trống sẽ tự seed OHLC demo lúc startup (gồm mã đại diện các ngành).  
- Kiểm tra http://localhost:5555/api/v1/market/overview?fast=true

### Không tải được dữ liệu ngành (`/sectors`)

- Backend phải phản hồi: http://localhost:5555/api/v1/market/sectors?fast=true  
- Nếu API treo: `docker compose restart backend` (tránh reload khi đang chạy ranking AI lâu).  
- Frontend timeout 60s; dùng luôn `fast=true` (chỉ DB, không chờ finfo).

### AI ranking / best-stock treo hoặc timeout

- Endpoint nặng (5 agent × tối đa 10 mã); lần đầu **2–5 phút**, lần sau cache ~10 phút.  
- UI timeout ranking ~15 phút; `best-stock` / `top-stocks` trả **degraded** (HTTP 200, `best_stock: null`) khi lỗi thay vì 500.  
- Giảm số mã watchlist hoặc bật Ollama ổn định (`OLLAMA_URL` đúng trong Docker).

### Backend không trả lời sau khi sửa code

- Uvicorn `--reload` có thể chờ task nền (ranking AI). `docker compose restart backend` để thoát trạng thái kẹt.

### Cổng 3000 bận

Đổi mapping trong `docker-compose.yml`, ví dụ `'3010:3000'`, và truy cập http://localhost:3010.

## Tài liệu thêm

- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) — tóm tắt triển khai  
- [TESTING_GUIDE.md](./TESTING_GUIDE.md) — kiểm thử  

## Lưu ý pháp lý

Công cụ hỗ trợ nghiên cứu / học tập, **không phải** lời khuyên đầu tư. Kiểm tra dữ liệu và rủi ro trước khi giao dịch thật.

## Repository

https://github.com/HoangLong1502/-Suggested-stock.git
