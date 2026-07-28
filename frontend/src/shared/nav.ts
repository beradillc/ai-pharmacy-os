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
    href: "/hoa-don",
    label: "Hoá đơn",
    short: "Hoá đơn",
    permission: "sales.read",
    group: "ban-hang",
    primary: true,
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
