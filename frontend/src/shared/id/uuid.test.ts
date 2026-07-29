import { afterEach, describe, expect, it, vi } from "vitest";

import { randomUuid } from "./uuid";

const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

/**
 * 🔴 Test này phải chạy được ở CẢ HAI thế giới, vì đó chính là lỗi nó canh.
 *
 * `vitest` chạy trong Node — nơi `crypto.randomUUID` LUÔN tồn tại. Đó là lý do
 * bộ test cũ không thấy gì trong khi POS không bán được trên bất kỳ điện thoại
 * nào: điện thoại mở qua địa chỉ LAN, ngữ cảnh không bảo mật, `randomUUID` là
 * `undefined`. Nên ở đây phải **cố ý xoá `randomUUID` đi** rồi chạy lại.
 */
afterEach(() => vi.unstubAllGlobals());

describe("randomUuid", () => {
  it("dùng crypto.randomUUID khi có (ngữ cảnh bảo mật / localhost)", () => {
    expect(randomUuid()).toMatch(V4);
  });

  it("🔴 vẫn sinh được UUID v4 hợp lệ khi KHÔNG có crypto.randomUUID (qua LAN)", () => {
    const real = globalThis.crypto;
    vi.stubGlobal("crypto", { getRandomValues: real.getRandomValues.bind(real) });
    expect(globalThis.crypto.randomUUID).toBeUndefined();
    expect(randomUuid()).toMatch(V4);
  });

  it("không trùng nhau — client_uuid là khoá chống trùng đơn, trùng là nuốt mất một lần bán", () => {
    const real = globalThis.crypto;
    vi.stubGlobal("crypto", { getRandomValues: real.getRandomValues.bind(real) });
    const seen = new Set(Array.from({ length: 2000 }, () => randomUuid()));
    expect(seen.size).toBe(2000);
  });
});
