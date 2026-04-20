/**
 * BarChartAnimated — 柱状图
 * 柱子 spring 依次生长 + 渐变 + 发光；数值标签 easeOut countUp + 延迟渐现；
 * X 轴标签 measureText 动态选字号；Y 轴刻度自动生成。
 */
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { measureText } from "@remotion/layout-utils";
import { theme, barGradient, glowShadow } from "../design-system";
import { fontFamily } from "../fonts";
import type { BarChartAnimatedProps } from "../types";

const DEFAULT_COLORS = [
  theme.colors.primary,
  theme.colors.accent,
  theme.colors.secondary,
  theme.colors.danger,
  "#ce93d8",
  "#80deea",
];

const BAR_DELAY = 6;
const GAP = 24;

function computeYSteps(maxVal: number): number[] {
  // 取 4 档刻度，向上取整到合理的量级
  const magnitude = Math.pow(10, Math.floor(Math.log10(maxVal)));
  const ceilMax = Math.ceil(maxVal / magnitude) * magnitude;
  const step = ceilMax / 4;
  return [0, step, step * 2, step * 3, ceilMax];
}

export const BarChartAnimated: React.FC<BarChartAnimatedProps> = ({
  title,
  data,
  unit = "",
  highlightIndex,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const maxVal = Math.max(...data.map((d) => d.value), 1);
  const ySteps = computeYSteps(maxVal);
  const yMax = ySteps[ySteps.length - 1];

  // X 轴标签：根据最长标签选字号（label 26 / small 20）
  const maxLabel = data.reduce((a, d) => (d.label.length > a.length ? d.label : a), "");
  const chartAreaWidth = width - 2 * theme.spacing.pagePadding - 120;
  const perLabelWidth = chartAreaWidth / data.length - 16;
  const labelAt = (size: number) =>
    measureText({ text: maxLabel, fontFamily, fontSize: size, fontWeight: "400" }).width;
  const xLabelFontSize =
    labelAt(theme.fontSize.label) <= perLabelWidth
      ? theme.fontSize.label
      : theme.fontSize.small;

  const chartHeight = height - 420;
  const titleAnim = spring({ frame, fps, config: theme.springs.gentle, durationInFrames: 25 });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.colors.background,
        padding: `60px ${theme.spacing.pagePadding}px`,
        display: "flex",
        flexDirection: "column",
        gap: 24,
        fontFamily: theme.fonts.title,
      }}
    >
      <div
        style={{
          fontSize: theme.fontSize.title,
          fontWeight: 800,
          color: theme.colors.accent,
          textAlign: "center",
          opacity: interpolate(titleAnim, [0, 1], [0, 1]),
          transform: `translateY(${interpolate(titleAnim, [0, 1], [-20, 0])}px)`,
          flexShrink: 0,
        }}
      >
        {title}
      </div>

      <div style={{ display: "flex", flex: 1, gap: 20, marginTop: 12 }}>
        {/* Y 轴刻度 */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            height: chartHeight,
            paddingRight: 16,
            borderRight: `2px solid ${theme.colors.border}`,
          }}
        >
          {ySteps
            .slice()
            .reverse()
            .map((s) => (
              <div
                key={s}
                style={{
                  color: theme.colors.textSecondary,
                  fontSize: theme.fontSize.small,
                  textAlign: "right",
                  fontFamily: theme.fonts.data,
                }}
              >
                {s}
                {unit}
              </div>
            ))}
        </div>

        {/* 柱区 + X 轴 */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          <div
            style={{
              display: "flex",
              alignItems: "flex-end",
              height: chartHeight,
              borderBottom: `2px solid ${theme.colors.border}`,
              gap: GAP,
            }}
          >
            {data.map((item, i) => {
              const progress = spring({
                frame: frame - i * BAR_DELAY - 10,
                fps,
                config: theme.springs.smooth,
                durationInFrames: 45,
              });
              const valueOpacity = interpolate(
                frame - i * BAR_DELAY - 35,
                [0, 15],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
              );
              const valueProgress = interpolate(
                frame - i * BAR_DELAY - 20,
                [0, 30],
                [0, 1],
                {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                  easing: theme.easings.easeOutCubic,
                },
              );
              const displayValue = Math.round(item.value * valueProgress);

              const barH = (item.value / yMax) * chartHeight * progress;
              const color = item.color || DEFAULT_COLORS[i % DEFAULT_COLORS.length];
              const isHighlighted = highlightIndex === i;

              return (
                <div
                  key={i}
                  style={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "flex-end",
                    alignItems: "center",
                    gap: 10,
                  }}
                >
                  <div
                    style={{
                      opacity: valueOpacity,
                      color,
                      fontSize: theme.fontSize.label,
                      fontWeight: 900,
                      fontFamily: theme.fonts.data,
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {displayValue}
                    {unit}
                  </div>
                  <div
                    style={{
                      width: "72%",
                      height: barH,
                      background: barGradient(color),
                      borderRadius: "8px 8px 0 0",
                      boxShadow: glowShadow(color, isHighlighted ? 40 : 24),
                      opacity: progress,
                      outline: isHighlighted ? `2px solid ${color}` : "none",
                      outlineOffset: 2,
                    }}
                  />
                </div>
              );
            })}
          </div>

          <div style={{ display: "flex", gap: GAP, marginTop: 16 }}>
            {data.map((item, i) => {
              const labelOp = interpolate(frame - i * BAR_DELAY - 15, [0, 15], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              });
              return (
                <div
                  key={i}
                  style={{
                    flex: 1,
                    opacity: labelOp,
                    textAlign: "center",
                    fontSize: xLabelFontSize,
                    color: theme.colors.textSecondary,
                    lineHeight: 1.3,
                  }}
                >
                  {item.label}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
