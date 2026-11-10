# EcoLogix AI — Nền Tảng Multi-Agent AI Tối Ưu Chuỗi Cung Ứng & Logistics Xanh Cho SMEs

> **Đề án tham dự Cuộc thi AI IN ECONOMICS 2026**  
> **Đơn vị tổ chức:** Câu lạc bộ Sinh viên Kinh tế (ESCUTE) & Khoa Kinh tế Trường Đại học Sư phạm Kỹ thuật TP.HCM (HCM-UTE).

---

## 🌟 1. Kiến Trúc Full-Stack Chuẩn Production (`backend/` + `frontend/`)

Toàn bộ dự án vận hành trên **một máy chủ hợp nhất duy nhất** tại:
👉 **`http://localhost:3000`** (hoặc triển khai tách Frontend Vercel + Backend FastAPI qua `ECOLOGIX_CORS_ORIGINS`).

* **Frontend (`frontend/`):** React 18 + Tailwind CSS + Leaflet GIS + Chart.js ([`frontend/index.html`](frontend/index.html)) — Chia 18 mô-đun giao diện (`components/` & `pages/`), xác thực Bearer token (`localStorage` / `sessionStorage`), thông báo Toast, Modal xác nhận & bộ lọc phân trang.
* **Backend API (`backend/`):** FastAPI modular theo 9 routers (`backend/routers/`), Dependency RBAC ([`backend/dependencies.py`](backend/dependencies.py)), CSDL SQLite 24 bảng ([`backend/database/`](backend/database/)), dự báo `lightgbm.LGBMRegressor`, tối ưu định tuyến CVRPTW, hệ sinh thái 6 AI Agents và bộ xuất báo cáo PDF/Excel.
* **Khởi chạy nhanh:**
  ```bash
  python run.py
  ```
  *(Các điểm vào cũ `python run_react_app.py` và `api_server.py` vẫn được giữ làm shim tương thích ngược).*

---

## 🔐 2. Xác Thực, Phiên Làm Việc & Phân Quyền (Auth & RBAC)

* **Đăng ký & Xác thực OTP:** `POST /api/auth/register` + `POST /api/auth/verify` + `POST /api/auth/resend-otp`, mật khẩu băm `PBKDF2-HMAC-SHA256` kèm salt ngẫu nhiên.
* **Token Phiên HMAC-SHA256:** `POST /api/auth/login` trả về signed Bearer token, kiểm tra đồng bộ qua `GET /api/auth/me` và đăng xuất qua `POST /api/auth/logout`. Hỗ trợ đặt lại mật khẩu (`POST /api/auth/forgot` & `POST /api/auth/reset`).
* **Kiểm soát RBAC 4 vai trò:** `Admin`, `Manager`, `Dispatcher`, `Auditor` thông qua [`require_roles`](backend/dependencies.py). Mặc định chế độ demo (`ECOLOGIX_STRICT_AUTH=false`) cho phép trải nghiệm ngay và tự động kích hoạt strict auth khi đặt `ECOLOGIX_STRICT_AUTH=true` trong `.env`.

---

## 🧠 3. Các Công Nghệ & Mô Hình Đã Hiện Thực Hóa

1. **Dự báo nhu cầu (`backend/services/forecasting_service.py`):** Huấn luyện **`lightgbm.LGBMRegressor`** trên chuỗi thời gian lịch sử 60 ngày + đơn hàng thực tế (`order_items`) + dữ liệu CSV nhập thêm (`POST /api/forecast/import-history`), đo MAPE out-of-sample, tính Safety Stock ($Z \times \sigma \times \sqrt{L}$), ROP và phát hành lệnh nhập kho tự động.
2. **Tối ưu lộ trình xanh (`backend/services/routing_service.py`):** Giải thuật Nearest-Neighbor + **2-Opt Local Search** có kiểm tra tải trọng tối đa (`max_load_kg`), tự động né khung giờ cấm tải nội đô TP.HCM (`RESTRICTED_TIME_WINDOW` trong `backend/config.py`), hỗ trợ cả đơn hàng SQLite và bộ **100 điểm TP.HCM & Đồng Nai** (`backend/data/delivery_points_100.json`).
3. **Hệ sinh thái 6 AI Agents (`backend/agents/`):** `Supervisor`, `Demand`, `Inventory`, `Route`, `Finance`, `ESG` truy vấn trực tiếp SQLite với chuỗi suy luận minh bạch (Reasoning Trace), làm mới lịch sử qua `DELETE /api/ai/messages`, có hỗ trợ cấu hình Gemini API Key trong phần Cài đặt.
4. **Xuất báo cáo thật (`backend/utils/exporters.py`):** Tạo file **PDF chuẩn tiếng Việt UTF-8** (ReportLab + font TrueType đa nền tảng) và **Excel 3 sheets** (OpenPyXL), hỗ trợ tải xuống kèm Bearer token.

---

## ⚙️ 4. Biến Môi Trường & Triển Khai

Sao chép `.env.example` thành `.env` khi triển khai:
```env
HOST=0.0.0.0
PORT=3000
ECOLOGIX_SECRET_KEY=replace-with-strong-random-secret
ECOLOGIX_STRICT_AUTH=false
ECOLOGIX_CORS_ORIGINS=*
```

### Triển khai Frontend lên Vercel
Do cấu trúc mới đặt toàn bộ giao diện tĩnh trong [`frontend/`](frontend/), khi cấu hình Project trên Vercel hãy đặt:
* **Root Directory:** `frontend` (đã có sẵn [`frontend/vercel.json`](frontend/vercel.json) rewrite SPA routes).

---

## 🧪 5. Kiểm Thử Tự Động (`tests/`)

Chạy toàn bộ bộ test đơn vị & tích hợp API (sử dụng bản sao SQLite cô lập tạm thời qua `ECOLOGIX_DB_PATH`):
```bash
python -m unittest discover -s tests -v
```

---

## 📁 6. Cấu Trúc Thư Mục Dự Án

```
AIinEco/
├── run.py                         # Entrypoint chính khởi chạy FastAPI + Uvicorn (http://localhost:3000)
├── api_server.py / run_react_app.py # Shim tương thích ngược
├── .env.example                   # Mẫu biến môi trường (SECRET_KEY, STRICT_AUTH, CORS_ORIGINS, PORT)
├── requirements.txt               # Danh mục thư viện Python
├── backend/
│   ├── main.py                    # Khởi tạo FastAPI App, CORS, Static mounts & 9 API Routers
│   ├── config.py                  # Cấu hình bảo mật & tham số Live-Code
│   ├── dependencies.py            # FastAPI Auth & RBAC Dependencies (get_current_user, require_roles)
│   ├── routers/                   # 9 module API (auth, dashboard, inventory, orders, vehicles, partners, analytics, ai, system)
│   ├── agents/                    # 6 AI Agents (supervisor, demand, inventory, route, finance, esg)
│   ├── services/                  # Nghiệp vụ & ML (auth, inventory, order, vehicle, partner, forecasting, routing, financial, carbon, ai)
│   ├── database/                  # connection.py (hỗ trợ ECOLOGIX_DB_PATH), models.py (24 bảng), seed.py, ecologix.db
│   ├── utils/                     # helpers.py (HMAC token, PBKDF2, audit log), validators.py, exporters.py
│   ├── data/                      # delivery_points_100.json, delivery_points_100.csv
│   └── assets/fonts/              # Font TrueType tùy chọn cho xuất PDF
├── frontend/
│   ├── index.html                 # Entry SPA React 18 + Tailwind CSS + Leaflet + Chart.js
│   ├── vercel.json                # Cấu hình rewrite cho Vercel (Root Directory = frontend)
│   ├── assets/                    # Logo & tài nguyên tĩnh
│   ├── components/                # common.jsx (auth, ModalShell, ConfirmModal, LoadingSkeleton), EcoLeafletMap.jsx
│   └── pages/                     # 16 màn hình nghiệp vụ & App router
├── scripts/
│   └── generate_dummy_data.py     # Script sinh dữ liệu 100 điểm TP.HCM & Đồng Nai
└── tests/                         # Bộ kiểm thử tự động unittest + API live
```
