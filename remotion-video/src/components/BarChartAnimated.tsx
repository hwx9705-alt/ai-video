/**
 * BarChartAnimated — 柱状图
 * 柱子从底部依次生长，每根错帧 8 帧
 */
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../design-system";
import type { BarChartAnimatedProps } from "../types";

const DEFAULT_COLORS = [
  theme.colors.primary,
  theme.colors.accent,
  theme.colors.secondary,
  theme.colors.danger,
  "#ce93d8",
  "#80deea",
];

const CHART_H = 440;
const BAR_DELAY = 8;
const GAP = 20;
const PAD = 16;

export const BarChartAnimated: React.FC<BarChartAnimatedProps> = ({
  title,
  data,
  unit = "",
  highlightIndex,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const maxVal = Math.max(...data.map((d) => d.value), 1);
  const barW = Math.min(120, Math.floor(1400 / data.length) - 32);

  const titleAnim = spring({ frame, fps, config: { damping: 20, stiffness: 80 }, durationInFrames: 25 });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.colors.background,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: `60px ${theme.spacing.pagePadding}px`,
        fontFamily: theme.fonts.title,
      }}
    >
      {/* 标题 */}
      <div
        style={{
          fontSize: theme.fontSize.title,
          fontWeight: 800,
          color: theme.colors.accent,
          marginBottom: 48,
          textAlign: "center",
          opacity: interpolate(titleAnim, [0, 1], [0, 1]),
          transform: `translateY(${interpolate(titleAnim, [0, 1], [-20, 0])}px)`,
          flexShrink: 0,
        }}
      >
        {title}
      </div>

      {/* 图表容器：柱区 + X轴，同一 flex 列 */}
      <div style={{ width: "100%", display: "flex", flexDirection: "column" }}>
        {/* 柱区：fixed height，柱子和值标签均绝对定位 */}
        <div
          style={{
            display: "flex",
            alignItems: "stretch",
            gap: GAP,
            height: CHART_H,
            paddingLeft: PAD,
            paddingRight: PAD,
            borderBottom: `2px solid ${theme.colors.border}`,
          }}
        >
          {data.map((item, i) => {
            const progress = spring({
              frame: frame - i * BAR_DELAY,
              fps,
              config: { damping: 14, stiffness: 70, mass: 1.2 },
              durationInFrames: 45,
            });
            const barH = interpolate(progress, [0, 1], [0, (item.value / maxVal) * CHART_H]);
            const color = item.color || DEFAULT_COLORS[i % DEFAULT_COLORS.length];
            const isHighlighted = highlightIndex === i;
            const showLabel = progress > 0.85;

            return (
              <div
                key={i}
                style={{
                  flex: 1,
                  position: "relative",
                }}
              >
                {/* 数值标签：绝对定位在柱顶上方 */}
                <div
                  style={{
                    position: "absolute",
                    bottom: barH + 8,
                    left: 0,
                    right: 0,
                    textAlign: "center",
                    fontSize: theme.fontSize.label,
                    fontWeight: 700,
                    color: theme.colors.text,
                    fontFamily: theme.fonts.data,
                    opacity: showLabel ? 1 : 0,
                    pointerEvents: "none",
                  }}
                >
                  {showLabel ? `${item.value}${unit}` : ""}
                </div>

                {/* 柱子：从底部向上生长 */}
                <div
                  style={{
                    position: "absolute",
                    bottom: 0,
                    left: "50%",
                    transform: "translateX(-50%)",
                    width: barW,
                    height: barH,
                    backgroundColor: color,
                    borderRadius: "6px 6px 0 0",
                    boxShadow: isHighlighted ? `0 0 24px ${color}88` : "none",
                    border: isHighlighted ? `2px solid ${color}` : "none",
                  }}
                />
              </div>
            );
          })}
        </div>

        {/* X 轴标签：与柱区用相同 gap + padding，保证对齐 */}
        <div
          style={{
            display: "flex",
            gap: GAP,
            paddingLeft: PAD,
            paddingRight: PAD,
            marginTop: 14,
          }}
        >
          {data.map((item, i) => (
            <div
              key={i}
              style={{
                flex: 1,
                textAlign: "center",
                fontSize: theme.fontSize.label,
                color: theme.colors.textSecondary,
                lineHeight: 1.3,
              }}
            >
              {item.label}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
