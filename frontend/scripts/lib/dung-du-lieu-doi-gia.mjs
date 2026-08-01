/**
 * Dựng dữ liệu cho cột **Thay đổi** của màn Nhật ký (M-05): đổi giá bán một thuốc rồi
 * **đổi lại nguyên giá cũ**.
 *
 * Để lại **hai** dòng `CATALOG_DRUG_PRICE_CHANGED` mang `old_price`/`new_price` trong sổ
 * audit (sổ chỉ-ghi-thêm, đúng như thiết kế) nhưng **giá niêm yết cuối cùng không đổi** —
 * nên không báo cáo doanh thu nào lệch và không khách nào bị tính sai giá.
 *
 * Tách khỏi `check-nhat-ky.mjs` có chủ đích: cổng ấy nằm nhóm **ĐỌC THUẦN**, còn tệp này
 * **CÓ GHI** và phải gõ tay. §7dg bài học 4: một cổng không chạy được vì thiếu dữ liệu thì
 * việc phải làm là **dựng dữ liệu**, không phải ghi chú thích — nhưng dựng phải là một
 * hành động người ta thấy mình đang làm, không phải tác dụng phụ của một lệnh kiểm tra.
 *
 * ⚠️ Chỉ chạy trên **CSDL kiểm thử**.
 *
 * Dùng:  EMAIL=… PASSWORD=… node scripts/lib/dung-du-lieu-doi-gia.mjs
 */

import { API, EMAIL, PASSWORD } from "./moi-truong.mjs";

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

const thuoc = await (await fetch(`${API}/drugs?limit=20`, { headers: H })).json();
const t = (Array.isArray(thuoc) ? thuoc : []).find((d) => Number(d.sale_price) > 0);
if (!t) {
  console.error("🔴 Không tìm thấy thuốc nào có giá bán > 0 trong 20 mã đầu.");
  process.exit(2);
}

const cu = Number(t.sale_price);
const tam = cu + 1000;

async function dat(gia, lyDo) {
  const r = await fetch(`${API}/drugs/${t.id}/price`, {
    method: "PUT",
    headers: H,
    body: JSON.stringify({ new_price: String(gia), reason: lyDo }),
  });
  if (!r.ok) {
    console.error(`🔴 PUT /drugs/${t.id}/price → ${r.status}: ${(await r.text()).slice(0, 200)}`);
    process.exit(1);
  }
}

await dat(tam, "dựng dữ liệu cổng Nhật ký (M-05) — sẽ trả lại ngay");
await dat(cu, "trả lại giá niêm yết cũ");

// Xác nhận bằng lệnh thật, không tin lời khai của chính mình (kỷ luật #5).
const lai = await (await fetch(`${API}/drugs/${t.id}`, { headers: H })).json();
const khop = Number(lai.sale_price) === cu;
console.log(
  `${khop ? "✓" : "🔴"} "${t.name}": ${cu} → ${tam} → ${lai.sale_price}` +
    (khop ? " (đã trả lại đúng giá cũ)" : " — GIÁ CHƯA VỀ ĐÚNG, sửa tay ngay"),
);
console.log("  Sổ audit nay có 2 dòng 'Đổi giá bán' mang giá cũ → giá mới.");
process.exit(khop ? 0 : 1);
