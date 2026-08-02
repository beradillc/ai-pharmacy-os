import { describe, expect, it } from "vitest";

import { ApiError, thongDiepLoi } from "./errors";

/**
 * 🔴 **Lỗi 422 phải đọc được bằng tiếng Việt VÀ nói rõ ô nào.**
 *
 * Ca thật, quay video 02 ngày 02/08: dược sĩ bấm "Lưu thông tin cơ sở" và nhận đúng dòng
 * `String should have at most 12 characters` — tiếng Anh, không nói ô nào, không nói phải
 * làm gì. Trường `loc` chứa sẵn tên ô thì bị vứt đi.
 *
 * Không cổng nào bắt được: `tsc` xanh (chuỗi vẫn là chuỗi), `eslint` xanh, và cổng trình
 * duyệt chỉ kiểm *có hiện thông báo lỗi không*, không kiểm *thông báo ấy có đọc được không*.
 * Nó lộ ra vì có người NHÌN vào khung hình bản quay.
 */
function loi422(chiTiet: unknown) {
  return new ApiError({
    type: "https://errors.pharmacy-os/validation",
    title: "Dữ liệu không hợp lệ",
    status: 422,
    detail: chiTiet,
  } as never);
}

describe("thông điệp lỗi 422 đọc được", () => {
  it("ghép TÊN Ô với thông điệp đã dịch", () => {
    const s = thongDiepLoi(
      loi422([
        {
          type: "string_too_long",
          loc: ["body", "ma_co_so_ban_le"],
          msg: "String should have at most 12 characters",
        },
      ]),
    );
    expect(s).toBe("Mã cơ sở bán lẻ: tối đa 12 ký tự");
    expect(s).not.toMatch(/String should have/);
  });

  it("nhiều lỗi thì nối lại, mỗi lỗi vẫn có tên ô", () => {
    const s = thongDiepLoi(
      loi422([
        { loc: ["body", "ten_co_so"], msg: "Field required" },
        { loc: ["body", "dien_thoai"], msg: "String should have at least 8 characters" },
      ]),
    );
    expect(s).toBe("Tên cơ sở: chưa điền · Điện thoại: cần ít nhất 8 ký tự");
  });

  it("ô chưa có nhãn tiếng Việt thì dùng tên gốc, KHÔNG bịa", () => {
    const s = thongDiepLoi(loi422([{ loc: ["body", "truong_la_hoac"], msg: "Field required" }]));
    expect(s).toBe("truong_la_hoac: chưa điền");
  });

  it("thông điệp chưa dịch được thì GIỮ NGUYÊN VĂN, không đoán", () => {
    // Thà một câu tiếng Anh có kèm tên ô, còn hơn một câu tiếng Việt đoán sai nghĩa.
    const s = thongDiepLoi(loi422([{ loc: ["body", "ma_so_thue"], msg: "Value error, kiểu lạ" }]));
    expect(s).toBe("Mã số thuế: Value error, kiểu lạ");
  });

  it("detail là chuỗi thì giữ nguyên (lỗi nghiệp vụ, đã tiếng Việt sẵn)", () => {
    expect(thongDiepLoi(loi422("Không đủ tồn: cần 12, còn 10"))).toBe(
      "Không đủ tồn: cần 12, còn 10",
    );
  });
});
