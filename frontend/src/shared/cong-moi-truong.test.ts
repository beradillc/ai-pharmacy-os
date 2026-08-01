import { readFileSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";

import { describe, expect, it } from "vitest";

/**
 * 🔴 **Cổng canh chính các cổng — địa chỉ và mật khẩu không được nằm trong mã.** (N-4, 02/08)
 *
 * Kỷ luật #24: *"một danh sách các lỗi đã biết mà không có cổng là một danh sách các lỗi SẼ
 * LẶP LẠI"*. N-4 là một lỗi đã biết, ghi trong PROJECT_STATE từ 01/08. Tệp này là cổng của nó.
 *
 * Hai tính chất, mỗi cái sinh từ một sự cố thật:
 *
 *   ① **Không script nào ghi cứng địa chỉ.** LAN IP đổi theo ngày. Ngày 01/08 ba cổng âm thầm
 *      chạy vào `192.168.1.10` của hôm trước và đỏ vì **hạ tầng** — mà log đỏ vì hạ tầng đọc
 *      **y hệt** log đỏ vì sản phẩm. Đến 02/08 có tới **ba** giá trị mặc định cùng tồn tại
 *      trong cùng thư mục (`192.168.1.10`, `192.168.1.8`, `localhost`).
 *
 *   ② **Không script nào ghi cứng thông tin đăng nhập.** Bốn script từng nhúng thẳng mật khẩu
 *      thật vào mã nguồn và chúng **đã vào git**. Một mật khẩu trong repo không tự biến mất
 *      khi người ta đổi nó ở CSDL — nó nằm lại trong lịch sử.
 *
 * Cổng đọc **thẳng thư mục script** (kỷ luật #22: đọc nguồn bên kia, không chép lại nó), nên
 * một script mới thêm ngày mai cũng bị soi mà không phải sửa gì ở đây.
 */
const THU_MUC_SCRIPT = resolve(__dirname, "../../scripts");
const CHO_PHEP = new Set(["moi-truong.mjs"]); // chỗ duy nhất được biết cách suy ra địa chỉ

function scriptCong(): { ten: string; noi_dung: string }[] {
  const ra: { ten: string; noi_dung: string }[] = [];
  for (const goc of [THU_MUC_SCRIPT, join(THU_MUC_SCRIPT, "lib")]) {
    for (const ten of readdirSync(goc)) {
      if (!ten.endsWith(".mjs") || CHO_PHEP.has(ten)) continue;
      ra.push({ ten, noi_dung: readFileSync(join(goc, ten), "utf8") });
    }
  }
  return ra;
}

/**
 * Chú thích được phép nhắc tới địa chỉ ("Chạy: BASE_URL=http://localhost:3000 …") — đó là tài
 * liệu, không phải giá trị chạy. Chỉ soi phần MÃ. Bỏ chú thích trước khi so, thay vì nới lỏng
 * mẫu nhận dạng: một cổng đỏ vì lý do sai thì lần sau người ta tắt nó đi.
 */
function boChuThich(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
}

describe("cổng trình duyệt không giấu cấu hình trong mã (N-4)", () => {
  it("phép quét chạm được tới thư mục script", () => {
    // Tự kiểm phép đo trước khi tin nó (kỷ luật #15/#22). Đường dẫn sai ⇒ danh sách rỗng ⇒
    // MỌI khẳng định bên dưới thành đúng vô nghĩa. Lúc viết cổng có 36 script.
    expect(scriptCong().length).toBeGreaterThan(25);
  });

  it("không script nào ghi cứng địa chỉ máy chủ", () => {
    const sai = scriptCong()
      .filter(({ noi_dung }) => /https?:\/\/(?:\d{1,3}\.){3}\d{1,3}|https?:\/\/localhost/.test(boChuThich(noi_dung)))
      .map(({ ten }) => ten);
    expect(
      sai,
      `Địa chỉ ghi cứng ⇒ cổng chạy vào IP của một ngày đã qua, đỏ vì HẠ TẦNG mà log đọc y hệt đỏ vì SẢN PHẨM. Nhập BASE/API từ lib/moi-truong.mjs: ${sai.join(", ")}`,
    ).toEqual([]);
  });

  it("không script nào ghi cứng thông tin đăng nhập", () => {
    const sai = scriptCong()
      .filter(({ noi_dung }) => {
        const ma = boChuThich(noi_dung);
        // Chuỗi hình dạng email, hoặc một giá trị mặc định gán cho EMAIL/PASSWORD.
        return (
          /"[^"\s]+@[^"\s]+\.[a-z]{2,}"/.test(ma) ||
          /\b(?:EMAIL|PASSWORD)\b[^\n;]*\?\?\s*"/.test(ma)
        );
      })
      .map(({ ten }) => ten);
    expect(
      sai,
      `Mật khẩu/tài khoản trong mã nguồn là mật khẩu TRONG GIT — đổi ở CSDL không xoá được nó khỏi lịch sử. Đưa vào scripts/ui-gates.env: ${sai.join(", ")}`,
    ).toEqual([]);
  });

  it("mẫu cấu hình có mặt trong repo, bản thật thì không", () => {
    // Một môi trường không có tệp mẫu trong repo là môi trường chỉ dựng lại được bằng trí nhớ
    // của một người — đúng câu .gitignore tự viết về chính nó.
    const goc = resolve(__dirname, "../../..");
    expect(readdirSync(join(goc, "scripts"))).toContain("ui-gates.env.example");
    expect(readFileSync(join(goc, ".gitignore"), "utf8")).toContain("scripts/ui-gates.env");
  });
});
