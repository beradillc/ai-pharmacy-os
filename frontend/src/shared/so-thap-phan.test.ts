import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { formatQty, formatSo } from "@/shared/format/number";

/**
 * 🔴 **Cổng bắt chéo hai thế giới: `Decimal` của Python ↔ chuỗi hiển thị của React.**
 *
 * Backend khai số lượng là `Numeric(18, 3)`. Một lô **100 viên** đi qua JSON thành chuỗi
 * `"100.000"`. Dựng thẳng chuỗi ấy vào JSX thì người Việt đọc là **một trăm nghìn** — dấu
 * chấm ở Việt Nam ngăn hàng nghìn, ở JSON là dấu thập phân. Không cổng nào đỏ: `tsc` xanh vì
 * `string` là `string`, `pytest` xanh vì backend trả đúng, ảnh chụp trông bình thường vì
 * `100.000` là một con số hợp lệ.
 *
 * **Ca thật, Chain phát hiện 2026-08-04:** màn Kiểm kê hiện *"sổ ghi 100.000"* cho một lô
 * **100 viên**. Đo bằng lệnh trên API thật: `{'lot_no': 'Aa', 'quantity': '100.000'}`.
 *
 * **Lần thứ hai cùng họ.** Lần đầu 2026-08-01: ô hoạt chất hiện `1.0000`, đã đẻ ra `formatSo`.
 * Hàm chữa bệnh có sẵn từ hôm đó — thứ thiếu là **cái bắt người ta phải dùng nó**. Đúng kết
 * luận kiểm toán 26/07: *một danh sách lỗi đã biết mà không có cổng là danh sách lỗi sẽ lặp
 * lại* (kỷ luật #24).
 */
const SRC = resolve(__dirname, "..");

/** Tên trường `Decimal` backend phơi ra qua API — đọc từ chính schema Python, không chép tay. */
function truongDecimalTuBackend(): string[] {
  const goc = resolve(SRC, "../../backend/src/pharmacy_os/modules");
  const ten = new Set<string>();
  const quet = (thuMuc: string) => {
    for (const m of readdirSync(thuMuc)) {
      if (m === "__pycache__") continue;
      const duong = join(thuMuc, m);
      if (statSync(duong).isDirectory()) quet(duong);
      else if (m === "schemas.py") {
        for (const khop of readFileSync(duong, "utf8").matchAll(
          /^\s+([a-z_][a-z0-9_]*)\s*:\s*Decimal/gm,
        )) {
          ten.add(khop[1]);
        }
      }
    }
  };
  quet(goc);
  // Tự kiểm phép đo trước khi tin nó (kỷ luật #15). Danh sách rỗng — đường dẫn sai, hay
  // schema đổi cách khai — làm MỌI khẳng định bên dưới thành đúng vô nghĩa.
  expect(ten.size).toBeGreaterThan(20);
  return [...ten];
}

function tepTsx(goc: string = SRC): string[] {
  const ra: string[] = [];
  for (const m of readdirSync(goc)) {
    if (m === "node_modules") continue;
    const duong = join(goc, m);
    if (statSync(duong).isDirectory()) ra.push(...tepTsx(duong));
    else if (m.endsWith(".tsx")) ra.push(duong);
  }
  return ra;
}

describe("số thập phân của backend không được dựng thô vào màn", () => {
  it("mọi chỗ hiển thị trường Decimal đều đi qua hàm định dạng", () => {
    const truong = truongDecimalTuBackend();

    /**
     * Chỉ soi phép **DỰNG THẲNG** một trường ra màn, không soi mọi dòng có nhắc tới tên
     * trường. Ba dạng, đúng ba dạng đã gây lỗi thật hôm 04/08:
     *
     *     {r.quantity}                  {dong?.system_qty ?? "—"}       (x?.counted_qty ?? "—")
     *
     * 🔴 **Vì sao siết chặt thay vì quét rộng.** Bản đầu bắt mọi dòng chứa tên trường ⇒ 6
     * dương tính giả trên 13 (`csv.busy === "revenue"` · dựng payload · `diemGon(...)` đã
     * định dạng · `lech` đã qua `Number()`). Một cổng kêu oan một nửa số lần là cổng người
     * ta sẽ tắt, hoặc tệ hơn — thêm ngoại lệ theo phản xạ cho tới lúc nó không còn bắt gì.
     *
     * 🟠 **Giới hạn khai thẳng, không giấu:** quét theo DÒNG nên **không thấy** JSX bị
     * `prettier` ngắt qua nhiều dòng. Đây là **sàn**, không phải trần — cùng thân phận với
     * phép quét `target_type` ở `nhat-ky/nhan-hanh-vi.test.ts`, và ở đó bài học đã là "một
     * phép quét bám vào cách trình định dạng ngắt dòng là phép quét sẽ hỏng vào một ngày
     * không ai chọn".
     */
    const ten = truong.join("|");
    const mau = new RegExp(
      // 🔴 `(?<![\w$])` trước `(` là chỗ QUYẾT ĐỊNH: thiếu nó thì mẫu bắt luôn **mọi lời
      // gọi hàm** — `Number(d.quantity_sold)`, `money(d.sale_price)`, `formatQty(s.avg…)` —
      // tức 12 dương tính giả, trong đó có cả những chỗ ĐÃ định dạng đúng. Đo thật trước khi
      // sửa: bản không có lookbehind báo đỏ 12 dòng, không dòng nào là lỗi.
      // `(?<!\$)` loại `${…}` trong template literal: hai chỗ duy nhất còn lại là dựng KHOÁ
      // CACHE và lặp lại con số người dùng vừa gõ — không chỗ nào hiển thị Decimal của
      // backend. Đánh đổi có ý thức: mẫu này không soi template literal, nên nó là SÀN.
      String.raw`(?:(?<!\$)\{|(?<![\w$])\()\s*[A-Za-z_$][\w$]*\??\.(?:${ten})\s*(?:\?\?\s*"[^"]*"\s*)?[})]`,
    );

    const tho: string[] = [];
    for (const duong of tepTsx()) {
      const dong = readFileSync(duong, "utf8").split("\n");
      dong.forEach((line, i) => {
        if (!mau.test(line)) return;
        // Gán vào prop thì không phải hiển thị (`value=`, `busy=`…) — trừ `placeholder`,
        // vốn LÀ thứ người dùng đọc.
        if (/\b(?!placeholder)[a-zA-Z]+=\{/.test(line)) return;
        tho.push(`${relative(SRC, duong)}:${i + 1}  ${line.trim().slice(0, 80)}`);
      });
    }

    expect(
      tho,
      `Dựng thẳng Decimal của backend vào JSX — "100.000" sẽ đọc thành MỘT TRĂM NGHÌN. ` +
        `Dùng formatQty (số lượng) / formatMoney (tiền) / formatSo (giá trị trong ô nhập):\n` +
        tho.join("\n"),
    ).toEqual([]);
  });

  it("formatQty đọc đúng chuỗi Decimal mà backend thật sự trả về", () => {
    // Bốn giá trị này lấy NGUYÊN VĂN từ `GET /inventory/stock` trên CSDL qt650 ngày 04/08 —
    // không phải ví dụ tôi bịa ra cho vừa hàm. Đây là vế độc lập của phép so (kỷ luật #23).
    expect(formatQty("100.000")).toBe("100");
    expect(formatQty("5.000")).toBe("5");
    expect(formatQty("1077.000")).toBe("1.077");
    expect(formatQty("49.000")).toBe("49");
    // Phần lẻ THẬT thì phải giữ — nửa vỉ là chuyện có thật ở quầy.
    expect(formatQty("16.500")).toBe("16,5");
  });

  it("formatSo KHÔNG chấm hàng nghìn — nó dùng cho giá trị trong ô nhập", () => {
    // Chấm hàng nghìn trong một ô nhập là chỗ `"1.500"` được gửi lên máy chủ và hiểu thành
    // *một phẩy năm*: sai 1000 lần, và sai IM LẶNG.
    expect(formatSo("1500.000")).toBe("1500");
    expect(formatQty("1500.000")).toBe("1.500");
  });
});
