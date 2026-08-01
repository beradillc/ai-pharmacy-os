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
#   ./scripts/ui-gates.sh                  # nhóm đọc-thuần (mặc định, an toàn)
#   ./scripts/ui-gates.sh --all            # + nhóm ghi, ĐÒI xác nhận CSDL dùng-một-lần
#   BASE_URL=http://localhost:3000 ./scripts/ui-gates.sh
set -uo pipefail

BASE_URL="${BASE_URL:-http://192.168.1.10:3000}"

# 🔴 HAI QUY ƯỚC TÊN BIẾN cùng tồn tại — phát hiện ngay lần chạy đầu của chính tệp này
# (31/07): cổng viết trước dùng `BERAS_EMAIL/BERAS_PASSWORD`, cổng viết sau dùng
# `EMAIL/PASSWORD`. Chạy tay từng cái thì không ai thấy; gom lại một lệnh thì lộ ngay.
# Xuất CẢ HAI ở đây thay vì sửa 8 script: chỗ biết thông tin đăng nhập nên có đúng một.
# Thống nhất tên là việc dọn riêng, không gộp vào lần thay đổi này.
EMAIL="${EMAIL:-${BERAS_EMAIL:-trinhthu@nhathuoc650.vn}}"
PASSWORD="${PASSWORD:-${BERAS_PASSWORD:-NhaThuoc650@2026}}"
export EMAIL PASSWORD
export BERAS_EMAIL="$EMAIL" BERAS_PASSWORD="$PASSWORD"
API_URL="${API_URL:-${BASE_URL%:*}:8000/api/v1}"
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
  check-pos-tien.mjs        # quầy: thành tiền · khách đưa · thối lại (đọc thuần)
  check-pos-rx-photo.mjs    # quầy: nút Chụp đơn thuốc hiện đúng lúc (đọc thuần)
  check-luu-tru.mjs         # Cài đặt → Lưu trữ: ảnh chỉ tải khi bấm (ghi audit khi mở)
  check-nhin-thay.mjs       # kỷ luật #21: nhìn thấy được ≠ có trên trang (mọi màn, 390px)
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

say() { printf '\n\033[1m▶ %s\033[0m\n' "$1"; }
die() { printf '\033[31m🔴 %s\033[0m\n' "$1" >&2; exit 2; }

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
