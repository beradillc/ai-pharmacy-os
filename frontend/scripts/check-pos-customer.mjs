/**
 * Luồng bắt khách ở quầy — kiểm trên trình duyệt THẬT, khổ iPhone, qua LAN IP.
 *
 * Canh sáu tính chất của quyết định Đ-4 (Chain chốt 2026-07-29):
 *  ① ô số điện thoại nằm NGAY TRÊN giỏ hàng, trong luồng bán, không giấu sau nút
 *  ② số đã có khách ⇒ **tự gắn**, không tạo hồ sơ trùng
 *  ③ đơn gửi lên **kèm `customer_id`**
 *  ④ bán xong **tự bỏ gắn** — người tiếp theo ở quầy là một người KHÁC
 *  ⑤ số chưa có ⇒ mời tạo, và **nói rõ** tích điểm phải hỏi riêng
 *  ⑥ không lỗi JS
 *
 * 🔴 ④ đã bắt được một lỗi thật ngay lần chạy đầu: bán xong khách **vẫn còn
 * gắn**. Nguyên nhân là tôi gắn khách ngay trong thân render (`if (found) …
 * onChange(found)`) — cha gọi `setCustomer(null)`, component vẽ lại, ô số điện
 * thoại vẫn giữ giá trị nên `found` vẫn có, và nó gắn lại tức thì. Bỏ gắn thành
 * ra không bỏ được, và mọi hoá đơn sau đó sẽ mang tên khách trước.
 *
 * Chạy:  cd frontend && BERAS_EMAIL=… BERAS_PASSWORD=… npm run check:pos-customer
 */
import { webkit } from "playwright-core";

const BASE = process.env.BERAS_BASE ?? "http://192.168.1.10:3000";
const EMAIL = process.env.BERAS_EMAIL;
const PASSWORD = process.env.BERAS_PASSWORD;
/** Số điện thoại CÓ THẬT trong CSDL đã seed — cổng cần một ca "tra ra". */
const KNOWN_PHONE = process.env.BERAS_KNOWN_PHONE ?? "0932567890";

if (!EMAIL || !PASSWORD) {
  console.error("Thiếu BERAS_EMAIL / BERAS_PASSWORD.");
  process.exit(2);
}

const B = BASE;
const b=await webkit.launch(); const p=await (await b.newContext({viewport:{width:402,height:874},locale:"vi-VN"})).newPage();
const errs=[]; p.on("pageerror",e=>errs.push(e.message));
let saleBody=null;
p.on("request", r=>{ if(r.url().endsWith("/sales")&&r.method()==="POST") saleBody=r.postDataJSON(); });
await p.goto(`${B}/login`,{waitUntil:"networkidle"});
await p.fill('input[type="email"]',EMAIL); await p.fill('input[type="password"]',PASSWORD);
await p.click('button[type="submit"]'); await p.waitForURL(u=>!u.pathname.includes("login"),{timeout:25000});
await p.waitForResponse(r=>r.url().includes("/drugs"),{timeout:15000}).catch(()=>{});
await p.goto(`${B}/`,{waitUntil:"networkidle"});
const o = p.locator('input[aria-label="Số điện thoại khách hàng"]');
await o.waitFor({timeout:20000});
console.log("① ô số điện thoại có mặt ngay trên giỏ hàng ✓");
await o.fill(KNOWN_PHONE); await p.waitForTimeout(3000);
const gan = await p.locator('button:has-text("Bỏ gắn")').count();
const ten = gan ? await p.locator('section strong').first().innerText() : "(chưa gắn)";
console.log(`② số CÓ THẬT → tự gắn: ${gan?"CÓ":"KHÔNG"} · ${ten}`);
await p.locator('input[placeholder*="Tìm thuốc"]').fill("Berberin"); await p.waitForTimeout(1500);
await p.locator('button:has-text("Thêm")').first().click(); await p.waitForTimeout(700);
await p.locator('button:has-text("Thanh toán")').click();
await p.locator("text=Đã bán thành công").waitFor({timeout:25000});
console.log(`③ đơn gửi lên có customer_id: ${saleBody?.customer_id ? "CÓ ("+saleBody.customer_id.slice(0,8)+")" : "🔴 KHÔNG"}`);
await p.waitForTimeout(1200);
const conGan = await p.locator('button:has-text("Bỏ gắn")').count();
console.log(`④ bán xong tự bỏ gắn khách: ${conGan===0?"CÓ":"🔴 VẪN CÒN GẮN"}`);
await o.fill("0999888777"); await p.waitForTimeout(3000);
const moiTao = await p.locator('input[aria-label="Tên khách hàng mới"]').count();
const ranhGioi = await p.locator("text=phải hỏi riêng").count();
console.log(`⑤ số CHƯA có → mời tạo: ${moiTao?"CÓ":"KHÔNG"} · nói rõ tích điểm phải hỏi riêng: ${ranhGioi?"CÓ":"KHÔNG"}`);
console.log(`⑥ lỗi JS: ${errs.length}`);
const ok = gan===1 && !!saleBody?.customer_id && conGan===0 && moiTao===1 && ranhGioi>0 && errs.length===0;
console.log(ok?"\n✓ Luồng bắt khách ở quầy chạy đúng Đ-4":"\n🔴 CÓ CHỖ SAI");
if(errs.length) console.log(errs.slice(0,2).join(" | "));
await b.close(); process.exit(ok?0:1);
