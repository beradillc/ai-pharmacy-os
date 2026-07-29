import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { PO_STATUS_LABEL, PO_STATUSES } from "./use-purchase-orders";

/**
 * 🔴 Cổng canh một lỗi KHÔNG cổng nào khác thấy được.
 *
 * TypeScript kiểm kiểu trong phạm vi TypeScript. Enum trạng thái đơn mua sống
 * ở Python, đi qua JSON dưới dạng `string`, và tới đây thì mọi chuỗi đều hợp
 * lệ. Nên khi backend thêm `RECEIVED`, giao diện *không hỏng* — nó chỉ âm thầm
 * bỏ sót đúng những đơn đã nhận đủ hàng: rơi khỏi bộ lọc, hiện mã thô. Lệch đó
 * sống được **suốt Sprint 10** cho tới khi dựng màn Nhận hàng mới lộ ra.
 *
 * Test này **đọc file Python thật**. Chép enum sang một hằng số trong test là
 * so bản sao với bản sao — hai bản cùng cũ đi thì test vẫn xanh, đúng cái bẫy
 * làm lỗi này lọt lần đầu.
 */
const ENTITIES_PY = join(
  __dirname,
  "../../../../backend/src/pharmacy_os/modules/procurement/domain/entities.py",
);

function backendStatuses(): string[] {
  const src = readFileSync(ENTITIES_PY, "utf8");
  const block = /class PurchaseOrderStatus\(StrEnum\):\n((?:\s{4}\w+ = "[^"]+"\n)+)/.exec(src);
  if (!block) throw new Error(`Không tìm thấy enum PurchaseOrderStatus trong ${ENTITIES_PY}`);
  return [...block[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]);
}

describe("PO_STATUSES khớp enum backend", () => {
  it("đọc được enum từ mã nguồn Python", () => {
    // Nếu backend đổi cách viết enum, test dưới sẽ đỏ vì lý do SAI (mảng rỗng
    // so mảng rỗng thì bằng nhau). Chặn ở đây.
    expect(backendStatuses().length).toBeGreaterThanOrEqual(5);
  });

  it("không thiếu trạng thái nào so với backend", () => {
    expect([...PO_STATUSES].sort()).toEqual(backendStatuses().sort());
  });

  it("mọi trạng thái đều có nhãn tiếng Việt", () => {
    for (const s of backendStatuses()) {
      expect(PO_STATUS_LABEL[s], `thiếu nhãn cho "${s}"`).toBeTruthy();
      expect(PO_STATUS_LABEL[s]).not.toBe(s);
    }
  });
});
