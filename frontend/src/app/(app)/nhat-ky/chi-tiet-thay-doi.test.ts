import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

import { describe, expect, it } from "vitest";

import {
  NHAN_TRUONG,
  TAC_NHAN_HE_THONG,
  nhanThietBi,
  tenNguoiThucHien,
  thayDoiGiaTri,
} from "./chi-tiet-thay-doi";

/**
 * 🔴 **Cổng bắt chéo hai ngôn ngữ — cùng khuôn `nhan-hanh-vi.test.ts`, khác đối tượng.**
 *
 * Ở đó chuỗi cần khớp là **mã hành vi** (`AuditAction`). Ở đây là **tên khoá trong
 * `context`** — và khoá này còn khó thấy hơn: nó không được khai ở một chỗ nào cả, nó là
 * **đối số từ khoá** rải trong các lời gọi `.with_context(...)` khắp 12 module. Gõ sai
 * `old_prices` thì `tsc` xanh, `pytest` xanh, và màn hình **im lặng không hiện thay đổi
 * nào** — đúng thứ M-05 sinh ra để sửa.
 *
 * Kiểm **cả hai chiều** (kỷ luật #22): thiếu nhãn ⇒ mã máy lọt ra màn tiếng Việt; thừa nhãn
 * ⇒ bên Python đã đổi tên mà bên này chưa biết, và dòng dùng tên **mới** đang hỏng lặng lẽ.
 */
const BACKEND = resolve(__dirname, "../../../../../backend/src/pharmacy_os");

function tepPython(goc: string): string[] {
  const ra: string[] = [];
  for (const ten of readdirSync(goc)) {
    const duong = join(goc, ten);
    if (statSync(duong).isDirectory()) ra.push(...tepPython(duong));
    else if (ten.endsWith(".py")) ra.push(duong);
  }
  return ra;
}

/**
 * Các đuôi trường có cặp cũ/mới **đầy đủ** ở phía Python — thứ màn hình phải dịch được.
 *
 * 🔴 Quét **toàn bộ tệp**, không chỉ phần trong ngoặc `.with_context(...)`. Bản đầu của cổng
 * này chỉ quét trong ngoặc và tìm được **0 cặp** dù backend đang ghi 2 — vì mọi module đều
 * gói audit sau một helper riêng (`self._record(ctx, action, id, old_price=…, new_price=…)`)
 * rồi mới `**extra` vào `with_context`. Phép đo tự kiểm đã bắt được chính nó (kỷ luật #15,
 * *"phải đo cả chính phép đo"*); không có ngưỡng `>= 2` thì cổng đã **xanh trọn vẹn trong
 * lúc không đo gì cả**.
 *
 * Điều kiện **đủ cả hai vế** cũng là thứ loại `new_password=` — một tham số hàm, không phải
 * khoá ngữ cảnh — mà không cần danh sách loại trừ viết tay.
 */
function truongCuMoiCuaBackend(): string[] {
  const tep = [...tepPython(join(BACKEND, "modules")), ...tepPython(join(BACKEND, "core"))];
  // Tự kiểm phép quét trước khi tin nó (kỷ luật #15).
  expect(tep.length).toBeGreaterThan(50);

  const cu = new Set<string>();
  const moi = new Set<string>();
  for (const duong of tep) {
    const src = readFileSync(duong, "utf8");
    for (const m of src.matchAll(/\bold_([a-z][a-z_]*)\s*=/g)) cu.add(m[1]);
    for (const m of src.matchAll(/\bnew_([a-z][a-z_]*)\s*=/g)) moi.add(m[1]);
    for (const m of src.matchAll(/\b([a-z][a-z_]*)_before\s*=/g)) cu.add(m[1]);
    for (const m of src.matchAll(/\b([a-z][a-z_]*)_after\s*=/g)) moi.add(m[1]);
  }
  const dayDu = [...cu].filter((t) => moi.has(t)).sort();
  // Lúc viết cổng này backend có đúng 2 cặp (`price`, `count`). 0 cặp nghĩa là phép quét
  // hỏng, KHÔNG phải backend sạch — và 0 cặp làm mọi khẳng định dưới đây thành đúng vô nghĩa.
  expect(dayDu.length).toBeGreaterThanOrEqual(2);
  return dayDu;
}

describe("nhãn trường cũ → mới (bắt chéo Python ↔ TypeScript)", () => {
  it("mọi cặp cũ/mới backend đang ghi đều có nhãn tiếng Việt", () => {
    const thieu = truongCuMoiCuaBackend().filter((t) => !(t in NHAN_TRUONG));
    expect(
      thieu,
      `Trường chưa có nhãn — sẽ hiện nguyên tên máy giữa tiếng Việt: ${thieu.join(", ")}`,
    ).toEqual([]);
  });

  it("không có nhãn thừa trỏ vào trường backend không còn ghi", () => {
    const that = new Set(truongCuMoiCuaBackend());
    const thua = Object.keys(NHAN_TRUONG).filter((t) => !that.has(t));
    expect(
      thua,
      `Nhãn trỏ vào trường backend không ghi — hoặc đã đổi tên, hoặc gõ sai: ${thua.join(", ")}`,
    ).toEqual([]);
  });
});

describe("ghép cặp giá trị cũ → mới", () => {
  it("ghép được cặp old_/new_", () => {
    expect(thayDoiGiaTri({ old_price: "20000", new_price: "25000" })).toEqual([
      { truong: "price", nhan: "Giá bán", cu: "20000", moi: "25000" },
    ]);
  });

  it("ghép được cặp _before/_after", () => {
    expect(thayDoiGiaTri({ count_before: "2", count_after: "0" })).toEqual([
      { truong: "count", nhan: "Số hoạt chất", cu: "2", moi: "0" },
    ]);
  });

  it("KHÔNG hiện khi thiếu một vế — '→ 25.000' đọc như 'giá cũ là rỗng'", () => {
    expect(thayDoiGiaTri({ new_price: "25000" })).toEqual([]);
    expect(thayDoiGiaTri({ old_price: "20000" })).toEqual([]);
  });

  it("bỏ qua khoá ngữ cảnh thường, không nhận nhầm", () => {
    expect(thayDoiGiaTri({ client_ip: "10.0.0.1", branch_id: "abc", user_agent: "x" })).toEqual(
      [],
    );
  });

  it("trường lạ vẫn hiện, chỉ là chưa có nhãn — không giấu dòng", () => {
    expect(thayDoiGiaTri({ old_zzz: "1", new_zzz: "2" })).toEqual([
      { truong: "zzz", nhan: "zzz", cu: "1", moi: "2" },
    ]);
  });
});

describe("người thực hiện", () => {
  const tra = (id: string) => (id === "aaaa1111-0000-0000-0000-000000000000" ? "Chị Thu" : undefined);

  it("tra được tên thì hiện tên", () => {
    expect(tenNguoiThucHien("aaaa1111-0000-0000-0000-000000000000", tra)).toBe("Chị Thu");
  });

  it("không có tác nhân ⇒ 'hệ thống'", () => {
    expect(tenNguoiThucHien(null, tra)).toBe("hệ thống");
  });

  it.each(Object.keys(TAC_NHAN_HE_THONG))(
    "🔴 tác nhân hệ thống %s ⇒ nhãn chữ, KHÔNG phải 'Mã 00000000'",
    (ma) => {
      // Ảnh chụp 01/08 bắt được ca này; không phép đo nào trong cổng trình duyệt thấy, vì
      // `Mã 00000000` là một mã rút gọn hợp lệ về mọi mặt trừ ý nghĩa.
      //
      // Khẳng định là "KHÔNG rơi về mã hex", không phải "phải bắt đầu bằng 'hệ thống'":
      // `_DEV_USER` cố ý mang nhãn cảnh báo chứ không phải nhãn hệ thống, và ép mọi nhãn
      // vào một khuôn chữ là bắt bảng nhãn nói dối cho vừa phép kiểm.
      expect(tenNguoiThucHien(ma, tra)).not.toMatch(/^Mã /);
      expect(tenNguoiThucHien(ma, tra)).toBe(TAC_NHAN_HE_THONG[ma]);
    },
  );

  it("tra không ra thì hiện mã rút gọn, không bỏ trống", () => {
    expect(tenNguoiThucHien("bbbb2222-0000-0000-0000-000000000000", tra)).toBe("Mã bbbb2222");
  });

  it("🔴 MỌI mã hệ thống khai bên Python đều có nhãn (bắt chéo, cả hai chiều)", () => {
    // Kỷ luật #22: **đọc** nguồn bên kia, không chép lại nó. Bản vá đầu chỉ biết một mã
    // (`UUID(int=0)`) và để lọt ba mã còn lại — cổng trình duyệt vẫn đỏ đúng 4 dòng.
    // Bắt theo **tên hằng**, không bắt mọi UUID trông giống: chỉ hằng có `USER`/`ACTOR`
    // trong tên mới bao giờ đi vào `actor_user_id`. `_DEV_TENANT`/`_DEV_BRANCH` cũng là
    // UUID canh mở đầu bằng 8 số 0 nhưng **không phải tác nhân** — gán nhãn cho chúng là
    // dựng một bảng nói dối theo hướng ngược lại.
    const that = new Set<string>();
    for (const duong of tepPython(join(BACKEND, "api")).concat(
      tepPython(join(BACKEND, "modules")),
    )) {
      const src = readFileSync(duong, "utf8");
      for (const m of src.matchAll(
        /^_?[A-Z][A-Z0-9_]*(?:USER|ACTOR)[A-Z0-9_]*\s*(?::[^=]+)?=\s*UUID\("([0-9a-f-]{36})"\)/gm,
      )) {
        that.add(m[1].toLowerCase());
      }
      if (
        /^_?[A-Z][A-Z0-9_]*(?:USER|ACTOR)[A-Z0-9_]*\s*(?::[^=]+)?=\s*UUID\(int=0\)/m.test(src)
      ) {
        that.add("00000000-0000-0000-0000-000000000000");
      }
    }
    // Tự kiểm phép quét (kỷ luật #15): 0 mã ⇒ phép quét hỏng, không phải mã nguồn sạch.
    // Lúc viết cổng: 5 mã (1× UUID(int=0) + 3× 5a1e* + 1× _DEV_USER).
    expect(that.size).toBeGreaterThanOrEqual(5);

    const thieu = [...that].filter((m) => !(m in TAC_NHAN_HE_THONG));
    expect(thieu, `Mã hệ thống chưa có nhãn — sẽ hiện "Mã 00000000": ${thieu.join(", ")}`).toEqual(
      [],
    );

    const thua = Object.keys(TAC_NHAN_HE_THONG).filter((m) => !that.has(m));
    expect(thua, `Nhãn trỏ vào mã Python không còn khai: ${thua.join(", ")}`).toEqual([]);
  });
});

describe("nhãn thiết bị từ User-Agent", () => {
  const CA: [string, string][] = [
    [
      "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
      "iPhone · Safari",
    ],
    [
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Máy tính · Chrome",
    ],
    [
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36 Edg/120.0",
      "Máy tính · Edge",
    ],
    [
      "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36",
      "Điện thoại Android · Chrome",
    ],
    [
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/121.0",
      "Máy tính · Firefox",
    ],
    [
      "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Safari/604.1",
      "iPad · Safari",
    ],
  ];

  it.each(CA)("đọc đúng: %s", (ua, mong) => {
    expect(nhanThietBi(ua)).toBe(mong);
  });

  it("không có User-Agent thì trả null, KHÔNG bịa 'Không rõ'", () => {
    expect(nhanThietBi(undefined)).toBeNull();
    expect(nhanThietBi("")).toBeNull();
  });

  it("chuỗi lạ vẫn hiện phần đầu, để người soát sổ thấy có cái gì đó lạ", () => {
    expect(nhanThietBi("curl/8.4.0")).toBe("curl/8.4.0…");
  });

  it("Edge đứng trước Chrome — Edge tự khai cả 'Chrome' lẫn 'Safari' trong UA", () => {
    expect(nhanThietBi("Windows Chrome/1 Safari/2 Edg/3")).toBe("Máy tính · Edge");
  });
});
