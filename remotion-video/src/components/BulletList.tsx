/**
 * BulletList — 要点列表
 * 标题先入，每条要点从右侧滑入（错帧 12 帧）
 */
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../design-system";
import type { BulletListProps } from "../types";

const ITEM_DELAY = 12;

export const BulletList: React.FC<BulletListProps> = ({ title, items }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleAnim = spring({ frame, fps, config: { damping: 16, stiffness: 90 }, durationInFrames: 28 });

  // 装饰线
  const lineAnim = spring({ frame: frame - 8, fps, config: { damping: 20, stiffness: 80 }, durationInFrames: 25 });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.colors.background,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: `60px ${theme.spacing.pagePadding}px`,
        fontFamily: theme.fonts.title,
      }}
    >
      {/* 标题 */}
      <div
        style={{
          fontSize: theme.fontSize.title,
          fontWeight: 900,
          color: theme.colors.accent,
          marginBottom: 16,
          opacity: interpolate(titleAnim, [0, 1], [0, 1]),
          transform: `translateY(${interpolate(titleAnim, [0, 1], [-24, 0])}px)`,
        }}
      >
        {title}
      </div>

      {/* 装饰线 */}
      <div
        style={{
          width: interpolate(lineAnim, [0, 1], [0, 120]),
          height: 3,
          backgroundColor: theme.colors.accent,
          borderRadius: 2,
          marginBottom: 40,
          opacity: 0.7,
        }}
      />

      {/* 要点列表 */}
      <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
        {items.map((item, i) => {
          const itemAnim = spring({
            frame: frame - 20 - i * ITEM_DELAY,
            fps,
            config: { damping: 16, stiffness: 80 },
            durationInFrames: 28,
          });
          const itemOpacity = interpolate(itemAnim, [0, 1], [0, 1]);
          const itemX = interpolate(itemAnim, [0, 1], [60, 0]);

          // bullet 弹出
          const bulletAnim = spring({
            frame: frame - 20 - i * ITEM_DELAY,
            fps,
            config: { damping: 12, stiffness: 140 },
            durationInFrames: 20,
          });
          const bulletScale = interpolate(bulletAnim, [0, 1], [0, 1]);

          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 20,
                opacity: itemOpacity,
                transform: `translateX(${itemX}px)`,
              }}
            >
              {/* Bullet 图标 */}
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: "50%",
                  backgroundColor: theme.colors.primary,
                  marginTop: 10,
                  flexShrink: 0,
                  transform: `scale(${bulletScale})`,
                  boxShadow: `0 0 8px ${theme.colors.primary}88`,
                }}
              />
              <div
                style={{
                  fontSize: theme.fontSize.body,
                  color: theme.colors.text,
                  lineHeight: 1.6,
                  maxWidth: 1100,
                }}
              >
                {item.text}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
