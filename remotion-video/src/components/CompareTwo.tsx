/**
 * CompareTwo — 左右对比
 * 两张卡片从左右两侧飞入，VS 居中出现，要点逐条淡入
 */
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../design-system";
import type { CompareTwoProps } from "../types";

export const CompareTwo: React.FC<CompareTwoProps> = ({
  title,
  left,
  right,
  vsText = "VS",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 标题
  const titleAnim = spring({ frame, fps, config: { damping: 20, stiffness: 80 }, durationInFrames: 25 });

  // 左卡片：从左侧飞入
  const leftAnim = spring({ frame: frame - 10, fps, config: { damping: 16, stiffness: 80 }, durationInFrames: 35 });
  const leftX = interpolate(leftAnim, [0, 1], [-300, 0]);
  const leftOpacity = interpolate(leftAnim, [0, 1], [0, 1]);

  // 右卡片：从右侧飞入
  const rightAnim = spring({ frame: frame - 10, fps, config: { damping: 16, stiffness: 80 }, durationInFrames: 35 });
  const rightX = interpolate(rightAnim, [0, 1], [300, 0]);
  const rightOpacity = interpolate(rightAnim, [0, 1], [0, 1]);

  // VS 文字
  const vsAnim = spring({ frame: frame - 25, fps, config: { damping: 14, stiffness: 100 }, durationInFrames: 25 });

  const leftColor = left.color || theme.colors.primary;
  const rightColor = right.color || theme.colors.danger;

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
      {/* 标题 */}
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

      {/* 三列布局 */}
      <div style={{ display: "flex", width: "100%", gap: 0, alignItems: "stretch", flex: 1 }}>
        {/* 左卡片 */}
        <div
          style={{
            flex: 1,
            opacity: leftOpacity,
            transform: `translateX(${leftX}px)`,
            backgroundColor: theme.colors.surface,
            borderRadius: 16,
            padding: 40,
            borderTop: `4px solid ${leftColor}`,
            display: "flex",
            flexDirection: "column",
            gap: 20,
            marginRight: 24,
          }}
        >
          <div style={{ fontSize: 34, fontWeight: 800, color: leftColor, marginBottom: 8 }}>
            {left.label}
          </div>
          {left.points.map((pt, i) => {
            const ptAnim = spring({ frame: frame - 30 - i * 12, fps, config: { damping: 18, stiffness: 80 }, durationInFrames: 25 });
            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 14,
                  opacity: interpolate(ptAnim, [0, 1], [0, 1]),
                  transform: `translateX(${interpolate(ptAnim, [0, 1], [-20, 0])}px)`,
                }}
              >
                <div style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: leftColor, marginTop: 12, flexShrink: 0 }} />
                <div style={{ fontSize: theme.fontSize.body, color: theme.colors.text, lineHeight: 1.5 }}>{pt}</div>
              </div>
            );
          })}
        </div>

        {/* VS 中心 */}
        <div
          style={{
            width: 100,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexDirection: "column",
            gap: 8,
            flexShrink: 0,
          }}
        >
          <div
            style={{
              fontSize: 42,
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

        {/* 右卡片 */}
        <div
          style={{
            flex: 1,
            opacity: rightOpacity,
            transform: `translateX(${rightX}px)`,
            backgroundColor: theme.colors.surface,
            borderRadius: 16,
            padding: 40,
            borderTop: `4px solid ${rightColor}`,
            display: "flex",
            flexDirection: "column",
            gap: 20,
            marginLeft: 24,
          }}
        >
          <div style={{ fontSize: 34, fontWeight: 800, color: rightColor, marginBottom: 8 }}>
            {right.label}
          </div>
          {right.points.map((pt, i) => {
            const ptAnim = spring({ frame: frame - 30 - i * 12, fps, config: { damping: 18, stiffness: 80 }, durationInFrames: 25 });
            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 14,
                  opacity: interpolate(ptAnim, [0, 1], [0, 1]),
                  transform: `translateX(${interpolate(ptAnim, [0, 1], [20, 0])}px)`,
                }}
              >
                <div style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: rightColor, marginTop: 12, flexShrink: 0 }} />
                <div style={{ fontSize: theme.fontSize.body, color: theme.colors.text, lineHeight: 1.5 }}>{pt}</div>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
