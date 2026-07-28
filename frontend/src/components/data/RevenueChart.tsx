"use client";

import { useId, useState } from "react";

import { formatMoney } from "@/shared/format/number";

import styles from "./RevenueChart.module.css";

export interface RevenuePoint {
  /** ISO `YYYY-MM-DD`. */
  date: string;
  revenue: number;
}

/**
 * Doanh thu theo ngày — MỘT chuỗi, nên là đường + vùng tô, không phải cột.
 *
 * Vì sao vẽ tay bằng SVG thay vì kéo thư viện: đây là biểu đồ duy nhất của sản
 * phẩm. Recharts/Chart.js nặng hơn toàn bộ `src/` hiện tại, và kéo theo một hệ
 * màu thứ hai cạnh tranh với token. Nếu sau này cần từ ba loại biểu đồ trở lên
 * thì mở lại quyết định này (`docs/ui/DESIGN_SYSTEM.md` §8).
 *
 * Màu: `--chart-1` — một chuỗi thì **không cần chú giải**, tiêu đề đã nói nó là gì.
 *
 * Nhãn trực tiếp chỉ ở ba điểm (cao nhất · thấp nhất · mới nhất), không phải mọi
 * điểm: một con số trên từng điểm là cách chắc chắn nhất để không ai đọc được
 * đường.
 */
export function RevenueChart({
  points,
  height = 180,
}: {
  points: RevenuePoint[];
  height?: number;
}) {
  const gradientId = useId();
  const [hover, setHover] = useState<number | null>(null);

  if (points.length < 2) {
    return <p className={styles.thin}>Chưa đủ dữ liệu để vẽ biểu đồ.</p>;
  }

  // Toạ độ trong hệ 0–100 × 0–100 rồi để SVG co giãn: không phải đo DOM, không
  // phải lắng nghe resize, và co giãn mượt ở mọi bề rộng.
  const width = 100;
  const max = Math.max(...points.map((p) => p.revenue), 1);
  const stepX = width / (points.length - 1);
  const xy = points.map((p, i) => ({
    x: i * stepX,
    y: 100 - (p.revenue / max) * 92 - 4, // chừa 4% trên/dưới để nét không cụt
    ...p,
  }));

  const line = xy.map((p, i) => `${i === 0 ? "M" : "L"}${p.x} ${p.y}`).join(" ");
  const area = `${line} L${width} 100 L0 100 Z`;

  const peak = xy.reduce((a, b) => (b.revenue > a.revenue ? b : a));
  const low = xy.reduce((a, b) => (b.revenue < a.revenue ? b : a));
  const last = xy[xy.length - 1];
  const marked = new Set([peak, low, last]);
  const active = hover === null ? null : xy[hover];

  return (
    <figure className={styles.figure}>
      <svg
        className={styles.svg}
        viewBox={`0 0 ${width} 100`}
        preserveAspectRatio="none"
        style={{ height }}
        role="img"
        aria-label={`Doanh thu ${points.length} ngày gần nhất, cao nhất ${formatMoney(
          String(peak.revenue),
        )} đồng ngày ${peak.date}`}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--chart-1)" stopOpacity="0.28" />
            <stop offset="100%" stopColor="var(--chart-1)" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {[25, 50, 75].map((y) => (
          <line key={y} x1="0" y1={y} x2={width} y2={y} className={styles.grid} />
        ))}

        <path d={area} fill={`url(#${gradientId})`} />
        {/* vectorEffect: giữ nét 2px thật kể cả khi viewBox bị kéo giãn phi tỉ lệ */}
        <path d={line} className={styles.line} vectorEffect="non-scaling-stroke" />

        {active && (
          <line
            x1={active.x}
            y1="0"
            x2={active.x}
            y2="100"
            className={styles.crosshair}
            vectorEffect="non-scaling-stroke"
          />
        )}

        {xy.map((p, i) => (
          <circle
            key={p.date}
            cx={p.x}
            cy={p.y}
            r={marked.has(p) || hover === i ? 1.6 : 0}
            className={styles.dot}
          />
        ))}

        {/* Vùng bắt chuột rộng hơn nét vẽ — ngón tay không trúng một đường 2px. */}
        {xy.map((p, i) => (
          <rect
            key={`hit-${p.date}`}
            x={p.x - stepX / 2}
            y="0"
            width={stepX}
            height="100"
            fill="transparent"
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
          />
        ))}
      </svg>

      <figcaption className={styles.caption}>
        {active ? (
          <span className={styles.tooltip}>
            <strong>{viDate(active.date)}</strong> · {formatMoney(String(active.revenue))} ₫
          </span>
        ) : (
          <>
            <span>
              Cao nhất {viDate(peak.date)} · {formatMoney(String(peak.revenue))} ₫
            </span>
            <span className={styles.muted}>
              Thấp nhất {viDate(low.date)} · {formatMoney(String(low.revenue))} ₫
            </span>
          </>
        )}
      </figcaption>
    </figure>
  );
}

function viDate(iso: string): string {
  const [, m, d] = iso.split("-");
  return `${d}/${m}`;
}
