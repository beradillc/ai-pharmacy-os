#!/usr/bin/env bash
#
# lan-dev.sh — chạy BERAS ở chế độ LAN development: điện thoại/tablet cùng Wi-Fi
# mở được giao diện và gọi được API.
#
# Dùng: `make lan` (hoặc `scripts/lan-dev.sh`) · dừng: Ctrl+C
#
# ─── BA ĐIỀU TỆP NÀY LÀM VÌ LÝ DO BẢO MẬT, KHÔNG PHẢI VÌ TIỆN ─────────────────
#
# ① TẮT `SECURITY__ALLOW_DEV_AUTH`.
#    Máy dev để cờ này BẬT trong `backend/.env`. Khi API chỉ nghe trên
#    `127.0.0.1` thì nó vô hại. Mở ra `0.0.0.0` thì nó thành lỗ hổng lớn nhất
#    của cả hệ thống: `api/deps.py` cho phép request KHÔNG có bearer token tự
#    khai `X-Tenant-Id` / `X-Branch-Id` / `X-User-Id`, và cấp cho nó
#    `_DEV_PERMISSIONS = ALL_PERMISSIONS`. Nghĩa là mọi điện thoại trong nhà —
#    kể cả máy của khách — đọc ghi được MỌI tenant với MỌI quyền, không cần mật
#    khẩu. Chế độ LAN vì vậy chạy bằng đăng nhập THẬT (JWT), không có đường tắt.
#
# ② CSDL KHÔNG ra LAN. `docker-compose.yml` nay bind `127.0.0.1` cho Postgres và
#    Redis. Script kiểm lại bằng `ss` và DỪNG nếu thấy chúng nghe trên 0.0.0.0.
#
# ③ CORS liệt kê ĐÚNG hai nguồn (localhost + LAN IP hiện tại), không `*`.
#
# Không sửa một dòng mã nghiệp vụ nào — toàn bộ khác biệt nằm ở biến môi trường
# lúc khởi chạy.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
PG_CONTAINER="${PG_CONTAINER:-ai_pharmacy_os-postgres-1}"

BOLD=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'; GREEN=$'\033[32m'; YEL=$'\033[33m'; OFF=$'\033[0m'
say()  { printf '\n%s▶ %s%s\n' "$BOLD" "$1" "$OFF"; }
ok()   { printf '   %s✓%s %s\n' "$GREEN" "$OFF" "$1"; }
warn() { printf '   %s!%s %s\n' "$YEL" "$OFF" "$1"; }
die()  { printf '\n%s✗ %s%s\n' "$RED" "$1" "$OFF" >&2; exit 1; }

# ─── 1. Địa chỉ LAN ──────────────────────────────────────────────────────────
say "1/7 · Địa chỉ LAN"
# Lấy IP nguồn của tuyến ra Internet: đúng card mạng đang dùng thật, nên không
# nhầm sang các cầu docker (172.17/172.18/172.19) vốn cũng là "inet scope global".
LAN_IP="$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K[\d.]+' | head -1 || true)"
[ -n "$LAN_IP" ] || die "Không xác định được IPv4 LAN. Máy có đang nối mạng không?"
case "$LAN_IP" in
  127.*) die "Chỉ thấy loopback ($LAN_IP) — chưa nối Wi-Fi/LAN." ;;
esac
IFACE="$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'dev \K\S+' | head -1)"
SUBNET="$(ip -4 route show dev "$IFACE" 2>/dev/null | grep -oP '^\d+\.\d+\.\d+\.\d+/\d+' | head -1)"
ok "LAN IP: ${BOLD}${LAN_IP}${OFF} (card ${IFACE}, dải ${SUBNET:-?})"

# ─── 2. Cổng ─────────────────────────────────────────────────────────────────
say "2/7 · Cổng"
port_owner() { ss -tlnp 2>/dev/null | awk -v p=":$1\$" '$4 ~ p {print $NF; exit}'; }
for p in "$BACKEND_PORT" "$FRONTEND_PORT"; do
  owner="$(port_owner "$p" || true)"
  if [ -n "$owner" ]; then
    warn "cổng $p đang bị chiếm: $owner"
    warn "  → dừng tiến trình đó rồi chạy lại, hoặc đặt BACKEND_PORT/FRONTEND_PORT khác"
    die "Cổng $p không rảnh."
  fi
  ok "cổng $p rảnh"
done

# ─── 3. Hạ tầng + kiểm CSDL KHÔNG ra LAN ─────────────────────────────────────
say "3/7 · Postgres + Redis (chỉ loopback)"
docker compose up -d >/dev/null
for _ in $(seq 1 60); do
  docker exec -e PGPASSWORD=pharma "$PG_CONTAINER" pg_isready -U pharma >/dev/null 2>&1 && break
  sleep 1
done
docker exec -e PGPASSWORD=pharma "$PG_CONTAINER" pg_isready -U pharma >/dev/null 2>&1 \
  || die "Postgres không sẵn sàng."
ok "Postgres sẵn sàng"

# Kiểm bằng `ss` chứ không tin tệp compose: một container còn chạy từ trước khi
# sửa binding vẫn giữ nguyên cổng cũ cho tới khi được dựng lại.
exposed=""
for p in 5432 6379; do
  if ss -tln 2>/dev/null | grep -qE "^\S+\s+\S+\s+\S+\s+(0\.0\.0\.0|\*|\[::\]):$p\b"; then
    exposed="$exposed $p"
  fi
done
if [ -n "$exposed" ]; then
  printf '\n%s✗ CSDL ĐANG MỞ RA LAN — cổng:%s%s\n' "$RED" "$exposed" "$OFF" >&2
  cat >&2 <<EOF
   docker-compose.yml đã bind 127.0.0.1, nhưng container đang chạy được tạo TRƯỚC
   thay đổi đó nên vẫn giữ cổng cũ. Dựng lại rồi chạy lại script:

       docker compose down && docker compose up -d
EOF
  exit 1
fi
ok "5432 + 6379 chỉ nghe loopback — không thiết bị nào trong mạng vào được"

# ─── 4. Tường lửa ────────────────────────────────────────────────────────────
say "4/7 · Tường lửa"
UFW_NOTE=""
if command -v ufw >/dev/null 2>&1 && grep -qi '^ENABLED=yes' /etc/ufw/ufw.conf 2>/dev/null; then
  POLICY="$(grep -oP '^DEFAULT_INPUT_POLICY="\K[A-Z]+' /etc/default/ufw 2>/dev/null || echo '?')"
  warn "UFW đang BẬT, chính sách vào mặc định: $POLICY"
  if [ "$POLICY" = "DROP" ] || [ "$POLICY" = "REJECT" ]; then
    UFW_NOTE="yes"
    cat <<EOF
   ${DIM}Điện thoại sẽ KHÔNG vào được cho tới khi mở đúng 2 cổng. Script KHÔNG tự
   chạy lệnh này — sửa tường lửa là việc của người, và cần sudo:${OFF}

       sudo ufw allow from ${SUBNET:-192.168.1.0/24} to any port ${FRONTEND_PORT} proto tcp comment 'BERAS dev FE'
       sudo ufw allow from ${SUBNET:-192.168.1.0/24} to any port ${BACKEND_PORT} proto tcp comment 'BERAS dev API'

   ${DIM}Giới hạn theo dải mạng nhà, KHÔNG mở cho mọi nguồn. Gỡ khi xong:${OFF}
       sudo ufw delete allow from ${SUBNET:-192.168.1.0/24} to any port ${FRONTEND_PORT} proto tcp
       sudo ufw delete allow from ${SUBNET:-192.168.1.0/24} to any port ${BACKEND_PORT} proto tcp
EOF
  fi
else
  ok "Không thấy UFW bật"
fi

# ─── 5. Backend ──────────────────────────────────────────────────────────────
say "5/7 · Backend (0.0.0.0:${BACKEND_PORT})"
[ -f backend/.env ] || die "Thiếu backend/.env — cp backend/.env.example backend/.env rồi điền SECURITY__JWT_SECRET."
[ -x backend/.venv/bin/uvicorn ] || die "Thiếu backend/.venv. Chạy: cd backend && pip install -e '.[dev]'"

# Biến môi trường ĐÈ .env (pydantic-settings ưu tiên biến môi trường hơn dotenv).
# Không ghi gì vào .env, không đụng mã.
export SECURITY__ALLOW_DEV_AUTH=false
export APP__CORS_ORIGINS="[\"http://localhost:${FRONTEND_PORT}\",\"http://${LAN_IP}:${FRONTEND_PORT}\"]"

( cd backend && exec ./.venv/bin/uvicorn pharmacy_os.main:app \
    --host 0.0.0.0 --port "$BACKEND_PORT" ) &
BACKEND_PID=$!

cleanup() {
  printf '\n%sĐang dừng…%s\n' "$DIM" "$OFF"
  kill "$BACKEND_PID" "${FRONTEND_PID:-}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 60); do
  curl -fsS -o /dev/null "http://127.0.0.1:${BACKEND_PORT}/api/v1/health" 2>/dev/null && break
  kill -0 "$BACKEND_PID" 2>/dev/null || die "Backend thoát khi khởi động — xem log phía trên."
  sleep 1
done
curl -fsS -o /dev/null "http://127.0.0.1:${BACKEND_PORT}/api/v1/health" || die "Backend không trả lời /health."
ok "health: $(curl -fsS "http://127.0.0.1:${BACKEND_PORT}/api/v1/health")"
ok "xác thực: dev-auth ĐÃ TẮT (bắt buộc đăng nhập thật)"

# Kiểm dev-auth thật sự đóng: gọi một endpoint nghiệp vụ KHÔNG kèm token.
code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${BACKEND_PORT}/api/v1/drugs" \
        -H "X-Tenant-Id: 00000000-0000-0000-0000-000000000001")"
[ "$code" = "401" ] || die "Cửa dev-auth CHƯA đóng: GET /drugs không token trả $code (chờ 401)."
ok "gọi API không token + tự khai X-Tenant-Id → 401 (đúng)"

# Kiểm CORS: nguồn LAN được phép, nguồn lạ thì không.
allow_lan="$(curl -s -o /dev/null -D - "http://127.0.0.1:${BACKEND_PORT}/api/v1/health" \
             -H "Origin: http://${LAN_IP}:${FRONTEND_PORT}" | grep -ci 'access-control-allow-origin' || true)"
allow_evil="$(curl -s -o /dev/null -D - "http://127.0.0.1:${BACKEND_PORT}/api/v1/health" \
              -H "Origin: http://evil.example" | grep -ci 'access-control-allow-origin' || true)"
[ "$allow_lan" -ge 1 ] || die "CORS chặn nhầm nguồn LAN http://${LAN_IP}:${FRONTEND_PORT}."
[ "$allow_evil" -eq 0 ] || die "CORS đang cho qua nguồn lạ — kiểm lại APP__CORS_ORIGINS."
ok "CORS: cho http://${LAN_IP}:${FRONTEND_PORT}, chặn nguồn lạ (không dùng \`*\`)"

# ─── 6. Frontend ─────────────────────────────────────────────────────────────
say "6/7 · Frontend (0.0.0.0:${FRONTEND_PORT})"
[ -d frontend/node_modules ] || die "Thiếu frontend/node_modules. Chạy: cd frontend && npm install"

# Điện thoại KHÔNG phân giải được `localhost` của laptop — mặc định
# `http://localhost:8000/api/v1` trong `shared/api/client.ts` sẽ trỏ về chính
# điện thoại. Phải trỏ thẳng LAN IP.
# NEXT_PUBLIC_LAN_ORIGIN đi vào `allowedDevOrigins` của next.config.ts. Thiếu nó,
# Next CHẶN mọi request chéo nguồn tới tài nguyên dev ⇒ React không hydrate ⇒ mọi
# màn trong ứng dụng hiện ra TRẮNG khi mở qua LAN IP (Chain báo 29/07).
( cd frontend && NEXT_PUBLIC_API_BASE_URL="http://${LAN_IP}:${BACKEND_PORT}/api/v1" \
    NEXT_PUBLIC_LAN_ORIGIN="${LAN_IP}" \
    exec npx next dev -H 0.0.0.0 -p "$FRONTEND_PORT" ) &
FRONTEND_PID=$!

for _ in $(seq 1 90); do
  curl -fsS -o /dev/null "http://127.0.0.1:${FRONTEND_PORT}/login" 2>/dev/null && break
  kill -0 "$FRONTEND_PID" 2>/dev/null || die "Frontend thoát khi khởi động."
  sleep 1
done
curl -fsS -o /dev/null "http://127.0.0.1:${FRONTEND_PORT}/login" || die "Frontend không trả lời."
ok "next dev đang phục vụ /login"

# ─── 7. Kiểm từ chính LAN IP (không phải loopback) ───────────────────────────
say "7/7 · Kiểm qua LAN IP — đúng đường điện thoại đi"
api_code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://${LAN_IP}:${BACKEND_PORT}/api/v1/health" || echo 000)"
fe_code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "http://${LAN_IP}:${FRONTEND_PORT}/login" || echo 000)"
[ "$api_code" = "200" ] && ok "http://${LAN_IP}:${BACKEND_PORT}/api/v1/health → 200" \
                        || warn "API qua LAN IP → $api_code"
[ "$fe_code" = "200" ]  && ok "http://${LAN_IP}:${FRONTEND_PORT}/login → 200" \
                        || warn "Frontend qua LAN IP → $fe_code"

# Kiểm URL API mà TRÌNH DUYỆT thật sự nhận, không tin thứ tự ưu tiên biến môi
# trường. `frontend/.env.local` trên máy này chứa `http://localhost:8000/api/v1`;
# theo tài liệu Next thì biến môi trường của tiến trình thắng `.env.local`, nhưng
# "theo tài liệu" là một giả định, và giả định đúng là thứ đã sai ba lần trong
# hai ngày. Ở đây đọc thẳng mã JS đang phục vụ và đối chiếu.
chunks="$(curl -s --max-time 8 "http://${LAN_IP}:${FRONTEND_PORT}/login" \
          | grep -oE '/_next/static/chunks/[^"]+\.js' | sort -u | head -30 || true)"
baked=""
for c in $chunks; do
  hit="$(curl -s --max-time 8 "http://${LAN_IP}:${FRONTEND_PORT}${c}" \
         | grep -oE 'TURBOPACK compile-time value", "http://[^"]+/api/v1' | head -1 || true)"
  [ -n "$hit" ] && baked="${hit##*\", \"}" && break
done
if [ -z "$baked" ]; then
  warn "không đọc được URL API đã nhúng (Turbopack đổi cách sinh mã?) — kiểm tay trên điện thoại"
elif [ "$baked" = "http://${LAN_IP}:${BACKEND_PORT}/api/v1" ]; then
  ok "URL API trình duyệt nhận: ${baked}"
else
  die "Trình duyệt sẽ gọi ${baked} — điện thoại KHÔNG phân giải được địa chỉ đó.
   Nguyên nhân thường gặp: frontend/.env.local đang đè biến. Sửa hoặc xoá dòng
   NEXT_PUBLIC_API_BASE_URL trong tệp đó rồi chạy lại."
fi

cat <<EOF

${BOLD}════════════════════════════════════════════════════════════════${OFF}
  ${BOLD}BERAS đang chạy ở chế độ LAN${OFF}

  Điện thoại/tablet cùng Wi-Fi mở:

        ${BOLD}http://${LAN_IP}:${FRONTEND_PORT}${OFF}

  API cho điện thoại : http://${LAN_IP}:${BACKEND_PORT}/api/v1
  Trên chính laptop  : http://localhost:${FRONTEND_PORT}

  CSDL               : 127.0.0.1:5432 — KHÔNG ra LAN
  Xác thực           : đăng nhập thật (dev-auth đã tắt)
$( [ -n "$UFW_NOTE" ] && printf '  %sTường lửa%s          : UFW đang chặn — chạy 2 lệnh ufw ở mục 4 phía trên\n' "$YEL" "$OFF" )
  Dừng               : Ctrl+C
${BOLD}════════════════════════════════════════════════════════════════${OFF}

EOF

wait
