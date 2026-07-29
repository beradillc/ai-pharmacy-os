import { describe, expect, it } from "vitest";

import { digitsOf, filterLoaded, looksLikePhone, PHONE_MIN_DIGITS } from "./use-customers";
import type { Customer } from "@/shared/api/types";

const c = (full_name: string, phone: string | null = null): Customer =>
  ({ id: crypto.randomUUID(), full_name, phone }) as Customer;

describe("looksLikePhone — chọn đường tra cứu", () => {
  it("số điện thoại đầy đủ ⇒ hỏi máy chủ", () => {
    for (const t of ["0901112223", "0901 112 223", "0901.112.223", "+84901112223"]) {
      expect(looksLikePhone(t), t).toBe(true);
    }
  });

  it("gõ dở chưa đủ số ⇒ CHƯA hỏi máy chủ", () => {
    // Hỏi máy chủ ở mỗi phím bấm là một lời gọi mạng cho mỗi chữ số, phần lớn
    // chắc chắn không ra gì. Đợi tới khi con số bắt đầu giống một số điện thoại.
    expect(looksLikePhone("090")).toBe(false);
    expect(looksLikePhone("0901112")).toBe(false);
    expect(digitsOf("0901112").length).toBe(PHONE_MIN_DIGITS - 1);
  });

  it("🔴 tên có lẫn số vẫn là TÊN, không phải số điện thoại", () => {
    // "Nguyễn Văn A 0901112223" là người ta dán cả dòng vào ô tìm kiếm. Nếu coi
    // là số điện thoại thì tra chính xác sẽ không ra gì, và màn hình báo "không
    // tìm thấy" trong khi khách đó CÓ trong hệ thống.
    expect(looksLikePhone("Nguyễn Văn A 0901112223")).toBe(false);
    expect(looksLikePhone("Phòng 12345678")).toBe(false);
  });

  it("ô rỗng không hỏi gì cả", () => {
    expect(looksLikePhone("")).toBe(false);
    expect(looksLikePhone("   ")).toBe(false);
  });
});

describe("digitsOf — chuẩn hoá giống backend", () => {
  it("bỏ mọi ký tự không phải chữ số", () => {
    expect(digitsOf("0901 112 223")).toBe("0901112223");
    expect(digitsOf("0901-112.223")).toBe("0901112223");
    expect(digitsOf("+84 901 112 223")).toBe("84901112223");
  });

  it("cùng một số gõ khác kiểu ⇒ cùng khoá cache, không gọi mạng lại", () => {
    const forms = ["0901112223", "0901 112 223", "0901.112.223", "  0901112223  "];
    expect(new Set(forms.map(digitsOf)).size).toBe(1);
  });
});

describe("filterLoaded — lọc theo tên trong trang đã tải", () => {
  const rows = [c("Nguyễn Văn An", "0901112223"), c("Trần Thị Bích"), c("Lê Văn Cường")];

  it("khớp một phần tên, không phân biệt hoa thường", () => {
    expect(filterLoaded(rows, "văn").map((r) => r.full_name)).toEqual([
      "Nguyễn Văn An",
      "Lê Văn Cường",
    ]);
  });

  it("ô rỗng trả nguyên trang, không lọc mất ai", () => {
    expect(filterLoaded(rows, "   ")).toHaveLength(3);
  });

  it("khách chưa có số điện thoại không làm hỏng bộ lọc", () => {
    expect(() => filterLoaded(rows, "0901")).not.toThrow();
    expect(filterLoaded(rows, "0901")).toHaveLength(1);
  });
});
