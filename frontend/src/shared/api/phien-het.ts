/**
 * Chỗ báo **phiên đăng nhập đã hết** — một điểm phát, một điểm nhận (V3-10, Chain nêu 04/08).
 *
 * 🔴 **Vì sao cần tệp trung gian này thay vì gọi thẳng.** Chỗ **phát hiện** phiên hết là
 * `shared/api/client.ts` (nó thấy mã 401). Chỗ **xử lý** là tầng ứng dụng (xoá phiên, đẩy về
 * `/login`) — và tầng đó nằm trong `features/auth` + `next/navigation`. Cho `shared/api` gọi
 * thẳng vào đó là kéo cả bộ định tuyến và kho trạng thái vào một tệp mà **mọi** lượt gọi API
 * đều nạp, kể cả trong test.
 *
 * Nên: `shared/api` chỉ **hô lên**, tầng ứng dụng **đăng ký** người nghe. Hướng phụ thuộc giữ
 * nguyên chiều cũ.
 *
 * **Bối cảnh nó sinh ra:** trước bản này `ApiError.isUnauthenticated` **đã tồn tại nhưng
 * không nơi nào gọi** — `grep` cả frontend chỉ ra đúng một dòng: chính dòng khai báo nó. Nên
 * không có đường nào đưa người dùng về màn đăng nhập, và mọi lỗi rơi vào `ErrorState` chung,
 * nơi chỉ có nút **Thử lại** — thứ không bao giờ chữa được một phiên đã hết.
 */

type NguoiNghe = () => void;

let nguoiNghe: NguoiNghe | null = null;

/** Tầng ứng dụng đăng ký cách xử lý. Trả về hàm gỡ đăng ký (dùng trong `useEffect`). */
export function khiPhienHet(fn: NguoiNghe): () => void {
  nguoiNghe = fn;
  return () => {
    if (nguoiNghe === fn) nguoiNghe = null;
  };
}

/**
 * `shared/api/client.ts` gọi khi máy chủ trả **401**.
 *
 * Không ném lỗi khi chưa ai đăng ký: lượt gọi API đầu tiên có thể chạy trước khi khung ứng
 * dụng kịp gắn người nghe, và một ngoại lệ ở đây sẽ che mất **lỗi thật** đang trên đường ném
 * ra cho người gọi.
 */
export function baoPhienHet(): void {
  nguoiNghe?.();
}

/**
 * Cờ *"vừa bị đá ra vì hết phiên"*, để màn đăng nhập nói được lý do.
 *
 * 🔴 **Vì sao KHÔNG dùng `?phien=het` trên URL** — đã thử và đo thấy hỏng: `AppShell` có sẵn
 * một hiệu ứng `if (hydrated && !session) router.replace("/login")`. `logout()` làm
 * `session` thành `null`, nên hiệu ứng ấy chạy ngay sau và **ghi đè mất tham số truy vấn**.
 * Cổng đo được đúng triệu chứng: về `/login` đúng, nhưng câu giải thích biến mất.
 *
 * `sessionStorage` không bị cuộc đua ấy chạm tới, và tự hết khi đóng tab — đúng vòng đời của
 * một thông báo dùng một lần.
 *
 * Một hằng `KHOA`, hai nơi dùng: bên ghi và bên đọc **không được** gõ lại chuỗi (kỷ luật #22
 * — hai chuỗi rời nhau thì gõ sai một bên không làm đỏ cổng nào, câu thông báo chỉ lặng lẽ
 * không bao giờ hiện).
 */
const KHOA = "beras.phien-het";

export function ghiNhoPhienHet(): void {
  if (typeof window !== "undefined") window.sessionStorage.setItem(KHOA, "1");
}

/** Đọc **và xoá** — thông báo dùng một lần, F5 lại không hiện nữa. */
export function docVaXoaPhienHet(): boolean {
  if (typeof window === "undefined") return false;
  const co = window.sessionStorage.getItem(KHOA) === "1";
  if (co) window.sessionStorage.removeItem(KHOA);
  return co;
}
