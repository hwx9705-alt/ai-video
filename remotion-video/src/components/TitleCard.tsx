/**
 * TitleCard — 段落标题转场
 * 编号先出 → 主标题缩放弹出（fitText 自适应）→ 装饰线 → 副标题从下滑入。
 */
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { fitText } from "@remotion/layout-utils";
import { theme } from "../design-system";
import { fontFamily } from "../fonts";
import type { TitleCardProps } from "../types";

export const TitleCard: React.FC<TitleCardProps> = ({
  title,
  subtitle,
  sectionNumber,
}) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();

  const numAnim = spring({
    frame,
    fps,
    config: theme.springs.snappy,
    durationInFrames: 20,
  });

  const titleAnim = spring({
    frame: frame - 10,
    fps,
    config: theme.springs.smooth,
    durationInFrames: 35,
  });
  const titleScale = interpolate(titleAnim, [0, 1], [0.7, 1]);
  const titleOpacity = interpolate(titleAnim, [0, 1], [0, 1]);

  const lineAnim = spring({
    frame: frame - 20,
    fps,
    config: theme.springs.gentle,
    durationInFrames: 25,
  });

  const subAnim = spring({
    frame: frame - 30,
    fps,
    config: theme.springs.smooth,
    durationInFrames: 30,
  });
  const subOpacity = interpolate(subAnim, [0, 1], [0, 1]);
  const subY = interpolate(subAnim, [0, 1], [32, 0]);

  // fitText：主标题自适应，上限 hero*1.5
  const availWidth = width - 320;
  const fit = fitText({
    text: title,
    withinWidth: availWidth,
    fontFamily,
    fontWeight: "900",
  });
  const heroFontSize = Math.min(fit.fontSize, theme.fontSize.hero * 1.5);

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
      {sectionNumber !== undefined && (
        <div
          style={{
            fontSize: theme.fontSize.small,
            fontWeight: 700,
            color: theme.colors.primary,
            letterSpacing: 6,
            marginBottom: 20,
            opacity: interpolate(numAnim, [0, 1], [0, 0.85]),
            textTransform: "uppercase",
          }}
        >
          PART {String(sectionNumber).padStart(2, "0")}
        </div>
      )}

      <div
        style={{
          fontSize: heroFontSize,
          fontWeight: 900,
          color: theme.colors.text,
          textAlign: "center",
          opacity: titleOpacity,
          transform: `scale(${titleScale})`,
          lineHeight: 1.2,
          padding: "0 80px",
          letterSpacing: 2,
        }}
      >
        {title}
      </div>

      <div
        style={{
          width: interpolate(lineAnim, [0, 1], [0, 220]),
          height: 4,
          backgroundColor: theme.colors.accent,
          borderRadius: 2,
          margin: "32px 0",
          opacity: interpolate(lineAnim, [0, 1], [0, 0.8]),
        }}
      />

      {subtitle && (
        <div
          style={{
            fontSize: theme.fontSize.subtitle,
            color: theme.colors.accent,
            textAlign: "center",
            opacity: subOpacity,
            transform: `translateY(${subY}px)`,
            padding: "0 120px",
            lineHeight: 1.5,
          }}
        >
          {subtitle}
        </div>
      )}
    </AbsoluteFill>
  );
};
