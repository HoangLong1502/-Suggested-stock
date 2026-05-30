# Hướng dẫn chạy Bot Trading (How to Run)

Tài liệu này dành cho người **clone repo lần đầu** — làm theo từng bước, **không cần hỏi người viết code**.

---

## 1. Cần cài gì trước?

| Phần mềm | Bắt buộc? | Ghi chú |
|----------|-----------|---------|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | **Có** (cách khuyên dùng) | Bật WSL2 trên Windows nếu được hỏi |
| Git | Có | Clone repository |
| RAM ≥ 8 GB | Khuyên dùng | Postgres + Redis + Next dev |
| [Ollama](https://ollama.com/) | Không | Chỉ khi muốn LLM local cho agent |

**Không cần** cài Node.js hay Python trên máy nếu chạy **100% bằng Docker**.

---

## 2. Clone & vào thư mục

```powershell
git clone https://github.com/HoangLong1502/-Suggested-stock.git Bot_Trading
cd Bot_Trading
```

(Hoặc clone URL repo thực tế bạn đang dùng.)

---

## 3. Chạy toàn bộ stack (khuyên dùng)

Tại **thư mục gốc** `Bot_Trading` (có file `docker-compose.yml`):

```powershell
docker compose up --build
```

**Lần đầu** có thể mất **5–15 phút** (build image, `npm install` trong container frontend).

### Khi nào coi là chạy OK?

Đợi log có dạng:

- `postgres` → `database system is ready to accept connections`
- `backend` → `Application startup complete`
- `frontend` → `Ready` hoặc `compiled successfully`

### Mở trình duyệt

| Mục | URL |
|-----|-----|
| **Dashboard** | http://localhost:3000 |
| **Phân tích ngành** | http://localhost:3000/sectors |
| **API health / overview** | http://localhost:5555/api/v1/market/overview?fast=true |
| **Swagger (API docs)** | http://localhost:5555/docs |

### Kiểm tra nhanh (copy-paste)

```powershell
curl http://localhost:5555/api/v1/market/overview?fast=true
```

Phải trả JSON có `watchlist`, `indices` (có thể rỗng vài giây đầu rồi có dữ liệu).

---

## 4. Dừng / chạy lại

```powershell
# Dừng (giữ dữ liệu DB)
docker compose down

# Chạy lại nền
docker compose up -d --build

# Xem log
docker compose logs -f backend
docker compose logs -f frontend
```

**Xóa hết dữ liệu Postgres** (cẩn thận):

```powershell
docker compose down -v
```

---

## 5. Lần đầu chạy — nên biết gì?

1. **Frontend** trong Docker tự chạy `npm install` — đừng chạy `npm run dev` ở thư mục gốc (sẽ lỗi thiếu `package.json`).
2. **Backend** đợi Postgres healthy rồi mới start (tránh lỗi `Temporary failure in name resolution`).
3. **Giá watchlist** sync từ **VCI (vnstock)** ~8 giây/lần; lần đầu có thể thấy 0 rồi đầy sau 1–2 phút.
4. **DB trống** → backend tự **seed OHLC demo** để UI không trắng trơn.
5. **AI ranking / best-stock** lần đầu có thể **2–5 phút** (5 agent × nhiều mã).
6. **Giá hiển thị** đơn vị **nghìn VNĐ** (vd `27,55` = 27.550 đ/cp).

### Watchlist mặc định (30 mã)

`OIL, PLX, SSI, CII, MBB, BSR, DPM, HAG, MSN, MSR, SGP, DCM, HPG, FPR, MCH, VTP, VTB, ACV, MWG, POW, SAB, TCB, VCB, VIC, VJC, VNM, FPT, VHM, GAS, BID, CTG`

---

## 6. Các lệnh thường dùng

```powershell
# Chỉ restart backend (sau sửa code Python)
docker compose restart backend

# Chỉ restart frontend
docker compose restart frontend

# Rebuild khi đổi Dockerfile / requirements
docker compose up --build backend frontend
```

---

## 7. Chạy KHÔNG dùng Docker (tùy chọn)

Chỉ dùng khi bạn quen Python/Node. Vẫn cần **Postgres + Redis** chạy (có thể chỉ bật 2 service Docker):

```powershell
docker compose up -d postgres redis
```

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt

$env:DATABASE_URL="postgresql+asyncpg://bottrader:bottrader@localhost:5432/bottrading"
$env:REDIS_URL="redis://localhost:6379/0"

uvicorn app.main:app --reload --port 8000
```

API: http://localhost:8000/docs

### Frontend

```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_API_URL="http://localhost:8000/api/v1"
npm run dev
```

UI: http://localhost:3000

> Nếu backend chạy qua Docker (port **5555**), dùng:  
> `$env:NEXT_PUBLIC_API_URL="http://localhost:5555/api/v1"`

---

## 8. Biến môi trường

Đã cấu hình sẵn trong `docker-compose.yml`:

| Biến | Giá trị (Docker) | Ý nghĩa |
|------|-------------------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:5555/api/v1` | Browser gọi API |
| `INTERNAL_API_URL` | `http://backend:8000/api/v1` | Next.js SSR trong Docker |
| `DATABASE_URL` | Postgres service | Lưu giá, OHLC, watchlist |
| `REDIS_URL` | Redis service | Pub/sub agent (phụ) |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | LLM local (tùy chọn) |

### Ollama trên Windows/Mac (Docker)

Container không truy cập `127.0.0.1` của máy host. Sửa trong `docker-compose.yml`:

```yaml
OLLAMA_URL=http://host.docker.internal:11434
```

Rồi trên host: `ollama serve` và `ollama pull <model>`.

---

## 9. API hữu ích khi test

```http
GET  /api/v1/market/overview?fast=true
GET  /api/v1/market/stock/FPT          # Chi tiết 1 mã (trần/sàn, sổ lệnh)
GET  /api/v1/market/sectors?fast=true
GET  /api/v1/agents/debate/MCH         # AI phân tích 1 mã (~1–2 phút)
GET  /api/v1/agents/best-stock         # Best pick hội đồng (~2–5 phút lần đầu)
GET  /api/v1/agents/top-stocks?limit=10
WS   ws://localhost:5555/ws/market     # Giá realtime (không qua /api/v1)
```

Swagger đầy đủ: http://localhost:5555/docs

---

## 10. Xử lý lỗi thường gặp

### `npm error ENOENT ... package.json` ở `F:\Bot_Trading`

**Nguyên nhân:** chạy `npm run dev` ở **thư mục gốc**.  
**Cách sửa:** dùng `docker compose up` hoặc `cd frontend` rồi mới `npm run dev`.

### Backend: `Temporary failure in name resolution` / không kết nối Postgres

**Nguyên nhân:** backend start trước khi Postgres sẵn sàng.  
**Cách sửa:**

```powershell
docker compose down
docker compose up --build
```

Hoặc: `docker compose restart backend` sau khi postgres đã `Healthy`.

### UI trắng / chữ đen, không có style

**Cách sửa:** dùng Docker với volume `frontend_node_modules` (đã có trong compose).  
`docker compose down` → `docker compose up --build`  
Hoặc chạy frontend trên host: `cd frontend && npm install && npm run dev`.

### Watchlist giá = 0 hoặc top movers trống

1. Đợi 1–2 phút cho sync VCI.  
2. Mở http://localhost:5555/api/v1/market/overview?fast=true  
3. `docker compose restart backend`

### AI ranking treo / timeout

- Bình thường lần đầu **2–5 phút**.  
- Đừng reload liên tục; đợi cache (~10 phút).  
- `docker compose restart backend` nếu log không còn phản hồi.

### Cổng 3000 hoặc 5555 đã bị chiếm

Sửa `docker-compose.yml`:

```yaml
ports:
  - '3010:3000'   # frontend
  - '5556:8000'   # backend
```

Và `NEXT_PUBLIC_API_URL=http://localhost:5556/api/v1`.

### Giá “lạ” so với app khác

- App dùng **nghìn VNĐ** (`13,00` = 13.000 đ).  
- Kiểm tra đúng **mã** (vd `PLX` Petrolimex ≠ `PXL` Long Sơn).  
- Ngoài giờ giao dịch: hiển thị **giá đóng cửa phiên gần nhất**.

---

## 11. Kiến trúc tóm tắt

```
Browser (3000) → Next.js → FastAPI (5555) → PostgreSQL (5432)
                              ↓
                           Redis (6379) — pub/sub agent, tùy chọn mở rộng
                              ↓
                           VCI / vnstock (giá realtime)
```

- **PostgreSQL:** lưu giá, lịch sử, watchlist — **bắt buộc**.  
- **Redis:** nhắn tin nội bộ agent — **phụ**, stack vẫn cần cho compose hiện tại.  
- **WebSocket** `/ws/market`: cập nhật giá không reload trang.

---

## 12. Tài liệu liên quan

| File | Nội dung |
|------|----------|
| [README.md](./README.md) | Tổng quan dự án |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Kiến trúc agent |
| [AI_AGENTS_GUIDE.md](./AI_AGENTS_GUIDE.md) | Cách hoạt động AI |
| [TESTING_GUIDE.md](./TESTING_GUIDE.md) | Kiểm thử |

---

## 13. Lưu ý pháp lý

Công cụ **hỗ trợ nghiên cứu / học tập**, không phải lời khuyên đầu tư. Tự kiểm tra dữ liệu và rủi ro trước khi giao dịch.
