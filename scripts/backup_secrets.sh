#!/usr/bin/env bash
# Sao lưu .env.prod (khoá mã hoá at-rest) TÁCH RIÊNG khỏi bản dump CSDL — đúng quy
# tắc B.2 docs/18: "Sao lưu khoá TÁCH RIÊNG khỏi bản dump CSDL. Để chung một chỗ thì
# mất một lần là mất cả hai."
set -Eeuo pipefail
SRC="${SRC:-$HOME/ai-pharmacy-os/.env.prod}"
DEST_DIR="${DEST_DIR:-$HOME/pharmacy_secrets_backup}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
STAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$DEST_DIR"
chmod 700 "$DEST_DIR"
cp "$SRC" "$DEST_DIR/env_prod_$STAMP.bak"
chmod 600 "$DEST_DIR/env_prod_$STAMP.bak"

find "$DEST_DIR" -name 'env_prod_*.bak' -mtime "+$RETENTION_DAYS" -delete
echo "$(date -Is) sao lưu bí mật: $DEST_DIR/env_prod_$STAMP.bak"
