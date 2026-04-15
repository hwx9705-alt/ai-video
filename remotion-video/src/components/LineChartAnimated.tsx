/**
 * LineChartAnimated — 折线图
 * stroke-dashoffset 从左到右绘制，标注在线到达时弹出
 * 使用纯 JS 欧氏距离计算路径长度，保证 headless 渲染稳定
 */
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { theme } from "../design-system";
import type { LineChartAnimatedProps } from "../types";

const SVG_W = 1400;
const SVG_H = 520;
const M = { top: 40, right: 60, bottom: 70, left: 90 };
const CW = SVG_W - M.left - M.right;
const CH = SVG_H - M.top - M.bottom;

const DRAW_FRAMES = 60;

function calcPathLength(pts: [number, number][]): number {
  let total = 0;
  for (let i = 1; i < pts.length; i++) {
    const dx = pts[i][0] - pts[i - 1][0];
    const dy = pts[i][1] - pts[i - 1][1];
    total += Math.sqrt(dx * dx + dy * dy);
  }
  return total;
}

function ptsToPath(pts: [number, number][]): string {
  return pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
}

export const LineChartAnimated: React.FC<LineChartAnimatedProps> = ({
  title,
  data,
  unit = "",
  annotations = [],
}) => {
  const frame = useCurrentFrame();

  const xCount = data.length;
  const maxY = Math.max(...data.map((d) => d.y), 1);

  const toX = (i: number) =>
    M.left + (xCount > 1 ? (i / (xCount - 1)) * CW : CW / 2);
  const toY = (v: number) => M.top + CH - (v / maxY) * CH;

  const pts: [number, number][] = data.map((d, i) => [toX(i), toY(d.y)]);
  const pathD = ptsToPath(pts);
  const totalLen = calcPathLength(pts);

  const rawProgress = frame / DRAW_FRAMES;
  const progress = Math.min(1, Math.max(0, rawProgress));
  const dashOffset = totalLen * (1 - progress);

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((r) => ({
    val: maxY * r,
    y: toY(maxY * r),
  }));

  // 找到当前线到达了哪个数据点
  const currentXProgress = progress * (xCount - 1);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.colors.background,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "48px 60px 32px",
        fontFamily: theme.fonts.title,
      }}
    >
      {/* 标题 */}
      <div
        style={{
          fontSize: theme.fontSize.title,
          fontWeight: 800,
          color: theme.colors.accent,
          marginBottom: 24,
          textAlign: "center",
          opacity: interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" }),
        }}
      >
        {title}
      </div>

      {/* Y 轴标签 */}
      {unit && (
        <div
          style={{
            position: "absolute",
            left: 24,
            top: "48%",
            fontSize: 20,
            color: theme.colors.textMuted,
            transform: "rotate(-90deg) translateX(-50%)",
          }}
        >
          {unit}
        </div>
      )}

      <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} style={{ width: "100%", flex: 1, overflow: "visible" }}>
        {/* 网格线 + Y 轴刻度 */}
        {yTicks.map(({ val, y }) => (
          <g key={y}>
            <line x1={M.left} y1={y} x2={SVG_W - M.right} y2={y} stroke={`${theme.colors.border}`} strokeWidth={1} />
            <text x={M.left - 10} y={y + 6} textAnchor="end" fontSize={20} fill={theme.colors.textMuted}>
              {val >= 10000 ? `${(val / 10000).toFixed(1)}w` : val >= 1000 ? `${(val / 1000).toFixed(1)}k` : val.toFixed(val < 10 ? 1 : 0)}
            </text>
          </g>
        ))}

        {/* X 轴 */}
        <line x1={M.left} y1={M.top + CH} x2={SVG_W - M.right} y2={M.top + CH} stroke={theme.colors.textMuted} strokeWidth={2} />
        {/* Y 轴 */}
        <line x1={M.left} y1={M.top} x2={M.left} y2={M.top + CH} stroke={theme.colors.textMuted} strokeWidth={2} />

        {/* X 轴标签 */}
        {data.map((d, i) => (
          <text key={i} x={toX(i)} y={M.top + CH + 40} textAnchor="middle" fontSize={22} fill={theme.colors.textSecondary}>
            {d.x}
          </text>
        ))}

        {/* 折线 */}
        <path
          d={pathD}
          fill="none"
          stroke={theme.colors.primary}
          strokeWidth={4}
          strokeDasharray={totalLen}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* 数据点 */}
        {pts.map(([px, py], i) => {
          const dotOpacity = Math.min(1, Math.max(0, currentXProgress - i + 0.5));
          return (
            <circle key={i} cx={px} cy={py} r={6} fill={theme.colors.primary} opacity={dotOpacity} />
          );
        })}

        {/* 数值标注（线到达后显示） */}
        {pts.map(([px, py], i) => {
          const labelOpacity = Math.min(1, Math.max(0, (currentXProgress - i) * 3));
          return (
            <text key={i} x={px} y={py - 14} textAnchor="middle" fontSize={20} fill={theme.colors.primary} fontWeight={700} opacity={labelOpacity}>
              {data[i].y}{unit}
            </text>
          );
        })}

        {/* 自定义标注 */}
        {annotations.map((ann, i) => {
          const dataIdx = data.findIndex((d) => d.x === ann.x);
          if (dataIdx < 0) return null;
          const annOpacity = Math.min(1, Math.max(0, (currentXProgress - dataIdx) * 3));
          const px = toX(dataIdx);
          const py = toY(data[dataIdx].y);
          return (
            <g key={i} opacity={annOpacity}>
              <rect x={px + 10} y={py - 40} width={ann.text.length * 14 + 16} height={34} rx={6} fill={theme.colors.surface} />
              <text x={px + 18} y={py - 18} fontSize={20} fill={theme.colors.accent} fontWeight={700}>{ann.text}</text>
            </g>
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};
