/**
 * DataReveal — 大数字冲击展示
 * 核心数字从 0 countUp 到目标值，副标题延迟淡入
 */
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../design-system";
import type { DataRevealProps } from "../types";

function parseNumber(str: string): number {
  // 提取字符串中的数字部分（支持小数）
  const match = str.match(/[\d.]+/);
  return match ? parseFloat(match[0]) : 0;
}

export const DataReveal: React.FC<DataRevealProps> = ({
  number,
  prefix = "",
  suffix = "",
  subtitle,
  highlightColor = theme.colors.accent,
  countUp = true,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const targetNum = parseNumber(number);
  // 从字符串里提取非数字部分作为内嵌后缀（如 "3.73亿" 中的 "亿"）
  const inlineSuffix = number.replace(/[\d.]/g, "").trim();

  // 数字动画：前 60 帧 countUp
  const countProgress = spring({
    frame,
    fps,
    config: { damping: 20, stiffness: 60, mass: 1.2 },
    durationInFrames: Math.min(60, durationInFrames - 20),
  });

  const displayNum = countUp
    ? interpolate(countProgress, [0, 1], [0, targetNum])
    : targetNum;

  // 格式化数字：整数直接显示，小数保留原字符串的小数位数
  const decimalPlaces = (number.match(/\.(\d+)/) || [])[1]?.length ?? 0;
  const formattedNum = decimalPlaces > 0
    ? displayNum.toFixed(decimalPlaces)
    : Math.round(displayNum).toString();

  // 整体缩放弹入
  const scaleAnim = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 100, mass: 0.8 },
    durationInFrames: 30,
  });
  const scale = interpolate(scaleAnim, [0, 1], [0.6, 1]);
  const opacity = interpolate(scaleAnim, [0, 1], [0, 1]);

  // 副标题淡入（延迟 25 帧）
  const subtitleAnim = spring({
    frame: frame - 25,
    fps,
    config: { damping: 16, stiffness: 80 },
    durationInFrames: 30,
  });
  const subtitleOpacity = interpolate(subtitleAnim, [0, 1], [0, 1]);
  const subtitleY = interpolate(subtitleAnim, [0, 1], [20, 0]);

  // 装饰线（延迟 15 帧）
  const lineAnim = spring({
    frame: frame - 15,
    fps,
    config: { damping: 20, stiffness: 70 },
    durationInFrames: 25,
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.colors.background,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: theme.fonts.title,
      }}
    >
      {/* 数字主体 */}
      <div
        style={{
          opacity,
          transform: `scale(${scale})`,
          display: "flex",
          alignItems: "baseline",
          gap: 8,
        }}
      >
        {prefix && (
          <span style={{ fontSize: 56, fontWeight: 700, color: theme.colors.textSecondary }}>
            {prefix}
          </span>
        )}
        <span
          style={{
            fontSize: theme.fontSize.hero,
            fontWeight: 900,
            color: highlightColor,
            fontFamily: theme.fonts.data,
            letterSpacing: -2,
            lineHeight: 1,
          }}
        >
          {formattedNum}
        </span>
        {(inlineSuffix || suffix) && (
          <span style={{ fontSize: 52, fontWeight: 700, color: highlightColor }}>
            {inlineSuffix || suffix}
          </span>
        )}
      </div>

      {/* 装饰线 */}
      <div
        style={{
          width: interpolate(lineAnim, [0, 1], [0, 200]),
          height: 3,
          backgroundColor: highlightColor,
          borderRadius: 2,
          margin: "28px 0",
          opacity: interpolate(lineAnim, [0, 1], [0, 0.6]),
        }}
      />

      {/* 副标题 */}
      <div
        style={{
          opacity: subtitleOpacity,
          transform: `translateY(${subtitleY}px)`,
          fontSize: theme.fontSize.subtitle,
          color: theme.colors.textSecondary,
          textAlign: "center",
          maxWidth: 900,
          lineHeight: 1.5,
          padding: "0 80px",
        }}
      >
        {subtitle}
      </div>
    </AbsoluteFill>
  );
};
