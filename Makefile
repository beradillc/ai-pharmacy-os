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
.PHONY: help install lint typecheck contracts test test-concurrency check check-fe hooks up down migrate seed serve demo lan

help:
	@echo "install    - install backend with dev extras into current venv"
	@echo "hooks      - cài pre-commit hook (BẮT BUỘC làm 1 lần sau khi clone)"
	@echo "lint       - ruff check + format check (TOÀN REPO, không chỉ backend/)"
	@echo "typecheck  - mypy (pharmacy_os + seeds)"
	@echo "contracts  - import-linter dependency rules"
	@echo "test       - pytest backend + pytest plugins/payment_vnpay  (CẦN 'make up')"
	@echo "test-concurrency - chỉ test đua trên Postgres thật (~7s, tự alembic upgrade head)"
	@echo "check      - lint + contracts + typecheck + test  (~3 phút; pytest 163s, đo 27/07)"
	@echo "up/down    - start/stop postgres+redis (docker compose)"
	@echo "migrate    - alembic upgrade head"
	@echo "serve      - run FastAPI dev server"
	@echo "demo       - dựng bản demo cho khách (CSDL riêng + dữ liệu nhà thuốc thật)"
	@echo "lan        - chạy FE+API cho điện thoại cùng Wi-Fi test (CSDL không ra LAN)"
	@echo "check-fe   - cổng frontend: lint + typecheck + test + build"

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

# Test đua B-01/B-02/B-04 trên Postgres THẬT (đã vá ở F-5 2026-07-27 — 10 passed,
# 0 xfail). Đọc backend/tests/concurrency/README.md trước khi diễn giải kết quả, và
# giữ nguyên quy tắc: xfail ở thư mục đó = BUG CHƯA VÁ, không phải "test đã xanh".
# 🔴 NỢ F-4 (kiểm toán 26/07 R-7): bộ test chạy trên SQLite, và chênh lệch dialect đã cho
# lọt BỐN lỗi thật tới deployment — `audit_logs.action` varchar(32) · tràn cột varchar hàng
# loạt · migration 0045 thiếu `server_default` (1439 test SQLite xanh hết) · `FOR UPDATE SKIP
# LOCKED` bị SQLite NUỐT IM LẶNG ở đúng hai chỗ cần khoá hàng.
#
# Hai nền, một bộ test: SQLite cho vòng lặp nhanh (`make test`), Postgres cho lượt trước khi
# đóng mục. Cần `docker compose up -d postgres` và CSDL `beras_test`.
test-pg:
	docker exec -e PGPASSWORD=pharma ai_pharmacy_os-postgres-1 psql -U pharma -d postgres \
	  -c "DROP DATABASE IF EXISTS beras_test" -c "CREATE DATABASE beras_test" >/dev/null
	cd backend && TEST_DB_URL=postgresql://pharma:pharma@localhost:5432/beras_test \
	  ./.venv/bin/python -m pytest tests -q

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

# Dựng bản demo đưa khách xem: CSDL RIÊNG (pharmacy_os_demo), migrate, seed tham
# chiếu, rồi seed một nhà thuốc có 36 thuốc / 28 ngày lịch sử bán. Không đụng CSDL
# phát triển, và KHÔNG tự xoá gì — xem đầu scripts/demo.sh.
demo:
	./scripts/demo.sh

# Chế độ LAN development: FE + API bind 0.0.0.0 để điện thoại cùng Wi-Fi vào được;
# Postgres/Redis vẫn chỉ loopback; dev-auth TẮT (nếu không, mọi máy trong mạng có
# toàn quyền mà không cần mật khẩu). Xem đầu scripts/lan-dev.sh.
lan:
	./scripts/lan-dev.sh

# Cổng frontend. Từ 2026-07-29 có `test` THẬT (vitest) — trước đó cổng FE chỉ là
# lint+tsc+build, và tài liệu phải ghi rõ đó KHÔNG phải "có test phủ".
# Ranh giới tầng components/* ⇄ features/* nay do eslint cưỡng chế, không còn nằm
# trong tài liệu (bản frontend của import-linter bên backend).
check-fe:
	cd frontend && npm run lint && npx tsc --noEmit && npm run test && npm run build

# Cổng TRÌNH DUYỆT THẬT (kỷ luật #15). Khác `check-fe` ở đúng một điểm quyết định:
# `check-fe` không mở trình duyệt nào — nó xanh trọn vẹn trong lúc app trắng tinh trên
# điện thoại (29/07). Cổng này chạy Firefox/WebKit thật qua đúng địa chỉ người dùng gõ.
#
# Cần app đang chạy: `make lan` trước.
# Mặc định chỉ nhóm ĐỌC-THUẦN — an toàn cả trên CSDL demo của Chain.
ui-gates:
	./scripts/ui-gates.sh

# Thêm nhóm GHI (bán đơn thật). Hỏi xác nhận trước khi ghi bất cứ gì.
ui-gates-all:
	./scripts/ui-gates.sh --all

# Đóng một mục có ĐỘNG TỚI GIAO DIỆN: bốn cổng + pytest + cổng trình duyệt.
# `make check` một mình KHÔNG đủ cho thay đổi giao diện — nó không mở trình duyệt nào.
check-ui: check check-fe ui-gates
