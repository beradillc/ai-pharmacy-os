#!/bin/bash
# Đẩy vào kho bare xong thì cập nhật luôn bản làm việc /srv/vault/Vault.
#
# Vì sao cần: 05/08 phát hiện `GD-DieuPhoi-GiaoViec.md` trên server lệch bản Mint —
# vì đẩy vào bare repo KHÔNG tự động cập nhật bản làm việc. Không có hook này thì
# mỗi lần đẩy là bản làm việc tụt lại một commit, im lặng, cho tới lúc ai đó so
# checksum mới biết.
#
# Dùng --ff-only CÓ CHỦ Ý: sau khi Chain làm việc trực tiếp trên server, bản làm
# việc có thể có thay đổi riêng. Ép checkout sẽ XOÁ TRẮNG việc đó. Thà để pull
# thất bại và báo lỗi còn hơn nuốt mất việc của người ta.
unset GIT_DIR GIT_WORK_TREE
CAY=/srv/vault/Vault
if git -C "$CAY" pull --ff-only origin master 2>&1 | sed 's/^/  [bản làm việc] /'; then
  echo "  ✅ bản làm việc đã lên $(git -C "$CAY" log -1 --format=%h)"
else
  echo "  ⚠️  KHÔNG cập nhật được bản làm việc — có thay đổi cục bộ chưa commit?"
  echo "     Vào /srv/vault/Vault xử lý tay, kho bare vẫn đã nhận đủ."
fi
