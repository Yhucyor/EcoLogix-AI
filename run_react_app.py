"""
EcoLogix AI - Khởi Chạy Full-Stack Web Application (FastAPI + React 18 & Tailwind CSS)
Phục vụ giao diện React & REST API nối trực tiếp SQLite, LightGBM, CVRPTW, 6 Agents tại http://localhost:3000
"""
import os
import sys
import uvicorn

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("=" * 72)
    print("🌱 ECOLOGIX AI - FULL-STACK REACT 18 + FASTAPI + SQLITE WEB APPLICATION")
    print("🏆 Đề án tham dự Cuộc thi AI IN ECONOMICS 2026 (HCM-UTE)")
    print("👉 Truy cập ngay tại: http://localhost:3000")
    print("=" * 72)
    try:
        uvicorn.run("api_server:app", host="0.0.0.0", port=3000, log_level="info")
    except KeyboardInterrupt:
        print("\nĐã dừng máy chủ web.")
        sys.exit(0)
