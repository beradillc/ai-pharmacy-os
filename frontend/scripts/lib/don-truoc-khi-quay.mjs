/**
 * Dọn vết của lượt quay trước — **chạy TRƯỚC mỗi lượt quay có ghi dữ liệu**.
 *
 * 🔴 Vì sao có tệp này: từ video 04 trở đi, mỗi lượt quay hỏng để lại vết THẬT trong CSDL.
 *    Ba video đầu chỉ đọc nên quay lại bao nhiêu lần cũng được; từ đây thì không. Ngày 02/08
 *    ba lượt quay hỏng để lại **ba kho trùng tên** trên màn — và thứ bắt được là **ảnh khung
 *    hình**, không phải log, vì log của lượt cuối vẫn `EXIT=0` sạch sẽ.
 *
 * Nguyên tắc: **dọn TRƯỚC, không dọn SAU khi phát hiện.** Dọn sau nghĩa là phải phát hiện
 * đã, mà phát hiện thì phụ thuộc việc có ai mở ảnh ra nhìn hay không — đúng thứ kỷ luật #10
 * gọi là cưỡng chế bằng trí nhớ.
 *
 * Dùng:  node scripts/lib/don-truoc-khi-quay.mjs
 */
import { API, EMAIL, PASSWORD, doiDangNhap } from "./moi-truong.mjs";

doiDangNhap();

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
const H = { "Content-Type": "application/json", Authorization: `Bearer ${phien.access_token}` };
const lay = async (d) => await (await fetch(`${API}${d}`, { headers: H })).json();
const vaCham = async (d, body) =>
  await fetch(`${API}${d}`, { method: "PATCH", headers: H, body: JSON.stringify(body) });

// ── 1. Kho do bản quay tạo ra ────────────────────────────────────────────────
// Mã kho của bản quay luôn mang tiền tố `QUAY-` (xem `record-v04.mjs`), nên phân biệt được
// với kho thật của quầy mà không phải đoán theo tên.
// 🔴 DỌN TRÙNG LẶP, KHÔNG XOÁ SẠCH. Lượt viết đầu tôi ngừng HẾT kho `QUAY-*` — và thế là
//    xoá đúng cái kho mà video 04 vừa tạo ra cho video 05 dùng. Cả bộ video là một chuỗi
//    dữ liệu nối nhau; dọn sạch giữa chuỗi thì mắt xích sau không còn gì để làm việc.
//    Đúng: giữ cái MỚI NHẤT (kết quả của video trước), ngừng những cái cũ hơn.
const ds = await lay("/locations");
const kho = (Array.isArray(ds) ? ds : (ds.items ?? []))
  .filter((x) => String(x.code ?? "").startsWith("QUAY-") && x.is_active)
  .sort((a, b) => String(a.code).localeCompare(String(b.code)));
const cu = kho.slice(0, -1);
for (const k of cu) {
  await vaCham(`/locations/${k.id}`, { is_active: false });
}
console.log(
  `dọn kho quay: ngừng ${cu.length} kho trùng` +
    (kho.length ? ` · GIỮ ${kho[kho.length - 1].code} (video trước tạo ra)` : " · chưa có kho nào"),
);

// ── 2. Đơn mua ăn dở ─────────────────────────────────────────────────────────
// `PARTIALLY_RECEIVED` không đóng cũng không huỷ được (sổ liên thông L-1), nên chỉ đếm và
// báo — không giả vờ dọn được thứ API không cho dọn.
const po = await lay("/purchase-orders");
const anDo = (Array.isArray(po) ? po : (po.items ?? [])).filter(
  (p) => p.status === "PARTIALLY_RECEIVED",
);
if (anDo.length) {
  console.log(
    `⚠️  ${anDo.length} đơn mua đang nhận dở (${anDo.map((p) => p.code).join(", ")}) — ` +
      "API không cho đóng/huỷ (sổ liên thông L-1). Chúng vẫn hiện trên màn lúc quay.",
  );
}

// ── 3. Tự kiểm: đọc lại, đừng tin lệnh vừa gửi ───────────────────────────────
const lai = await lay("/locations");
const con = (Array.isArray(lai) ? lai : (lai.items ?? [])).filter(
  (x) => String(x.code ?? "").startsWith("QUAY-") && x.is_active,
);
if (con.length > 1) {
  console.error(`🔴 Dọn xong nhưng đọc lại vẫn còn ${con.length} kho quay — phải còn tối đa 1.`);
  process.exit(1);
}
console.log(`✅ Còn ${con.length} kho quay đang hoạt động — quay được.`);
