/**
 * Mô hình điều hướng — bốn tính chất, mỗi tính chất đã từng sai hoặc suýt sai.
 *
 * Vì sao test tệp này TRƯỚC mọi tệp khác: `shared/nav.ts` là chỗ **cả bốn** bề
 * mặt điều hướng cùng đọc (sidebar · thanh dưới · ngăn "Thêm" · lưới hành động
 * nhanh). Một lỗi ở đây hỏng cùng lúc bốn chỗ, và nó là loại lỗi `tsc` không bắt
 * được vì kiểu vẫn đúng.
 */
import { describe, expect, it } from "vitest";

import {
  bottomNavItems,
  BOTTOM_NAV_SLOTS,
  isActive,
  NAV,
  overflowNavItems,
  quickActionItems,
  visibleNav,
} from "./nav";

const ALL = NAV.map((i) => i.permission);
const CASHIER = ["sales.create"];

describe("gating theo quyền", () => {
  it("chỉ trả mục người dùng có quyền", () => {
    expect(visibleNav([]).length).toBe(0);
    expect(visibleNav(CASHIER).map((i) => i.href)).toEqual(["/"]);
    expect(visibleNav(ALL).length).toBe(NAV.length);
  });

  it("không mục nào lọt ra khi KHÔNG có quyền tương ứng", () => {
    for (const item of NAV) {
      const others = ALL.filter((p) => p !== item.permission);
      expect(visibleNav(others).map((i) => i.href)).not.toContain(item.href);
    }
  });
});

describe("thanh dưới", () => {
  it("tối đa 4 ô (ô thứ 5 luôn là 'Thêm')", () => {
    expect(bottomNavItems(ALL).length).toBe(BOTTOM_NAV_SLOTS - 1);
  });

  it("CO LẠI khi thiếu quyền — không độn ô giả", () => {
    // Một ô bấm vào không đi đâu là lời hứa suông; dự án đã bỏ kiểu đó từ Sprint 9.
    expect(bottomNavItems(CASHIER).map((i) => i.short)).toEqual(["Bán hàng"]);
    expect(bottomNavItems([]).length).toBe(0);
  });

  it("mỗi mục thanh dưới đều khai primary tường minh", () => {
    // Không dựa vào `slice()` cắt bớt hộ: mô hình phải nói đúng thứ nó làm.
    for (const item of bottomNavItems(ALL)) expect(item.primary).toBe(true);
  });
});

describe("ngăn 'Thêm' và lưới hành động nhanh", () => {
  it("Thêm chứa ĐÚNG phần còn lại, không trùng không sót", () => {
    const bar = bottomNavItems(ALL).map((i) => i.href);
    const more = overflowNavItems(ALL).map((i) => i.href);
    expect([...bar, ...more].sort()).toEqual(visibleNav(ALL).map((i) => i.href).sort());
    expect(more.filter((h) => bar.includes(h))).toEqual([]);
  });

  it("Cài đặt KHÔNG nằm trong lưới hành động nhanh", () => {
    // Lưới đó là chỗ bắt đầu một việc lúc 7h sáng, không phải mục lục — và giữ nó
    // nguyên vẹn là cách thêm màn mới mà màn Tổng quan không đổi một pixel.
    expect(quickActionItems(ALL).map((i) => i.href)).not.toContain("/cai-dat");
    expect(visibleNav(ALL).map((i) => i.href)).toContain("/cai-dat");
  });
});

describe("mục đang chọn", () => {
  it("so khớp CHÍNH XÁC, không phải startsWith", () => {
    // Route bán hàng là "/", mà mọi đường dẫn đều bắt đầu bằng "/" ⇒ startsWith
    // sẽ tô sáng "Bán hàng" ở MỌI màn.
    const sell = NAV.find((i) => i.href === "/")!;
    expect(isActive(sell, "/")).toBe(true);
    expect(isActive(sell, "/ton-kho")).toBe(false);
    expect(isActive(sell, "/bang-dieu-hanh")).toBe(false);
  });
});

describe("hai màn gộp một mục menu (Chain giao 2026-08-01)", () => {
  it("mục gộp SÁNG LÊN ở cả hai màn của nó", () => {
    // Không thì người dùng đang ở /kiem-ke mà menu không tô sáng gì — họ mất dấu mình
    // đang đứng ở đâu, đúng thứ mô hình điều hướng này sinh ra để tránh.
    const kho = NAV.find((i) => i.href === "/so-do-kho")!;
    expect(isActive(kho, "/so-do-kho")).toBe(true);
    expect(isActive(kho, "/kiem-ke")).toBe(true);
    expect(isActive(kho, "/ton-kho")).toBe(false);

    const nhap = NAV.find((i) => i.href === "/nhap-nhanh")!;
    expect(isActive(nhap, "/khoi-tao-ton")).toBe(true);
    expect(isActive(nhap, "/")).toBe(false);
  });

  it("KHÔNG màn nào mất lối vào khi gộp", () => {
    // 🔴 Tính chất thật sự đáng canh. Gộp menu là xoá bớt dòng khỏi NAV, và một dòng bị
    // xoá nhầm nghĩa là một màn còn sống nhưng KHÔNG CÒN CỬA NÀO VÀO — `tsc` không bắt
    // được, `build` không bắt được, và không ai nhận ra cho tới lúc cần dùng màn đó.
    const coLoiVao = new Set(NAV.flatMap((i) => [i.href, ...(i.alsoActiveFor ?? [])]));
    for (const man of [
      "/",
      "/bang-dieu-hanh",
      "/hoa-don",
      "/khach-hang",
      "/ton-kho",
      "/danh-muc-thuoc",
      "/nhap-nhanh",
      "/khoi-tao-ton",
      "/kiem-ke",
      "/so-do-kho",
      "/don-mua-hang",
      "/nha-cung-cap",
      "/de-xuat-dat-hang",
      "/bao-cao",
      "/nhan-vien",
      "/cai-dat",
    ]) {
      expect(coLoiVao).toContain(man);
    }
  });

  it("màn gộp KHÔNG xuất hiện hai lần trên menu", () => {
    const hrefs = new Set(NAV.map((i) => i.href));
    for (const i of NAV) for (const p of i.alsoActiveFor ?? []) expect(hrefs).not.toContain(p);
  });
});

describe("tính toàn vẹn của bảng NAV", () => {
  it("không trùng href", () => {
    const hrefs = NAV.map((i) => i.href);
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });

  it("nhãn ngắn đủ ngắn cho một ô rộng 20% màn hình", () => {
    for (const item of NAV) expect(item.short.length).toBeLessThanOrEqual(10);
  });
});
