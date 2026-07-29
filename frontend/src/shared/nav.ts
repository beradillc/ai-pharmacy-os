/**
 * Mô hình điều hướng DUY NHẤT của BERAS.
 *
 * Yêu cầu UI mục 6: *"Không tạo hai hệ thống logic khác nhau. Dùng cùng
 * route/navigation model."* Tệp này **là** chỗ thoả điều đó: `Sidebar`,
 * `BottomNavigation`, trang "Thêm" và lưới Quick Action đều đọc từ đây. Thêm một
 * màn = thêm một dòng ở đây, không phải sửa bốn chỗ.
 *
 * 🔴 Quyết định GĐ 2026-07-29 (Chain uỷ quyền): **không đổi tên route nào.**
 * `/` vẫn là màn bán hàng, `/bang-dieu-hanh` vẫn là tổng quan. Bản thiết kế đầu
 * đề nghị đổi `/`→`/ban-hang` và `/bang-dieu-hanh`→`/`, nhưng đó là đổi thói quen
 * của người đứng quầy để lấy một cái lợi thẩm mỹ. Cái yêu cầu thực sự cần —
 * *một* mô hình điều hướng — đạt được bằng tệp này, không cần đụng URL.
 * Chi tiết: `docs/ui/ROUTING_PLAN.md` §8.
 */

/** Nhóm trên sidebar. Nhóm rỗng (không mục nào đủ quyền) bị ẩn cả tiêu đề. */
export type NavGroup = "ban-hang" | "kho" | "quan-tri";

export interface NavItem {
  href: string;
  label: string;
  /** Nhãn ngắn cho bottom nav — "Đơn mua hàng" không vừa một ô rộng 20% màn hình. */
  short: string;
  /** Gating theo QUYỀN, không theo tên vai. Thiếu quyền ⇒ mục không hiện. */
  permission: string;
  group: NavGroup;
  /** Có mặt trong 5 ô bottom nav trên mobile. */
  primary: boolean;
  /**
   * Có mặt trong lưới "hành động nhanh" trên màn Tổng quan. Mặc định có.
   *
   * `false` cho những mục KHÔNG phải việc hằng ngày (ví dụ Cài đặt): lưới hành
   * động nhanh là chỗ để bắt đầu một việc lúc 7 giờ sáng, không phải mục lục.
   * Giữ nó nguyên vẹn cũng là cách thêm màn mới mà màn Tổng quan không đổi.
   */
  quickAction?: boolean;
  /** Tên icon — xem `components/layout/NavIcon.tsx`. */
  icon: NavIconName;
}

export type NavIconName =
  | "dashboard"
  | "sell"
  | "receipt"
  | "customer"
  | "stock"
  | "purchase"
  | "suggest"
  | "report"
  | "settings"
  | "more";

export const NAV_GROUP_LABEL: Record<NavGroup, string> = {
  "ban-hang": "Bán hàng",
  kho: "Kho",
  "quan-tri": "Quản trị",
};

export const NAV: readonly NavItem[] = [
  {
    href: "/bang-dieu-hanh",
    label: "Tổng quan",
    short: "Tổng quan",
    permission: "analytics.read",
    group: "ban-hang",
    primary: true,
    icon: "dashboard",
  },
  {
    href: "/",
    label: "Bán hàng",
    short: "Bán hàng",
    permission: "sales.create",
    group: "ban-hang",
    primary: true,
    icon: "sell",
  },
  {
    href: "/ton-kho",
    label: "Kho",
    short: "Kho",
    permission: "inventory.read",
    group: "kho",
    primary: true,
    icon: "stock",
  },
  {
    href: "/bao-cao",
    label: "Báo cáo",
    short: "Báo cáo",
    permission: "sales.read",
    group: "quan-tri",
    primary: true,
    icon: "report",
  },
  {
    href: "/hoa-don",
    label: "Hoá đơn",
    short: "Hoá đơn",
    permission: "sales.read",
    group: "ban-hang",
    // `false` tường minh: bốn ô của thanh dưới đã chốt là Tổng quan · Bán hàng ·
    // Kho · Báo cáo. Để `true` rồi trông chờ `slice(0, 4)` cắt bớt thì mô hình
    // nói một đằng, hành vi một nẻo — và người sửa sau sẽ đổi thứ tự mà không
    // biết mình vừa đổi cả thanh điều hướng.
    primary: false,
    icon: "receipt",
  },
  {
    href: "/khach-hang",
    label: "Khách hàng",
    short: "Khách",
    permission: "crm.read",
    group: "ban-hang",
    primary: false,
    icon: "customer",
  },
  {
    href: "/don-mua-hang",
    label: "Đơn mua hàng",
    short: "Đơn mua",
    permission: "procurement.po.read",
    group: "kho",
    primary: false,
    icon: "purchase",
  },
  {
    href: "/cai-dat",
    label: "Cài đặt",
    short: "Cài đặt",
    // Ai đăng nhập được cũng đổi được giao diện của chính mình ⇒ gắn vào quyền
    // hẹp nhất mà mọi vai đều có. Không tạo quyền mới cho một tuỳ chọn hiển thị.
    permission: "sales.read",
    group: "quan-tri",
    primary: false,
    quickAction: false,
    icon: "settings",
  },
  {
    href: "/de-xuat-dat-hang",
    label: "Đề xuất đặt hàng",
    short: "Đề xuất",
    permission: "analytics.read",
    group: "kho",
    primary: false,
    icon: "suggest",
  },
] as const;

/** Số ô tối đa của bottom nav, KỂ CẢ ô "Thêm". */
export const BOTTOM_NAV_SLOTS = 5;

/** Mục người dùng được thấy, giữ nguyên thứ tự khai báo. */
export function visibleNav(permissions: readonly string[]): NavItem[] {
  const held = new Set(permissions);
  return NAV.filter((item) => held.has(item.permission));
}

/**
 * Bốn ô đầu của bottom nav (ô thứ năm luôn là "Thêm").
 *
 * Nếu người dùng có ít hơn 4 mục `primary`, thanh **co lại** — không độn ô giả
 * để cho đủ năm. Một ô bấm vào không đi đâu là một lời hứa suông, cùng loại với
 * "hiện menu rồi báo lỗi quyền" mà dự án đã bỏ từ Sprint 9.
 */
export function bottomNavItems(permissions: readonly string[]): NavItem[] {
  return visibleNav(permissions)
    .filter((item) => item.primary)
    .slice(0, BOTTOM_NAV_SLOTS - 1);
}

/** Mục hiện trên lưới hành động nhanh của màn Tổng quan. */
export function quickActionItems(permissions: readonly string[]): NavItem[] {
  return visibleNav(permissions).filter((item) => item.quickAction !== false);
}

/** Mục KHÔNG nằm trên bottom nav — nội dung của trang/ngăn "Thêm". */
export function overflowNavItems(permissions: readonly string[]): NavItem[] {
  const onBar = new Set(bottomNavItems(permissions).map((i) => i.href));
  return visibleNav(permissions).filter((item) => !onBar.has(item.href));
}

/**
 * Mục đang được chọn, so khớp CHÍNH XÁC.
 *
 * Không dùng `startsWith`: route bán hàng là `"/"`, mà mọi đường dẫn đều bắt đầu
 * bằng `"/"` ⇒ `startsWith` sẽ tô sáng "Bán hàng" ở mọi màn.
 */
export function isActive(item: NavItem, pathname: string): boolean {
  return item.href === pathname;
}
