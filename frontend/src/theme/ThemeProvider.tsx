"use client";

import { useCallback, useSyncExternalStore } from "react";

import { DEFAULT_THEME, isThemeId, THEME_STORAGE_KEY, type ThemeId } from "./themes";

/**
 * Hệ theme của BERAS.
 *
 * ─── Vì sao KHÔNG dùng React Context ─────────────────────────────────────────
 * Nguồn sự thật của theme là **thuộc tính `data-theme` trên thẻ `<html>`** — thứ
 * mà CSS đọc. Đưa nó vào context nghĩa là có hai nguồn sự thật phải giữ đồng bộ,
 * và mọi component đọc context sẽ **render lại khi đổi theme** — đúng thứ đặc tả
 * cấm ("không render lại toàn bộ app").
 *
 * `useSyncExternalStore` là công cụ React làm sẵn cho đúng tình huống này: DOM là
 * store bên ngoài, hook chỉ *đọc* nó. Đổi theme ⇒ đặt một thuộc tính ⇒ trình duyệt
 * tính lại biến CSS đã kế thừa. **Không component nghiệp vụ nào render lại.**
 * Chỉ những component thật sự gọi `useTheme()` (đúng một: nút chọn theme) mới vẽ lại.
 *
 * Phần thưởng kèm theo: bắt luôn sự kiện `storage`, nên đổi theme ở tab này thì
 * tab kia đổi theo — không phải tính năng được yêu cầu, nhưng nó rơi ra miễn phí
 * từ việc chọn đúng công cụ.
 */

const THEME_EVENT = "beras:themechange";

function subscribe(onChange: () => void): () => void {
  window.addEventListener(THEME_EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(THEME_EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

function getSnapshot(): ThemeId {
  const attr = document.documentElement.getAttribute("data-theme");
  return isThemeId(attr) ? attr : DEFAULT_THEME;
}

/** Máy chủ không có DOM — luôn dựng Classic, rồi script chống nháy sửa lại
 *  trước khi trang vẽ. */
function getServerSnapshot(): ThemeId {
  return DEFAULT_THEME;
}

export function useTheme() {
  const theme = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const setTheme = useCallback((id: ThemeId) => {
    const root = document.documentElement;
    // Classic KHÔNG đặt thuộc tính — nó là cascade gốc, không phải một khối CSS
    // trùng lặp. Cách duy nhất chắc chắn Classic không đổi một pixel là không có
    // luật nào chen vào nó.
    if (id === DEFAULT_THEME) root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", id);

    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, id);
    } catch {
      // Chế độ riêng tư của một số trình duyệt ném lỗi khi ghi localStorage.
      // Theme vẫn đổi cho phiên này, chỉ không nhớ được sang lần sau — chấp nhận
      // được, và chắc chắn tốt hơn là làm sập màn hình cài đặt.
    }
    window.dispatchEvent(new Event(THEME_EVENT));
  }, []);

  return { theme, setTheme };
}

/**
 * Không giữ trạng thái, không bọc context — chỉ là chỗ đặt tên cho ý niệm "ứng
 * dụng có hệ theme". Giữ lại để nếu sau này theme cần lưu **theo người dùng** thì
 * có đúng một chỗ để thêm việc đồng bộ với máy chủ.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

/**
 * Script chạy TRƯỚC khi trang vẽ lần đầu, nhúng thẳng vào `<head>`.
 *
 * Không có nó, người đã chọn Warm sẽ thấy một nháy Classic ở **mỗi** lần tải
 * trang — React chỉ chạy sau khi HTML đã vẽ xong. Đây là lý do đoạn này là chuỗi
 * thô chứ không phải một component.
 *
 * Bọc `try`: một trang không vẽ được chỉ vì không đọc nổi tuỳ chọn màu là cái giá
 * quá đắt.
 */
export const THEME_INIT_SCRIPT = `
(function(){try{var t=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});
if(t&&t!==${JSON.stringify(DEFAULT_THEME)})document.documentElement.setAttribute('data-theme',t);}catch(e){}})();
`.trim();
