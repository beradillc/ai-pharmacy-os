import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { NAV } from "./nav";

/**
 * 🔴 **Cổng bắt chéo mã QUYỀN — Python ↔ TypeScript.**
 *
 * Kỷ luật #22 liệt kê *"mã quyền"* là một trong bốn chuỗi nối hai thế giới đã gây lỗi thật
 * trong ba ngày (30/07–01/08), với hậu quả riêng của nó: **cột hoặc nút không bao giờ
 * hiện**. Nhưng cổng canh nó thì **chưa ai dựng** — kỷ luật ghi lại bài học, không tự sinh
 * ra phép kiểm. Tệp này là phép kiểm ấy.
 *
 * Vì sao loại lỗi này không làm đỏ gì cả: `permissions.has("compliance.ledger.read")` nhận
 * một `string`, và `"compliance.ledger.reed"` cũng là một `string` hợp lệ. `tsc` xanh,
 * `eslint` xanh, `pytest` xanh. Kết quả: mục menu **không bao giờ xuất hiện** với bất kỳ
 * ai — và nó trông y hệt *"tính năng chưa làm"* chứ không giống *"gõ sai một chữ"*.
 *
 * Kiểm **cả hai chiều**:
 *   • mã dùng ở frontend mà Python không khai ⇒ nút/màn chết lặng;
 *   • mã Python khai mà frontend không dùng ⇒ **không phải lỗi**, chỉ là quyền dùng ở tầng
 *     API. Chiều này KHÔNG khẳng định — khẳng định nó sẽ ép mọi quyền mới phải có màn ngay,
 *     tức là bắt bảng nói dối cho vừa phép kiểm.
 */
const SYSTEM_ROLES_PY = resolve(
  __dirname,
  "../../../backend/src/pharmacy_os/modules/iam/domain/system_roles.py",
);
const APP_DIR = resolve(__dirname, "../app");
const FEATURES_DIR = resolve(__dirname, "../features");

function quyenThatTuBackend(): Set<string> {
  const src = readFileSync(SYSTEM_ROLES_PY, "utf8");
  const ma = [...src.matchAll(/"([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)"/g)].map((m) => m[1]);
  // Tự kiểm phép đo trước khi tin nó (kỷ luật #15). Đường dẫn sai hay cách khai đổi ⇒ 0 mã,
  // và một tập rỗng làm MỌI khẳng định bên dưới thành đúng vô nghĩa.
  expect(ma.length).toBeGreaterThan(40);
  return new Set(ma);
}

function tepNguon(goc: string): string[] {
  const ra: string[] = [];
  for (const ten of readdirSync(goc)) {
    const duong = join(goc, ten);
    if (statSync(duong).isDirectory()) ra.push(...tepNguon(duong));
    else if (/\.tsx?$/.test(ten) && !/\.test\.tsx?$/.test(ten)) ra.push(duong);
  }
  return ra;
}

/**
 * Mã quyền được **gác trong mã màn hình**: `quyen.has("…")`, `permissions.includes("…")`,
 * `.has("…")` trên một `Set` quyền.
 *
 * Bắt theo **hình dạng lời gọi**, không bắt mọi chuỗi có dấu chấm: `"vi-VN"`, `"page.tsx"`,
 * `"2026-08-01"` cũng có dấu chấm và sẽ làm cổng đỏ vì lý do sai — mà một cổng đỏ vì lý do
 * sai thì lần sau người ta tắt nó đi.
 */
function quyenDungOFrontend(): Map<string, string[]> {
  const ra = new Map<string, string[]>();
  const tep = [...tepNguon(APP_DIR), ...tepNguon(FEATURES_DIR)];
  expect(tep.length).toBeGreaterThan(20);

  for (const duong of tep) {
    const src = readFileSync(duong, "utf8");
    for (const m of src.matchAll(
      /(?:quyen|permissions|perms)\??\.(?:has|includes)\(\s*"([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)"/g,
    )) {
      ra.set(m[1], [...(ra.get(m[1]) ?? []), duong]);
    }
  }
  return ra;
}

describe("mã quyền khớp giữa Python và TypeScript", () => {
  it("mọi quyền gác một mục MENU đều có thật bên Python", () => {
    const that = quyenThatTuBackend();
    const sai = NAV.filter((i) => !that.has(i.permission)).map(
      (i) => `${i.href} → "${i.permission}"`,
    );
    expect(
      sai,
      `Mục menu gác bằng quyền KHÔNG TỒN TẠI ⇒ không ai thấy nó, và nó trông y hệt "chưa làm": ${sai.join(", ")}`,
    ).toEqual([]);
  });

  it("mọi quyền gác một nút/cột trong màn đều có thật bên Python", () => {
    const that = quyenThatTuBackend();
    const dung = quyenDungOFrontend();
    // Tự kiểm: lúc viết cổng có 6 chỗ gác quyền trong mã màn hình. 0 chỗ ⇒ mẫu nhận dạng
    // đã lạc hậu (đổi tên biến `quyen`), không phải màn hình hết gác quyền.
    expect(dung.size).toBeGreaterThanOrEqual(4);

    const sai = [...dung.entries()]
      .filter(([ma]) => !that.has(ma))
      .map(([ma, tep]) => `"${ma}" tại ${tep.map((t) => t.split("/src/")[1]).join(", ")}`);
    expect(sai, `Quyền KHÔNG TỒN TẠI ⇒ nút/cột chết lặng: ${sai.join(" · ")}`).toEqual([]);
  });

  it("mã quyền của màn Sổ kiểm soát đúng cả hai bậc", () => {
    const that = quyenThatTuBackend();
    // Vào màn: đọc. Ký sổ: một hành vi pháp lý không đảo ngược ⇒ quyền riêng.
    expect(that.has("compliance.ledger.read")).toBe(true);
    expect(that.has("compliance.ledger.sign")).toBe(true);
    expect(NAV.find((i) => i.href === "/so-kiem-soat")?.permission).toBe(
      "compliance.ledger.read",
    );
  });
});
