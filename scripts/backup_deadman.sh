#!/usr/bin/env bash
# Dead-man's switch cho backup — đóng nợ docs/18 §A.5.
#
# **Vấn đề nó giải.** `backup_verify.sh` cảnh báo rất tốt khi backup CHẠY và HỎNG. Nó
# không nói được gì khi backup **không chạy lần nào**: sai đường dẫn trong crontab,
# docker chưa lên, hết đĩa, máy vừa reboot, cron daemon chết. Trong mọi ca đó
# "không có cảnh báo" trông **giống hệt** "backup thành công" — đúng dạng niềm tin giả
# mà cả đợt kiểm toán 2026-07-26 đang sửa.
#
# **Vì sao phải là script RIÊNG, không thêm vào backup_verify.sh.** Một thứ giám sát
# nằm bên trong thứ nó giám sát thì im lặng cùng lúc với nó. Script này chỉ nhìn **dấu
# vết để lại trên đĩa** và không phụ thuộc gì vào việc `backup_verify.sh` có chạy hay
# không — đó là toàn bộ giá trị của nó.
#
# **Nó kiểm đúng ba điều, theo thứ tự nghiêm trọng giảm dần:**
#   1. Có bản backup nào không?           (chưa từng chạy — tệ nhất, dễ bỏ sót nhất)
#   2. Bản mới nhất có quá cũ không?      (cron đã chết ở đâu đó)
#   3. Bản mới nhất có rỗng bất thường không? (chạy nhưng ra file vô dụng)
#
# **Cách chạy** — trên một lịch KHÁC với lịch backup, tốt nhất là máy khác:
#
#     crontab -e  →  15 * * * * /duong/dan/scripts/backup_deadman.sh
#
# Đặt lệch 15 phút so với `0 * * * *` của backup: chạy cùng phút thì nó sẽ bắt gặp
# đúng lúc bản mới đang được ghi dở.
#
# ⚠️ Giới hạn khai rõ: chạy bằng cron thì **chính nó cũng im lặng được**. Đây là một
# lớp, không phải một đảm bảo. Lớp thật sự đóng lỗ hổng là một dịch vụ NGOÀI máy chủ
# (healthchecks.io, Uptime Kuma…) mà script này ping vào — xem `PING_URL`.
set -Eeuo pipefail

BACKUP_DIR="${BACKUP_DIR:-$HOME/pharmacy_backups}"
MAX_AGE_MINUTES="${MAX_AGE_MINUTES:-90}"   # RPO 1 giờ + 30 phút dung sai
MIN_BYTES="${MIN_BYTES:-10240}"
ALERT_CMD="${ALERT_CMD:-}"                 # vd: 'curl -s -X POST https://... -d @-'
PING_URL="${PING_URL:-}"                   # vd: https://hc-ping.com/<uuid> — ping khi ĐẠT

# Tên biến KHÁC tham số: `local msg="...$msg"` tự tham chiếu chính nó — dưới `set -u`
# vế phải đọc `msg` khi nó vừa thành local và còn rỗng ⇒ script chết với "unbound
# variable" và **cảnh báo mất sạch nội dung**. Mã thoát vẫn là 1, nên nhìn từ ngoài
# trông như đang hoạt động. Bắt được nhờ kỷ luật #14 (chạy thử từng ca hỏng), không
# phải nhờ đọc lại code.
fail() {
  local reason="$1"
  local msg="🔴 BACKUP DEAD-MAN: $reason"
  echo "$msg" >&2
  [ -n "$ALERT_CMD" ] && printf '%s\n' "$msg" | sh -c "$ALERT_CMD" || true
  exit 1
}

[ -d "$BACKUP_DIR" ] || fail "thư mục backup $BACKUP_DIR không tồn tại — backup chưa từng chạy?"

# `find -printf` sắp theo thời gian sửa đổi, không theo tên: tên có dấu thời gian
# nhưng tin vào tên là tin vào thứ script khác ĐẶT, không phải thứ hệ thống tệp GHI.
LATEST="$(find "$BACKUP_DIR" -maxdepth 1 -name 'pharmacy_os_*.sql' -type f -printf '%T@ %p\n' \
  | sort -rn | head -1 | cut -d' ' -f2- || true)"

[ -n "$LATEST" ] || fail "không có bản backup nào trong $BACKUP_DIR"

AGE_MINUTES=$(( ( $(date +%s) - $(stat -c %Y "$LATEST") ) / 60 ))
SIZE=$(stat -c %s "$LATEST")

if [ "$AGE_MINUTES" -gt "$MAX_AGE_MINUTES" ]; then
  fail "bản mới nhất đã $AGE_MINUTES phút tuổi (ngưỡng $MAX_AGE_MINUTES) — $(basename "$LATEST"). Cron có còn chạy không?"
fi

if [ "$SIZE" -lt "$MIN_BYTES" ]; then
  fail "bản mới nhất chỉ $SIZE byte (ngưỡng $MIN_BYTES) — $(basename "$LATEST")"
fi

echo "✅ BACKUP SỐNG: $(basename "$LATEST") · $AGE_MINUTES phút tuổi · $SIZE byte"

# Ping dịch vụ ngoài. Đây là chỗ biến "một cron nữa" thành một dead-man's switch thật:
# dịch vụ bên ngoài cảnh báo khi KHÔNG nhận được ping, nên nó phát hiện được cả trường
# hợp chính script này chết.
[ -n "$PING_URL" ] && curl -fsS -m 10 "$PING_URL" > /dev/null || true
