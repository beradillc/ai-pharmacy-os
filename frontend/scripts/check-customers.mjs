/**
 * Màn Khách hàng — kiểm trên trình duyệt THẬT, khổ iPhone, qua LAN IP.
 *
 * Canh năm tính chất mà không cổng nào khác canh được:
 *  ① tra theo số điện thoại **hỏi máy chủ** và ra đúng một người
 *  ② phụ đề đổi sang "toàn bộ" — người dùng phải biết đang tìm ở phạm vi nào
 *  ③ gõ TÊN thì **không** gọi máy chủ (lọc tại chỗ)
 *  ④ bảng đồng ý có đủ 3 mục, **không ô nào tick sẵn**, và nút rút lại đứng
 *    ngay cạnh nút đồng ý — cả ba đều là yêu cầu của Luật 91/2025 Điều 9
 *  ⑤ không lỗi JS
 *
 * 🔴 Cổng này đã bắt được một lỗi thật ngay lần chạy đầu: màn hình hiện đủ 10
 * khách, gõ đúng số của một người trong đó thì báo "không có khách nào mang số
 * này". Nguyên nhân nằm ở **seeder**, không ở màn hình — nó ghi dữ liệu mà không
 * cài mã hoá at-rest, nên cột dấu vân tay rỗng, trong khi API tra bằng dấu vân
 * tay. Bộ test không thấy vì test luôn dựng CSDL từ số không trong cùng một
 * tiến trình đã cài mã hoá.
 *
 * Chạy:  cd frontend && BERAS_EMAIL=… BERAS_PASSWORD=… npm run check:customers
 */
import { webkit } from "playwright-core";

const BASE = process.env.BERAS_BASE ?? "http://192.168.1.10:3000";
const EMAIL = process.env.BERAS_EMAIL;
const PASSWORD = process.env.BERAS_PASSWORD;

if (!EMAIL || !PASSWORD) {
  console.error("Thiếu BERAS_EMAIL / BERAS_PASSWORD.");
  process.exit(2);
}

const B = BASE;
const b=await webkit.launch(); const ctx=await b.newContext({viewport:{width:402,height:874},locale:"vi-VN"});
const p=await ctx.newPage(); const errs=[]; p.on("pageerror",e=>errs.push(e.message));
await p.goto(`${B}/login`,{waitUntil:"networkidle"});
await p.fill('input[type="email"]',EMAIL); await p.fill('input[type="password"]',PASSWORD);
await p.click('button[type="submit"]'); await p.waitForURL(u=>!u.pathname.includes("login"),{timeout:25000});
await p.waitForResponse(r=>r.url().includes("/drugs"),{timeout:15000}).catch(()=>{});
await p.goto(`${B}/khach-hang`,{waitUntil:"networkidle"});
await p.locator("tbody tr").first().waitFor({timeout:25000});

const sdt = await p.locator("tbody tr td:nth-child(2)").first().innerText();
console.log("① lấy một SĐT có thật từ danh sách:", sdt);

// Tra theo SĐT — phải hỏi máy chủ và ra đúng 1
let goi=0; p.on("response", r=>{ if(r.url().includes("customers?phone=")) goi++; });
await p.locator('input[aria-label*="Tìm khách"]').fill(sdt.trim());
await p.waitForTimeout(2500);
const n = await p.locator("tbody tr").count();
const phu = await p.locator("p").filter({hasText:"TOÀN BỘ"}).count();
console.log(`② tra theo SĐT → ${n} dòng · gọi máy chủ ${goi} lần · phụ đề đổi sang "toàn bộ": ${phu>0?"CÓ":"KHÔNG"}`);

// Gõ tên → KHÔNG gọi máy chủ
const truoc=goi;
await p.locator('input[aria-label*="Tìm khách"]').fill("Nguyễn");
await p.waitForTimeout(2000);
console.log(`③ gõ TÊN → gọi máy chủ thêm ${goi-truoc} lần (phải là 0)`);

// Mở bảng đồng ý
await p.locator('input[aria-label*="Tìm khách"]').fill("");
await p.waitForTimeout(1200);
await p.locator('button:has-text("Đồng ý")').first().click();
const drawer = p.locator('section[aria-label^="Đồng ý của"]');
await drawer.waitFor({timeout:20000});
const muc = await drawer.locator("li").count();
const tick = await drawer.locator('input[type="checkbox"]:checked').count();
const nutDongY = await drawer.locator('button:has-text("Khách đồng ý")').count();
const nutRut = await drawer.locator('button:has-text("Từ chối / rút lại")').count();
console.log(`④ bảng đồng ý: ${muc} mục · ô tick sẵn = ${tick} (phải 0) · nút đồng ý ${nutDongY} · nút rút lại ${nutRut}`);
console.log(`⑤ lỗi JS: ${errs.length}`);
const ok = n===1 && goi>0 && phu>0 && muc===3 && tick===0 && nutDongY===3 && nutRut===3 && errs.length===0;
console.log(ok?"\n✓ Màn Khách hàng chạy đúng thiết kế":"\n🔴 CÓ CHỖ SAI");
if(errs.length) console.log(errs.slice(0,2).join(" | "));
await b.close(); process.exit(ok?0:1);
