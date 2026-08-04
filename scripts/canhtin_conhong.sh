#!/bin/bash
# Canh tin Vĩnh Long còn sống không? — dùng khi hộp thư im lặng lâu.
#
# Vì sao cần: Chain chốt 04/08 BỎ thư nhịp tim hàng tuần (chỉ gửi thư khi có tin mới).
# Mất thư nhịp tim thì im lặng có hai nghĩa — chưa có tin, hay script đã chết. Lệnh này
# trả lời câu đó mà không cần thư định kỳ nào.
S=~/.local/state/canhtin-vinhlong/lastrun.txt
printf 'timer: '; systemctl --user is-active canhtin-vinhlong.timer
printf 'mốc kế tiếp: '; systemctl --user list-timers canhtin-vinhlong.timer --no-pager | sed -n 2p | cut -c1-28
if [ ! -f "$S" ]; then echo "❌ CHƯA CHẠY LẦN NÀO"; exit 1; fi
now=$(date +%s); last=$(cut -d. -f1 < "$S"); phut=$(( (now - last) / 60 ))
echo "chạy xong lần cuối: $(date -d "@$last" '+%H:%M %d/%m') — cách đây $phut phút"
echo "đã theo dõi: $(wc -l < ~/.local/state/canhtin-vinhlong/seen.txt) tin"
# Mốc 30 phút + RandomizedDelaySec 120s ⇒ quá 90 phút là bất thường thật, không phải trễ nhịp.
if [ "$phut" -gt 90 ]; then echo "🔴 BẤT THƯỜNG — quá 90 phút không chạy"; exit 1; fi
echo "✅ BÌNH THƯỜNG"
