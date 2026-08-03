"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuthStore } from "@/features/auth/auth-store";
import { useLogin } from "@/features/auth/use-login";
import { ApiError } from "@/shared/api/errors";
import { docVaXoaPhienHet } from "@/shared/api/phien-het";
import type { BranchOption } from "@/shared/api/types";

import styles from "./page.module.css";

function ManDangNhap() {
  const router = useRouter();
  // Đọc cờ MỘT LẦN lúc gắn, rồi xoá. Không đọc qua tham số URL: `AppShell` có một hiệu ứng
  // `replace("/login")` chạy ngay sau `logout()` và ghi đè mất tham số — đã đo thấy hỏng.
  const [phienHet] = useState(docVaXoaPhienHet);
  const login = useLogin();
  const session = useAuthStore((s) => s.session);
  const hydrate = useAuthStore((s) => s.hydrate);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (session) router.replace("/");
  }, [session, router]);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [branches, setBranches] = useState<BranchOption[] | null>(null);
  const [branchId, setBranchId] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await login.mutateAsync({ email, password, branch_id: branchId || undefined });
      router.push("/");
    } catch (err) {
      if (err instanceof ApiError && err.isBranchSelectionRequired) {
        // 400 branch-required: the account reaches several branches and the
        // server won't guess — show the picker it sent back and let the
        // cashier resubmit with branch_id set (docs/15_IAM_DESIGN.md §4).
        setBranches((err.problem.branches as BranchOption[]) ?? []);
        return;
      }
      setError(err instanceof Error ? err.message : "Đăng nhập thất bại");
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.card}>
        {/* Mascot chính thức (gấu đội áo blouse, kính tròn, cầm tablet) chưa
            có tài sản thiết kế — docs/16_BRAND_UI_GUIDE.md §6. Placeholder rõ
            ràng để không ai nhầm đây là art thật. */}
        <div className={styles.mascot} aria-hidden="true">
          🐻
        </div>
        <h1 className={styles.brand}>BERAS</h1>
        <p className={styles.tagline}>Sổ Quản Lý Nhà Thuốc</p>

        {/* 🔴 Nói ra VÌ SAO vừa bị đá về đây (V3-10). Không có câu này thì người đang gõ dở
            một phiếu nhập bị văng ra màn đăng nhập mà không hiểu chuyện gì, và kết luận là
            phần mềm tự thoát. `?phien=het` do AppShell gắn khi máy chủ trả 401. */}
        {phienHet && (
          <p className={styles.error} role="status">
            Phiên đăng nhập đã hết. Vui lòng đăng nhập lại.
          </p>
        )}

        {branches ? (
          <form
            className={styles.form}
            onSubmit={(e) => {
              e.preventDefault();
              handleSubmit(e);
            }}
          >
            <label className={styles.label} htmlFor="branch">
              Chọn chi nhánh
            </label>
            <select
              id="branch"
              className={styles.input}
              value={branchId}
              onChange={(e) => setBranchId(e.target.value)}
              required
            >
              <option value="" disabled>
                — chọn chi nhánh —
              </option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name} ({b.code})
                </option>
              ))}
            </select>
            <button className={styles.submit} type="submit" disabled={login.isPending}>
              {login.isPending ? "Đang vào..." : "Vào ca làm việc"}
            </button>
          </form>
        ) : (
          <form className={styles.form} onSubmit={handleSubmit}>
            <label className={styles.label} htmlFor="email">
              Email
            </label>
            <input
              id="email"
              className={styles.input}
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <label className={styles.label} htmlFor="password">
              Mật khẩu
            </label>
            <input
              id="password"
              className={styles.input}
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button className={styles.submit} type="submit" disabled={login.isPending}>
              {login.isPending ? "Đang đăng nhập..." : "Đăng nhập"}
            </button>
          </form>
        )}

        {error && <p className={styles.error}>{error}</p>}
      </div>
    </main>
  );
}

export default function LoginPage() {
  return <ManDangNhap />;
}
