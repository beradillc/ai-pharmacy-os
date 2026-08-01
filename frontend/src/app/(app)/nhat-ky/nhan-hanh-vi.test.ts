import { execFileSync } from "node:child_process";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

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

/** Mọi tệp `.py` của backend — dùng chung cho các phép quét bắt chéo bên dưới. */
function tepPythonBackend(goc: string = BACKEND): string[] {
  const ra: string[] = [];
  for (const ten of readdirSync(goc)) {
    if (ten === "__pycache__") continue;
    const duong = join(goc, ten);
    if (statSync(duong).isDirectory()) ra.push(...tepPythonBackend(duong));
    else if (ten.endsWith(".py")) ra.push(duong);
  }
  return ra;
}

function maThatTuBackend(): string[] {
  const src = readFileSync(ENTRY_PY, "utf8");
  const ma = [
    ...src.matchAll(/^ {4}([A-Z][A-Z0-9_]+) = "([A-Z][A-Z0-9_]+)"$/gm),
  ].map((m) => m[2]);
  // Tự kiểm phép đo trước khi tin nó (kỷ luật #15: "phải đo cả chính phép đo"). Nếu đường
  // dẫn sai hay `AuditAction` đổi cách khai, ta sẽ nhận 0 mã — và một danh sách rỗng làm
  // MỌI khẳng định bên dưới thành đúng vô nghĩa.
  expect(ma.length).toBeGreaterThan(50);
  return ma;
}

describe("nhãn hành vi nhật ký", () => {
  it("mọi mã của backend đều có nhãn tiếng Việt", () => {
    const thieu = maThatTuBackend().filter((m) => !(m in NHAN));
    expect(
      thieu,
      `Mã chưa có nhãn — chúng sẽ hiện nguyên xi trên màn: ${thieu.join(", ")}`,
    ).toEqual([]);
  });

  it("không có nhãn nào trỏ tới mã KHÔNG TỒN TẠI ở backend", () => {
    // Chiều ngược lại quan trọng không kém: một nhãn thừa không làm hỏng màn, nhưng nó là
    // dấu hiệu mã đã bị đổi tên ở backend — và dòng dùng tên MỚI thì đang hiện mã máy.
    const that = new Set(maThatTuBackend());
    const thua = Object.keys(NHAN).filter((m) => !that.has(m));
    expect(
      thua,
      `Nhãn trỏ tới mã không có ở backend: ${thua.join(", ")}`,
    ).toEqual([]);
  });

  it("mọi lựa chọn của bộ lọc đều là mã thật", () => {
    // Bộ lọc trỏ sai mã thì `select` vẫn đổi được, danh sách vẫn tải được — chỉ là **luôn
    // rỗng**. Đọc như "kỳ này không có hoạt động nào", không như một lỗi.
    const that = new Set(maThatTuBackend());
    const sai = NHOM.filter((n) => n.ma !== "" && !that.has(n.ma)).map(
      (n) => n.ma,
    );
    expect(sai, `Bộ lọc trỏ tới mã không tồn tại: ${sai.join(", ")}`).toEqual(
      [],
    );
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
    // 🔴 ĐỌC CẢ TỆP, không quét theo DÒNG. Bản đầu dùng `grep -rhoE` với mẫu
    // `_record\(ctx, [^,]+, "[a-z_]+"` — mẫu ấy đòi `_record(` và `ctx,` nằm CÙNG một dòng,
    // nhưng `ruff format` xuống dòng những lời gọi dài, và bốn chỗ ghi audit có dạng:
    //
    //     await self._record(
    //         ctx, AuditAction.CONTROLLED_LEDGER_ENTRY_RECORDED, "controlled_ledger_entry", …
    //     )
    //
    // ⇒ `grep` không thấy chúng. Kiểm lại bằng chính lệnh cũ ngày 01/08: nó trả về 18 loại,
    // thiếu đúng `controlled_ledger_entry` · `tenant_compliance_config` · `ai_recommendation`
    // · `reorder_suggestion`.
    //
    // 🔴 VÀ VÌ SAO CỔNG VẪN XANH — chỗ này tinh vi hơn "phép quét mù": cổng có **hai chiều**
    // (thiếu nhãn / thừa nhãn), và bảng nhãn tình cờ **cũng thiếu đúng bốn loại đó**. Hai
    // cái sai KHỚP NHAU nên cả hai chiều đều xanh. Một cổng hai chiều chỉ chứng minh hai bên
    // **nhất quán**, không chứng minh bên nào **đúng** — nên phép quét phải tự kiểm bằng
    // một mốc bên ngoài (`length > 10`), và mốc đó cũng phải đủ cao để nhận ra thiếu bốn.
    //
    // Một phép quét bám vào cách TRÌNH ĐỊNH DẠNG ngắt dòng là một phép quét sẽ hỏng vào một
    // ngày không ai chọn.
    const ma = new Set<string>();
    for (const duong of tepPythonBackend()) {
      const src = readFileSync(duong, "utf8");
      for (const m of src.matchAll(/target_type\s*=\s*"([a-z][a-z0-9_]*)"/g))
        ma.add(m[1]);
      // Dạng theo vị trí: `_record(ctx, AuditAction.X, "loai", …)` — `[\s\S]` để qua được
      // xuống dòng, `{0,80}` để không nuốt sang lời gọi khác.
      for (const m of src.matchAll(
        /_record\([\s\S]{0,80}?AuditAction\.[A-Z_]+,\s*"([a-z][a-z0-9_]*)"/g,
      )) {
        ma.add(m[1]);
      }
    }
    const duy = [...ma].sort();
    // Tự kiểm phép đo: quét hỏng thì trả danh sách rỗng, và một danh sách rỗng làm mọi
    // khẳng định bên dưới thành đúng vô nghĩa (kỷ luật #15).
    expect(duy.length).toBeGreaterThan(10);
    return duy;
  }

  it("mọi loại đối tượng của backend đều có nhãn tiếng Việt", () => {
    const thieu = loaiThatTuBackend().filter((m) => !(m in DOI_TUONG));
    expect(
      thieu,
      `Loại đối tượng chưa có nhãn — sẽ hiện nguyên xi: ${thieu.join(", ")}`,
    ).toEqual([]);
  });

  it("không có nhãn nào trỏ tới loại KHÔNG TỒN TẠI ở backend", () => {
    const that = new Set(loaiThatTuBackend());
    const thua = Object.keys(DOI_TUONG).filter((m) => !that.has(m));
    expect(
      thua,
      `Nhãn trỏ tới loại không có ở backend: ${thua.join(", ")}`,
    ).toEqual([]);
  });
});
