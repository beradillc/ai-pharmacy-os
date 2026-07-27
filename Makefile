# AI Pharmacy OS — developer shortcuts.
#
# PHẠM VI CỔNG (sửa 2026-07-26 theo audit F-1 — đọc trước khi đổi lại):
# lint và test chạy từ GỐC REPO, không phải từ backend/. Trước đây chạy từ backend/
# nên cổng bỏ sót demo_preview.py (audit A-08) và toàn bộ 16 test của
# plugins/payment_vnpay/ — GỒM test thuật toán ký tiền (audit P0-03). Đừng thu hẹp lại.
#
# HẠ TẦNG BẮT BUỘC (từ 2026-07-27, F-4): `test` và `check` nay CẦN Postgres chạy
# (`make up`). tests/concurrency/ FAIL chứ không SKIP khi thiếu Postgres — skip lặng
# rồi báo xanh đúng là bệnh "niềm tin giả" mà đợt kiểm toán đang sửa. Đây là cái giá
# đã biết của lựa chọn đó, không phải lỗi. Chi tiết: backend/tests/concurrency/README.md
.PHONY: help install lint typecheck contracts test test-concurrency check hooks up down migrate seed serve

help:
	@echo "install    - install backend with dev extras into current venv"
	@echo "hooks      - cài pre-commit hook (BẮT BUỘC làm 1 lần sau khi clone)"
	@echo "lint       - ruff check + format check (TOÀN REPO, không chỉ backend/)"
	@echo "typecheck  - mypy (pharmacy_os + seeds)"
	@echo "contracts  - import-linter dependency rules"
	@echo "test       - pytest backend + pytest plugins/payment_vnpay  (CẦN 'make up')"
	@echo "test-concurrency - chỉ test đua trên Postgres thật (~6s). xfail = BUG CHƯA VÁ"
	@echo "check      - lint + contracts + typecheck + test  (~9 phút, pytest chiếm ~536s)"
	@echo "up/down    - start/stop postgres+redis (docker compose)"
	@echo "migrate    - alembic upgrade head"
	@echo "serve      - run FastAPI dev server"

install:
	cd backend && pip install -e ".[dev]"

# Cài hook vào core.hooksPath. Phải chạy tay 1 lần: core.hooksPath là cấu hình
# CỤC BỘ, không đi theo git clone. Đây chính là bài học audit C-03 — .github/workflows/ci.yml
# nằm sẵn trong repo từ commit đầu tiên và chưa từng chạy lần nào suốt 209 commit,
# vì không ai nối dây cho nó.
hooks:
	git config core.hooksPath scripts/hooks
	@echo "✅ core.hooksPath = scripts/hooks"
	@echo "   Kiểm hook có RĂNG thật (đừng tin dòng trên): xem scripts/hooks/README.md"

lint:
	ruff check . && ruff format --check .

typecheck:
	cd backend && mypy

contracts:
	cd backend && lint-imports

test:
	cd backend && pytest
	cd plugins/payment_vnpay && pytest

# Test đua B-01/B-02/B-04 trên Postgres THẬT. Đọc backend/tests/concurrency/README.md
# trước khi diễn giải kết quả: "3 passed, 7 xfailed" + EXIT=0 KHÔNG có nghĩa là tồn kho
# đã đúng — nó có nghĩa là 7 lỗi đã biết vẫn đang hỏng đúng như dự đoán.
test-concurrency:
	cd backend && pytest tests/concurrency

check: lint contracts typecheck test

up:
	docker compose up -d

down:
	docker compose down

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python -m seeds.run

serve:
	cd backend && uvicorn pharmacy_os.main:app --reload
