/**
 * Đơn offline bị máy chủ TỪ CHỐI phải HIỆN RA, và phải sống sót qua F5.
 *
 * 🔴 Sinh từ một lỗi MẤT DỮ LIỆU thật (31/07): `flushQueue` xoá đơn bị từ chối khỏi
 * IndexedDB rồi đẩy vào một state React mà không màn nào đọc. Thu ngân đã thu tiền của
 * khách; đơn không tồn tại ở đâu cả; không ai biết.
 *
 * Không lớp test nào khác canh được: nó nằm trong IndexedDB của trình duyệt (backend
 * không thấy) và chỉ xảy ra khi mất mạng rồi có lại (vitest không dựng được luồng đó
 * cùng giao diện thật).
 *
 * Cách dựng tình huống: bơm vào hàng chờ đúng ca đã sinh ra việc này — đơn có **cảnh báo
 * dị ứng mà chưa ghi lý do** ⇒ máy chủ trả 422 với một lý do nghiệp vụ, không phải lỗi mạng.
 *
 * 🔴 Lần đầu tôi dựng bằng một `drug_id` không tồn tại và cổng đỏ oan: `/sync/sales` trả
 * **200** cho đơn ấy. Kết quả tự mâu thuẫn (cổng đỏ nhưng cả hai bảng đều rỗng) — và kỷ
 * luật #15 nói kết quả tự mâu thuẫn LUÔN là lỗi phép đo. Ghi lại ở đây để không ai dựng
 * lại theo cách đó.
 */
const KHACH_DI_UNG = process.env.KHACH_DI_UNG ?? "feaedcb0-93f0-478f-b00b-5e31205e14a0";
const THUOC_XUNG_DOT = process.env.THUOC_XUNG_DOT ?? "3744d1ca-50bd-45fc-969a-0320dca454e1";
import { firefox } from "playwright-core";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;
if (!EMAIL || !PASSWORD) { console.error("Thiếu EMAIL / PASSWORD."); process.exit(2); }

const b = await firefox.launch();
let hong = 0;

for (const [ten, w, h, mob] of [["desktop",1440,900,false],["mobile",390,844,true]]) {
  const ctx = await b.newContext({ viewport:{width:w,height:h}, isMobile:mob, hasTouch:mob });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/login`, { waitUntil: "load" }); await p.waitForTimeout(1500);
  await p.fill('input[type="email"]', EMAIL);
  await p.fill('input[type="password"]', PASSWORD);
  await p.click('button[type="submit"]'); await p.waitForTimeout(4000);

  // Bơm một đơn chắc chắn bị từ chối vào hàng chờ offline.
  await p.evaluate(async ({ khach, thuoc }) => {
    const db = await new Promise((res, rej) => {
      const r = indexedDB.open("beras-offline");
      r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
    });
    const tx = db.transaction("pendingSales", "readwrite");
    tx.objectStore("pendingSales").put({
      clientUuid: "gate-rejected-0001",
      queuedAt: new Date().toISOString(),
      request: {
        client_uuid: "gate-rejected-0001",
        lines: [{ drug_id: thuoc, quantity: "1", unit_price: "12000",
                  requires_prescription: false }],
        payments: [{ method: "CASH", amount: "12000" }],
        customer_id: khach,
        // KHÔNG có `allergy_acknowledgement` — đó chính là lý do máy chủ từ chối.
      },
    });
    await new Promise((res) => (tx.oncomplete = res));
  }, { khach: KHACH_DI_UNG, thuoc: THUOC_XUNG_DOT });

  // Tải lại → `useOfflineSync` xả hàng chờ → máy chủ từ chối → phải hiện khối cảnh báo.
  await p.goto(`${BASE}/bang-dieu-hanh`, { waitUntil: "load" });
  await p.waitForTimeout(5000);
  const sau = await p.evaluate(() => {
    const t = document.body.innerText;
    return {
      coCanhBao: /KHÔNG đồng bộ được/i.test(t),
      coNutXem: [...document.querySelectorAll("button")].some(x => /Xem và xử lý/.test(x.textContent ?? "")),
    };
  });

  // F5 lần nữa: đơn phải VẪN CÒN (trước bản vá, nó chỉ sống trong state ⇒ mất).
  await p.reload({ waitUntil: "load" }); await p.waitForTimeout(4000);
  const sauF5 = await p.evaluate(() => /KHÔNG đồng bộ được/i.test(document.body.innerText));

  // Mở ra, bấm "Bỏ hẳn" → phải biến mất, và đó là đường DUY NHẤT làm nó biến mất.
  let sauKhiBo = null;
  if (sau.coNutXem) {
    await p.locator("button", { hasText: /Xem và xử lý/ }).click(); await p.waitForTimeout(600);
    await p.locator("button", { hasText: /^Bỏ hẳn$/ }).first().click(); await p.waitForTimeout(1500);
    sauKhiBo = await p.evaluate(() => /KHÔNG đồng bộ được/i.test(document.body.innerText));
  }

  const dat = sau.coCanhBao && sau.coNutXem && sauF5 === true && sauKhiBo === false;
  if (!dat) hong++;
  console.log(`\n──${ten}──`);
  console.log(`  đơn bị từ chối → hiện cảnh báo : ${sau.coCanhBao ? "✓" : "🔴 KHÔNG HIỆN"}`);
  console.log(`  sống sót qua F5                : ${sauF5 ? "✓" : "🔴 MẤT"}`);
  console.log(`  bấm "Bỏ hẳn" → biến mất        : ${sauKhiBo === false ? "✓" : "🔴"}`);
  await ctx.close();
}
await b.close();
console.log(hong === 0 ? "\n✅ Đơn bị từ chối không còn biến mất im lặng." : `\n🔴 ${hong} khổ có vấn đề.`);
process.exit(hong === 0 ? 0 : 1);
