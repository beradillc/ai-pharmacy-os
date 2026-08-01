import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { LOC_TRANG_THAI, NGUON_DON, TRANG_THAI_DON } from "./nhan-don-thuoc";

/**
 * 🔴 Cổng bắt chéo hai ngôn ngữ — kỷ luật #22 (đề nghị 01/08).
 *
 * `PrescriptionStatus` khai bằng Python, nhãn khai bằng TypeScript, không trình biên dịch
 * nào nối hai đầu. Thêm một trạng thái ở backend mà quên nhãn ⇒ màn hiện `DRAFT` nguyên xi
 * giữa tiếng Việt, và `tsc`/`eslint`/`pytest` xanh hết vì mọi chuỗi đều hợp lệ.
 */
const ENTITIES_PY = resolve(
  __dirname,
  "../../../../backend/src/pharmacy_os/modules/prescription/domain/entities.py",
);

function maCua(enumName: string): string[] {
  const src = readFileSync(ENTITIES_PY, "utf8");
  const khoi = src.split(`class ${enumName}(StrEnum):`)[1];
  expect(khoi, `Không tìm thấy enum ${enumName} — phép đo hỏng, không phải sản phẩm`).toBeDefined();
  // Dừng ở dòng trống kép (hết khối enum), không quét sang class kế tiếp.
  const than = khoi.split("\n\n")[0];
  const ma = [...than.matchAll(/^ {4}[A-Z_]+ = "([A-Z_]+)"$/gm)].map((m) => m[1]);
  // Tự kiểm phép đo: danh sách rỗng làm mọi khẳng định phía sau đúng vô nghĩa (#15).
  expect(ma.length).toBeGreaterThan(2);
  return ma;
}

describe("nhãn đơn thuốc", () => {
  it("mọi trạng thái của backend đều có nhãn tiếng Việt", () => {
    const thieu = maCua("PrescriptionStatus").filter((m) => !(m in TRANG_THAI_DON));
    expect(thieu, `Trạng thái chưa có nhãn: ${thieu.join(", ")}`).toEqual([]);
  });

  it("mọi nguồn đơn của backend đều có nhãn tiếng Việt", () => {
    const thieu = maCua("PrescriptionSource").filter((m) => !(m in NGUON_DON));
    expect(thieu, `Nguồn đơn chưa có nhãn: ${thieu.join(", ")}`).toEqual([]);
  });

  it("không có nhãn nào trỏ tới trạng thái KHÔNG TỒN TẠI", () => {
    // Chiều ngược lại: nhãn thừa nghĩa là backend đã đổi tên, và dòng dùng tên MỚI đang
    // hiện mã máy mà không ai biết.
    const that = new Set(maCua("PrescriptionStatus"));
    const thua = Object.keys(TRANG_THAI_DON).filter((m) => !that.has(m));
    expect(thua, `Nhãn trỏ tới trạng thái không có ở backend: ${thua.join(", ")}`).toEqual([]);
  });

  it("mọi lựa chọn của bộ lọc đều là trạng thái thật", () => {
    // Bộ lọc trỏ sai mã thì màn vẫn chạy, chỉ **luôn rỗng** — đọc như "kỳ này không có
    // đơn nào", không như một lỗi.
    const that = new Set(maCua("PrescriptionStatus"));
    const sai = LOC_TRANG_THAI.filter((n) => n.ma !== "" && !that.has(n.ma)).map((n) => n.ma);
    expect(sai, `Bộ lọc trỏ tới trạng thái không tồn tại: ${sai.join(", ")}`).toEqual([]);
  });
});
