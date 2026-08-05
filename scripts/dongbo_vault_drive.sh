#!/bin/bash
# Đẩy Vault trên server lên Google Drive, thư mục "vault sever" — NGANG HÀNG với
# thư mục "Vault" mà máy gõ vẫn đẩy lên (Chain chốt 05/08).
#
# Vì sao TÁCH thư mục chứ không ghi chung: hai máy cùng `rclone sync` vào một thư
# mục là hai thằng cùng xoá file của nhau — `sync` xoá mọi thứ ở đích không có ở
# nguồn. Tách ra thì mỗi bên một bản, không đánh nhau, và còn đối chiếu được.
#
# Vì sao KHÔNG đẩy thư mục .git: 37 MB nhưng gồm hàng nghìn file nhỏ, Drive xử lý
# rất chậm và mỗi lượt lại quét lại từ đầu. Thay bằng MỘT file bundle — git bundle
# chứa đủ 100% lịch sử, khôi phục bằng `git clone vault.bundle`. Một file thay vì
# vài nghìn.

set -uo pipefail

RCLONE=~/.local/bin/rclone
NGUON=/srv/vault/Vault
BARE=/srv/vault/vault.git
DICH="beradillc_gdrive:vault sever"
BUNDLE=/srv/vault/vault.bundle
LOG=~/dongbo-vault-drive.log

echo "=== $(date '+%F %T') bắt đầu ==="

# ① Lịch sử → một file bundle, kiểm tính toàn vẹn trước khi đẩy đi.
#    `bundle verify` là cổng thật: bundle hỏng mà vẫn đẩy lên thì ngày cần khôi
#    phục mới biết, tức là đúng lúc không sửa được nữa.
if git -C "$BARE" bundle create "$BUNDLE.tmp" --all >/dev/null 2>&1 \
   && git -C "$BARE" bundle verify "$BUNDLE.tmp" >/dev/null 2>&1; then
    mv -f "$BUNDLE.tmp" "$BUNDLE"
    echo "  ✅ bundle: $(git -C "$BARE" rev-list --count --all) commit · $(du -h "$BUNDLE" | cut -f1)"
else
    rm -f "$BUNDLE.tmp"
    echo "  🔴 BUNDLE HỎNG — không đẩy lịch sử lượt này, file cũ trên Drive giữ nguyên"
fi

# ② File làm việc → Drive. Bỏ .git (đã có bundle) và rác cục bộ.
"$RCLONE" sync "$NGUON" "$DICH" \
    --exclude ".git/**" \
    --exclude ".obsidian/**" \
    --exclude "*.tmp" --exclude "*.swp" --exclude ".DS_Store" \
    --transfers 4 --checkers 8 --fast-list \
    --stats-one-line --stats 1m 2>&1 | sed 's/^/  /'
MA_SYNC=${PIPESTATUS[0]}

# ③ Hồ sơ ngoài Vault (Desktop/Downloads cứu từ máy Mint 05/08) → cùng thư mục.
#    Chúng KHÔNG nằm trong git nên bundle không chứa; không đẩy riêng thì 168 MB
#    hồ sơ công trình chỉ có đúng một bản trên server — hỏng đúng mục đích cứu nó.
if [ -d /srv/vault/ngoai-vault ]; then
    "$RCLONE" sync /srv/vault/ngoai-vault "$DICH/_ngoai-vault" \
        --exclude "*.tmp" --exclude ".DS_Store" \
        --transfers 4 --checkers 8 --fast-list --stats-one-line --stats 1m 2>&1 | sed 's/^/  /'
    MA_NGOAI=${PIPESTATUS[0]}
else
    MA_NGOAI=0
fi

# ④ Bundle → cùng thư mục đó, để khôi phục chỉ cần lấy một chỗ.
"$RCLONE" copy "$BUNDLE" "$DICH/_lichsu/" --stats-one-line 2>&1 | sed 's/^/  /'
MA_BUNDLE=${PIPESTATUS[0]}

if [ "$MA_SYNC" -eq 0 ] && [ "$MA_BUNDLE" -eq 0 ] && [ "$MA_NGOAI" -eq 0 ]; then
    date +%s > /srv/vault/.dongbo_lancuoi
    echo "=== $(date '+%F %T') XONG ==="
    exit 0
fi
# Mã thoát đọc từ PIPESTATUS chứ không phải $? — pipe qua `sed` sẽ nuốt mã của rclone
# và mọi lượt đều báo thành công (kỷ luật #8 của dự án).
echo "=== $(date '+%F %T') LỖI: sync=$MA_SYNC ngoai=$MA_NGOAI bundle=$MA_BUNDLE ==="
exit 1
