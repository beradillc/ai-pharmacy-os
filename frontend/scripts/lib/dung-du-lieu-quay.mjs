/**
 * Dựng dữ liệu tối thiểu để QUAY VIDEO trên một CSDL sạch. (02/08, Chain duyệt sản xuất video)
 *
 * Vì sao cần: `qt650` có 70 thuốc nhưng **0 nhà cung cấp, 0 đơn mua** — nên cảnh *"Nhận hàng"*
 * (đoạn 04 của `record-tutorial.mjs`) không có nút để bấm, và bản quay dừng giữa chừng. Đúng
 * điều kiện `M-01` mà `04_DANH_SACH_VIDEO.md` đã ghi từ đầu: *"cần có nhà cung cấp"*.
 *
 * Nguyên tắc: **chỉ dựng thứ video cần, bằng API thật** — không chèn thẳng vào CSDL. Đi đường
 * API nghĩa là dữ liệu dựng ra đi qua đúng các luật nghiệp vụ, audit và ràng buộc mà quầy sẽ
 * đi qua; chèn thẳng SQL thì dựng được cả những trạng thái phần mềm không bao giờ tạo ra, và
 * video sẽ quay một màn hình không tồn tại trong đời thật.
 *
 * **Idempotent** — chạy lại không sinh thêm nhà cung cấp/đơn mua. Quay lại nhiều lần là
 * chuyện bình thường, mà mỗi lượt quay thêm một đơn mua rác thì tới lượt thứ năm màn Đơn mua
 * hàng đã đầy dòng không ai giải thích được trên hình.
 *
 * Chạy:  cd frontend && node scripts/lib/dung-du-lieu-quay.mjs
 */
import { API, EMAIL, PASSWORD, doiDangNhap } from "./moi-truong.mjs";

doiDangNhap();

const NCC = "Công ty Dược phẩm Trung ương 1";
const SO_DONG = 4; // 4 mặt hàng — đủ để thấy bảng nhiều dòng, chưa tới mức tràn màn 390px

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
const H = {
  "Content-Type": "application/json",
  Authorization: `Bearer ${phien.access_token}`,
};
const lay = async (d) => (await (await fetch(`${API}${d}`, { headers: H })).json());
const gui = async (d, body) => {
  const r = await fetch(`${API}${d}`, { method: "POST", headers: H, body: JSON.stringify(body) });
  if (!r.ok) {
    console.error(`🔴 POST ${d} → ${r.status}: ${(await r.text()).slice(0, 200)}`);
    process.exit(1);
  }
  return r.json();
};

// ── 1. Nhà cung cấp ──────────────────────────────────────────────────────────
const dsNcc = await lay("/suppliers");
let ncc = (Array.isArray(dsNcc) ? dsNcc : (dsNcc.items ?? [])).find((s) => s.name === NCC);
if (ncc) {
  console.log(`nhà cung cấp: đã có (${ncc.name})`);
} else {
  ncc = await gui("/suppliers", {
    name: NCC,
    tax_code: "0100108385",
    contact_name: "Nguyễn Văn Hải",
    phone: "02438253901",
    address: "356 Giải Phóng, Thanh Xuân, Hà Nội",
  });
  console.log(`nhà cung cấp: TẠO MỚI (${ncc.name})`);
}

// ── 2. Đơn mua hàng đang chờ nhận ────────────────────────────────────────────
// Trạng thái sau `/place` là **ORDERED** (không phải "PLACED" như tên endpoint gợi ý — lượt
// chạy đầu đoán theo tên endpoint và phép tự-kiểm bắt được ngay: tạo xong đọc lại ra 0 đơn).
// Chỉ dựng nếu CHƯA có đơn nào ở trạng thái chờ nhận — đó đúng là thứ cảnh "Nhận hàng" cần,
// và cũng là phép tự kiểm: đếm trước khi tạo, thay vì tạo rồi hy vọng.
// 🔴 Chỉ `ORDERED` mới dùng lại được — **`PARTIALLY_RECEIVED` thì KHÔNG.**
//    Bản quay không idempotent: một lượt quay hỏng giữa chừng để lại phiếu ăn dở, và lượt sau
//    mở đúng phiếu đó ra thì các dòng đã nhận còn 0 để nhận ⇒ không bao giờ hiện câu
//    "Đã nhận hàng và chốt phiếu" ⇒ bản quay chết ở đoạn 07 với thông điệp đọc như lỗi sản
//    phẩm. Cảnh quay cần một phiếu CÒN NGUYÊN, không phải "một phiếu bất kỳ chưa đóng".
const dsPo = await lay("/purchase-orders");
const tatCa = Array.isArray(dsPo) ? dsPo : (dsPo.items ?? []);
const poNguyen = tatCa.filter((p) => p.status === "ORDERED");
const poAnDo = tatCa.filter((p) => p.status === "PARTIALLY_RECEIVED");

// 🔴 **Phiếu ăn dở KHÔNG đóng và KHÔNG huỷ được** — cả `/close` lẫn `/cancel` đều trả 422
//    (`/close` đòi trạng thái RECEIVED). Lối ra duy nhất của một phiếu `PARTIALLY_RECEIVED`
//    là **nhận nốt phần còn thiếu**. Đây là khoảng trống nghiệp vụ thật, không phải lỗi script:
//    nhà cung cấp giao thiếu rồi không giao nữa thì phiếu kẹt vĩnh viễn. Đã ghi cho Chain.
//    Ở đây chỉ cần cảnh báo và bỏ qua — script tạo phiếu MỚI còn nguyên để quay.
if (poAnDo.length > 0) {
  console.log(
    `⚠️  ${poAnDo.length} đơn mua đang PARTIALLY_RECEIVED (${poAnDo.map((p) => p.code).join(", ")}) — ` +
      `không đóng/huỷ được qua API. Chúng vẫn hiện trên màn Đơn mua hàng lúc quay.`,
  );
}

if (poNguyen.length > 0) {
  console.log(`đơn mua còn nguyên: đã có ${poNguyen.length} — không tạo thêm`);
  console.log(`\n✅ Dữ liệu quay sẵn sàng.`);
  process.exit(0);
}

const dsThuoc = await lay("/drugs?limit=200");
const thuoc = (Array.isArray(dsThuoc) ? dsThuoc : (dsThuoc.items ?? [])).slice(0, SO_DONG);
// Tự kiểm phép đo trước khi tin nó (kỷ luật #15): 0 thuốc ⇒ mọi khẳng định sau là vô nghĩa.
if (thuoc.length < SO_DONG) {
  console.error(`🔴 Chỉ tìm được ${thuoc.length} thuốc, cần ${SO_DONG}. Danh mục chưa nạp?`);
  process.exit(2);
}

const po = await gui("/purchase-orders", {
  supplier_id: ncc.id,
  items: thuoc.map((t) => ({
    drug_id: t.id,
    quantity_ordered: "100",
    unit_price: String(Math.max(1000, Math.round((Number(t.sale_price ?? 5000) * 0.7) / 100) * 100)),
  })),
});
await gui(`/purchase-orders/${po.id}/place`, {});
console.log(`đơn mua: TẠO MỚI ${po.code ?? po.id} · ${thuoc.length} mặt hàng · đã đặt`);

// ── 3. Xác nhận bằng lệnh thật, không tin số dòng vừa in ra ──────────────────
const lai = await lay("/purchase-orders");
const cho = (Array.isArray(lai) ? lai : (lai.items ?? [])).filter((p) =>
  p.status === "ORDERED",
);
console.log(`xác nhận: ${cho.length} đơn ở trạng thái chờ nhận`);
if (cho.length < 1) {
  console.error("🔴 Tạo xong nhưng đọc lại không thấy đơn chờ nhận nào — dừng.");
  process.exit(1);
}
console.log(`\n✅ Dữ liệu quay sẵn sàng.`);
