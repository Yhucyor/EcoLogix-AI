# EcoLogix AI — Nền Tảng Multi-Agent AI Tối Ưu Chuỗi Cung Ứng & Logistics Xanh Cho SMEs

> **Đề án tham dự Cuộc thi AI IN ECONOMICS 2026**  
> **Đơn vị tổ chức:** Câu lạc bộ Sinh viên Kinh tế (ESCUTE) & Khoa Kinh tế — Trường Đại học Sư phạm Kỹ thuật TP.HCM (HCM-UTE).

---

## 1. Tổng Quan Kiến Trúc & Công Nghệ

**EcoLogix AI** được thiết kế theo kiến trúc **Unified Full-Stack Web Application** — một tiến trình FastAPI phục vụ đồng thời cả REST API lẫn React 18 SPA:

| Thành phần | Công nghệ sử dụng | Mô tả chính |
| :--- | :--- | :--- |
| **Backend API** | **FastAPI** + **Uvicorn** (`backend/main.py`) | 9 routers RESTful, xác thực Bearer Token HMAC-SHA256, phân quyền RBAC 4 vai trò (`Admin`, `Manager`, `Dispatcher`, `Auditor`). |
| **Database (Dual-Mode)** | **TiDB Cloud Serverless** (`PyMySQL + TLS`) / **SQLite** | 24 bảng nghiệp vụ liên kết chặt chẽ (`backend/database/models.py`). Tự động kết nối TiDB khi có `TIDB_HOST`, fallback về SQLite cục bộ (`ecologix.db`) khi chạy offline hoặc test. |
| **Frontend SPA** | **React 18** + **Tailwind CSS v3** + **Leaflet** + **Chart.js** | 17 mô-đun `.jsx` (`frontend/components/` & `frontend/pages/`), responsive desktop/tablet/mobile, hỗ trợ Dark Mode và tìm kiếm nhanh `⌘/Ctrl + K`. |
| **Dự báo nhu cầu** | **LightGBM (`LGBMRegressor`)** + Pandas + Scikit-Learn | Huấn luyện trên lịch sử 60 ngày, đơn hàng thực tế và CSV import; tính MAPE, Safety Stock, ROP và đề xuất nhập kho (EOQ). |
| **Tối ưu lộ trình (Green VRPTW)** | **Clarke-Wright Savings + SA-GVRPTW + 2-Opt/Or-Opt + OSRM** | Ma trận khoảng cách đường bộ thực tế & bám sát mặt đường OpenStreetMap (OSRM), xét tải trọng, khung giờ khách hàng, giờ cấm tải nội đô và xe điện EV. |
| **Multi-Agent AI** | **6 AI Agents chuyên trách** (`backend/agents/`) | `Supervisor`, `Demand`, `Inventory`, `Route`, `Finance`, `ESG` truy vấn trực tiếp CSDL kèm Reasoning Trace và tùy chọn Gemini (`gemini-2.0-flash`). |
| **Báo cáo & Email** | **ReportLab (PDF)** + **OpenPyXL (XLSX)** + **Gmail SMTP** | Xuất PDF & Excel 3 sheets; gửi email OTP đăng ký, khôi phục mật khẩu và đặt lịch tư vấn 1-1 qua SMTP (`STARTTLS`). |

---

## 2. Các Tính Năng Đã Hoàn Thiện

### 2.1. Xác thực, Email OTP & Onboarding Doanh Nghiệp
- **Đăng ký, Xác thực OTP 6 số, Đăng nhập, Quên mật khẩu** qua `/api/auth/*` ([`backend/routers/auth.py`](backend/routers/auth.py)):
  - Mật khẩu băm `PBKDF2-HMAC-SHA256` kèm salt ngẫu nhiên.
  - Gửi email HTML qua Gmail SMTP (`email_service.py`), có fallback an toàn khi chưa cấu hình SMTP.
- **Luồng Onboarding thông minh**:
  - Khi người dùng bấm **"Bắt đầu ngay"** từ Trang chủ (`LandingPage.jsx`), hệ thống gọi `GET /api/onboarding/current` kiểm tra tài khoản đã có hồ sơ doanh nghiệp chưa để hiển thị lựa chọn *"Tiếp tục dự án hiện tại"* hoặc *"Chỉnh sửa cấu hình"* (`OnboardingPage.jsx`).

### 2.2. Quản trị Chuỗi cung ứng Toàn diện (Dashboard & Nghiệp vụ)
- **Dashboard (`DashboardPage.jsx`)**: KPI giảm CO₂, tiết kiệm chi phí, đơn đang giao, hiệu suất tồn kho, cảnh báo thiếu hàng, biểu đồ Chi phí vs Doanh thu (Chart.js) và bản đồ đội xe Leaflet.
- **Quản lý Kho (`InventoryPage.jsx`)**: Đa kho hàng, thêm/sửa/xóa SKU, giao dịch Nhập/Xuất/Điều chuyển/Kiểm kê (`inventory_transactions`) với kiểm tra tồn kho không âm.
- **Đơn hàng, Đội xe & Đối tác (`OrdersPage.jsx`, `VehiclesPage.jsx`, `PartnersPage.jsx`)**: Tạo đơn có tự động trừ tồn kho, quản lý đội xe Diesel & Electric, phân loại khách hàng VIP/Standard và nhà cung cấp.

### 2.3. Tối Ưu Lộ Trình Xanh (Green VRPTW) & Bản Đồ Bám Đường Thực Tế
- **Đa thuật toán tối ưu (`backend/services/routing_service.py`)**:
  - `auto`: Auto Ensemble (Best-of-3) đối chiếu cả 3 thuật toán với Baseline FIFO thực tế và chọn phương án có hàm mục tiêu xanh thấp nhất.
  - `simulated_annealing`: Simulated Annealing (`SA-GVRPTW`) với 3 phép biến đổi (*2-Opt reversal*, *Swap*, *Relocate*).
  - `clarke_wright`: Clarke-Wright Savings (`CVRP`) hỗ trợ tự động chia tải đa xe (`multi_vehicle=True`, ưu tiên xe điện EV cho đơn nội đô).
  - `nn_or_opt`: Time-Window Nearest Neighbor kết hợp 2-Opt & Or-Opt (bộ lọc delta $O(1)$).
- **Hàm mục tiêu Green VRPTW**: Tối ưu đồng thời tổng quãng đường, hệ số tiêu hao theo tải trọng mang theo (`weighted_load_km`), phạt trễ khung giờ khách hàng (`late_minutes`) và né khung giờ cấm tải nội đô TP.HCM (`RESTRICTED_TIME_WINDOW`).
- **Khớp đường phố thực tế OpenStreetMap / OSRM (`EcoLeafletMap.jsx` & `/api/routing/road-geometry`)**:
  - Lấy ma trận khoảng cách đường đi thực tế (`/table/v1/driving`) và hình học từng ngã rẽ/cầu vượt (`/route/v1/driving`) qua `routing.openstreetmap.de` + fallback `router.project-osrm.org`, có cache bộ nhớ & chia chunk cho tuyến 100 điểm.
  - Vẽ tuyến với viền Halo nổi bật, đánh số thứ tự điểm dừng `1..N`, tự tách nhẹ ghim trùng tọa độ và hỗ trợ 7 chế độ nền bản đồ (OSM, Voyager, Dark, Vệ tinh, Stamen Toner, Địa hình, Tối giản).
- **So sánh Xe Xanh & Thực nghiệm 100 điểm**: Bảng gợi ý chuyển đổi Diesel vs Electric (0 phát thải ống xả Scope 1) và bộ thực nghiệm 25 / 50 / 100 điểm TP.HCM – Bình Dương – Đồng Nai (`backend/data/delivery_points_100.json`).

### 2.4. Dự Báo Nhu Cầu, 6 AI Agents & Xuất Báo Cáo
- **Dự báo LightGBM (`ForecastingPage.jsx`)**: Hỗ trợ chân trời 7/14/30/90 ngày, nhập dữ liệu bán hàng CSV, hiển thị dải tin cậy (Upper/Lower), Safety Stock, ROP và tạo phiếu nhập kho đề xuất.
- **Trợ lý AI 6 Agents (`AiAssistantPage.jsx`)**: Điều phối câu hỏi tiếng Việt qua `Supervisor Agent`, lưu hội thoại vào bảng `ai_conversations` / `ai_messages`, làm mới đoạn chat qua `DELETE /api/ai/messages`.
- **Xuất Báo cáo (`ReportsPage.jsx`)**: Tải trực tiếp báo cáo PDF (`GET /api/reports/export/pdf`) và Excel 3 sheets (`GET /api/reports/export/xlsx`), kèm phân tích độ nhạy Live-Code (`SettingsPage.jsx`).

---

## 3. Cấu Trúc Thư Mục Dự Án

```text
AIinEco/
├── run.py                         # Entrypoint chính (Uvicorn phục vụ FastAPI + SPA trên $PORT, mặc định 3000)
├── api_server.py / run_react_app.py # Shim tương thích ngược
├── render.yaml                    # Cấu hình Render Blueprint (Python 3.11.11 + TiDB Cloud + SMTP)
├── Procfile                       # Khai báo `web: python run.py`
├── .python-version                # Ghim phiên bản Python 3.11.11
├── .env.example                   # Mẫu biến môi trường (không chứa mật khẩu thật)
├── requirements.txt               # Thư viện Python (FastAPI, LightGBM, PyMySQL, ReportLab, OpenPyXL...)
├── backend/
│   ├── main.py                    # Khởi tạo FastAPI, auto-bootstrap DB, CORS, static mounts & SPA routes
│   ├── config.py                  # Đọc .env, cấu hình bảo mật, SMTP & biến số kinh tế Live-Code
│   ├── dependencies.py            # Auth Bearer token & RBAC (`get_current_user`, `require_roles`)
│   ├── routers/                   # 9 routers: auth, dashboard, inventory, orders, vehicles, partners, analytics, ai, system
│   ├── agents/                    # 6 AI Agents: supervisor, demand, inventory, route, finance, esg
│   ├── services/                  # Lớp nghiệp vụ & thuật toán (routing_service, forecasting_service, email_service...)
│   ├── database/
│   │   ├── connection.py          # Dual-driver TiDB Cloud (PyMySQL + TLS) / SQLite + dịch placeholder `?` -> `%s`
│   │   ├── models.py              # Schema DDL 24 bảng (tương thích SQLite & TiDB/MySQL)
│   │   ├── seed.py                # Bộ tạo dữ liệu mẫu liên kết 24 bảng
│   │   └── ecologix.db            # Dữ liệu SQLite mặc định cho chạy local offline
│   ├── utils/                     # helpers.py (PBKDF2, HMAC token, log), exporters.py (PDF/XLSX), validators.py
│   ├── data/                      # delivery_points_100.json, delivery_points_100.csv
│   └── assets/fonts/              # Thư mục đặt font TrueType tùy chọn cho xuất PDF
├── frontend/
│   ├── index.html                 # Entry SPA (React 18 + Tailwind CDN + Leaflet + Chart.js + Babel loader)
│   ├── vercel.json                # Cấu hình rewrite tĩnh dự phòng nếu tách riêng Frontend
│   ├── assets/                    # Logo & favicon
│   ├── components/                # 2 components: `common.jsx`, `EcoLeafletMap.jsx`
│   └── pages/                     # 15 pages: Landing, Login, Onboarding, Dashboard, Inventory, Forecasting,
│                                  # Orders, Routing, Vehicles, Partners, AiAssistant, Reports, Notifications, Settings, App
├── scripts/
│   ├── generate_dummy_data.py     # Sinh dữ liệu 100 điểm giao hàng
│   └── migrate_sqlite_to_tidb.py  # Đồng bộ toàn bộ 24 bảng từ SQLite lên TiDB Cloud
└── tests/
    ├── support.py                 # LiveApiTestCase & IsolatedDbTestCase (cô lập DB tạm & tắt OSRM mạng)
    ├── test_analytics_vrp_api.py  # Test LightGBM, Green VRP, OSRM chunking/cache, TiDB dialect, PDF/XLSX, Email
    ├── test_auth_rbac.py          # Test đăng ký, OTP, login, reset password, RBAC 4 vai trò
    └── test_inventory_orders.py   # Test kho hàng, tồn âm, tạo/xóa đơn hàng, đội xe, đối tác
```

---

## 4. Hướng Dẫn Cài Đặt & Chạy Local

### Bước 1: Tạo môi trường & cài thư viện
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

### Bước 2: Cấu hình biến môi trường (`.env`)
Sao chép `.env.example` thành `.env` và điền thông tin tương ứng:
```bash
cp .env.example .env
```
* **Nếu chạy SQLite cục bộ:** Để trống `TIDB_HOST` — hệ thống tự dùng `backend/database/ecologix.db`.
* **Nếu kết nối TiDB Cloud Serverless:** Điền `TIDB_HOST`, `TIDB_PORT=4000`, `TIDB_USER`, `TIDB_PASSWORD`, `TIDB_DATABASE=ecologix`.
* **Nếu muốn gửi email OTP / Tư vấn thật:** Điền `SMTP_USER`, `SMTP_PASSWORD` (Gmail App Password 16 ký tự), `SMTP_FROM`.

### Bước 3: Đồng bộ dữ liệu (tùy chọn) & Khởi chạy
```bash
# (Tùy chọn) Đồng bộ dữ liệu mẫu từ SQLite sang TiDB Cloud lần đầu:
python scripts/migrate_sqlite_to_tidb.py

# Chạy máy chủ hợp nhất tại http://localhost:3000
python run.py
```

### Tài khoản demo có sẵn
* **Admin:** `admin@ecologix.vn` / `password123`
* **Manager:** `nguyen.van.a@ecologix.vn` / `password123`
* **Dispatcher:** `thuy.nguyen@abc.com` / `password123`
* **Auditor:** `tuan.tran@ecologix.vn` / `password123`

---

## 5. Hướng Dẫn Deploy Production (Render + TiDB Cloud)

> **Lưu ý nền tảng:** **Vercel** giới hạn bundle Python Serverless tối đa 250 MB (vượt giới hạn khi đóng gói `lightgbm` + `scipy` + `scikit-learn` + `pandas` + `numpy`) và không cho ghi file SQLite bền vững. Vì vậy, dự án được cấu hình chuẩn để deploy trọn gói trên **Render** kết hợp cơ sở dữ liệu **TiDB Cloud Serverless**.

1. **Mở IP Access List trên TiDB Cloud**: Trong TiDB Cloud Console → Cluster → **Networking / IP Access List**, thêm `0.0.0.0/0` để server Render có thể kết nối (vẫn bảo vệ bằng TLS + mật khẩu).
2. **Đẩy code lên GitHub** (kiểm tra `git status` để chắc chắn `.env` đã bị `.gitignore` bỏ qua).
3. **Deploy bằng Render Blueprint (`render.yaml`)**:
   - Render Dashboard → **New +** → **Blueprint** → chọn repo GitHub.
   - Nhập 5 biến `sync: false` lấy từ `.env` của bạn: `TIDB_USER`, `TIDB_PASSWORD`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`.
   - Nhấn **Deploy Blueprint** và kiểm tra `https://<service>.onrender.com/api/health`.
4. **Siết bảo mật khi lên Production**: Trong tab **Environment** trên Render, cập nhật `ECOLOGIX_STRICT_AUTH=true` và đặt `ECOLOGIX_CORS_ORIGINS=https://<service>.onrender.com`.

---

## 6. Kiểm Thử Tự Động

Chạy toàn bộ 11 test cases bằng `unittest` (dùng SQLite tạm qua `ECOLOGIX_DB_PATH` và mock ngoại vi nên chạy hoàn toàn offline, không chạm TiDB Cloud):
```bash
python -m unittest discover -s tests -v
```

---

## 7. Đánh Giá Hiện Trạng: Các Điểm Thiếu Sót & Hướng Cải Thiện Tiếp Theo

Qua rà soát toàn bộ mã nguồn hiện tại, dưới đây là các hạng mục bạn nên ưu tiên hoàn thiện nếu đưa dự án từ bản thi đấu/demo sang vận hành thương mại lâu dài:

### 7.1. Bảo mật & Phân quyền
1. **Ẩn `demo_otp` / `demo_token` khỏi API Response (`backend/routers/auth.py`)**: Hiện `/api/auth/register`, `/api/auth/resend-otp` và `/api/auth/forgot` vẫn trả kèm `demo_otp` / `demo_token` trong JSON kể cả khi SMTP đã gửi thành công. Cần chỉ trả các trường này khi `not email_sent and not config.STRICT_AUTH`.
2. **Bật `ECOLOGIX_STRICT_AUTH=true` & siết CORS khi chạy thật (`backend/dependencies.py`, `render.yaml`)**: Mặc định đang bật chế độ trải nghiệm (`STRICT_AUTH=false`, fallback về `DEFAULT_DEMO_USER` và `CORS=*`). Nên tách rõ profile `dev` và `prod`.
3. **Cô lập dữ liệu Multi-Tenant theo `company_id`**: Một số truy vấn ở `dashboard.py`, `supervisor_agent.py` và các service đang mặc định `company_id = 1` hoặc chưa lọc `WHERE company_id = ?` theo tài khoản đăng nhập. Nếu cho nhiều doanh nghiệp cùng đăng ký trên một hệ thống, cần bổ sung lọc theo `current_user["company_id"]` ở mọi bảng nghiệp vụ.

### 7.2. Hạ tầng, Lưu trữ & Hiệu năng
4. **Lưu cấu hình Live-Code vào DB thay vì sửa file `backend/config.py`**: Hàm `save_live_config()` hiện ghi đè trực tiếp file `config.py` trên ổ đĩa. Khi chạy trên container có filesystem tạm như Render Free, thay đổi sẽ mất sau mỗi lần restart/redeploy — nên lưu và đọc trực tiếp từ bảng `system_settings` trong TiDB Cloud.
5. **Bổ sung Font tiếng Việt vào `backend/assets/fonts/` (`backend/utils/exporters.py`)**: Thư mục `backend/assets/fonts/` hiện đang trống. Trên máy Linux/container của Render không có sẵn font Windows (`Arial`/`Tahoma`), nếu môi trường thiếu `DejaVuSans.ttf` thì file PDF xuất ra sẽ fallback về `Helvetica` và bị lỗi font dấu tiếng Việt. Cần copy sẵn `DejaVuSans.ttf` và `DejaVuSans-Bold.ttf` vào thư mục này.
6. **Build Frontend bằng Vite thay vì Babel/Tailwind CDN runtime (`frontend/index.html`)**: Hiện trình duyệt phải tải Tailwind CDN + Babel Standalone để biên dịch 17 file `.jsx` trực tiếp ở client mỗi lần tải trang. Chuyển sang build tĩnh (`vite build`) sẽ giảm mạnh thời gian First Contentful Paint và loại bỏ phụ thuộc CDN ngoài.
7. **Hoàn thiện Dark Mode đồng bộ**: Trong `App.jsx` đã có công tắc Dark Mode, nhưng nhiều thẻ nội dung ở các trang con vẫn dùng lớp cố định nền sáng (`bg-white`, `border-sky-100`).

### 7.3. Kiểm thử & Bảo trì Mã Nguồn
8. **Thiếu test E2E giao diện & CI/CD**: Bộ test `tests/` mới kiểm tra tầng Backend/API bằng Python `unittest`; chưa có Playwright/Cypress kiểm tra luồng bấm UI thực tế trên trình duyệt hay GitHub Actions (`.github/workflows`) tự động chạy test trước khi deploy.
9. **Vài chi tiết nhỏ**:
   - Trong `backend/services/forecasting_service.py` (dòng 107), thuộc tính `dt.dayofweek` đang sinh cảnh báo `Pandas4Warning` (nên đổi sang `dt.day_of_week`).
   - Có một bản kế hoạch tham khảo cũ `PROJECT_COMPLETION_PLAN.md` và gói UI mẫu `ui-ux-pro-max-skill/` ở thư mục gốc có thể dọn gọn nếu muốn repo nhẹ hơn trước khi nộp/công bố.
