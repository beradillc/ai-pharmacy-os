# Backend image for AI Pharmacy OS.
#
# ⚠️ Build context là **GỐC REPO**, không phải ./backend (sửa 2026-07-28).
#     docker build -f infra/docker/backend.Dockerfile -t pharmacy-os-backend .
#
# Vì sao đổi: `backend/pyproject.toml` khai `readme = "../README.md"`. Với context
# ./backend thì file đó nằm NGOÀI context và `pip install .` chết ở bước sinh metadata:
#     OSError: Readme file does not exist: ../README.md
# Image này nằm trong repo từ Sprint 2 và **chưa từng build được lần nào** — cùng dạng
# với `.github/workflows/ci.yml` mà kiểm toán 2026-07-26 bắt (C-03): hạ tầng viết sẵn
# mà không nối dây thì bằng không. Lần build đầu tiên là 2026-07-28.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# `readme = "../README.md"` trong pyproject được giải tương đối với CHÍNH pyproject
# (ở /app), nên đích đúng là **/README.md**, không phải /app/README.md. Trông lệch chỗ,
# nhưng đó là điều pyproject đang khai — và đổi pyproject sẽ làm hỏng `pip install -e .`
# ở máy dev, nơi README thật sự nằm một cấp trên backend/.
COPY README.md /README.md
COPY backend/pyproject.toml ./pyproject.toml
COPY backend/src ./src
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./alembic.ini
# `seeds/` KHÔNG phải thứ tuỳ chọn: `python -m seeds.bootstrap_tenant` là đường duy nhất
# tạo tenant/tài khoản đầu tiên trên một deployment mới. Thiếu nó thì image dựng lên
# nhưng không ai đăng nhập vào được.
COPY backend/seeds ./seeds

RUN pip install --upgrade pip && pip install .

EXPOSE 8000
CMD ["uvicorn", "pharmacy_os.main:app", "--host", "0.0.0.0", "--port", "8000"]
