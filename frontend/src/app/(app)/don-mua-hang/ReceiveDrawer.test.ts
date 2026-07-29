import { afterEach, describe, expect, it, vi } from "vitest";

import { remainingOf } from "@/features/procurement/use-goods-receipt";

import { expiryNote } from "./ReceiveDrawer";

/** Ngày cố định, giữa ban ngày giờ Việt Nam. `vitest.config.ts` ghim
 * `TZ=Asia/Ho_Chi_Minh` để test đo mã, không đo máy chạy nó. */
const NOW = new Date("2026-07-29T14:00:00+07:00");

function at(iso: string) {
  vi.useFakeTimers();
  vi.setSystemTime(NOW);
  return expiryNote(iso);
}

afterEach(() => vi.useRealTimers());

describe("expiryNote — cảnh báo hạn dùng", () => {
  it("im lặng khi chưa nhập gì", () => {
    expect(at("")).toBeNull();
  });

  it("im lặng khi còn hạn dài", () => {
    expect(at("2027-07-29")).toBeNull();
  });

  it("cảnh báo vàng khi còn dưới 90 ngày", () => {
    const note = at("2026-09-01");
    expect(note?.expired).toBe(false);
    expect(note?.text).toContain("Còn 34 ngày");
  });

  it("ngưỡng đúng 90 ngày vẫn cảnh báo (bao gồm biên)", () => {
    expect(at("2026-10-27")?.text).toContain("Còn 90 ngày");
    expect(at("2026-10-28")).toBeNull();
  });

  it("cảnh báo ĐỎ khi đã quá hạn", () => {
    const note = at("2026-07-01");
    expect(note?.expired).toBe(true);
    expect(note?.text).toContain("Đã quá hạn 28 ngày");
  });

  it("🔴 lô hết hạn ĐÚNG HÔM NAY chưa tính là quá hạn", () => {
    // Hạn dùng ghi trên vỉ thuốc là ngày CÒN dùng được, không phải ngày đầu
    // tiên hỏng. Lệch một ngày ở đây là gán "quá hạn" cho hàng còn bán được,
    // và người nhận hàng sẽ học cách bỏ qua cảnh báo — lúc đó cảnh báo thật
    // cũng mất tác dụng.
    const note = at("2026-07-29");
    expect(note?.expired).toBe(false);
    expect(note?.text).toContain("Còn 0 ngày");
  });
});

describe("remainingOf — còn phải nhận bao nhiêu", () => {
  it("trừ số đã nhận cộng dồn, không phải lần này", () => {
    expect(remainingOf({ quantity_ordered: "100", quantity_received: "40" })).toBe(60);
  });

  it("nhận đủ thì còn 0 — dòng biến khỏi bảng nhận hàng", () => {
    expect(remainingOf({ quantity_ordered: "100", quantity_received: "100" })).toBe(0);
  });

  it("giữ được phần thập phân (thuốc bán lẻ theo viên/ml)", () => {
    expect(remainingOf({ quantity_ordered: "10.5", quantity_received: "0.5" })).toBe(10);
  });
});
