/**
 * Định dạng số/ngày/tiền.
 *
 * Mọi con số người dùng đọc đều đi qua đây, và **hai trong số các hàm này đã từng
 * hiện sai ra màn hình** (ngày ISO thay vì dd/mm/yyyy; ký hiệu ₫ rơi font). Chúng
 * là hàm thuần, không cớ gì để không có test.
 */
import { describe, expect, it } from "vitest";

import { CURRENCY, daysOfStockLeft, formatDate, formatMoney, formatQty, money } from "./number";

describe("tiền", () => {
  it("nhóm hàng nghìn theo kiểu Việt (dấu chấm)", () => {
    expect(formatMoney("2393000")).toBe("2.393.000");
    expect(formatMoney("0")).toBe("0");
  });

  it("KHÔNG ép sang number sớm — nhận chuỗi Decimal của backend", () => {
    // Backend trả Decimal dạng chuỗi; ép sang number sớm là tự chuốc sai số dấu
    // phẩy động lên đúng những con số người ta mang đi đối chiếu với sổ.
    expect(formatMoney("28487900.00000")).toBe("28.487.900");
  });

  it("chuỗi không phải số thì trả nguyên, không ra NaN", () => {
    expect(formatMoney("không-phải-số")).toBe("không-phải-số");
  });

  it("ký hiệu tiền là 'đ' — chữ cái tiếng Việt, chắc chắn có trong font đã nhúng", () => {
    // ₫ (U+20AB) KHÔNG nằm trong bộ Be Vietnam Pro đã nhúng ⇒ rơi về font dự
    // phòng, nét khác hẳn phần số ngay cạnh. Thấy rõ trên ảnh chụp 29/07.
    expect(CURRENCY).toBe("đ");
    expect(money("536300")).toBe("536.300 đ");
  });
});

describe("số lượng", () => {
  it("bỏ số 0 thừa sau dấu phẩy", () => {
    expect(formatQty("16.000")).toBe("16");
    expect(formatQty("16.500")).toBe("16,5");
  });
});

describe("ngày", () => {
  it("đổi ISO sang dd/mm/yyyy", () => {
    // Dược sĩ đọc hạn dùng trên hộp thuốc là 05/09/2027, không phải 2027-09-05.
    expect(formatDate("2027-09-05")).toBe("05/09/2027");
    expect(formatDate("2026-08-12T00:00:00Z")).toBe("12/08/2026");
  });

  it("chuỗi lạ thì trả nguyên thay vì ra 'NaN/NaN/NaN'", () => {
    expect(formatDate("chưa rõ")).toBe("chưa rõ");
  });
});

describe("số ngày còn hàng", () => {
  it("làm tròn XUỐNG — thà báo sớm còn hơn báo muộn", () => {
    expect(daysOfStockLeft("100", "12")).toBe(8);
  });

  it("tốc độ bán 0 hoặc âm ⇒ null, KHÔNG ra vô cực", () => {
    // "Còn Infinity ngày" là câu vô nghĩa với người đứng quầy.
    expect(daysOfStockLeft("100", "0")).toBeNull();
    expect(daysOfStockLeft("100", "-1")).toBeNull();
  });

  it("dữ liệu hỏng ⇒ null", () => {
    expect(daysOfStockLeft("x", "1")).toBeNull();
  });
});
