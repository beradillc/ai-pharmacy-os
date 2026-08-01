"use client";

import { useState } from "react";

import { ConfirmDialog } from "@/components/overlay/ConfirmDialog";
import {
  ROLE_LABEL,
  useAssignments,
  useAssignRole,
  useRevokeRole,
  useRoles,
} from "@/features/iam/use-staff";
import { ApiError } from "@/shared/api/errors";
import type { BranchOption, RoleAssignment, StaffUser } from "@/shared/api/types";
import { DetailDialog } from "@/components/overlay/DetailDialog";

import styles from "@/shared/ui/screen.module.css";

import local from "./page.module.css";

/**
 * Bảng cấp/thu hồi vai trò cho một nhân viên.
 *
 * 🔴 Đây là màn **nguy hiểm nhất** của cả sản phẩm: cấp sai một vai là mở cửa
 * nghiệp vụ cho người không nên có. Ba quyết định giao diện đều xuất phát từ đó:
 *
 * ① **Phạm vi hiện thành chữ, không phải một ô chọn im lặng.** `branch_id = null`
 *    nghĩa là **toàn chuỗi** (Luật 44/2024 Điều 17a — dược sĩ phụ trách chuỗi).
 *    Một thu ngân bị cấp nhầm phạm vi chuỗi thì vào được mọi cơ sở. Nên mặc định
 *    là **chi nhánh đang làm việc**, và chọn "toàn chuỗi" phải là hành động có ý thức.
 *
 * ② **Hiện số quyền của từng vai ngay lúc chọn.** "Thu ngân" và "Quản trị hệ
 *    thống" nhìn na ná nhau trong một danh sách thả xuống; *10 quyền* và *50
 *    quyền* thì không.
 *
 * ③ **Thu hồi phải xác nhận.** Gỡ vai của chính mình, hoặc gỡ vai cuối cùng của
 *    quản trị viên duy nhất, là cách khoá cửa mà không ai mở lại được.
 */
export function RolePanel({
  user,
  branches,
  onClose,
}: {
  user: StaffUser;
  branches: readonly BranchOption[];
  onClose: () => void;
}) {
  const roles = useRoles();
  const assignments = useAssignments(user.id);
  const assign = useAssignRole(user.id);
  const revoke = useRevokeRole(user.id);

  const [roleId, setRoleId] = useState("");
  const [scope, setScope] = useState<string>(branches[0]?.id ?? "");
  const [error, setError] = useState<string | null>(null);
  const [revoking, setRevoking] = useState<RoleAssignment | null>(null);

  const rows = assignments.data ?? [];
  const chosen = roles.data?.find((r) => r.id === roleId);

  function report(err: unknown, fallback: string) {
    setError(err instanceof ApiError ? err.problem.detail : fallback);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!roleId) return;
    setError(null);
    try {
      await assign.mutateAsync({ role_id: roleId, branch_id: scope === "" ? null : scope });
      setRoleId("");
    } catch (err) {
      report(err, "Không cấp được vai trò.");
    }
  }

  async function confirmRevoke() {
    const a = revoking;
    setRevoking(null);
    if (!a) return;
    setError(null);
    try {
      await revoke.mutateAsync(a.id);
    } catch (err) {
      report(err, "Không thu hồi được vai trò.");
    }
  }

  function branchLabel(branchId: string | null): string {
    if (branchId === null) return "Toàn chuỗi";
    return branches.find((b) => b.id === branchId)?.name ?? `CN ${branchId.slice(0, 8)}`;
  }

  return (
    <DetailDialog open title={`Vai trò · ${user.full_name}`} onClose={onClose}>

      {error && (
        <div className={styles.error} role="alert">
          <span>{error}</span>
          <button type="button" className={styles.retry} onClick={() => setError(null)}>
            Đóng
          </button>
        </div>
      )}

      {assignments.isLoading ? (
        <div className={styles.skeleton} />
      ) : rows.length === 0 ? (
        <p className={local.warnBox}>
          <strong>Chưa có vai trò nào.</strong> Tài khoản đăng nhập được nhưng không
          vào được màn nào — mọi endpoint đều trả 403.
        </p>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Vai trò</th>
                <th>Phạm vi</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.id}>
                  <td>{ROLE_LABEL[a.role_code] ?? a.role_code}</td>
                  <td>
                    <span
                      className={`${styles.chip} ${
                        a.branch_id === null ? styles.chipWarn : styles.chipMuted
                      }`}
                    >
                      {branchLabel(a.branch_id)}
                    </span>
                  </td>
                  <td className={styles.num}>
                    <button
                      type="button"
                      className={styles.ghost}
                      onClick={() => setRevoking(a)}
                      disabled={revoke.isPending}
                    >
                      Thu hồi
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <form className={local.form} onSubmit={submit}>
        <div className={local.row}>
          <label className={local.field}>
            <span className={local.label}>Cấp thêm vai trò</span>
            <select
              className={styles.select}
              value={roleId}
              onChange={(e) => setRoleId(e.target.value)}
              required
            >
              <option value="">— chọn vai trò —</option>
              {(roles.data ?? []).map((r) => (
                <option key={r.id} value={r.id}>
                  {ROLE_LABEL[r.code] ?? r.name} ({r.permissions.length} quyền)
                </option>
              ))}
            </select>
          </label>

          <label className={local.field}>
            <span className={local.label}>Phạm vi</span>
            <select
              className={styles.select}
              value={scope}
              onChange={(e) => setScope(e.target.value)}
            >
              {branches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
              <option value="">Toàn chuỗi (mọi cơ sở)</option>
            </select>
          </label>
        </div>

        {chosen && (
          <p className={scope === "" ? local.warnBox : local.hint}>
            {scope === "" ? (
              <>
                <strong>Cấp cho TOÀN CHUỖI.</strong> Người này sẽ có{" "}
                {chosen.permissions.length} quyền ở <strong>mọi cơ sở</strong>, kể cả
                cơ sở mở sau này.
              </>
            ) : (
              <>
                {chosen.permissions.length} quyền, chỉ trong{" "}
                {branches.find((b) => b.id === scope)?.name}.
              </>
            )}
          </p>
        )}

        <div className={local.actions}>
          <button type="submit" className={styles.button} disabled={!roleId || assign.isPending}>
            {assign.isPending ? "Đang cấp…" : "Cấp vai trò"}
          </button>
        </div>
      </form>

      <ConfirmDialog
        open={revoking !== null}
        title={`Thu hồi "${revoking ? (ROLE_LABEL[revoking.role_code] ?? revoking.role_code) : ""}"?`}
        description={`${user.full_name} sẽ mất mọi quyền của vai này ngay lập tức. Phiên đang mở của họ vẫn giữ quyền cũ cho tới khi token hết hạn hoặc đăng nhập lại.`}
        confirmLabel="Thu hồi"
        tone="danger"
        onConfirm={confirmRevoke}
        onCancel={() => setRevoking(null)}
      />
    </DetailDialog>
  );
}
