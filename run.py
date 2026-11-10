"""
EcoLogix AI - Unified Entrypoint (`python run.py`)
Khởi chạy Backend FastAPI (`backend.main:app`) + Frontend SPA (`frontend/`) tại http://localhost:3000.
"""
import os
import sys
import uvicorn


def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "3000"))
    print("=" * 72)
    print("🌱 ECOLOGIX AI - FULL-STACK REACT 18 + FASTAPI + SQLITE APPLICATION")
    print("🏆 Đề án tham dự Cuộc thi AI IN ECONOMICS 2026 (HCM-UTE)")
    print(f"👉 Truy cập ngay tại: http://localhost:{port}")
    print("=" * 72)
    try:
        uvicorn.run("backend.main:app", host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        print("\nĐã dừng máy chủ web.")
        sys.exit(0)


if __name__ == "__main__":
    main()

