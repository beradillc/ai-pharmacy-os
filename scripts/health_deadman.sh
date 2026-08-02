#!/usr/bin/env bash
# Dead-man's switch cho ỨNG DỤNG — đóng nợ F-18b.
#
# **Vấn đề nó giải.** `/metrics` một mình là một tệp không ai đọc. Dự án này chưa có máy
# chủ Prometheus nào, và một endpoint số đo không có bên tiêu thụ thì đúng bằng
# `.github/workflows/ci.yml` — nằm trong repo từ commit đầu, **chưa chạy lần nào** suốt
# 209 commit (kiểm toán C-03). Hạ tầng viết sẵn mà không nối dây thì bằng không.
#
# Script này là bên tiêu thụ, có ngay từ ngày đầu. Nó đọc `/metrics` và hét lên khi:
#   1. Không gọi được         → app CHẾT hoặc mạng đứt (tệ nhất, và im lặng nhất)
#   2. Tỉ lệ 5xx vượt ngưỡng  → app sống nhưng đang hỏng
#   3. Uptime tụt về gần 0    → app vừa KHỞI ĐỘNG LẠI mà không ai ra lệnh (crash loop)
#
# **Ca số 3 là lý do chính script này đáng tồn tại.** Một app crash rồi tự dựng lại 40 giây
# một lần **vẫn trả 200 cho mọi phép kiểm sức khoẻ** — `curl /health` xanh, người dùng thì
# mất đơn hàng đang gõ dở mỗi lần nó chết. Chỉ có uptime tụt mới lộ ra.
#
# **Song sinh với `backup_deadman.sh`, cố ý cùng khuôn:** cùng cách nhận `ALERT_CMD`/
# `PING_URL`, cùng cách trả mã thoát, cùng cách tự khai giới hạn. Hai script, hai thứ được
# canh (dữ liệu đã sao lưu chưa · ứng dụng còn phục vụ không), một cách dùng.
#
# **Cách chạy** — trên một lịch KHÁC lịch của app, tốt nhất là MÁY KHÁC:
#
#     crontab -e  →  */5 * * * * /duong/dan/scripts/health_deadman.sh
#
# ⚠️ Giới hạn khai rõ: chạy bằng cron trên **cùng máy** với app thì máy chết là cả hai cùng
# im. Đây là một lớp, không phải một đảm bảo. Lớp thật sự đóng lỗ hổng là một dịch vụ NGOÀI
# (healthchecks.io, Uptime Kuma…) mà script này ping vào — xem `PING_URL`.
set -Eeuo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
METRICS_TOKEN="${METRICS_TOKEN:-}"
MAX_5XX_PCT="${MAX_5XX_PCT:-5}"        # % request là 5xx thì coi là đang hỏng
MIN_UPTIME_S="${MIN_UPTIME_S:-120}"    # uptime dưới mức này ⇒ nghi vừa khởi động lại
ALERT_CMD="${ALERT_CMD:-}"             # vd: 'curl -s -X POST https://... -d @-'
PING_URL="${PING_URL:-}"               # dịch vụ ngoài; chỉ ping khi MỌI phép kiểm xanh

if [ -z "$METRICS_TOKEN" ]; then
  echo "health_deadman: thiếu METRICS_TOKEN — cùng giá trị APP__METRICS_TOKEN của app." >&2
  exit 2
fi

bao_dong() {
  # In ra stderr LUÔN LUÔN, kể cả khi có ALERT_CMD: cron gửi mail phần stderr, và một cảnh
  # báo chỉ đi vào một cái webhook thì lúc webhook hỏng là lúc không còn gì cả.
  echo "🔴 health_deadman: $*" >&2
  [ -n "$ALERT_CMD" ] && printf '%s\n' "🔴 AI Pharmacy OS: $*" | eval "$ALERT_CMD" || true
}

# `--max-time` bắt buộc: không có nó thì một máy chủ treo (nhận kết nối rồi im) làm chính
# script canh treo theo, và "cron không báo gì" trông y hệt "mọi thứ đều ổn".
if ! SO_DO=$(curl -sS --max-time 10 -H "Authorization: Bearer ${METRICS_TOKEN}" \
       "${BASE_URL}/metrics" 2>&1); then
  bao_dong "KHÔNG gọi được ${BASE_URL}/metrics — app chết hoặc mạng đứt. (${SO_DO})"
  exit 1
fi

doc() { printf '%s\n' "$SO_DO" | awk -v k="$1" '$1==k {print $2; exit}'; }

# Tự kiểm CHÍNH PHÉP ĐO trước khi tin nó (kỷ luật #15/#22): một phản hồi 200 rỗng, hoặc
# trang đăng nhập của một reverse proxy, đều "gọi được" mà không chứa số đo nào — và khi ấy
# mọi phép so phía dưới đều so với chuỗi rỗng, tức luôn xanh một cách vô nghĩa.
if [ "$(doc pharmacy_up)" != "1" ]; then
  bao_dong "Gọi được nhưng KHÔNG đọc ra pharmacy_up=1 — sai địa chỉ, sai token, hoặc có gì đó đứng chắn giữa. Nội dung: $(printf '%s' "$SO_DO" | head -c 200)"
  exit 1
fi

TONG=$(doc pharmacy_requests_total)
LOI=$(printf '%s\n' "$SO_DO" | awk '/^pharmacy_errors_total\{lop="5xx"\}/ {print $2; exit}')
UPTIME=$(doc pharmacy_uptime_seconds)
LOI_PCT=0
[ "${TONG:-0}" -gt 0 ] && LOI_PCT=$(( LOI * 100 / TONG ))

HONG=0
if [ "$LOI_PCT" -ge "$MAX_5XX_PCT" ] && [ "${TONG:-0}" -ge 20 ]; then
  # Ngưỡng 20 request là để một app vừa khởi động, mới phục vụ 3 lần và lỗi 1 lần, không bị
  # báo động vì "33% lỗi" — một tỉ lệ tính trên mẫu quá nhỏ là tin đồn, không phải số đo.
  bao_dong "Tỉ lệ 5xx = ${LOI_PCT}% (${LOI}/${TONG}), ngưỡng ${MAX_5XX_PCT}%."
  HONG=1
fi
if [ "${UPTIME:-0}" -lt "$MIN_UPTIME_S" ]; then
  bao_dong "Uptime chỉ ${UPTIME}s — app vừa khởi động lại. Nếu không ai ra lệnh thì đây là crash loop, và nó KHÔNG làm /health đỏ."
  HONG=1
fi

if [ "$HONG" = 0 ]; then
  echo "✅ health_deadman: up=1 · uptime=${UPTIME}s · ${TONG} request · 5xx=${LOI} (${LOI_PCT}%)"
  # Ping CHỈ khi mọi phép kiểm xanh — đó là toàn bộ ý nghĩa của dead-man's switch: dịch vụ
  # ngoài báo động khi **ngừng nhận được** ping, nên ping trong lúc đang hỏng là tự tay
  # tắt cái chuông duy nhất còn kêu được.
  [ -n "$PING_URL" ] && curl -sS --max-time 10 -o /dev/null "$PING_URL" || true
fi
exit "$HONG"
