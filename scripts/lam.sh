#!/bin/bash
# Vào thẳng phiên Claude đang chạy sẵn. Gõ `lam` là làm.
# Chưa có phiên (unit chưa chạy, hoặc vừa kill) thì tạo mới ngay tại đây thay vì
# báo lỗi — người dùng chỉ muốn vào làm, không muốn chẩn đoán systemd.
if tmux has-session -t bera 2>/dev/null; then
  exec tmux attach -t bera
fi
echo "Chưa có phiên sẵn, đang tạo..."
exec tmux new-session -s bera -c /srv/vault/Vault "claude --dangerously-skip-permissions; exec bash -l"
