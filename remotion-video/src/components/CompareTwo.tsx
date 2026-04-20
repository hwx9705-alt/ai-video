/**
 * CompareTwo — 左右对比
 * 两张卡片高度由内容决定（不再撑满整屏），label 用 fitText 自适应，
 * points 字号随条目数分档 + measureText 校对不溢出。
 */
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { fitText, measureText } from "@remotion/layout-utils";
import { theme, glowShadow } from "../design-system";
import { fontFamily } from "../fonts";
import type { CompareTwoProps } from "../types";

const CARD_GAP = 48;
const VS_WIDTH = 100;

function pickBodyFontSize(
  count: number,
  maxWidth: number,
  longestPt: string,
): number {
  const baseTiers =
    count <= 3
      ? [theme.fontSize.subtitle, theme.fontSize.body]
      : count <= 5
        ? [theme.fontSize.body, theme.fontSize.label]
        : [theme.fontSize.label, theme.fontSize.small];

  for (const size of baseTiers) {
    const w = measureText({
      text: longestPt,
      fontFamily,
      fontSize: size,
      fontWeight: "400",
    }).width;
    if (w <= maxWidth) return size;
  }
  return baseTiers[baseTiers.length - 1];
}

export const CompareTwo: React.FC<CompareTwoProps> = ({
  title,
  left,
  right,
  vsText = "VS",
}) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();

  const titleAnim = spring({
    frame,
    fps,
    config: theme.springs.gentle,
    durationInFrames: 25,
  });

  const leftAnim = spring({
    frame: frame - 10,
    fps,
    config: theme.springs.smooth,
    durationInFrames: 35,
  });
  const rightAnim = leftAnim;

  const vsAnim = spring({
    frame: frame - 25,
    fps,
    config: theme.springs.snappy,
    durationInFrames: 25,
  });

  const leftColor = left.color || theme.colors.primary;
  const rightColor = right.color || theme.colors.danger;

  // 布局计算
  const availWidth = width - 2 * theme.spacing.pagePadding;
  const cardWidth = (availWidth - CARD_GAP * 2 - VS_WIDTH) / 2;
  const cardInnerWidth = cardWidth - 80; // 左右 padding 40

  // label 用 fitText 自适应（限制在 subtitle 字号以内）
  const leftLabelFit = fitText({
    text: left.label,
    withinWidth: cardInnerWidth,
    fontFamily,
    fontWeight: "800",
  });
  const rightLabelFit = fitText({
    text: right.label,
    withinWidth: cardInnerWidth,
    fontFamily,
    fontWeight: "800",
  });
  const labelFontSize = Math.min(
    leftLabelFit.fontSize,
    rightLabelFit.fontSize,
    theme.fontSize.subtitle,
  );

  // points 字号分档
  const maxPtCount = Math.max(left.points.length, right.points.length);
  const longestPt = [...left.points, ...right.points].reduce(
    (a, p) => (p.length > a.length ? p : a),
    "",
  );
  const ptFontSize = pickBodyFontSize(maxPtCount, cardInnerWidth - 30, longestPt);
  const ptGap = maxPtCount <= 3 ? 26 : maxPtCount <= 5 ? 20 : 16;

  const renderCard = (
    side: "left" | "right",
    entry: CompareTwoProps["left"],
    color: string,
  ) => {
    const sideAnim = side === "left" ? leftAnim : rightAnim;
    const enterX = interpolate(sideAnim, [0, 1], side === "left" ? [-300, 0] : [300, 0]);
    const enterOpacity = interpolate(sideAnim, [0, 1], [0, 1]);

    return (
      <div
        style={{
          width: cardWidth,
          opacity: enterOpacity,
          transform: `translateX(${enterX}px)`,
          backgroundColor: theme.colors.surface,
          borderRadius: 16,
          padding: "36px 40px",
          borderTop: `4px solid ${color}`,
          display: "flex",
          flexDirection: "column",
          gap: ptGap,
          boxShadow: glowShadow(color, 40),
          flexShrink: 0,
        }}
      >
        <div
          style={{
            fontSize: labelFontSize,
            fontWeight: 800,
            color,
            marginBottom: 8,
          }}
        >
          {entry.label}
        </div>
        {entry.points.map((pt, i) => {
          const ptAnim = spring({
            frame: frame - 30 - i * 10,
            fps,
            config: theme.springs.smooth,
            durationInFrames: 25,
          });
          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 14,
                opacity: interpolate(ptAnim, [0, 1], [0, 1]),
                transform: `translateX(${interpolate(ptAnim, [0, 1], [side === "left" ? -20 : 20, 0])}px)`,
              }}
            >
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  backgroundColor: color,
                  marginTop: ptFontSize * 0.5,
                  flexShrink: 0,
                  boxShadow: `0 0 10px ${color}99`,
                }}
              />
              <div
                style={{
                  fontSize: ptFontSize,
                  color: theme.colors.text,
                  lineHeight: 1.5,
                }}
              >
                {pt}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.colors.background,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: `48px ${theme.spacing.pagePadding}px`,
        fontFamily: theme.fonts.title,
      }}
    >
      <div
        style={{
          fontSize: theme.fontSize.title,
          fontWeight: 800,
          color: theme.colors.accent,
          marginBottom: 40,
          textAlign: "center",
          opacity: interpolate(titleAnim, [0, 1], [0, 1]),
          transform: `translateY(${interpolate(titleAnim, [0, 1], [-20, 0])}px)`,
        }}
      >
        {title}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: CARD_GAP,
          width: "100%",
          justifyContent: "center",
        }}
      >
        {renderCard("left", left, leftColor)}

        <div
          style={{
            width: VS_WIDTH,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            alignSelf: "stretch",
            flexShrink: 0,
          }}
        >
          <div
            style={{
              fontSize: theme.fontSize.subtitle,
              fontWeight: 900,
              color: theme.colors.textMuted,
              opacity: interpolate(vsAnim, [0, 1], [0, 1]),
              transform: `scale(${interpolate(vsAnim, [0, 1], [0.5, 1])})`,
              letterSpacing: 2,
            }}
          >
            {vsText}
          </div>
        </div>

        {renderCard("right", right, rightColor)}
      </div>
    </AbsoluteFill>
  );
};
