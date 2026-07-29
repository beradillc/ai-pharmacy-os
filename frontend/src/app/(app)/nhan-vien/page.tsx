"use client";

import { useState } from "react";

import { ConfirmDialog } from "@/components/overlay/ConfirmDialog";

import { RolePanel } from "./RolePanel";
import {
  STAFF_PAGE_SIZE,
  STAFF_STATUS_LABEL,
  useCreateStaff,
  useRoles,
  useSetStaffActive,
  useStaff,
} from "@/features/iam/use-staff";
import { useAuthStore } from "@/features/auth/auth-store";
import { ApiError } from "@/shared/api/errors";
import type { StaffUser } from "@/shared/api/types";
import { formatTime } from "@/shared/format/number";
import styles from "@/shared/ui/screen.module.css";

import local from "./page.module.css";

const STATUS_CLASS: Record<string, string> = {
  ACTIVE: styles.chipOk,
  DISABLED: styles.chipMuted,
  LOCKED: styles.chipDanger,
};

/**
 * Màn Nhân viên.
 *
 * Lấp khoảng trống đã ghi trong `REMAINING_UI_ISSUES` mục 5: backend có **21
 * endpoint IAM** mà **không màn nào** dùng, nên tới hôm nay **không tạo được nhân
 * viên trên giao diện** — phải chạy lệnh dòng. Mọi buổi demo đều kết thúc bằng câu
 * *"vậy tôi thêm nhân viên thế nào?"*.
 *
 * Bốn việc: **xem ai đang có tài khoản · thêm người mới · cấp/thu hồi vai trò ·
 * tắt tài khoản người nghỉ việc**. Phần vai trò tách sang `RolePanel` — nó là chỗ
 * nguy hiểm nhất của cả sản phẩm và có lý do riêng cho từng quyết định giao diện.
 */
export default function StaffPage() {
  const session = useAuthStore((s) => s.session);
  const held = new Set(session?.permissions ?? []);
  const canCreate = held.has("iam.user.create");
  const canWrite = held.has("iam.user.write");
  const canAssign = held.has("iam.role.assign");

  const [page, setPage] = useState(0);
  const [creating, setCreating] = useState(false);
  const [toggling, setToggling] = useState<StaffUser | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [lastCreated, setLastCreated] = useState<string | null>(null);
  const [rolesFor, setRolesFor] = useState<StaffUser | null>(null);

  const { data, isLoading, error, refetch } = useStaff(page);
  const roles = useRoles();
  const create = useCreateStaff();
  const setActive = useSetStaffActive();
  const rows = data ?? [];

  function report(err: unknown, fallback: string) {
    setActionError(err instanceof ApiError ? err.problem.detail : fallback);
  }

  async function confirmToggle() {
    const user = toggling;
    setToggling(null);
    if (!user) return;
    setActionError(null);
    try {
      await setActive.mutateAsync({ id: user.id, active: user.status !== "ACTIVE" });
    } catch (err) {
      report(err, "Không đổi được trạng thái tài khoản.");
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Nhân viên</h1>
          <p className={styles.subtitle}>
            {rows.length} tài khoản · {roles.data?.length ?? 0} vai trò trong hệ thống
          </p>
        </div>
        {canCreate && (
          <div className={styles.controls}>
            <button type="button" className={styles.button} onClick={() => setCreating(true)}>
              Thêm nhân viên
            </button>
          </div>
        )}
      </div>

      {actionError && (
        <div className={styles.error} role="alert">
          <span>{actionError}</span>
          <button type="button" className={styles.retry} onClick={() => setActionError(null)}>
            Đóng
          </button>
        </div>
      )}

      {lastCreated && (
        <div className={local.notice} role="status">
          <strong>Đã tạo tài khoản {lastCreated}.</strong> Nhân viên{" "}
          <strong>bắt buộc đổi mật khẩu</strong> ở lần đăng nhập đầu — mật khẩu bạn vừa
          đặt chỉ dùng một lần. Vai trò chưa gán: tài khoản mới chưa vào được màn nào
          cho tới khi được cấp vai.
        </div>
      )}

      {error && (
        <div className={styles.error} role="alert">
          <span>
            {error instanceof ApiError ? error.problem.detail : "Không tải được danh sách."}
          </span>
          <button type="button" className={styles.retry} onClick={() => refetch()}>
            Thử lại
          </button>
        </div>
      )}

      <div className={styles.panel}>
        {isLoading ? (
          <>
            <div className={styles.skeleton} />
            <div className={styles.skeleton} />
          </>
        ) : rows.length === 0 ? (
          <p className={styles.empty}>Chưa có tài khoản nào.</p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Họ tên</th>
                  <th>Email đăng nhập</th>
                  <th>Trạng thái</th>
                  <th>Đăng nhập gần nhất</th>
                  {canWrite && <th />}
                </tr>
              </thead>
              <tbody>
                {rows.map((user) => (
                  <tr key={user.id}>
                    <td>
                      {user.full_name}
                      {user.must_change_password && (
                        <span className={`${styles.chip} ${styles.chipWarn} ${local.tag}`}>
                          chưa đổi mật khẩu
                        </span>
                      )}
                    </td>
                    <td className={styles.mono}>{user.email}</td>
                    <td>
                      <span className={`${styles.chip} ${STATUS_CLASS[user.status] ?? ""}`}>
                        {STAFF_STATUS_LABEL[user.status] ?? user.status}
                      </span>
                    </td>
                    <td className={`${styles.mono} ${styles.muted}`}>
                      {user.last_login_at ? formatTime(user.last_login_at) : "chưa bao giờ"}
                    </td>
                    {canWrite && (
                      <td className={styles.num}>
                        {canAssign && (
                          <button
                            type="button"
                            className={`${styles.ghost} ${local.spaced}`}
                            onClick={() => setRolesFor(rolesFor?.id === user.id ? null : user)}
                          >
                            Vai trò
                          </button>
                        )}
                        <button
                          type="button"
                          className={styles.ghost}
                          onClick={() => setToggling(user)}
                          // Không cho tự tắt tài khoản của chính mình: người dùng
                          // sẽ bị đá ra ngay lập tức và không ai bật lại được nếu
                          // đó là quản trị viên duy nhất.
                          disabled={user.id === session?.user_id}
                          title={
                            user.id === session?.user_id
                              ? "Không thể tự tắt tài khoản của chính mình"
                              : undefined
                          }
                        >
                          {user.status === "ACTIVE" ? "Tắt" : "Bật"}
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className={styles.pager}>
          <span>Trang {page + 1}</span>
          <button
            type="button"
            className={styles.ghost}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0 || isLoading}
          >
            Trước
          </button>
          <button
            type="button"
            className={styles.ghost}
            onClick={() => setPage((p) => p + 1)}
            disabled={isLoading || rows.length < STAFF_PAGE_SIZE}
          >
            Sau
          </button>
        </div>
      </div>

      {rolesFor && (
        <RolePanel
          user={rolesFor}
          branches={session?.accessible_branches ?? []}
          onClose={() => setRolesFor(null)}
        />
      )}

      <CreateStaffDialog
        open={creating}
        pending={create.isPending}
        onCancel={() => setCreating(false)}
        onSubmit={async (input) => {
          setActionError(null);
          try {
            const user = await create.mutateAsync(input);
            setCreating(false);
            setLastCreated(user.full_name);
          } catch (err) {
            report(err, "Không tạo được tài khoản.");
          }
        }}
      />

      <ConfirmDialog
        open={toggling !== null}
        title={
          toggling?.status === "ACTIVE"
            ? `Tắt tài khoản "${toggling?.full_name}"?`
            : `Bật lại tài khoản "${toggling?.full_name ?? ""}"?`
        }
        description={
          toggling?.status === "ACTIVE"
            ? "Người này sẽ không đăng nhập được nữa. Dữ liệu và lịch sử thao tác giữ nguyên — tắt tài khoản không xoá gì."
            : "Người này đăng nhập lại được ngay sau khi bật."
        }
        confirmLabel={toggling?.status === "ACTIVE" ? "Tắt tài khoản" : "Bật lại"}
        tone={toggling?.status === "ACTIVE" ? "danger" : "normal"}
        onConfirm={confirmToggle}
        onCancel={() => setToggling(null)}
      />
    </div>
  );
}

/** Hộp thoại tạo nhân viên — ba trường, không hơn. */
function CreateStaffDialog({
  open,
  pending,
  onSubmit,
  onCancel,
}: {
  open: boolean;
  pending: boolean;
  onSubmit: (input: { email: string; password: string; full_name: string }) => void;
  onCancel: () => void;
}) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  if (!open) return null;

  return (
    <section className={styles.drawer} aria-label="Thêm nhân viên">
      <div className={styles.drawerHead}>
        <h2 className={styles.drawerTitle}>Thêm nhân viên</h2>
      </div>
      <form
        className={local.form}
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit({ full_name: fullName.trim(), email: email.trim(), password });
        }}
      >
        <label className={local.field}>
          <span className={local.label}>Họ tên</span>
          <input
            className={styles.input}
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            autoFocus
          />
        </label>
        <label className={local.field}>
          <span className={local.label}>Email đăng nhập</span>
          <input
            className={styles.input}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label className={local.field}>
          <span className={local.label}>Mật khẩu lần đầu</span>
          <input
            className={styles.input}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            // Backend đòi tối thiểu; để trình duyệt chặn sớm thay vì đợi 422.
            minLength={12}
            required
          />
          <span className={local.hint}>
            Tối thiểu 12 ký tự. Nhân viên <strong>bắt buộc đổi</strong> ở lần đăng nhập
            đầu, nên đây chỉ là mật khẩu dùng một lần.
          </span>
        </label>
        <div className={local.actions}>
          <button type="button" className={styles.ghost} onClick={onCancel}>
            Huỷ
          </button>
          <button type="submit" className={styles.button} disabled={pending}>
            {pending ? "Đang tạo…" : "Tạo tài khoản"}
          </button>
        </div>
      </form>
    </section>
  );
}
