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
  /**
   * Đường dẫn KHÁC cũng làm mục này sáng lên — dùng cho hai màn được gộp thành một mục
   * menu (Chain giao 01/08).
   *
   * 🔴 Vì sao gộp bằng cách này chứ không dựng một route mới `/nhap-hang` chứa hai tab:
   * kỷ luật #17 cấm đổi tên route cũ, và bốn đường dẫn `/nhap-nhanh` `/khoi-tao-ton`
   * `/kiem-ke` `/so-do-kho` đang nằm trong dấu trang, trong tài liệu, và trong **tám cổng
   * trình duyệt**. Gộp là việc của MENU — hai màn vẫn là hai màn, chỉ vào chung một cửa và
   * có dải tab chuyển qua lại. Không có route nào chết, không có gì phải chuyển hướng.
   */
  alsoActiveFor?: readonly string[];
  /** Tên icon — xem `components/layout/NavIcon.tsx`. */
  icon: NavIconName;
}

export type NavIconName =
  | "drug"
  | "warehouse-map"
  | "receive"
  | "dashboard"
  | "sell"
  | "receipt"
  | "customer"
  | "stock"
  | "purchase"
  | "suggest"
  | "report"
  | "settings"
  | "staff"
  | "journal"
  | "prescription"
  | "controlled-book"
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
    href: "/danh-muc-thuoc",
    label: "Danh mục thuốc",
    short: "Danh mục",
    // `catalog.read` chứ không `catalog.update`: ai cũng xem được danh mục và hoạt chất
    // của thuốc — đó là thông tin an toàn thuốc, không phải bí mật. Nút SỬA bên trong
    // mới cần `catalog.update` (cấp chuỗi).
    permission: "catalog.read",
    group: "kho",
    primary: false,
    icon: "drug",
  },
  {
    href: "/nhap-nhanh",
    label: "Nhập hàng",
    short: "Nhập",
    permission: "inventory.receive",
    group: "kho",
    primary: false,
    // Gộp với `/khoi-tao-ton` (Chain giao 01/08): hai màn cùng một việc — đưa hàng vào ô —
    // khác nhau ở chỗ hàng đến từ nhà cung cấp hay đã nằm sẵn trên kệ từ trước.
    alsoActiveFor: ["/khoi-tao-ton"],
    icon: "receive",
  },
  {
    href: "/so-do-kho",
    label: "Sơ đồ & Kiểm kê",
    short: "Sơ đồ",
    // `location.read` chứ không `location.write`: ai đứng quầy cũng cần biết thuốc nằm ở
    // đâu. Nút dựng sơ đồ bên trong mới cần `location.write`.
    //
    // 🔴 Gác quyền theo màn ĐƯỢC VÀO ĐẦU TIÊN. `/so-do-kho` đứng trước vì nó là màn
    // ĐỌC — biết thuốc nằm ở đâu — còn kiểm kê là một việc phải mở phiên. Ai chỉ có
    // `inventory.read` mà thiếu `location.read` sẽ KHÔNG thấy mục này; đó là mất mát
    // thật, nhưng mọi vai chạm tới kho trong `system_roles.py` đều có cả hai, và một
    // mục menu dẫn tới màn sẽ-403 còn tệ hơn. Ghi ra đây để phiên sau không phải đoán.
    permission: "location.read",
    group: "kho",
    primary: false,
    alsoActiveFor: ["/kiem-ke"],
    icon: "warehouse-map",
  },
  {
    href: "/don-mua-hang",
    label: "Đơn mua hàng",
    short: "Đơn mua",
    permission: "procurement.po.read",
    group: "kho",
    primary: false,
    // Gộp với `/nha-cung-cap` (UAT 01/08, lỗi M-01): không có nhà cung cấp thì không tạo
    // được đơn mua — hai màn của cùng một việc, vào chung một cửa như các cặp đã gộp.
    alsoActiveFor: ["/nha-cung-cap"],
    icon: "purchase",
  },
  {
    href: "/nhan-vien",
    label: "Nhân viên",
    short: "Nhân viên",
    permission: "iam.user.read",
    group: "quan-tri",
    primary: false,
    quickAction: false,
    icon: "staff",
  },
  {
    href: "/don-thuoc",
    label: "Đơn thuốc",
    short: "Đơn thuốc",
    // `rx.read` — cùng quyền đã dùng để mở một đơn. Xem được một đơn thì xem được danh
    // sách đơn; không đẻ thêm bậc quyền cho một màn tra cứu.
    permission: "rx.read",
    group: "ban-hang",
    primary: false,
    quickAction: false,
    icon: "prescription",
  },
  {
    href: "/so-kiem-soat",
    label: "Sổ kiểm soát đặc biệt",
    short: "Sổ KSĐB",
    // `compliance.ledger.read` — quyền RIÊNG, không mượn `inventory.read`. Sổ này ghi ai
    // bán thuốc gây nghiện/hướng thần cho ai; xem được nó là một thẩm quyền khác hẳn với
    // xem tồn kho. Nút "Ký xác nhận" bên trong đòi thêm `compliance.ledger.sign`.
    permission: "compliance.ledger.read",
    group: "kho",
    primary: false,
    // Không phải việc hằng ngày của người đứng quầy — nó là việc **cuối ngày** của dược sĩ
    // phụ trách. Để trong lưới hành động nhanh sẽ đẩy một nghĩa vụ pháp lý xuống ngang hàng
    // với "bán một đơn", và làm loãng đúng cái lưới đó.
    quickAction: false,
    icon: "controlled-book",
  },
  {
    href: "/nhat-ky",
    label: "Nhật ký hoạt động",
    short: "Nhật ký",
    // Quyền RIÊNG, không mượn `iam.user.read` (UAT 01/08, lỗi M-04): xem *ai đã làm gì* và
    // *ai được làm việc gì* là hai thẩm quyền khác nhau. Gắn chung thì người có quyền tra
    // nhật ký mà không quản lý nhân sự sẽ không thấy mục này ở đâu cả.
    permission: "audit.dashboard.read",
    group: "quan-tri",
    primary: false,
    quickAction: false,
    icon: "journal",
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
  return item.href === pathname || (item.alsoActiveFor?.includes(pathname) ?? false);
}
