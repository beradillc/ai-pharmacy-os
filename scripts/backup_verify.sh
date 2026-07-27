#!/usr/bin/env bash
# Sao lưu Postgres + TỰ KIỂM CHỨNG KHÔI PHỤC + dọn bản cũ — D-OPS-01 (Chain khoá 2026-07-28).
#
# Điều kiện Chain đặt ra và script này thực hiện từng cái:
#   • RPO ≤ 1 giờ            → chạy mỗi giờ (xem §CÀI ĐẶT LỊCH bên dưới)
#   • Giữ 30 ngày            → RETENTION_DAYS=30
#   • Phát hiện + cảnh báo   → mọi nhánh hỏng đều thoát khác 0 và gọi ALERT_CMD
#   • "Backup KHÔNG phải DONE chỉ vì file dump được tạo"
#                            → bước 3 KHÔI PHỤC THẬT vào CSDL tạm rồi đối chiếu
#
# Bước 3 là lý do script này tồn tại. Một file dump có kích thước hợp lý vẫn có thể
# không khôi phục được — và ngày phát hiện ra điều đó không nên là ngày cần tới nó.
# Diễn tập F-16 (2026-07-28, docs/18) đã chứng minh đường khôi phục chạy được; script
# này biến việc đó từ một lần thành mọi lần.
set -Eeuo pipefail

# --- Cấu hình (ghi đè bằng biến môi trường) ---------------------------------
PG_CONTAINER="${PG_CONTAINER:-ai_pharmacy_os-postgres-1}"
PG_USER="${PG_USER:-pharma}"
PG_PASSWORD="${PG_PASSWORD:-pharma}"
PG_DB="${PG_DB:-pharmacy_os}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/pharmacy_backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
VERIFY_DB="${VERIFY_DB:-pharmacy_os_verify_$$}"
ALERT_CMD="${ALERT_CMD:-}"   # vd: 'curl -s -X POST https://... -d @-'

STAMP="$(date +%Y%m%d_%H%M%S)"
DUMP="$BACKUP_DIR/pharmacy_os_$STAMP.sql"
LOG="$BACKUP_DIR/pharmacy_os_$STAMP.log"

psql_in()  { docker exec -i -e PGPASSWORD="$PG_PASSWORD" "$PG_CONTAINER" psql -U "$PG_USER" "$@"; }
psql_run() { docker exec    -e PGPASSWORD="$PG_PASSWORD" "$PG_CONTAINER" psql -U "$PG_USER" "$@"; }

alert() {
  local msg="$1"
  echo "ALERT: $msg" >&2
  [[ -n "$ALERT_CMD" ]] && printf '%s\n' "$msg" | eval "$ALERT_CMD" || true
}

cleanup_verify_db() {
  psql_run -d postgres -q -c "DROP DATABASE IF EXISTS \"$VERIFY_DB\"" >/dev/null 2>&1 || true
}

# Bất kỳ lệnh nào hỏng — kể cả ở giữa chừng — đều phải kêu. Backup hỏng LẶNG LẼ là
# tình huống tệ nhất: người ta vẫn tin mình có đường lùi cho tới đúng lúc cần nó.
on_error() {
  local line=$1
  cleanup_verify_db
  alert "BACKUP THẤT BẠI ($PG_DB) tại dòng $line — xem $LOG"
  exit 1
}
trap 'on_error $LINENO' ERR

mkdir -p "$BACKUP_DIR"
exec > >(tee -a "$LOG") 2>&1
echo "=== $(date -Is) backup $PG_DB ==="

# --- 1. Sao lưu -------------------------------------------------------------
docker exec -e PGPASSWORD="$PG_PASSWORD" "$PG_CONTAINER" pg_dump -U "$PG_USER" "$PG_DB" > "$DUMP"
SIZE=$(stat -c%s "$DUMP")
echo "dump: $DUMP ($SIZE byte)"
if [[ "$SIZE" -lt 1024 ]]; then
  alert "BACKUP NGHI NGỜ ($PG_DB): file dump chỉ $SIZE byte"
  exit 1
fi

# --- 2. Chụp 'sự thật' của bản gốc -----------------------------------------
# Đếm trên chính lúc dump vừa xong. Không tuyệt đối chính xác nếu có ghi xen giữa —
# và đó là chủ đích: sai lệch nhỏ do ghi đồng thời được chấp nhận, còn sai lệch lớn
# (mất bảng, mất index) là thứ cần bắt.
BEFORE=$(psql_run -d "$PG_DB" -tA -c "
  SELECT (SELECT count(*) FROM information_schema.tables WHERE table_schema='public')
      || '|' || (SELECT count(*) FROM pg_indexes WHERE schemaname='public')
      || '|' || (SELECT version_num FROM alembic_version);")
echo "gốc:  $BEFORE"

# --- 3. KHÔI PHỤC THẬT rồi đối chiếu ---------------------------------------
# Đây là chỗ script này khác một dòng `pg_dump` trong crontab.
psql_run -d postgres -q -c "CREATE DATABASE \"$VERIFY_DB\""
# ON_ERROR_STOP=1 bắt buộc: thiếu nó psql chạy tiếp qua lỗi và vẫn trả mã thoát 0
# (bài học từ diễn tập F-16) — ta sẽ có bản khôi phục thiếu dữ liệu kèm dấu "thành công".
psql_in -d "$VERIFY_DB" -v ON_ERROR_STOP=1 -q < "$DUMP"
AFTER=$(psql_run -d "$VERIFY_DB" -tA -c "
  SELECT (SELECT count(*) FROM information_schema.tables WHERE table_schema='public')
      || '|' || (SELECT count(*) FROM pg_indexes WHERE schemaname='public')
      || '|' || (SELECT version_num FROM alembic_version);")
echo "khôi: $AFTER"
cleanup_verify_db

if [[ "$BEFORE" != "$AFTER" ]]; then
  alert "KHÔI PHỤC LỆCH ($PG_DB): gốc [$BEFORE] vs khôi phục [$AFTER] — bản backup KHÔNG dùng được"
  exit 1
fi
echo "✅ khôi phục kiểm chứng ĐẠT"

# --- 4. Dọn bản cũ ----------------------------------------------------------
# Xoá SAU khi bản mới đã kiểm chứng đạt, không phải trước: xoá trước rồi backup hỏng
# là tự tay thu hẹp đường lùi của chính mình.
find "$BACKUP_DIR" -name 'pharmacy_os_*.sql' -mtime "+$RETENTION_DAYS" -print -delete
find "$BACKUP_DIR" -name 'pharmacy_os_*.log' -mtime "+$RETENTION_DAYS" -delete

KEPT=$(find "$BACKUP_DIR" -name 'pharmacy_os_*.sql' | wc -l)
echo "=== XONG · giữ lại $KEPT bản · retention ${RETENTION_DAYS} ngày ==="

# --- CÀI ĐẶT LỊCH (RPO ≤ 1 giờ) ---------------------------------------------
#   crontab -e   →   0 * * * * /duong/dan/scripts/backup_verify.sh
#
# ⚠️ Cron IM LẶNG khi script không chạy được (sai đường dẫn, docker chưa lên, hết đĩa).
# "Không có cảnh báo" khi đó trông giống hệt "backup thành công". Phải có một thứ theo
# dõi NGOÀI cron kiểm rằng bản mới nhất không cũ quá 1 giờ — dead-man's switch. Chưa
# làm, đã ghi thành nợ trong docs/18 §A.5.
