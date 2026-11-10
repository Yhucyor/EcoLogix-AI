# KẾ HOẠCH HOÀN THIỆN DỰ ÁN ECOLOGIX AI
**Sản phẩm tham dự Cuộc thi AI IN ECONOMICS 2026 (HCM-UTE)**  
*Tài liệu rà soát hiện trạng thực tế trên mã nguồn và lộ trình nâng cấp chi tiết từ bản Demo hiện tại lên bản Hoàn thiện Production.*

---

## PHẦN 1. HIỆN TRẠNG ĐÃ ĐẠT ĐƯỢC (BASELINE)

Tính đến thời điểm hiện tại, nền tảng **EcoLogix AI** đã vận hành ổn định trên máy chủ hợp nhất tại `http://localhost:3000`:

- **Kiến trúc Backend (`api_server.py`, `run_react_app.py`, `services/`, `utils/`):**
  - FastAPI với hơn 50 REST endpoints kết nối trực tiếp cơ sở dữ liệu SQLite 24 bảng (`database/ecologix.db`, `database/models.py`, `database/seed.py`).
  - Đăng nhập/đăng ký với băm mật khẩu PBKDF2 (`utils/helpers.py`), tạo OTP xác thực & token đặt lại mật khẩu mô phỏng (`services/auth_service.py`).
  - Dự báo nhu cầu bằng **`lightgbm.LGBMRegressor`** trên chuỗi thời gian 60 ngày + đơn hàng thực tế (`services/forecasting_service.py`).
  - Tối ưu tuyến đường CVRPTW bằng Nearest Neighbor + **2-Opt Local Search** có kiểm tra tải trọng & khung giờ cấm tải `config.RESTRICTED_TIME_WINDOW` (`services/routing_service.py`), hỗ trợ cả đơn hàng DB và bộ 100 điểm TP.HCM – Bình Dương – Đồng Nai (`data/delivery_points_100.json`).
  - Hệ 6 Agents (`agents/`: `supervisor`, `demand`, `inventory`, `route`, `finance`, `esg`) truy vấn SQLite kèm Reasoning Trace và tùy chọn gọi Gemini REST API (`gemini-2.0-flash`).
  - Xuất báo cáo **PDF UTF-8** (ReportLab) và **Excel đa sheet** (OpenPyXL) qua `utils/exporters.py`.
  - Trạm cấu hình **Live-Code** ghi trực tiếp xuống `config.py` và đồng bộ bảng `system_settings`.
- **Kiến trúc Frontend (`webapp/`):**
  - Đã tách gọn từ `index.html` thành **2 component dùng chung** (`webapp/components/common.jsx`, `EcoLeafletMap.jsx`) và **16 trang module độc lập** (`webapp/pages/*.jsx`) kèm History URL Routing (`/`, `/login`, `/register`, `/onboarding`, `/dashboard`, `/routing`, ...).
  - Giao diện Landing (`LandingPage.jsx`), Đăng nhập/Đăng ký full màn hình (`LoginPage.jsx`), Popup Onboarding 1 cột giữa màn hình (`OnboardingPage.jsx`), Sidebar & Dashboard đồng bộ phong cách xanh trời – ngọc lục bảo kèm logo trong suốt (`webapp/assets/`), icon đa sắc và hiệu ứng `pointermove` spotlight.
  - Bản đồ Leaflet hỗ trợ 7 chế độ hiển thị (`Chuẩn OSM` có auto-fallback sang `tile.openstreetmap.de`, `Voyager`, `Dark Mode`, `Vệ tinh`, `Stamen Toner`, `Địa hình`, `Tối giản`).

---

## PHẦN 2. CÁC HẠNG MỤC ĐANG THIẾU HOẶC CHƯA HOÀN THIỆN

Qua rà soát trực tiếp mã nguồn hiện tại, dự án còn **6 nhóm lỗ hổng chính** cần bổ sung để hoàn chỉnh 100%:

### 1. Bảo mật API, Session thực tế & Phân quyền RBAC (`P0`)
- **Thiếu xác thực JWT / Session Cookie trên Backend:** Các endpoint trong `api_server.py` chưa có FastAPI dependency (`Depends(get_current_user)`) kiểm tra phiên đăng nhập; một số endpoint đang mặc định `user_id = 1` hoặc `company_id = 1` (ví dụ `api_settings`, `api_ai_chat`, `api_reports`).
- **Chưa ép quyền RBAC ở Backend & Frontend:** `services/auth_service.py` đã có `get_role_permissions()`, nhưng các route nhạy cảm (`/api/settings/live-code`, `/api/settings/rbac/{id}`, `DELETE /api/orders/{id}`, `/api/reports/export/*`) chưa chặn theo role (`Admin`, `Manager`, `Dispatcher`, `Auditor`), và UI React chưa ẩn/khóa nút tương ứng khi đăng nhập bằng vai trò `Dispatcher` hoặc `Auditor`.
- **Fallback Demo Auth quá mở:** Trong `webapp/pages/App.jsx`, nếu `localStorage.getItem('ecologix_user')` trống khi vào `/dashboard` hoặc `/settings`, ứng dụng đang tự fallback sang user demo `Nguyễn Văn A` thay vì yêu cầu đăng nhập (cần bật/tắt rõ bằng cờ Demo Mode vs Strict Auth Mode).
- **Bảo mật API Key:** `LLM_API_KEY` trong bảng `system_settings` (`api_server.py` dòng 864) đang lưu plaintext thay vì mã hóa hoặc che giá trị.

### 2. Đồng bộ UI/UX & Hoàn thiện CRUD cho 10 trang Workspace còn lại (`P0`–`P1`)
- **Chưa đồng bộ giao diện mới cho toàn bộ module con:** Mới chỉ có `LandingPage`, `LoginPage`, `OnboardingPage`, `App`, và `DashboardPage` dùng card `rounded-3xl border-sky-100`, hiệu ứng `.eco-card-glow` và nút pill gradient. **10 trang còn lại** (`InventoryPage.jsx`, `ForecastingPage.jsx`, `OrdersPage.jsx`, `RoutingPage.jsx`, `VehiclesPage.jsx`, `PartnersPage.jsx`, `AiAssistantPage.jsx`, `ReportsPage.jsx`, `NotificationsPage.jsx`, `SettingsPage.jsx`) vẫn dùng style card vuông `rounded-2xl border-border-light` phẳng cũ.
- **Thiếu Modal Sửa (Edit) dù API đã có hoặc còn khuyết:**
  - `InventoryPage.jsx`: Backend đã có `PUT /api/inventory/products/{product_id}` (`api_server.py` dòng 468), nhưng UI mới chỉ có form **Thêm SKU** và nút **Xóa**, chưa có nút **Sửa SKU**.
  - `VehiclesPage.jsx`: Mới cho phép đổi trạng thái (`Available` / `In Transit` / `Maintenance`) và Xóa, chưa có form sửa tên xe, tải trọng, định mức nhiên liệu.
  - `PartnersPage.jsx`: Cần bổ sung modal chỉnh sửa thông tin Khách hàng (`PUT /api/partners/customers/{id}` đã có ở Backend) và Nhà cung cấp.
- **Thiếu Confirmation Dialogs & Loading States chuẩn:** Các nút **Xóa** (SKU, Đơn hàng, Xe, Khách hàng, NCC) đang gọi thẳng `DELETE` ngay khi bấm mà không có hộp thoại xác nhận; trạng thái tải dữ liệu mới chỉ là dòng chữ `⏳ Đang tải...` chưa có skeleton UI.
- **Kiểm tra điều hướng phụ trên `AiAssistantPage.jsx`:** `agents/supervisor_agent.py` trả về `target_page = "route_planner"` ở nhánh tuyến đường (đã được map sang `'routing'` trong `AiAssistantPage.jsx` dòng 63, nên chuẩn hóa đồng nhất thành `'routing'` ngay tại Backend).

### 3. Nâng cấp AI / ML, Bản đồ GIS & Thuật toán Tối ưu (`P1`)
- **OR-Tools & Prophet (tương thích Python 3.11 / 3.12):** Trên môi trường Windows hiện tại dùng Python 3.15 chưa có wheel cho `ortools` và `prophet`. Nếu triển khai thực tế / Docker trên Python 3.11–3.12, cần tích hợp solver **Google OR-Tools (`ortools.constraint_solver`)** làm tùy chọn song song với engine 2-Opt nội bộ và hỗ trợ **Prophet** so sánh MAPE với LightGBM.
- **Dữ liệu huấn luyện LightGBM (`services/forecasting_service.py`):** `_build_daily_history()` đang trộn đơn hàng SQLite với baseline ngẫu nhiên có seed cố định (`np.random.default_rng`). Cần thêm chức năng **tải lên file CSV/Excel lịch sử bán hàng thực tế** của doanh nghiệp và lưu model đã train (`.txt` / `.pkl`) thay vì fit lại từ đầu mỗi request `GET /api/forecast`.
- **Multi-Agent Tool Calling thực thụ (`agents/supervisor_agent.py`):** Hiện Supervisor định tuyến bằng từ khóa `if any(k in q for k in [...])` và chỉ gọi Gemini để viết lại văn phong. Cần nâng cấp sang **Function Calling / Tool Use** (LangChain hoặc Gemini `tools`) để Agent tự chọn và kết hợp nhiều truy vấn SQL/VRP cho câu hỏi phức hợp.
- **Vẽ tuyến đường bám mặt đường thực tế trên Bản đồ:** Hiện `EcoLeafletMap.jsx` nối các điểm dừng bằng `L.polyline` đường thẳng chim bay. Cần tích hợp OSRM public API (hoặc fallback về đường thẳng khi offline) để hiển thị tuyến đi theo đúng đường phố thực tế, kèm nút hoạt ảnh xe chạy mô phỏng và tự động tìm tọa độ (Geocoding Nominatim) khi thêm khách hàng/kho mới.

### 4. Nghiệp vụ SaaS & Đa doanh nghiệp (Multi-tenant + PostgreSQL) (`P1`–`P2`)
- **Import hàng loạt (Excel/CSV):** Chưa có luồng Import sản phẩm SKU, Đơn hàng và Danh sách điểm giao hàng từ Excel/CSV (hiện mới chỉ có Export).
- **Chuyển đổi SQLite sang PostgreSQL (`database/connection.py`):** Truy vấn hiện tại viết trực tiếp cú pháp `sqlite3` (`?` placeholder, `PRAGMA`). Để chạy PostgreSQL thật cần trừu tượng hóa qua SQLAlchemy ORM / Core + Alembic migration.
- **Tách dữ liệu theo `company_id` (Multi-tenant):** Nhiều truy vấn trong `services/` và `api_server.py` (ví dụ `ORDER BY id ASC LIMIT 1` lấy công ty đầu tiên) chưa lọc theo `company_id` của user đang đăng nhập.
- **Node/Vite Build Pipeline (tùy chọn nâng cao):** Hiện Frontend chạy qua `@babel/standalone@8.1.1` + Tailwind Play CDN trực tiếp trên trình duyệt (tiện không cần Node.js, nhưng tải CDN mỗi lần mở trang và không có tree-shaking/bundle minify).

### 5. Kiểm thử Tự động (Automated Testing) & Kiểm định Trình duyệt (`P0`)
- **Chưa có thư mục `tests/` (`pytest`):** Chưa có bộ unit test và API integration test tự động kiểm tra auth, inventory stock invariants (nhập/xuất/chuyển kho không âm), VRP capacity constraints, LightGBM forecast output và export PDF/XLSX.
- **Chưa hoàn tất kiểm thử giao diện trực quan trên Chrome:** Phiên làm việc trước chưa kết nối được `chrome_devtools` MCP, nên cần chạy kiểm thử E2E bằng Playwright/Chrome thực tế cho toàn bộ luồng Landing -> Popup Bắt đầu -> Login -> Dashboard -> Routing Map -> Reports trên cả Desktop và Mobile.

### 6. Dọn dẹp Repository & Tài liệu (`P0`)
- **Cập nhật `README.md`:** Hiện `README.md` dòng 41 vẫn mô tả `webapp/index.html` là SPA 1 file, chưa cập nhật sơ đồ `webapp/components/*.jsx`, `webapp/pages/*.jsx`, `webapp/assets/` và danh sách đường dẫn URL (`/login`, `/register`, `/onboarding`, `/dashboard`, ...).
- **Rà soát tài liệu/thư mục phụ:** Đóng hoặc dọn các tham chiếu cũ tới file Streamlit đã xóa (`app.py`, `pages/landing.py`) nếu không sử dụng, và kiểm tra xem thư mục `ui-ux-pro-max-skill/` có cần giữ lại trong bản nộp cuối cùng hay tách riêng.

---

## PHẦN 3. LỘ TRÌNH HOÀN THIỆN CHI TIẾT (EXECUTION PLAN)

### Giai đoạn 1 — Đồng bộ Giao diện & Trải nghiệm Người dùng (Ưu tiên P0 | 1–2 ngày)
Mục tiêu: Toàn bộ 16 màn hình trong ứng dụng có giao diện đồng bộ 100%, không còn thao tác thiếu nút Sửa hay xóa nhầm.

- [ ] **1.1. Đồng bộ style `index` + `.eco-card-glow` cho 10 trang Workspace còn lại:**
  - Cập nhật `InventoryPage.jsx`, `ForecastingPage.jsx`, `OrdersPage.jsx`, `RoutingPage.jsx`, `VehiclesPage.jsx`, `PartnersPage.jsx`, `AiAssistantPage.jsx`, `ReportsPage.jsx`, `NotificationsPage.jsx`, `SettingsPage.jsx` dùng card `rounded-3xl border-sky-100 eco-card-glow`, tab pills đồng bộ, nút CTA gradient `rounded-full`.
- [ ] **1.2. Bổ sung Modal Sửa (Edit) cho các danh mục chính:**
  - `InventoryPage.jsx`: Nối nút **Sửa** vào API `PUT /api/inventory/products/{product_id}` đã có sẵn.
  - `VehiclesPage.jsx`: Bổ sung form/modal sửa thông tin xe (tải trọng, mức tiêu thụ L/100km, chi phí/km) gọi `PUT /api/vehicles/{vehicle_id}`.
  - `PartnersPage.jsx`: Bổ sung form/modal sửa Khách hàng (`PUT /api/partners/customers/{id}`) và endpoint + UI sửa Nhà cung cấp.
- [ ] **1.3. Thêm `ConfirmModal` & `LoadingSkeleton` vào `webapp/components/common.jsx`:**
  - Tạo component xác nhận dùng chung trước mọi thao tác `DELETE` (đơn hàng, SKU, xe, khách hàng, NCC).
  - Tạo component khung chờ skeleton mượt thay cho chữ `Đang tải...`.
- [ ] **1.4. Chuẩn hóa action của Agent:**
  - Sửa `target_page` trong `agents/supervisor_agent.py` dòng 83 từ `"route_planner"` thành `"routing"` để đồng bộ hoàn toàn với `App.jsx`.

**Tiêu chí hoàn thành Giai đoạn 1:** Mọi thao tác Thêm / Xem / Sửa / Xóa trên 100% các trang đều có giao diện đồng bộ với `index`, có hộp thoại xác nhận khi xóa và không có nút chết.

---

### Giai đoạn 2 — Bảo mật Backend, Session & Phân quyền RBAC Thực tế (Ưu tiên P0 | 1–2 ngày)
Mục tiêu: Đảm bảo an toàn xác thực, phân quyền đúng theo 4 vai trò (`Admin`, `Manager`, `Dispatcher`, `Auditor`) khi trình bày trước Hội đồng kỹ thuật.

- [ ] **2.1. JWT / Signed Session Token (`services/auth_service.py`, `api_server.py`):**
  - Sinh JWT access token (hoặc `itsdangerous` signed token) khi `/api/auth/login` thành công; đính kèm qua `Authorization: Bearer` trong `apiFetch()` (`webapp/components/common.jsx`) hoặc HTTPOnly Cookie.
  - Viết dependency `get_current_user` và `require_roles([...])` gắn vào các route API nghiệp vụ.
- [ ] **2.2. Áp dụng RBAC ở cả API & UI (`App.jsx`, `SettingsPage.jsx`, `ReportsPage.jsx`):**
  - `Admin` / `Manager`: toàn quyền (Live-Code `config.py`, RBAC, Báo cáo tài chính, CRUD).
  - `Dispatcher`: thao tác Đơn hàng, Đội xe, Kho & Tối ưu lộ trình; khóa/ẩn mục chỉnh sửa Live-Code & RBAC.
  - `Auditor`: chỉ xem Dashboard, Báo cáo Tài chính & ESG, Nhật ký kiểm toán (read-only).
- [ ] **2.3. Chế độ Strict Auth vs Quick Demo Switcher:**
  - Thêm cấu hình rõ ràng trong `.env` / `config.py` (`STRICT_AUTH = False` cho demo chấm thi nhanh, `True` cho triển khai doanh nghiệp thực tế).
- [ ] **2.4. Bảo vệ `LLM_API_KEY`:**
  - Che giá trị key khi trả về `/api/settings` (chỉ trả `has_api_key: true`) và đọc ưu tiên từ biến môi trường `.env` nếu có.

**Tiêu chí hoàn thành Giai đoạn 2:** Gọi endpoint `/api/settings/rbac/*` hoặc `/api/settings/live-code` bằng user `Dispatcher` hoặc chưa đăng nhập khi bật `STRICT_AUTH=True` phải trả `401`/`403` đúng chuẩn.

---

### Giai đoạn 3 — Nâng cấp Thuật toán AI, Bản đồ & Dữ liệu Thật (Ưu tiên P1 | 2–3 ngày)
Mục tiêu: Nâng độ sâu kỹ thuật AI/Economics lên mức thuyết phục cao nhất cho vòng Chung kết.

- [ ] **3.1. Nhập dữ liệu thực tế & Lưu Model LightGBM (`services/forecasting_service.py`):**
  - Bổ sung endpoint `POST /api/forecast/import-history` (nhận CSV/Excel chuỗi bán hàng theo ngày/SKU) và UI upload trong `ForecastingPage.jsx`.
  - Lưu mô hình LightGBM đã huấn luyện kèm chỉ số `RMSE`, `MAE`, `MAPE` vào cache để phản hồi nhanh.
- [ ] **3.2. Google OR-Tools CVRPTW & OSRM Road Routing (`services/routing_service.py`, `EcoLeafletMap.jsx`):**
  - Bổ sung lớp wrapper `solve_vrp_ortools()` tự động kích hoạt khi chạy trong môi trường Python 3.11/3.12 có cài `ortools` (fallback tự động sang Nearest Neighbor + 2-Opt khi không có `ortools`).
  - Tùy chọn gọi OSRM (`router.project-osrm.org`) để vẽ đường giao hàng bám theo đường phố thật trên Leaflet (fallback về đường thẳng nếu mất mạng).
  - Thêm nút **Mô phỏng xe chạy (Animated Truck Marker)** trên bản đồ ở `RoutingPage.jsx`.
- [ ] **3.3. Nâng cấp Multi-Agent Function Calling (`agents/supervisor_agent.py`):**
  - Khi người dùng cấu hình Gemini API Key, sử dụng Gemini Tool Calling / JSON Schema gắn trực tiếp với 5 hàm Python của 5 Specialist Agents (`run_inventory_agent`, `run_demand_agent`, `run_route_agent`, `run_finance_agent`, `run_esg_agent`) để trả lời linh hoạt mọi câu hỏi phức hợp thay vì chỉ rẽ nhánh từ khóa cứng.

**Tiêu chí hoàn thành Giai đoạn 3:** Hệ thống nhận được file CSV bán hàng thật, tối ưu tuyến đường bám đường phố trên bản đồ, và trả lời được các câu hỏi nối nhiều nghiệp vụ (ví dụ *"Nếu giá xăng tăng lên 27.000đ và phải giao 8 đơn ở Bình Dương thì chọn xe nào, chi phí tăng bao nhiêu?"*).

---

### Giai đoạn 4 — Kiểm thử Tự động (Pytest + Playwright E2E) & Dọn dẹp Repo (Ưu tiên P0 | 1–2 ngày)
Mục tiêu: Không còn lỗi ẩn khi demo trực tiếp hoặc đổi tham số Live-Code.

- [ ] **4.1. Bộ Unit & API Tests (`tests/`):**
  - `tests/test_auth.py`: Đăng ký, OTP verify, Login đúng/sai, RBAC permissions.
  - `tests/test_inventory_orders.py`: Nhập/Xuất/Chuyển kho, ngăn tồn âm, Tạo đơn trừ kho tự động.
  - `tests/test_ai_vrp.py`: LightGBM forecast 7/30/90 ngày, 2-Opt route distance `<=` baseline, kiểm tra né khung giờ cấm tải `16:00-18:00`, xuất PDF & Excel trả về file hợp lệ (`%PDF`, `PK`).
  - `tests/test_api_endpoints.py`: `TestClient(app)` kiểm tra 200 OK toàn bộ route SPA + REST API.
- [ ] **4.2. Kiểm thử E2E Trình duyệt thật (Chrome / Playwright):**
  - Kiểm tra hiển thị thực tế 0 lỗi console trên `http://localhost:3000`: Landing Page, 4 thẻ Tính năng -> Showcase, Popup Bắt đầu ngay, Login full màn hình, Sidebar icons & spotlight, 7 chế độ bản đồ Leaflet, CRUD và Export.
- [ ] **4.3. Cập nhật Tài liệu & Vệ sinh Workspace:**
  - Cập nhật `README.md` phản ánh đúng cấu trúc `webapp/components/*.jsx`, `webapp/pages/*.jsx`, `webapp/assets/` và danh sách đường dẫn URL.
  - Kiểm tra và dọn bỏ các file/thư mục không sử dụng trong bản nộp (`ui-ux-pro-max-skill/` nếu chỉ phục vụ thiết kế tham khảo).

---

### Giai đoạn 5 — Đóng gói Docker, PostgreSQL & Diễn tập 15 Phút Live-Code (Ưu tiên P1–P2 | 1–2 ngày)
Mục tiêu: Sẵn sàng chạy trên mọi máy chấm thi / server cloud và ứng biến trơn tru thử thách 15 phút Live-Code.

- [ ] **5.1. Đóng gói Docker (`Dockerfile`, `docker-compose.yml`, `.env.example`):**
  - Dùng base image `python:3.11-slim` để cài đặt được trọn bộ **`ortools`** + **`prophet`** + **`lightgbm`** cùng dịch vụ **PostgreSQL**.
  - Cung cấp lớp adapter trong `database/connection.py` (hỗ trợ cả `sqlite3` chạy Demo nhanh lẫn `PostgreSQL` qua biến `DATABASE_URL`).
- [ ] **5.2. Kịch bản Đảm bảo An toàn cho Phần thi 15 Phút Live-Code:**
  - Chuẩn bị script `scripts/reset_demo_db.py` (tạo lại `ecologix.db` sạch trong 1 giây nếu thao tác thử nghiệm làm lệch dữ liệu).
  - Kiểm tra sẵn bộ câu hỏi kiểm thử độ nhạy kinh tế: thay đổi **Giá xăng (23,500 -> 28,000)**, **Thuế Carbon (500 -> 1,200)**, **Giờ cấm tải (16:00–18:00 -> 15:30–19:00)** và đối chiếu ngay biến động trên Dashboard, Route Planner, Reports và Trợ lý AI.

---

## PHẦN 4. TỔNG HỢP ƯU TIÊN HÀNH ĐỘNG NGAY

1. **Làm ngay trước tiên (P0):**
   - Đồng bộ style `index` + nút **Sửa (Edit)** + **Confirm Dialog** cho 10 trang Workspace còn lại.
   - Bổ sung **JWT/Session + RBAC kiểm tra thật ở `api_server.py`**.
   - Viết bộ **`pytest` (`tests/`)** + chạy **kiểm thử trực tiếp trên Chrome** toàn bộ các luồng chính.
   - Cập nhật lại `README.md` cho khớp cấu trúc modular mới.
2. **Nâng điểm kỹ thuật (P1):**
   - Upload CSV/Excel dữ liệu bán hàng thật cho LightGBM + vẽ đường bám phố OSRM + Gemini Function Calling.
3. **Mở rộng triển khai (P2):**
   - Docker Python 3.11 (`ortools` + `prophet`) + PostgreSQL (`DATABASE_URL`).

