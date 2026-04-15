/**
 * TitleCard — 段落标题转场
 * 编号先出，主标题缩放弹出，副标题从下滑入
 */
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../design-system";
import type { TitleCardProps } from "../types";

export const TitleCard: React.FC<TitleCardProps> = ({
  title,
  subtitle,
  sectionNumber,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 编号
  const numAnim = spring({ frame, fps, config: { damping: 14, stiffness: 120 }, durationInFrames: 20 });

  // 主标题（延迟 10 帧）
  const titleAnim = spring({ frame: frame - 10, fps, config: { damping: 14, stiffness: 100, mass: 0.9 }, durationInFrames: 35 });
  const titleScale = interpolate(titleAnim, [0, 1], [0.7, 1]);
  const titleOpacity = interpolate(titleAnim, [0, 1], [0, 1]);

  // 装饰线（延迟 20 帧）
  const lineAnim = spring({ frame: frame - 20, fps, config: { damping: 20, stiffness: 80 }, durationInFrames: 25 });

  // 副标题（延迟 30 帧）
  const subAnim = spring({ frame: frame - 30, fps, config: { damping: 16, stiffness: 80 }, durationInFrames: 30 });
  const subOpacity = interpolate(subAnim, [0, 1], [0, 1]);
  const subY = interpolate(subAnim, [0, 1], [24, 0]);

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
      {/* 章节编号 */}
      {sectionNumber !== undefined && (
        <div
          style={{
            fontSize: 22,
            fontWeight: 700,
            color: theme.colors.primary,
            letterSpacing: 6,
            marginBottom: 20,
            opacity: interpolate(numAnim, [0, 1], [0, 0.8]),
            textTransform: "uppercase",
          }}
        >
          PART {String(sectionNumber).padStart(2, "0")}
        </div>
      )}

      {/* 主标题 */}
      <div
        style={{
          fontSize: theme.fontSize.hero,
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

      {/* 装饰线 */}
      <div
        style={{
          width: interpolate(lineAnim, [0, 1], [0, 180]),
          height: 4,
          backgroundColor: theme.colors.accent,
          borderRadius: 2,
          margin: "28px 0",
        }}
      />

      {/* 副标题 */}
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
