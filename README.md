# EcoLogix AI — Nền Tảng Multi-Agent AI Tối Ưu Chuỗi Cung Ứng & Logistics Xanh Cho SMEs

> **Đề án tham dự Cuộc thi AI IN ECONOMICS 2026**  
> **Đơn vị tổ chức:** Câu lạc bộ Sinh viên Kinh tế (ESCUTE) & Khoa Kinh tế Trường Đại học Sư phạm Kỹ thuật TP.HCM (HCM-UTE).

---

## 🌟 1. Kiến Trúc Full-Stack (FastAPI + React 18 & Tailwind CSS)

Toàn bộ dự án vận hành trên **một máy chủ hợp nhất duy nhất** tại địa chỉ:
👉 **`http://localhost:3000`**

* **Frontend:** React 18 + Tailwind CSS + Leaflet GIS + Chart.js ([`webapp/index.html`](webapp/index.html)) — Giao diện SaaS chuyên nghiệp với đầy đủ 16 phân hệ.
* **Backend API:** FastAPI + Uvicorn ([`api_server.py`](api_server.py)) — Kết nối trực tiếp cơ sở dữ liệu SQLite 24 bảng, mô hình LightGBM, thuật toán CVRPTW, 6 AI Agents và bộ xuất báo cáo PDF/Excel.
* **Cách khởi chạy:**
  ```bash
  python run_react_app.py
  ```

---

## 🧠 2. Các Công Nghệ & Mô Hình Đã Hiện Thực Hóa

1. **Dự báo nhu cầu (`services/forecasting_service.py`):** Huấn luyện **`lightgbm.LGBMRegressor`** trên chuỗi thời gian lịch sử 60 ngày + đơn hàng thực tế (`order_items`), đo MAPE out-of-sample, tính Safety Stock ($Z \times \sigma \times \sqrt{L}$), ROP và phát hành lệnh nhập kho tự động.
2. **Tối ưu lộ trình xanh (`services/routing_service.py`):** Giải thuật Nearest-Neighbor + **2-Opt Local Search** có kiểm tra tải trọng tối đa (`max_load_kg`), tự động né khung giờ cấm tải nội đô TP.HCM (`RESTRICTED_TIME_WINDOW` trong `config.py`), hỗ trợ cả đơn hàng SQLite và bộ **100 điểm TP.HCM & Đồng Nai** (`data/delivery_points_100.json`). *(Ghi chú: do Python 3.15 trên Windows chưa có wheel chính thức cho `ortools`, hệ thống chạy engine CVRPTW nội bộ tương thích đầy đủ).*
3. **Hệ sinh thái 6 AI Agents (`agents/`):** `Supervisor`, `Demand`, `Inventory`, `Route`, `Finance`, `ESG` truy vấn trực tiếp SQLite với chuỗi suy luận minh bạch (Reasoning Trace). Mặc định chạy Demo Engine nội bộ không bịa số liệu, có hỗ trợ cấu hình Gemini API Key trong phần Cài đặt.
4. **Xuất báo cáo thật (`utils/exporters.py`):** Tạo file **PDF chuẩn tiếng Việt UTF-8** (ReportLab + TrueType Arial) và **Excel 3 sheets** (OpenPyXL).

---

## 📁 3. Cấu Trúc Thư Mục Dự Án

```
AIinEco/
├── api_server.py              # FastAPI Unified Backend (~50 endpoints + Static Web)
├── run_react_app.py           # Khởi chạy toàn bộ ứng dụng tại http://localhost:3000
├── config.py                  # Biến cấu hình Live-Code 15 phút Chung kết
├── requirements.txt           # Danh mục thư viện Python
├── generate_dummy_data.py     # Script sinh dữ liệu 100 điểm TP.HCM & Đồng Nai
├── webapp/
│   └── index.html             # React 18 + Tailwind CSS SPA (16 Modules hoàn chỉnh)
├── agents/                    # 6 AI Agents độc lập (supervisor, demand, inventory, route, finance, esg)
├── services/                  # Nghiệp vụ (auth, inventory, order, vehicle, partner, forecasting, routing, financial, carbon, ai)
├── utils/                     # Helpers (PBKDF2 hash, audit log), Validators, Exporters (PDF/XLSX)
├── database/                  # connection.py, models.py (24 bảng), seed.py, ecologix.db
└── data/                      # delivery_points_100.json, delivery_points_100.csv
```
