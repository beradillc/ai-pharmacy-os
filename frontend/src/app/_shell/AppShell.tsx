"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuthStore } from "@/features/auth/auth-store";
import { RejectedSalesBanner } from "@/components/layout/RejectedSalesBanner";
import { DoiMatKhau } from "@/features/auth/DoiMatKhau";
import { ghiNhoPhienHet, khiPhienHet } from "@/shared/api/phien-het";
import { useOfflineSync } from "@/shared/offline/use-offline-sync";

import { AppHeader } from "@/components/layout/AppHeader";
import { BottomNavigation } from "@/components/layout/BottomNavigation";
import { MoreSheet } from "@/components/layout/MoreSheet";
import { PageTransition } from "@/components/layout/PageTransition";
import { Sidebar } from "@/components/layout/Sidebar";

import styles from "./AppShell.module.css";

/**
 * Khung dùng chung cho **mọi** màn sau đăng nhập — kể cả màn Bán hàng.
 *
 * 🔴 Sống ở `app/_shell/` chứ KHÔNG ở `components/`, và chỗ đứng đó là một tuyên
 * bố: đây là **composition root của giao diện**, không phải một component tái
 * dùng. Nó đọc phiên đăng nhập, đọc hàng đợi đồng bộ offline, đọc đường dẫn hiện
 * tại — tức là biết về `features/*`, thứ mà `components/*` bị cấm.
 *
 * Phát hiện ra chỗ này đứng sai là nhờ luật `no-restricted-imports` mới thêm
 * (2026-07-29): nó đỏ ngay ở lần chạy đầu. Chuyển tệp còn tốt hơn thêm một ngoại
 * lệ — một luật KHÔNG có ngoại lệ nào mạnh hơn hẳn một luật có danh sách miễn
 * trừ, vì danh sách đó không bao giờ ngắn lại.
 *
 * Thư mục `_shell` có gạch dưới ⇒ Next không coi là route (quy ước App Router).
 *
 * 🔴 Đây là chỗ đảo lại một phần quyết định Q1 (29/07), và lý do phải nói rõ:
 *
 * Q1 giữ POS toàn màn hình với lập luận *"thu ngân cần tối đa diện tích"*. Đó là
 * một **giả định của tôi**, không phải một quan sát. Chain dùng thật rồi báo:
 * *"mục Bán hàng thiếu danh mục bên trái, mỗi lần về phải bấm vào Quản lý thấy
 * bất tiện."* Người dùng thật đã trả lời: mất điều hướng khó chịu hơn là mất
 * 232px. Giữ nguyên lập luận cũ sau khi có dữ liệu ngược lại thì không còn là
 * nguyên tắc, chỉ là cố chấp.
 *
 * Cái Q1 **vẫn giữ**: không đổi URL nào. `/` vẫn là màn bán hàng.
 *
 * Đổi lại được gì: một shell duy nhất ⇒ header, sidebar, thanh dưới, ngăn "Thêm"
 * và hiệu ứng chuyển trang chỉ có MỘT bản. Trước đó `(app)` và `(pos)` có hai
 * header khác nhau, và đúng chỗ chênh nhau đó sinh ra lỗi Chain vừa báo.
 */
export function AppShell({
  children,
  /** Màn bán hàng cần chiều rộng tối đa cho lưới danh mục + giỏ hàng. */
  wide = false,
}: {
  children: React.ReactNode;
  wide?: boolean;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const session = useAuthStore((s) => s.session);
  const hydrated = useAuthStore((s) => s.hydrated);
  const hydrate = useAuthStore((s) => s.hydrate);
  const logout = useAuthStore((s) => s.logout);
  const { pendingCount, rejected, thuLai, boHan } = useOfflineSync();
  const [moreOpen, setMoreOpen] = useState(false);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (hydrated && !session) router.replace("/login");
  }, [hydrated, session, router]);

  /**
   * 🔴 **Phiên hết ⇒ về màn đăng nhập, KHÔNG mời "Thử lại"** (V3-10, Chain nêu 04/08).
   *
   * Trước bản này `ApiError.isUnauthenticated` **tồn tại nhưng không nơi nào gọi** — `grep`
   * cả frontend chỉ ra đúng dòng khai báo nó. Nên một token hết hạn rơi vào `ErrorState`
   * chung, và người dùng được mời **Thử lại**: gửi lại đúng cái token đã chết, không lần nào
   * thành công. Chain hỏi thẳng *"hết hạn thì đăng nhập lại, chứ thử lại cái gì?"*
   *
   * `logout()` trước rồi mới `replace()`: xoá phiên là thứ phải xảy ra **chắc chắn**, còn
   * điều hướng có thể bị một màn đang mở nuốt mất. Đảo thứ tự thì có ca người dùng ở lại
   * trong ứng dụng với một phiên đã chết trong tay.
   */
  useEffect(() => khiPhienHet(() => {
    // Ghi cờ TRƯỚC khi `logout()`: `logout()` làm `session` thành `null`, và hiệu ứng ngay
    // phía trên sẽ lập tức `replace("/login")`. Ghi sau thì có lượt màn đăng nhập dựng xong
    // trước khi cờ kịp có mặt.
    ghiNhoPhienHet();
    logout();
    router.replace("/login");
  }), [logout, router]);

  // Canh đăng nhập giữ nguyên cách đang chạy: đọc localStorage SAU khi mount, vì
  // lượt render phía máy chủ không có `window` — chuyển hướng sớm hơn sẽ đá văng
  // người đang đăng nhập mỗi lần F5.
  if (!hydrated || !session) return null;

  // 🔴 CỬA CHẶN — lỗi C-01 (UAT 01/08). Backend đặt `must_change_password` cho mọi tài khoản
  // mới và trả cờ đó ngay trong phản hồi đăng nhập, nhưng trước bản vá **không ai đọc nó**:
  // người dùng vào thẳng màn Bán hàng và dùng vĩnh viễn mật khẩu do người tạo tài khoản đặt.
  //
  // Chặn ở ĐÂY chứ không ở màn đăng nhập: `AppShell` là chỗ **mọi màn của khu quản lý đều đi
  // qua**, kể cả khi người dùng gõ thẳng một URL. Chặn ở màn đăng nhập thì gõ thẳng
  // `/ton-kho` là đi vòng được.
  //
  // Giữ nguyên thanh đầu (thương hiệu, nút Đăng xuất) — người vào nhầm tài khoản phải thoát
  // ra được mà không cần đổi mật khẩu của người khác.
  if (session.must_change_password) {
    return (
      <div className={styles.shell}>
        <AppHeader
          branchName={
            session.accessible_branches.find((b) => b.id === session.branch_id)?.name ?? ""
          }
          pendingCount={pendingCount}
          onLogout={logout}
        />
        <div className={styles.body}>
          <main className={styles.main}>
            <DoiMatKhau batBuoc />
          </main>
        </div>
      </div>
    );
  }

  const branchName =
    session.accessible_branches.find((b) => b.id === session.branch_id)?.name ??
    `CN ${session.branch_id.slice(0, 8)}`;

  return (
    <div className={styles.shell}>
      <AppHeader branchName={branchName} pendingCount={pendingCount} onLogout={logout} />

      <div className={styles.body}>
        <Sidebar permissions={session.permissions} pathname={pathname} />
        <main className={wide ? styles.mainWide : styles.main}>
          <div className={wide ? styles.innerWide : styles.inner}>
            {/* Trên MỌI màn, không riêng màn bán hàng: thu ngân có thể đang ở màn Kho
                lúc mạng có lại, và đơn bị từ chối là tiền đã thu của khách. */}
            <RejectedSalesBanner rejected={rejected} onThuLai={thuLai} onBoHan={boHan} />
            <PageTransition>{children}</PageTransition>
          </div>
        </main>
      </div>

      <BottomNavigation
        permissions={session.permissions}
        pathname={pathname}
        moreOpen={moreOpen}
        onOpenMore={() => setMoreOpen((v) => !v)}
      />
      <MoreSheet
        open={moreOpen}
        permissions={session.permissions}
        onClose={() => setMoreOpen(false)}
      />
    </div>
  );
}
