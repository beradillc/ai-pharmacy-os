#!/usr/bin/env bash
#
# Chạy MỌI cổng trình duyệt bằng một lệnh, in mã thoát tường minh của từng cổng.
#
# 🔴 VÌ SAO CÓ TỆP NÀY. Tuần 29–31/07 có **ba** lỗi mà chỉ cổng trình duyệt bắt được, và
# cả ba lần đều do tôi tự nhớ gõ lệnh:
#   · app TRẮNG TINH trên iPhone trong lúc lint/tsc/test/build đều xanh (29/07)
#   · cột định danh trượt khỏi màn hình ở 5/5 bảng (29/07)
#   · POS không hề gọi endpoint cảnh báo dị ứng — ba lớp test dưới vẫn xanh (31/07)
# Một cổng chỉ chạy khi người ta nhớ thì nó là **thói quen**, không phải cổng. Thói quen
# là thứ hỏng đầu tiên khi phiên sau bận.
#
# Kỷ luật #8: mã thoát đọc được là mã thoát của **chính lệnh đó** — không `| tail`, không
# suy ra từ lệnh cuối trong ống.
#
# HAI NHÓM, cố ý tách:
#
#   ĐỌC-THUẦN  chạy được lên bất kỳ CSDL nào, kể cả `nt650v2` của Chain.
#   GHI        BÁN ĐƠN THẬT / TẠO KHÁCH THẬT. Chỉ chạy lên CSDL dùng-một-lần.
#              Mặc định KHÔNG chạy — chạy nhầm lên CSDL demo là mỗi lần thêm một hoá đơn
#              rác, và không ai nhận ra cho tới lúc đối chiếu doanh thu.
#
# Dùng:
#   cp scripts/ui-gates.env.example scripts/ui-gates.env   # MỘT LẦN — điền tài khoản
#   ./scripts/ui-gates.sh                  # nhóm đọc-thuần (mặc định, an toàn)
#   ./scripts/ui-gates.sh --all            # + nhóm ghi, ĐÒI xác nhận CSDL dùng-một-lần
#   BASE_URL=http://localhost:3000 ./scripts/ui-gates.sh   # ép địa chỉ khác
set -uo pipefail

GOC="$(cd "$(dirname "$0")/.." && pwd)"

# Định nghĩa TRƯỚC mọi lệnh gọi — khối cấu hình bên dưới đã dùng `die`, và một `die` chưa
# tồn tại thì bash báo "command not found" rồi CHẠY TIẾP với cấu hình sai.
say() { printf '\n\033[1m▶ %s\033[0m\n' "$1"; }
die() { printf '\033[31m🔴 %s\033[0m\n' "$1" >&2; exit 2; }

# --- N-4 (02/08): thông tin đăng nhập đọc từ MỘT tệp, không nằm trong mã ------------------
# Trước hôm nay tệp này mặc định về `trinhthu@nhathuoc650.vn` — một tài khoản **không khớp
# CSDL nào đang chạy**. Cổng vẫn "chạy": nó đỏ ở màn login, và log đọc y hệt lỗi sản phẩm.
# Bốn script khác thì ghi cứng mật khẩu THẬT vào mã nguồn, đã vào git.
# Nay: mật khẩu chỉ đến từ `scripts/ui-gates.env` (gitignore), thiếu thì DỪNG có chỉ dẫn.
CAU_HINH="$GOC/scripts/ui-gates.env"
# shellcheck source=/dev/null
[ -f "$CAU_HINH" ] && set -a && . "$CAU_HINH" && set +a

# 🔴 BỐN QUY ƯỚC TÊN BIẾN cùng tồn tại, gom dần qua ba lần vấp:
#   31/07 — `BERAS_EMAIL/BERAS_PASSWORD` (cổng viết trước) ⇄ `EMAIL/PASSWORD` (viết sau);
#   01/08 — `BERAS_BASE` (2 cổng) ⇄ `BASE_URL` (còn lại), và `API_URL` tính ra nhưng KHÔNG
#           export ⇒ ba cổng âm thầm chạy vào IP cũ, đỏ vì HẠ TẦNG chứ không vì sản phẩm;
#   02/08 — 30/33 script còn ghi cứng IP mặc định của một ngày đã qua (ba giá trị khác nhau).
# Nay `frontend/scripts/lib/moi-truong.mjs` là chỗ duy nhất biết; ở đây chỉ xuất ra cho nó.
EMAIL="${EMAIL:-${BERAS_EMAIL:-}}"
PASSWORD="${PASSWORD:-${BERAS_PASSWORD:-}}"
if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
  printf '\033[31m🔴 Chưa có tài khoản chạy cổng.\033[0m\n' >&2
  printf '   cp scripts/ui-gates.env.example scripts/ui-gates.env   (rồi điền tài khoản)\n' >&2
  exit 2
fi
export EMAIL PASSWORD
export BERAS_EMAIL="$EMAIL" BERAS_PASSWORD="$PASSWORD"

# Địa chỉ: để trống thì suy LAN IP từ card mạng LÚC CHẠY. Một con số ghi cứng chỉ đúng cho
# cái ngày người ta gõ nó vào — LAN IP đổi theo ngày (§7dg ghi .10, hôm sau đã là .8).
if [ -z "${BASE_URL:-}" ]; then
  IP=$(ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1 \
       | grep -Ev '^172\.(1[6-9]|2[0-9]|3[01])\.' | sort -r | head -1)
  [ -n "$IP" ] || die "Không tìm được LAN IP. Đặt tay: BASE_URL=http://<ip>:3000 $0"
  BASE_URL="http://$IP:3000"
fi
BASE_URL="${BASE_URL%/}"
API_URL="${API_URL:-${BASE_URL%:*}:8000/api/v1}"
export BASE_URL API_URL
export BERAS_BASE="$BASE_URL"
CHAY_CA_NHOM_GHI=0
[ "${1:-}" = "--all" ] && CHAY_CA_NHOM_GHI=1

CONG_DOC=(
  check-browsers.mjs        # không màn nào trắng, cả Firefox lẫn WebKit
  check-customers.mjs       # màn Khách hàng
  check-receive-flow.mjs    # luồng nhận hàng
  check-pos-allergy.mjs     # cảnh báo dị ứng ở quầy (Đ-7)
  check-rejected-sales.mjs  # đơn offline bị từ chối KHÔNG được biến mất
  check-danh-muc-thuoc.mjs  # danh mục thuốc + hoạt chất + giá niêm yết
  check-hoa-don.mjs         # hoá đơn: cửa sổ có ✕ · In gọi mẫu K80 · không in cả trang (P3)
  check-cua-so.mjs          # P4: mọi lối vào chi tiết mở CỬA SỔ có ✕ chạm tới được
  check-can-xung.mjs        # P5: ô nhập không cao bất thường · chữ không vỡ · cỡ chữ đồng nhất
  check-pos-tien.mjs        # quầy: thành tiền · khách đưa · thối lại (đọc thuần)
  check-pos-rx-photo.mjs    # quầy: nút Chụp đơn thuốc hiện đúng lúc (đọc thuần)
  check-luu-tru.mjs         # Cài đặt → Lưu trữ: ảnh chỉ tải khi bấm (ghi audit khi mở)
  check-nhin-thay.mjs       # kỷ luật #21: nhìn thấy được ≠ có trên trang (mọi màn, 390px)
  check-nhat-ky.mjs         # Nhật ký hoạt động: đọc được, lọc được, không lọt mã máy (M-04)
  check-tai-khoan.mjs       # Cài đặt → Tài khoản của tôi: khớp đúng /auth/me (M-03)
  check-don-thuoc.mjs       # Đơn thuốc: tra được cả đơn CHƯA chụp ảnh (M-08)
  check-so-kiem-soat.mjs    # Sổ thuốc kiểm soát đặc biệt: cộng đúng + tự nói chưa rà PL (C-03)
  check-thong-tin-co-so.mjs # Cài đặt → Thông tin cơ sở: lưu thật, nói rõ nợ hoá đơn (M-02)
  measure-mobile.mjs        # thanh điều hướng che gì · cột định danh có khuất
  shot-desktop-mobile.mjs   # 6 màn × 2 khổ: trắng · cuộn ngang · phần tử tràn
)
CONG_GHI=(
  check-pos-customer.mjs    # 🔴 BÁN một đơn
  check-sale-appears.mjs    # 🔴 BÁN một đơn
  write-rx-photo.mjs        # 🔴 TẠO một đơn thuốc + lưu ảnh (luồng chụp đơn end-to-end)
  write-pos-etc.mjs         # 🔴 BÁN một đơn ETC: chụp ⇒ dược sĩ duyệt ⇒ thanh toán (P1)
  check-so-do-kho.mjs       # 🔴 TẠO kho/kệ/ô thật — sơ đồ kho (BERAS V2 Phase 1)
  check-vi-tri-lay-hang.mjs # 🔴 CẤT hàng thật vào ô — trọn vòng tới quầy (V2 Phase 2)
  check-nhap-nhanh.mjs      # 🔴 NHẬN hàng thật, gắn ô ngay (V2 Phase 5-6)
  check-khoi-tao-ton.mjs    # 🔴 KHỞI TẠO tồn thật, nhập theo kệ (V2 Phase 9-10)
  check-kiem-ke.mjs         # 🔴 KIỂM KÊ: nộp không đụng tồn, duyệt mới đụng (V2 Phase 11)
)

# --- điều kiện cần: ứng dụng phải đang chạy -----------------------------------
# Hỏng ở đây phải nói rõ PHẢI LÀM GÌ. Một cổng báo lỗi khó hiểu thì lần sau người ta bỏ qua.
say "0/2 · Ứng dụng có đang chạy không"
# `curl -w '%{http_code}'` ĐÃ in "000" khi không nối được, nên `|| echo 000` in thêm lần
# nữa thành "000000" — một con số vô nghĩa trong output của chính cổng làm người đọc mất
# lòng tin vào cổng. Bỏ nhánh `||`, chỉ nuốt mã thoát.
FE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$BASE_URL/login"; true)
BE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$API_URL/health"; true)
printf '   frontend %s → %s\n   backend  %s → %s\n' "$BASE_URL" "$FE" "$API_URL" "$BE"
if [ "$FE" != "200" ] || [ "$BE" != "200" ]; then
  die "Chưa chạy. Bật bằng:  make lan     (rồi chạy lại lệnh này)"
fi

if [ "$CHAY_CA_NHOM_GHI" = "1" ]; then
  say "Nhóm GHI được yêu cầu — các cổng này BÁN ĐƠN THẬT"
  DB=$(curl -s --max-time 5 "$API_URL/health" || true)
  printf '   CSDL đang phục vụ: %s\n' "$DB"
  printf '   \033[33mChỉ tiếp tục nếu đây là CSDL dùng-một-lần.\033[0m Gõ "co" để chạy: '
  read -r tra_loi
  [ "$tra_loi" = "co" ] || die "Đã dừng. Không có gì được ghi."
fi

# --- chạy từng cổng ------------------------------------------------------------
say "1/2 · Chạy cổng"
cd "$(dirname "$0")/../frontend" || die "không vào được frontend/"
KET_QUA=()
HONG=0

chay() {
  local f="$1" nhom="$2"
  printf '   %-26s ' "$f"
  BASE_URL="$BASE_URL" node "scripts/$f" > "/tmp/ui-gate-$f.log" 2>&1
  local ma=$?                       # mã thoát của CHÍNH node, không phải của lệnh nào khác
  if [ "$ma" -eq 0 ]; then
    printf '\033[32mEXIT=0 ✓\033[0m\n'
  else
    printf '\033[31mEXIT=%s 🔴\033[0m\n' "$ma"
    HONG=$((HONG + 1))
  fi
  KET_QUA+=("$f|$nhom|$ma")
}

for f in "${CONG_DOC[@]}"; do chay "$f" "đọc"; done
[ "$CHAY_CA_NHOM_GHI" = "1" ] && for f in "${CONG_GHI[@]}"; do chay "$f" "ghi"; done

# --- tổng kết -------------------------------------------------------------------
say "2/2 · Tổng kết"
printf '| Cổng | Nhóm | Mã thoát |\n|---|---|---|\n'
for d in "${KET_QUA[@]}"; do
  IFS='|' read -r f nhom ma <<< "$d"
  printf '| %s | %s | %s %s |\n' "$f" "$nhom" "$ma" "$([ "$ma" -eq 0 ] && echo ✓ || echo 🔴)"
done
[ "$CHAY_CA_NHOM_GHI" = "0" ] && printf '\n(nhóm GHI bị bỏ qua — thêm --all để chạy)\n'

if [ "$HONG" -eq 0 ]; then
  printf '\n\033[32m✅ %s cổng trình duyệt XANH.\033[0m\n' "${#KET_QUA[@]}"
  exit 0
fi
printf '\n\033[31m🔴 %s cổng ĐỎ. Nhật ký: /tmp/ui-gate-<tên>.log\033[0m\n' "$HONG"
exit 1
