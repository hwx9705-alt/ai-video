/**
 * BulletList — 要点列表
 * 标题先入，条目按 length 分档字号，spring translateX 依次滑入。
 */
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { measureText } from "@remotion/layout-utils";
import { theme, glowShadow } from "../design-system";
import { fontFamily } from "../fonts";
import type { BulletListProps } from "../types";

const ITEM_DELAY = 11;

function pickItemFontSize(count: number, longest: string, maxWidth: number): number {
  const tiers =
    count <= 3
      ? [theme.fontSize.subtitle, theme.fontSize.body, theme.fontSize.label]
      : count <= 5
        ? [theme.fontSize.body, theme.fontSize.label, theme.fontSize.small]
        : [theme.fontSize.label, theme.fontSize.small];
  for (const s of tiers) {
    const w = measureText({ text: longest, fontFamily, fontSize: s, fontWeight: "400" }).width;
    if (w <= maxWidth) return s;
  }
  return tiers[tiers.length - 1];
}

export const BulletList: React.FC<BulletListProps> = ({ title, items }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();

  const titleAnim = spring({
    frame,
    fps,
    config: theme.springs.smooth,
    durationInFrames: 28,
  });
  const lineAnim = spring({
    frame: frame - 8,
    fps,
    config: theme.springs.gentle,
    durationInFrames: 25,
  });

  const longest = items.reduce((a, it) => (it.text.length > a.length ? it.text : a), "");
  const itemMaxWidth = width - 2 * theme.spacing.pagePadding - 50;
  const itemFontSize = pickItemFontSize(items.length, longest, itemMaxWidth);
  const gap = items.length <= 3 ? 32 : items.length <= 5 ? 24 : 18;

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
      <div
        style={{
          fontSize: theme.fontSize.title,
          fontWeight: 900,
          color: theme.colors.accent,
          marginBottom: 20,
          opacity: interpolate(titleAnim, [0, 1], [0, 1]),
          transform: `translateY(${interpolate(titleAnim, [0, 1], [-24, 0])}px)`,
        }}
      >
        {title}
      </div>

      <div
        style={{
          width: interpolate(lineAnim, [0, 1], [0, 160]),
          height: 3,
          backgroundColor: theme.colors.accent,
          borderRadius: 2,
          marginBottom: 44,
          opacity: 0.7,
        }}
      />

      <div style={{ display: "flex", flexDirection: "column", gap }}>
        {items.map((item, i) => {
          const itemAnim = spring({
            frame: frame - 20 - i * ITEM_DELAY,
            fps,
            config: theme.springs.smooth,
            durationInFrames: 28,
          });
          const itemOpacity = interpolate(itemAnim, [0, 1], [0, 1]);
          const itemX = interpolate(itemAnim, [0, 1], [80, 0]);

          const bulletAnim = spring({
            frame: frame - 20 - i * ITEM_DELAY,
            fps,
            config: theme.springs.snappy,
            durationInFrames: 20,
          });
          const bulletScale = interpolate(bulletAnim, [0, 1], [0, 1]);
          const bulletSize = itemFontSize < theme.fontSize.body ? 12 : 16;

          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 22,
                opacity: itemOpacity,
                transform: `translateX(${itemX}px)`,
              }}
            >
              <div
                style={{
                  width: bulletSize,
                  height: bulletSize,
                  borderRadius: "50%",
                  backgroundColor: theme.colors.primary,
                  marginTop: itemFontSize * 0.45,
                  flexShrink: 0,
                  transform: `scale(${bulletScale})`,
                  boxShadow: glowShadow(theme.colors.primary, 10),
                }}
              />
              <div
                style={{
                  fontSize: itemFontSize,
                  color: theme.colors.text,
                  lineHeight: 1.6,
                  flex: 1,
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
