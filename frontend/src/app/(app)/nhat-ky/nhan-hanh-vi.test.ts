import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { DOI_TUONG, NHAN, NHOM } from "./nhan-hanh-vi";

/**
 * 🔴 **Cổng bắt chéo hai ngôn ngữ.** Mã hành vi được khai bằng Python
 * (`AuditAction` trong `core/audit/entry.py`), nhãn tiếng Việt khai bằng TypeScript. Không
 * trình biên dịch nào nối được hai đầu — nên khi tôi tự đoán mã lúc dựng màn (01/08),
 * gần hết bảng nhãn sai (`STOCK_RECEIVED` thay vì `INVENTORY_STOCK_RECEIVED`,
 * `ROLE_ASSIGNED` thay vì `ROLE_GRANTED`) mà `tsc`, `eslint`, `pytest` đều xanh: mọi chuỗi
 * đều là chuỗi hợp lệ. Hậu quả là màn nhật ký **đầy chữ không ai đọc được**.
 *
 * Cùng họ với `styles.primary` (class không tồn tại) và `sales.refund` (quyền không tồn
 * tại): **một chuỗi sai không làm đỏ cổng nào**. Test này là chỗ nó đỏ được.
 */
const BACKEND = resolve(__dirname, "../../../../../backend/src/pharmacy_os");
const ENTRY_PY = resolve(BACKEND, "core/audit/entry.py");

function maThatTuBackend(): string[] {
  const src = readFileSync(ENTRY_PY, "utf8");
  const ma = [...src.matchAll(/^ {4}([A-Z][A-Z0-9_]+) = "([A-Z][A-Z0-9_]+)"$/gm)].map(
    (m) => m[2],
  );
  // Tự kiểm phép đo trước khi tin nó (kỷ luật #15: "phải đo cả chính phép đo"). Nếu đường
  // dẫn sai hay `AuditAction` đổi cách khai, ta sẽ nhận 0 mã — và một danh sách rỗng làm
  // MỌI khẳng định bên dưới thành đúng vô nghĩa.
  expect(ma.length).toBeGreaterThan(50);
  return ma;
}

describe("nhãn hành vi nhật ký", () => {
  it("mọi mã của backend đều có nhãn tiếng Việt", () => {
    const thieu = maThatTuBackend().filter((m) => !(m in NHAN));
    expect(thieu, `Mã chưa có nhãn — chúng sẽ hiện nguyên xi trên màn: ${thieu.join(", ")}`)
      .toEqual([]);
  });

  it("không có nhãn nào trỏ tới mã KHÔNG TỒN TẠI ở backend", () => {
    // Chiều ngược lại quan trọng không kém: một nhãn thừa không làm hỏng màn, nhưng nó là
    // dấu hiệu mã đã bị đổi tên ở backend — và dòng dùng tên MỚI thì đang hiện mã máy.
    const that = new Set(maThatTuBackend());
    const thua = Object.keys(NHAN).filter((m) => !that.has(m));
    expect(thua, `Nhãn trỏ tới mã không có ở backend: ${thua.join(", ")}`).toEqual([]);
  });

  it("mọi lựa chọn của bộ lọc đều là mã thật", () => {
    // Bộ lọc trỏ sai mã thì `select` vẫn đổi được, danh sách vẫn tải được — chỉ là **luôn
    // rỗng**. Đọc như "kỳ này không có hoạt động nào", không như một lỗi.
    const that = new Set(maThatTuBackend());
    const sai = NHOM.filter((n) => n.ma !== "" && !that.has(n.ma)).map((n) => n.ma);
    expect(sai, `Bộ lọc trỏ tới mã không tồn tại: ${sai.join(", ")}`).toEqual([]);
  });
});

describe("nhãn loại đối tượng", () => {
  /**
   * `target_type` không có enum — nó là chuỗi tự do truyền vào mỗi chỗ ghi audit. Nên phải
   * quét mã nguồn thay vì đọc một khai báo. Hai dạng gọi đang tồn tại:
   *   `target_type="drug"`                       (đặt tên tham số)
   *   `self._record(ctx, AuditAction.X, "drug", …)` (theo vị trí)
   */
  function loaiThatTuBackend(): string[] {
    const src = execFileSync(
      "grep",
      ["-rhoE", '--include=*.py', 'target_type="[a-z_]+"|_record\\(ctx, [^,]+, "[a-z_]+"', BACKEND],
      { encoding: "utf8" },
    );
    const ma = [...src.matchAll(/"([a-z_]+)"/g)].map((m) => m[1]);
    const duy = [...new Set(ma)].filter((m) => m !== "");
    // Tự kiểm phép đo: quét hỏng thì trả danh sách rỗng, và một danh sách rỗng làm mọi
    // khẳng định bên dưới thành đúng vô nghĩa (kỷ luật #15).
    expect(duy.length).toBeGreaterThan(10);
    return duy;
  }

  it("mọi loại đối tượng của backend đều có nhãn tiếng Việt", () => {
    const thieu = loaiThatTuBackend().filter((m) => !(m in DOI_TUONG));
    expect(thieu, `Loại đối tượng chưa có nhãn — sẽ hiện nguyên xi: ${thieu.join(", ")}`)
      .toEqual([]);
  });

  it("không có nhãn nào trỏ tới loại KHÔNG TỒN TẠI ở backend", () => {
    const that = new Set(loaiThatTuBackend());
    const thua = Object.keys(DOI_TUONG).filter((m) => !that.has(m));
    expect(thua, `Nhãn trỏ tới loại không có ở backend: ${thua.join(", ")}`).toEqual([]);
  });
});
