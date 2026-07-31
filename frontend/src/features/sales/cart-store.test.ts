import { describe, expect, it } from "vitest";

import { cartTotal, countPriceDeviations, type CartLine } from "./cart-store";

function dong(over: Partial<CartLine> = {}): CartLine {
  return {
    drugId: "d1",
    name: "Paracetamol 500mg",
    unitName: "viên",
    requiresPrescription: false,
    quantity: "1",
    unitPrice: "10000",
    listedPrice: "10000",
    ...over,
  };
}

describe("countPriceDeviations", () => {
  it("bán đúng giá niêm yết thì không có dòng nào lệch", () => {
    expect(countPriceDeviations([dong()])).toBe(0);
  });

  it("🔴 so bằng SỐ, không bằng chuỗi — 12000 và 12000.00 là cùng một giá", () => {
    // Máy chủ chuẩn hoá giá về 2 chữ số thập phân, nên `GET /drugs` trả "12000.00".
    // So chuỗi ở đây sẽ bắt quầy giải thích một khoản lệch không tồn tại.
    expect(
      countPriceDeviations([dong({ unitPrice: "12000", listedPrice: "12000.00" })]),
    ).toBe(0);
  });

  it("bán cao hơn giá niêm yết là lệch", () => {
    expect(countPriceDeviations([dong({ unitPrice: "12000" })])).toBe(1);
  });

  it("bán thấp hơn giá niêm yết cũng là lệch — Chain chọn phương án đối xứng", () => {
    expect(countPriceDeviations([dong({ unitPrice: "8000" })])).toBe(1);
  });

  it("mã CHƯA đặt giá niêm yết không tính là lệch", () => {
    // Không có giá niêm yết thì không có gì để lệch — trùng quy tắc máy chủ.
    expect(countPriceDeviations([dong({ listedPrice: null, unitPrice: "7000" })])).toBe(0);
  });

  it("đếm đúng số DÒNG lệch, không phải có-hay-không", () => {
    expect(
      countPriceDeviations([
        dong({ drugId: "a", unitPrice: "9000" }),
        dong({ drugId: "b" }),
        dong({ drugId: "c", unitPrice: "11000" }),
      ]),
    ).toBe(2);
  });
});

describe("cartTotal", () => {
  it("nhân số lượng với đơn giá của từng dòng", () => {
    expect(cartTotal([dong({ quantity: "3" }), dong({ drugId: "b", unitPrice: "5000" })])).toBe(
      35000,
    );
  });

  it("giỏ rỗng là 0 — thối lại phải tính được trước khi có hàng", () => {
    expect(cartTotal([])).toBe(0);
  });
});
