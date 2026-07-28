import type { NavIconName } from "@/shared/nav";

/**
 * Icon điều hướng — SVG nội tuyến, vẽ tay.
 *
 * Vì sao không kéo một bộ icon: dự án cần đúng 8 hình. Một gói icon mang theo vài
 * nghìn hình, một hệ token màu riêng, và một thứ phải nâng cấp về sau — cho tám
 * hình thì đó là cái giá sai. Cũng là lý do không sao chép icon độc quyền của bất
 * kỳ ai (yêu cầu nói rõ): các hình dưới đây là hình học cơ bản, không phải bản vẽ
 * của ai.
 *
 * `stroke="currentColor"` ⇒ icon tự lấy màu chữ của mục nav, nên trạng thái chọn/
 * chưa chọn chỉ cần đổi màu ở CSS, không phải đổi SVG.
 */
export function NavIcon({ name, filled = false }: { name: NavIconName; filled?: boolean }) {
  const common = {
    width: 22,
    height: 22,
    viewBox: "0 0 24 24",
    fill: filled ? "currentColor" : "none",
    stroke: "currentColor",
    strokeWidth: filled ? 1.5 : 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    focusable: false,
  };

  switch (name) {
    case "dashboard":
      return (
        <svg {...common}>
          <rect x="3" y="3" width="7" height="9" rx="1.5" />
          <rect x="14" y="3" width="7" height="5" rx="1.5" />
          <rect x="14" y="11" width="7" height="10" rx="1.5" />
          <rect x="3" y="15" width="7" height="6" rx="1.5" />
        </svg>
      );
    case "sell":
      return (
        <svg {...common}>
          <path d="M3 5h2l2.2 10.2a2 2 0 0 0 2 1.6h7.4a2 2 0 0 0 2-1.5L20 8H6" />
          <circle cx="10" cy="20" r="1.2" />
          <circle cx="17" cy="20" r="1.2" />
        </svg>
      );
    case "receipt":
      return (
        <svg {...common}>
          <path d="M6 2.5h12v19l-2.5-1.8-2.5 1.8-2.5-1.8L8 21.5 6 19.7z" />
          <path d="M9.5 8h5M9.5 12h5" />
        </svg>
      );
    case "customer":
      return (
        <svg {...common}>
          <circle cx="12" cy="8" r="3.5" />
          <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
        </svg>
      );
    case "stock":
      return (
        <svg {...common}>
          <path d="M3 7.5 12 3l9 4.5v9L12 21l-9-4.5z" />
          <path d="M3 7.5 12 12l9-4.5M12 12v9" />
        </svg>
      );
    case "purchase":
      return (
        <svg {...common}>
          <rect x="3" y="7" width="18" height="13" rx="2" />
          <path d="M8 7V5.5A3.5 3.5 0 0 1 16 5.5V7" />
        </svg>
      );
    case "suggest":
      return (
        <svg {...common}>
          <path d="M12 3v2M4.9 6l1.4 1.4M19.1 6l-1.4 1.4" />
          <path d="M9 17a5 5 0 1 1 6 0v1.5H9z" />
          <path d="M10 21h4" />
        </svg>
      );
    case "more":
      return (
        <svg {...common}>
          <circle cx="5.5" cy="12" r="1.4" />
          <circle cx="12" cy="12" r="1.4" />
          <circle cx="18.5" cy="12" r="1.4" />
        </svg>
      );
  }
}
