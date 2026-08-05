#!/bin/bash
# Rà soát toàn bộ tính năng đang chạy trên bera-saas. Gõ `rasoat` là ra bảng.
#
# Vì sao thành lệnh chứ không phải một lượt gõ tay: hai ngày qua có BA thứ hỏng
# im lặng mà mọi dấu hiệu bề mặt đều xanh — `link-demo` in link chết, `Persistent=true`
# bị bỏ qua, múi giờ lệch 11 tiếng. Rà bằng trí nhớ thì lần sau lại sót đúng chỗ đó.
# Kỷ luật #10 của dự án: cưỡng chế bằng máy, không bằng trí nhớ.
#
# Quy ước: ✅ đo được và đạt · 🔴 đo được và HỎNG · ⚠️ KHÔNG đo được (khác với "ổn").

export PATH="$HOME/.local/bin:$PATH"
OK=0; XAU=0; MU=0

d() { # d <nhãn> <trạng thái> <chi tiết>
  case "$2" in
    ok)  printf "  ✅ %-26s %s\n" "$1" "$3"; OK=$((OK+1)) ;;
    xau) printf "  🔴 %-26s %s\n" "$1" "$3"; XAU=$((XAU+1)) ;;
    *)   printf "  ⚠️  %-26s %s\n" "$1" "$3"; MU=$((MU+1)) ;;
  esac
}

echo "════ RÀ SOÁT bera-saas · $(date '+%H:%M %d/%m/%Y') ════"
echo
echo "── MÁY ──"
UP=$(awk '{printf "%.1f", $1/3600}' /proc/uptime)
d "Thời gian chạy" ok "$UP giờ"
RAM=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
[ "$RAM" -ge 250 ] && d "RAM khả dụng" ok "$RAM MB" || d "RAM khả dụng" xau "$RAM MB — dưới ngưỡng 250"
DIA=$(df --output=pcent / | tail -1 | tr -dc 0-9)
[ "$DIA" -lt 85 ] && d "Đĩa /" ok "dùng $DIA%, còn $(df -h --output=avail / | tail -1 | tr -d ' ')" || d "Đĩa /" xau "dùng $DIA%"
DIAH=$(df --output=pcent /home | tail -1 | tr -dc 0-9)
[ "$DIAH" -lt 85 ] && d "Đĩa /home" ok "dùng $DIAH%, còn $(df -h --output=avail /home | tail -1 | tr -d ' ')" || d "Đĩa /home" xau "dùng $DIAH%"
d "Múi giờ" ok "$(timedatectl show -p Timezone --value 2>/dev/null || echo '?')"

echo
echo "── ỨNG DỤNG PHARMACY ──"
N=$(podman ps --format '{{.Names}}' 2>/dev/null | wc -l)
KHOE=$(podman ps --format '{{.Status}}' 2>/dev/null | grep -c healthy)
[ "$N" = 5 ] && [ "$KHOE" = 5 ] && d "Container" ok "5/5 khoẻ" || d "Container" xau "$N container, $KHOE khoẻ (mong đợi 5/5)"
MA=$(curl -s -o /dev/null -w '%{http_code}' -m 10 http://localhost:8080/api/v1/health 2>/dev/null)
[ "$MA" = 200 ] && d "API nội bộ" ok "HTTP 200" || d "API nội bộ" xau "HTTP ${MA:-không nối được}"
U=$(grep -oE 'https://[a-z0-9]+(-[a-z0-9]+)+\.trycloudflare\.com' ~/cloudflared-demo.log 2>/dev/null | grep -v '^https://api\.' | tail -1)
if [ -n "$U" ]; then
  MC=$(curl -s -o /dev/null -w '%{http_code}' -m 20 "$U/api/v1/health" 2>/dev/null)
  [ "$MC" = 200 ] && d "Link demo công khai" ok "$U" || d "Link demo công khai" xau "$U → HTTP ${MC:-hỏng}"
else d "Link demo công khai" mu "chưa có link trong log"; fi
B=$(ls -t ~/pharmacy_backups/*.sql 2>/dev/null | head -1)
if [ -n "$B" ]; then
  G=$(( ($(date +%s) - $(stat -c %Y "$B")) / 3600 ))
  [ "$G" -le 3 ] && d "Backup CSDL" ok "$(basename "$B") — $G giờ tuổi" || d "Backup CSDL" xau "$G giờ tuổi (ngưỡng 3)"
else d "Backup CSDL" xau "KHÔNG có bản backup nào"; fi

echo
echo "── VAULT ──"
if [ -d /srv/vault/vault.git ]; then
  C=$(git -C /srv/vault/vault.git rev-list --count --all 2>/dev/null)
  d "Kho lịch sử (bare)" ok "$C commit · $(df --output=target /srv/vault | tail -1) khác phân vùng PharmaOS"
else d "Kho lịch sử (bare)" xau "KHÔNG thấy /srv/vault/vault.git"; fi
if [ -d /srv/vault/Vault ]; then
  S=$(git -C /srv/vault/Vault status --porcelain 2>/dev/null | wc -l)
  [ "$S" = 0 ] && d "Bản làm việc" ok "$(git -C /srv/vault/Vault log -1 --format=%h), cây sạch" || d "Bản làm việc" mu "có $S thay đổi chưa commit"
else d "Bản làm việc" xau "KHÔNG thấy /srv/vault/Vault"; fi
QT=0; for f in CLAUDE.md 01-WikiHub/BeraLLC/KeToan/CLAUDE.md 01-WikiHub/BeraLLC/PhapLy/CLAUDE.md \
               01-WikiHub/HoSoCongTrinh/CLAUDE.md 04-GiaDinh/CLAUDE.md GD-DieuPhoi-GiaoViec.md; do
  [ -f "/srv/vault/Vault/$f" ] && QT=$((QT+1)); done
[ "$QT" = 6 ] && d "Quy tắc .md" ok "6/6 có đủ (5 vai + sổ điều phối)" || d "Quy tắc .md" xau "chỉ có $QT/6"
if [ -f /srv/vault/vault.bundle ]; then
  git -C /srv/vault/vault.git bundle verify /srv/vault/vault.bundle >/dev/null 2>&1 \
    && d "Bundle lịch sử" ok "$(du -h /srv/vault/vault.bundle | cut -f1), verify đạt" \
    || d "Bundle lịch sử" xau "verify KHÔNG đạt"
else d "Bundle lịch sử" xau "chưa sinh bundle"; fi

echo
echo "── TỰ ĐỘNG ──"
for u in pharmacy-os.service cloudflared-demo.service claude-phien.service ttyd-claude.service \
         canhmay.timer canhtin-vinhlong.timer dongbo-vault-drive.timer; do
  T=$(systemctl --user is-active "$u" 2>/dev/null)
  E=$(systemctl --user is-enabled "$u" 2>/dev/null)
  [ "$T" = active ] && [ "$E" = enabled ] && d "$u" ok "$T · $E" || d "$u" xau "$T · $E"
done
tmux has-session -t bera 2>/dev/null && d "Phiên Claude 'bera'" ok "sẵn sàng — gõ \`lam\` để vào" \
                                     || d "Phiên Claude 'bera'" xau "không có phiên"
CR=$(crontab -l 2>/dev/null | grep -cE '^[0-9*]')
[ "$CR" -ge 3 ] && d "Cron backup" ok "$CR job" || d "Cron backup" xau "chỉ $CR job (mong đợi 3)"

echo
echo "── SAO LƯU NGOÀI MÁY ──"
if [ -f /srv/vault/.dongbo_lancuoi ]; then
  P=$(( ($(date +%s) - $(cat /srv/vault/.dongbo_lancuoi)) / 60 ))
  [ "$P" -le 90 ] && d "Drive 'vault sever'" ok "đồng bộ cách đây $P phút" || d "Drive 'vault sever'" xau "$P phút — quá 90"
else d "Drive 'vault sever'" mu "chưa đồng bộ lần nào"; fi
d "GitHub (Pharmacy)" mu "kiểm bằng: git -C ~/ai-pharmacy-os fetch && git status"

echo
echo "── AN NINH ──"
# Đo bằng HÀNH VI, không bằng sự tồn tại của file: /etc/sudoers.d/ là 0750 root:root
# nên `[ -f ]` chạy dưới user chain luôn thất bại vì THIẾU QUYỀN, không phải vì thiếu
# file — bản đầu của script này báo đỏ nhầm đúng vì lý do đó (05/08).
if sudo -n timedatectl status >/dev/null 2>&1; then
  if sudo -n podman ps >/dev/null 2>&1; then
    d "sudoers NOPASSWD hẹp" xau "podman LỌT qua danh sách — phạm vi đã bị nới"
  else
    d "sudoers NOPASSWD hẹp" ok "lệnh trong danh sách chạy được, podman vẫn bị chặn"
  fi
else
  d "sudoers NOPASSWD hẹp" xau "lệnh trong danh sách KHÔNG chạy được"
fi
# ttyd là SHELL mở qua trình duyệt — phải chắc nó chỉ nghe trên tailnet, không
# nghe 0.0.0.0. Nghe sai chỗ là mở shell ra WiFi cho cả nhà/hàng xóm.
NGHE=$(/usr/sbin/ss -tln 2>/dev/null | grep -c "100\.76\.165\.120:7681")
RONG=$(/usr/sbin/ss -tln 2>/dev/null | grep -cE "(0\.0\.0\.0|\*):7681")
if [ "$RONG" -gt 0 ]; then d "ttyd chỉ trong tailnet" xau "ĐANG NGHE RỘNG — lộ ra ngoài tailnet"
elif [ "$NGHE" -gt 0 ]; then d "ttyd chỉ trong tailnet" ok "chỉ 100.76.165.120:7681"
else d "ttyd chỉ trong tailnet" mu "không thấy cổng 7681 đang nghe"; fi
tailscale status >/dev/null 2>&1 && d "Tailscale" ok "$(tailscale ip -4 2>/dev/null | head -1)" || d "Tailscale" xau "không đọc được"
systemctl is-active --quiet firewalld && d "firewalld" ok "active" || d "firewalld" xau "không chạy"
systemctl is-active --quiet fail2ban && d "fail2ban" ok "active" || d "fail2ban" mu "không chạy"

echo
echo "════ TỔNG: $OK đạt · $XAU hỏng · $MU không đo được ════"
[ "$XAU" -gt 0 ] && exit 1 || exit 0
