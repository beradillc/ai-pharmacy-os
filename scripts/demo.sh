#!/usr/bin/env bash
#
# demo.sh — dựng bản demo AI Pharmacy OS để đưa khách hàng xem, một lệnh.
#
# Dùng: `make demo` (hoặc `scripts/demo.sh`)
#
# Vì sao có tệp này: trước đây muốn có bản chạy được phải nhớ đúng thứ tự bốn
# việc (docker → migrate → seed tham chiếu → seed nhà thuốc) trên đúng một CSDL,
# và mỗi lần quên một bước thì hỏng theo một kiểu khác nhau. Một buổi demo hỏng
# vì thao tác chuẩn bị là buổi demo hỏng vô lý nhất.
#
# CSDL RIÊNG, không dùng chung với CSDL phát triển: demo cần dữ liệu ổn định và
# đẹp, còn CSDL dev thì lẫn đủ thứ rác của quá trình làm việc. Mặc định
# `pharmacy_os_demo`.
#
# 🔴 KHÔNG tự xoá CSDL. Nếu CSDL demo đã có sẵn tenant cùng email, script dừng
# và in ra lệnh xoá để NGƯỜI chạy — xoá dữ liệu là quyết định của người, và
# `DROP DATABASE` cố ý nằm ngoài quyền của công cụ tự động (PROJECT_STATE §7bu).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DEMO_DB="${DEMO_DB:-pharmacy_os_demo}"
DEMO_EMAIL="${DEMO_EMAIL:-demo@bera.vn}"
DEMO_PASSWORD="${DEMO_ADMIN_PASSWORD:-NhaThuocDemo2026}"
DEMO_TENANT="${DEMO_TENANT:-Nhà thuốc Bera Demo}"
DEMO_BRANCH="${DEMO_BRANCH:-Cơ sở 1 — Quận 1}"
DEMO_DAYS="${DEMO_DAYS:-28}"
PG_CONTAINER="${PG_CONTAINER:-ai_pharmacy_os-postgres-1}"
PG_USER="${PG_USER:-pharma}"
PG_PASSWORD="${PG_PASSWORD:-pharma}"

DEMO_URL="postgresql+asyncpg://${PG_USER}:${PG_PASSWORD}@localhost:5432/${DEMO_DB}"

say() { printf '\n\033[1m▶ %s\033[0m\n' "$1"; }

say "1/5 · Postgres + Redis"
docker compose up -d
# Chờ Postgres nhận kết nối THẬT, không chờ theo giây: `docker compose up -d`
# trả về khi container đã chạy, không phải khi CSDL đã sẵn sàng nhận truy vấn.
for _ in $(seq 1 60); do
  if docker exec -e PGPASSWORD="$PG_PASSWORD" "$PG_CONTAINER" \
      psql -U "$PG_USER" -d postgres -c 'SELECT 1' >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

say "2/5 · CSDL demo: ${DEMO_DB}"
if docker exec -e PGPASSWORD="$PG_PASSWORD" "$PG_CONTAINER" \
    psql -U "$PG_USER" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname='${DEMO_DB}'" | grep -q 1; then
  echo "   (đã có — dùng lại)"
else
  docker exec -e PGPASSWORD="$PG_PASSWORD" "$PG_CONTAINER" \
    psql -U "$PG_USER" -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${DEMO_DB}"
fi

if [ ! -f backend/.env ]; then
  echo "❌ Thiếu backend/.env — sao chép từ backend/.env.example rồi điền SECURITY__JWT_SECRET." >&2
  exit 1
fi

export DB__URL="$DEMO_URL"

say "3/5 · Migrate"
(cd backend && ./.venv/bin/alembic upgrade head >/dev/null)
echo "   xong"

say "4/5 · Dữ liệu tham chiếu (ATC, tương tác thuốc, vai trò hệ thống)"
(cd backend && ./.venv/bin/python -m seeds.run 2>&1 | tail -1)

say "5/5 · Nhà thuốc demo"
if ! (cd backend && DEMO_ADMIN_PASSWORD="$DEMO_PASSWORD" ./.venv/bin/python -m seeds.demo_pharmacy \
      --tenant-name "$DEMO_TENANT" --branch-name "$DEMO_BRANCH" \
      --admin-email "$DEMO_EMAIL" --days "$DEMO_DAYS" 2>&1 | grep -vE '\[info|\[warning'); then
  cat >&2 <<EOF

❌ Seed không chạy được. Thường gặp nhất: CSDL demo đã có tenant với email này.
   Dựng lại từ đầu (LỆNH NÀY XOÁ TOÀN BỘ CSDL DEMO — bạn chạy, không phải script):

   docker exec -e PGPASSWORD=${PG_PASSWORD} ${PG_CONTAINER} \\
     psql -U ${PG_USER} -d postgres -c 'DROP DATABASE ${DEMO_DB}'
   make demo
EOF
  exit 1
fi

cat <<EOF

════════════════════════════════════════════════════════════════
  Bản demo đã sẵn sàng.

  Chạy hai tiến trình sau (mỗi cái một cửa sổ):

    DB__URL='${DEMO_URL}' make serve
    cd frontend && npm run dev

  Mở  http://localhost:3000/login
  Đăng nhập  ${DEMO_EMAIL}  /  ${DEMO_PASSWORD}

  Kịch bản 10 phút cho khách: docs/20_DEMO_KHACH_HANG.md
════════════════════════════════════════════════════════════════
EOF
