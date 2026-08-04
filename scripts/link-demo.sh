#!/bin/bash
# In ra link demo công khai HIỆN TẠI, đã kiểm chứng là còn sống.
#
# Vì sao cần script này: `trycloudflare.com` cấp URL NGẪU NHIÊN và đổi mỗi lần
# cloudflared khởi động lại (unit có Restart=always, nên mạng chập một nhịp là đổi;
# reboot cũng đổi). Không có cách nào ghim URL nếu chưa có tên miền riêng.
#
# Ba lỗi của bản cũ đã sửa (04/08, sau reboot 19:31):
#  1. Regex cũ bắt luôn `api.trycloudflare.com` trong DÒNG BÁO LỖI
#     ("failed to request quick Tunnel: Post https://api.trycloudflare.com/tunnel").
#     Sáng nay tunnel fail 1 lần rồi mới lên — gõ đúng 16 giây đó là ra link rác.
#     → Nay chỉ nhận URL từ dòng banner của cloudflared, và loại thẳng `api.`.
#  2. Log ghi nối tiếp qua nhiều lần boot ⇒ trước khi tunnel mới đăng ký xong,
#     script in ra URL của LẦN BOOT TRƯỚC — đã chết mà nhìn vẫn như thật.
#     → Nay unit xoay log mỗi lần khởi động (ExecStartPre), log chỉ chứa lần này.
#  3. Bản cũ in link rồi mới hỏi thăm sức khoẻ ⇒ vẫn in ra link chết.
#     → Nay CHỜ tới khi link thật sự trả 200 mới in; không sống thì báo hỏng.

LOG=~/cloudflared-demo.log
CHO_TOI_DA=90          # giây — reboot xong cloudflared cần ~15-30s để đăng ký
UNIT=cloudflared-demo.service

lay_url() {
  # Chỉ lấy từ dòng banner cloudflared in ra ("INF |  https://xxx.trycloudflare.com |"),
  # loại bỏ api.trycloudflare.com (điểm cuối API, xuất hiện trong dòng lỗi).
  grep -oE 'https://[a-z0-9]+(-[a-z0-9]+)+\.trycloudflare\.com' "$LOG" 2>/dev/null \
    | grep -v '^https://api\.' | tail -1
}

if ! systemctl --user is-active --quiet "$UNIT"; then
  echo "❌ Đường hầm KHÔNG chạy. Xem: systemctl --user status $UNIT"
  exit 1
fi

t=0
while [ "$t" -lt "$CHO_TOI_DA" ]; do
  u=$(lay_url)
  if [ -n "$u" ]; then
    ma=$(curl -s -m 10 -o /dev/null -w '%{http_code}' "$u/api/v1/health" 2>/dev/null)
    if [ "$ma" = "200" ]; then
      echo "$u/"
      echo "✅ đã kiểm chứng: app trả 200 qua đúng link này"
      exit 0
    fi
  fi
  [ "$t" = 0 ] && echo "⏳ đang chờ đường hầm lên (tối đa ${CHO_TOI_DA}s)..." >&2
  sleep 3
  t=$((t + 3))
done

echo "❌ Sau ${CHO_TOI_DA}s vẫn chưa có link sống."
[ -n "$(lay_url)" ] && echo "   (thấy $(lay_url) nhưng không trả 200)"
echo "   Xem: journalctl --user -u $UNIT  hoặc  tail -30 $LOG"
exit 1
