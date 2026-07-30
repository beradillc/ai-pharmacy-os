/**
 * Hàng chờ bán offline — canh đúng một điều: **đơn không được biến mất**.
 *
 * 🔴 Vì sao file này tồn tại. Trước 31/07, đơn bị máy chủ từ chối bị `delete()` khỏi
 * IndexedDB rồi đẩy vào một biến state React mà **không màn nào đọc**. State chết khi rời
 * trang ⇒ đơn biến mất không dấu vết. Thu ngân đã thu tiền của khách, đơn không tồn tại ở
 * đâu cả, và không ai biết. Đó là mất dữ liệu, không phải lỗi giao diện.
 *
 * Không cổng nào khác canh được chuyện này: nó nằm trong IndexedDB của trình duyệt, không
 * phải trong CSDL máy chủ, nên backend test không thấy; và nó chỉ xảy ra khi mất mạng rồi
 * có lại, nên cổng trình duyệt thường cũng không đi qua.
 */
import "fake-indexeddb/auto";

import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/shared/api/errors";
import type { CreateSaleRequest } from "@/shared/api/types";

import { offlineDb } from "./db";
import {
  discardRejected,
  enqueueSale,
  flushQueue,
  pendingSalesCount,
  rejectedSales,
  rejectedSalesCount,
  retryRejected,
} from "./sync-queue";

const { apiFetch } = vi.hoisted(() => ({ apiFetch: vi.fn() }));
vi.mock("@/shared/api/client", () => ({ apiFetch }));

function don(uuid: string): CreateSaleRequest {
  return {
    client_uuid: uuid,
    lines: [{ drug_id: "d1", quantity: "1", unit_price: "10000", requires_prescription: false }],
    payments: [{ method: "CASH", amount: "10000" }],
  };
}

const loiNghiepVu = (detail: string, status = 422) =>
  new ApiError({ type: "x", title: "Không bán được", status, detail, instance: "/sync/sales" });

beforeEach(async () => {
  apiFetch.mockReset();
  await offlineDb.pendingSales.clear();
  await offlineDb.rejectedSales.clear();
});

describe("đơn bị máy chủ từ chối", () => {
  it("🔴 KHÔNG biến mất — chuyển sang bảng từ-chối, không xoá", async () => {
    await enqueueSale(don("a"));
    apiFetch.mockRejectedValueOnce(loiNghiepVu("Đơn có 1 cảnh báo dị ứng"));

    await flushQueue();

    expect(await pendingSalesCount()).toBe(0); // đã rời hàng chờ
    expect(await rejectedSalesCount()).toBe(1); // nhưng VẪN CÒN
  });

  it("giữ nguyên văn lý do và mã trạng thái", async () => {
    await enqueueSale(don("a"));
    apiFetch.mockRejectedValueOnce(loiNghiepVu("Không đủ tồn kho cho Paracetamol", 409));

    await flushQueue();
    const [r] = await rejectedSales();
    expect(r.reason).toBe("Không đủ tồn kho cho Paracetamol");
    expect(r.status).toBe(409);
    // Thu ngân cần đọc ĐÚNG câu máy chủ nói để biết sửa gì — rút gọn là làm mất thông tin.
  });

  it("giữ nguyên nội dung đơn để còn bán lại được", async () => {
    await enqueueSale(don("a"));
    apiFetch.mockRejectedValueOnce(loiNghiepVu("x"));
    await flushQueue();
    const [r] = await rejectedSales();
    expect(r.request.lines).toHaveLength(1);
    expect(r.request.client_uuid).toBe("a");
  });

  it("ghi cả lúc BÁN lẫn lúc BỊ TỪ CHỐI — hai mốc có thể cách nhau hàng giờ", async () => {
    await enqueueSale(don("a"));
    apiFetch.mockRejectedValueOnce(loiNghiepVu("x"));
    await flushQueue();
    const [r] = await rejectedSales();
    expect(r.queuedAt).toBeTruthy();
    expect(r.rejectedAt).toBeTruthy();
  });

  it("KHÔNG chặn những đơn xếp sau", async () => {
    await enqueueSale(don("a"));
    await enqueueSale(don("b"));
    apiFetch.mockRejectedValueOnce(loiNghiepVu("x")); // a hỏng
    apiFetch.mockResolvedValueOnce({ id: "s1" }); // b qua

    const ket = await flushQueue();
    expect(ket.synced).toBe(1);
    expect(await pendingSalesCount()).toBe(0);
    expect(await rejectedSalesCount()).toBe(1);
  });
});

describe("mất mạng", () => {
  it("giữ NGUYÊN trong hàng chờ, không tính là bị từ chối", async () => {
    await enqueueSale(don("a"));
    apiFetch.mockRejectedValueOnce(new Error("network down"));

    await flushQueue();

    expect(await pendingSalesCount()).toBe(1); // còn chờ
    expect(await rejectedSalesCount()).toBe(0); // KHÔNG phải từ chối
  });

  it("dừng cả lượt — đơn sau vẫn giữ thứ tự cho lần thử tới", async () => {
    await enqueueSale(don("a"));
    await enqueueSale(don("b"));
    apiFetch.mockRejectedValueOnce(new Error("network down"));

    await flushQueue();
    expect(await pendingSalesCount()).toBe(2);
    expect(apiFetch).toHaveBeenCalledTimes(1); // không thử tiếp b
  });
});

describe("xử lý đơn bị từ chối", () => {
  it("thử lại → quay về hàng chờ, GIỮ NGUYÊN client_uuid", async () => {
    await enqueueSale(don("a"));
    apiFetch.mockRejectedValueOnce(loiNghiepVu("hết hàng"));
    await flushQueue();

    await retryRejected("a");

    expect(await rejectedSalesCount()).toBe(0);
    const [cho] = await offlineDb.pendingSales.toArray();
    // `client_uuid` không đổi ⇒ `/sync/sales` vẫn idempotent ⇒ thử lại KHÔNG thành hai đơn.
    expect(cho.clientUuid).toBe("a");
    expect(cho.request.client_uuid).toBe("a");
  });

  it("bỏ hẳn là hành động CÓ NGƯỜI BẤM, không tự xảy ra", async () => {
    await enqueueSale(don("a"));
    apiFetch.mockRejectedValueOnce(loiNghiepVu("x"));
    await flushQueue();
    expect(await rejectedSalesCount()).toBe(1); // tự nó không mất

    await discardRejected("a");
    expect(await rejectedSalesCount()).toBe(0);
  });

  it("thử lại một mã không tồn tại thì im lặng, không nổ", async () => {
    await expect(retryRejected("khong-co")).resolves.toBeUndefined();
  });

  it("mới nhất lên đầu — thu ngân xử cái vừa hỏng trước", async () => {
    for (const u of ["a", "b"]) {
      await enqueueSale(don(u));
      apiFetch.mockRejectedValueOnce(loiNghiepVu(`lý do ${u}`));
      await flushQueue();
      await new Promise((r) => setTimeout(r, 5));
    }
    const ds = await rejectedSales();
    expect(ds.map((r) => r.clientUuid)).toEqual(["b", "a"]);
  });
});
