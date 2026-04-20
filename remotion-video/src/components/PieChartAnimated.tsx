/**
 * PieChartAnimated — 环形图（市场份额 / 占比分布）
 * SVG donut 分片按 spring 依次展开，图例延迟渐现。
 * 适合：总和=100% 且 ≤5 项的占比数据。
 */
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { theme } from "../design-system";
import type { PieChartAnimatedProps } from "../types";

const CX = 640;
const CY = 540;
const R_OUTER = 280;
const R_INNER = 150;

const polar = (cx: number, cy: number, r: number, angleDeg: number) => {
  const a = ((angleDeg - 90) * Math.PI) / 180;
  return [cx + r * Math.cos(a), cy + r * Math.sin(a)] as const;
};

const donutArc = (startDeg: number, endDeg: number): string => {
  const [x1, y1] = polar(CX, CY, R_OUTER, endDeg);
  const [x2, y2] = polar(CX, CY, R_OUTER, startDeg);
  const [x3, y3] = polar(CX, CY, R_INNER, startDeg);
  const [x4, y4] = polar(CX, CY, R_INNER, endDeg);
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${x1} ${y1} A ${R_OUTER} ${R_OUTER} 0 ${large} 0 ${x2} ${y2} L ${x3} ${y3} A ${R_INNER} ${R_INNER} 0 ${large} 1 ${x4} ${y4} Z`;
};

const DEFAULT_COLORS = [
  theme.colors.primary,
  theme.colors.secondary,
  theme.colors.accent,
  theme.colors.danger,
  theme.colors.textSecondary,
];

export const PieChartAnimated: React.FC<PieChartAnimatedProps> = ({
  title,
  data,
  centerLabel,
  unit = "%",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const total = data.reduce((s, d) => s + d.value, 0) || 1;

  let cursor = 0;
  const slices = data.map((d, i) => {
    const color = d.color || DEFAULT_COLORS[i % DEFAULT_COLORS.length];
    const startDeg = (cursor / total) * 360;
    const endDeg = ((cursor + d.value) / total) * 360;
    cursor += d.value;

    const progress = spring({
      frame: frame - 20 - i * 10,
      fps,
      config: theme.springs.snappy,
    });
    const currentEnd = startDeg + (endDeg - startDeg) * Math.max(0, progress);

    return { ...d, color, startDeg, endDeg, currentEnd, index: i };
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.colors.background,
        fontFamily: theme.fonts.title,
      }}
    >
      {/* 标题 */}
      <div
        style={{
          opacity: titleOpacity,
          position: "absolute",
          top: 80,
          left: 0,
          right: 0,
          textAlign: "center",
          color: theme.colors.accent,
          fontSize: theme.fontSize.title,
          fontWeight: 800,
          transform: `translateY(${interpolate(titleOpacity, [0, 1], [-20, 0])}px)`,
        }}
      >
        {title}
      </div>

      {/* 环形图 SVG */}
      <svg
        viewBox="0 0 1920 1080"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
      >
        {slices.map((s) =>
          s.currentEnd > s.startDeg + 0.5 ? (
            <path
              key={s.label}
              d={donutArc(s.startDeg, s.currentEnd)}
              fill={s.color}
              stroke={theme.colors.background}
              strokeWidth={3}
            />
          ) : null,
        )}

        {centerLabel && (
          <>
            <text
              x={CX}
              y={CY - 10}
              textAnchor="middle"
              fill={theme.colors.textSecondary}
              fontSize={theme.fontSize.label}
              fontFamily={theme.fonts.body}
            >
              {centerLabel}
            </text>
            <text
              x={CX}
              y={CY + 50}
              textAnchor="middle"
              fill={theme.colors.text}
              fontSize={theme.fontSize.title}
              fontWeight={900}
              fontFamily={theme.fonts.data}
            >
              {total}
              {unit}
            </text>
          </>
        )}
      </svg>

      {/* 图例（右侧） */}
      <div
        style={{
          position: "absolute",
          right: 140,
          top: 280,
          display: "flex",
          flexDirection: "column",
          gap: 22,
          minWidth: 440,
        }}
      >
        {slices.map((s) => {
          const legendOp = interpolate(
            frame,
            [30 + s.index * 10, 50 + s.index * 10],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
          );
          const pct = ((s.value / total) * 100).toFixed(0);
          return (
            <div
              key={s.label}
              style={{
                opacity: legendOp,
                display: "flex",
                alignItems: "center",
                gap: 16,
                transform: `translateX(${interpolate(legendOp, [0, 1], [20, 0])}px)`,
              }}
            >
              <div
                style={{
                  width: 22,
                  height: 22,
                  background: s.color,
                  borderRadius: 4,
                  boxShadow: `0 0 12px ${s.color}77`,
                  flexShrink: 0,
                }}
              />
              <div
                style={{
                  color: theme.colors.text,
                  fontSize: theme.fontSize.body,
                  flex: 1,
                }}
              >
                {s.label}
              </div>
              <div
                style={{
                  color: s.color,
                  fontSize: theme.fontSize.body,
                  fontWeight: 900,
                  fontFamily: theme.fonts.data,
                }}
              >
                {pct}
                {unit}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
