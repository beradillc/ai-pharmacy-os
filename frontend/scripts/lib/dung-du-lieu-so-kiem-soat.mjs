/**
 * Dựng dữ liệu cho màn **Sổ thuốc kiểm soát đặc biệt** (C-03): một chuỗi bút toán
 * nhập/xuất thật qua API, đủ để cột "Còn lại" (tồn lũy kế) có gì đó để cộng trừ.
 *
 * Vì sao phải dựng: `controlled_ledger_entries` trong CSDL kiểm thử có **0 dòng**, nên cổng
 * trình duyệt sẽ chỉ thấy trạng thái rỗng — và một cổng xanh trên màn rỗng **không chứng
 * minh được gì** ngoài việc màn không nổ. §7dg bài học 4: thiếu dữ liệu thì dựng dữ liệu,
 * không ghi chú thích rồi coi như đã đo.
 *
 * 🔴 TÁCH khỏi `check-so-kiem-soat.mjs` vì cổng ấy nằm nhóm **ĐỌC THUẦN**. Tệp này CÓ GHI —
 * và ghi vào một bảng **chỉ-ghi-thêm, không xoá được**, nên chỉ chạy trên CSDL kiểm thử.
 * Đây cũng là lý do nó không tự chạy: một lệnh kiểm tra âm thầm ghi vào sổ pháp lý là đúng
 * thứ không được phép xảy ra.
 *
 * Dùng:  EMAIL=… PASSWORD=… node scripts/lib/dung-du-lieu-so-kiem-soat.mjs
 */

if (!EMAIL || !PASSWORD) {
  console.error("Thiếu EMAIL / PASSWORD.");
  process.exit(2);
}

const phien = await (
  await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  })
).json();
if (!phien.access_token) {
  console.error("🔴 Đăng nhập thất bại.");
  process.exit(2);
}
const H = { Authorization: `Bearer ${phien.access_token}`, "Content-Type": "application/json" };

const thuoc = await (await fetch(`${API}/drugs?limit=5`, { headers: H })).json();
if (!Array.isArray(thuoc) || thuoc.length < 2) {
  console.error("🔴 Cần ít nhất 2 thuốc trong danh mục.");
  process.exit(2);
}

const homNay = new Date();
const luc = (soGioTruoc) =>
  new Date(homNay.getTime() - soGioTruoc * 3600e3).toISOString().replace("Z", "+00:00");

/**
 * Bốn bút toán, chọn để cột "Còn lại" đi qua đủ các trạng thái người soát sổ cần thấy:
 * nhập → xuất → xuất → nhập, và **hai mẫu sổ khác nhau** (PL_VIII cho gây nghiện,
 * PL_XVI cho thuốc độc) để bộ chọn mẫu sổ trên màn có gì để chuyển qua lại.
 *
 * `customer` + `prescription_code` là **bắt buộc** ở chiều XUAT của thuốc gây nghiện
 * (TT18 Điều 12.1.c + Phụ lục XIX) — backend từ chối 422 nếu thiếu, và đó là quy tắc đúng
 * chứ không phải phiền hà: bán thuốc gây nghiện mà không ghi ai mua là thứ thanh tra hỏi
 * đầu tiên.
 */

import { API, EMAIL, PASSWORD } from "./moi-truong.mjs";
const BUT_TOAN = [
  {
    drug_id: thuoc[0].id,
    category: "GAY_NGHIEN",
    direction: "NHAP",
    quantity: "100",
    lot_no: "LO-GN-2601",
    expiry_date: "2027-06-30",
    transaction_at: luc(72),
    source_or_destination: "Công ty CP Dược phẩm Trung ương 1",
    document_no: "HD-GN-0001",
    note: "Nhập theo hoá đơn kèm phiếu kiểm nghiệm",
  },
  {
    drug_id: thuoc[0].id,
    category: "GAY_NGHIEN",
    direction: "XUAT",
    quantity: "7",
    lot_no: "LO-GN-2601",
    expiry_date: "2027-06-30",
    transaction_at: luc(48),
    source_or_destination: "Bán lẻ theo đơn tại quầy",
    document_no: "PX-GN-0001",
    prescription_code: "DT-2026-000431",
    customer: { patient_name: "Nguyễn Văn Bệnh", patient_address: "12 Lê Lợi, P. Bến Nghé" },
  },
  {
    drug_id: thuoc[0].id,
    category: "GAY_NGHIEN",
    direction: "XUAT",
    quantity: "5",
    lot_no: "LO-GN-2601",
    expiry_date: "2027-06-30",
    transaction_at: luc(24),
    source_or_destination: "Bán lẻ theo đơn tại quầy",
    document_no: "PX-GN-0002",
    prescription_code: "DT-2026-000512",
    customer: { patient_name: "Trần Thị Mai", patient_address: "88 Nguyễn Trãi, P. 3" },
  },
  {
    drug_id: thuoc[1].id,
    category: "THUOC_DOC",
    direction: "NHAP",
    quantity: "40",
    lot_no: "LO-TD-2602",
    expiry_date: "2028-01-31",
    transaction_at: luc(20),
    source_or_destination: "Công ty TNHH Dược phẩm Miền Nam",
    document_no: "HD-TD-0007",
    note: "Thuốc độc — sổ Phụ lục XVI",
  },
];

let ok = 0;
for (const bt of BUT_TOAN) {
  const r = await fetch(`${API}/compliance/controlled-ledger`, {
    method: "POST",
    headers: H,
    body: JSON.stringify(bt),
  });
  if (r.ok) {
    ok += 1;
  } else {
    console.error(`  🔴 ${bt.document_no}: ${r.status} ${(await r.text()).slice(0, 220)}`);
  }
}

// Xác nhận bằng lệnh thật, không tin số dòng vừa đếm được (kỷ luật #5).
const q = "date_from=2026-01-01&date_to=2026-12-31";
const plViii = await (
  await fetch(`${API}/compliance/controlled-ledger/books/PL_VIII?${q}`, { headers: H })
).json();
const plXvi = await (
  await fetch(`${API}/compliance/controlled-ledger/books/PL_XVI?${q}`, { headers: H })
).json();

console.log(`  ghi ${ok}/${BUT_TOAN.length} bút toán`);
console.log(`  PL_VIII: ${plViii.length} dòng · tồn cuối ${plViii.at(-1)?.balance ?? "—"}`);
console.log(`  PL_XVI:  ${plXvi.length} dòng · tồn cuối ${plXvi.at(-1)?.balance ?? "—"}`);

const dat = plViii.length >= 3 && plXvi.length >= 1;
console.log(dat ? "✓ Sổ đã có dữ liệu cho cả hai mẫu." : "🔴 Chưa đủ dữ liệu.");
process.exit(dat ? 0 : 1);
