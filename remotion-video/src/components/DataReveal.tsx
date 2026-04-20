/**
 * DataReveal — 大数字冲击展示
 * easeOut 数字滚动 + 达成冲击 + 千分位格式化。
 * 字号通过 fitText 自适应容器宽。
 */
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { fitText } from "@remotion/layout-utils";
import { theme, glowShadow } from "../design-system";
import { fontFamily } from "../fonts";
import type { DataRevealProps } from "../types";

const COUNT_FROM = 10;
const COUNT_TO = 80;

function parseNumber(str: string): number {
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
  const { fps, width } = useVideoConfig();

  const targetNum = parseNumber(number);
  const inlineSuffix = number.replace(/[\d.]/g, "").trim();
  const decimalPlaces = (number.match(/\.(\d+)/) || [])[1]?.length ?? 0;

  const progress = countUp
    ? interpolate(frame, [COUNT_FROM, COUNT_TO], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: theme.easings.easeOutCubic,
      })
    : 1;

  const displayNum = targetNum * progress;
  const rawFormatted =
    decimalPlaces > 0 ? displayNum.toFixed(decimalPlaces) : Math.round(displayNum).toString();
  const formattedNum =
    decimalPlaces === 0 && targetNum >= 1000
      ? Math.round(displayNum).toLocaleString("en-US")
      : rawFormatted;

  // 冲击反馈：countUp 完成时一次脉冲
  const impactSpring = spring({
    frame: frame - COUNT_TO,
    fps,
    config: theme.springs.impact,
    durationInFrames: 20,
  });
  const pulse = 1 + Math.max(0, impactSpring) * 0.12;

  // fitText：根据目标字符串测量（用 target，避免 countUp 过程中字号抖动）
  const targetFormatted =
    decimalPlaces === 0 && targetNum >= 1000
      ? targetNum.toLocaleString("en-US")
      : number.replace(/[^\d.]/g, ""); // target raw number part
  const heroWidth = width - 2 * theme.spacing.pagePadding - 400; // 留 prefix/suffix 空间
  const fitted = fitText({
    text: targetFormatted || "0",
    withinWidth: heroWidth,
    fontFamily,
    fontWeight: "900",
  });
  const mainFontSize = Math.min(fitted.fontSize, theme.fontSize.hero * 2);
  const sideFontSize = Math.round(mainFontSize * 0.5);

  // 整体入场
  const scaleAnim = spring({
    frame,
    fps,
    config: theme.springs.snappy,
    durationInFrames: 30,
  });
  const scale = interpolate(scaleAnim, [0, 1], [0.6, 1]) * pulse;
  const opacity = interpolate(scaleAnim, [0, 1], [0, 1]);

  // 副标题（延迟 25 帧）
  const subtitleAnim = spring({
    frame: frame - 25,
    fps,
    config: theme.springs.gentle,
    durationInFrames: 30,
  });
  const subtitleOpacity = interpolate(subtitleAnim, [0, 1], [0, 1]);
  const subtitleY = interpolate(subtitleAnim, [0, 1], [20, 0]);

  // 装饰线（延迟 15 帧）
  const lineAnim = spring({
    frame: frame - 15,
    fps,
    config: theme.springs.gentle,
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
      <div
        style={{
          opacity,
          transform: `scale(${scale})`,
          display: "flex",
          alignItems: "baseline",
          gap: 12,
        }}
      >
        {prefix && (
          <span
            style={{
              fontSize: sideFontSize,
              fontWeight: 700,
              color: theme.colors.textSecondary,
            }}
          >
            {prefix}
          </span>
        )}
        <span
          style={{
            fontSize: mainFontSize,
            fontWeight: 900,
            color: highlightColor,
            fontFamily: theme.fonts.data,
            fontVariantNumeric: "tabular-nums",
            letterSpacing: -2,
            lineHeight: 1,
            textShadow: glowShadow(highlightColor, 40),
          }}
        >
          {formattedNum}
        </span>
        {(inlineSuffix || suffix) && (
          <span
            style={{
              fontSize: sideFontSize,
              fontWeight: 700,
              color: highlightColor,
            }}
          >
            {inlineSuffix || suffix}
          </span>
        )}
      </div>

      <div
        style={{
          width: interpolate(lineAnim, [0, 1], [0, 240]),
          height: 3,
          backgroundColor: highlightColor,
          borderRadius: 2,
          margin: "32px 0",
          opacity: interpolate(lineAnim, [0, 1], [0, 0.6]),
        }}
      />

      <div
        style={{
          opacity: subtitleOpacity,
          transform: `translateY(${subtitleY}px)`,
          fontSize: theme.fontSize.subtitle,
          color: theme.colors.textSecondary,
          textAlign: "center",
          maxWidth: 1100,
          lineHeight: 1.5,
          padding: "0 80px",
        }}
      >
        {subtitle}
      </div>
    </AbsoluteFill>
  );
};
