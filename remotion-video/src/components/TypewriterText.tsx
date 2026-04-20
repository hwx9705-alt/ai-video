/**
 * TypewriterText — 打字机效果文本
 * 字符逐帧递增显示，光标闪烁。可选 highlight 词在打字到位时变色。
 * 适合：代码演示、引文逐字、强调"过程"、对话式叙述。
 */
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { theme } from "../design-system";
import type { TypewriterTextProps } from "../types";

const CURSOR_BLINK_FRAMES = 16;

export const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  title,
  charsPerSecond = 8,
  highlight,
  showCursor = true,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const typedChars = Math.min(
    text.length,
    Math.floor((frame * charsPerSecond) / fps),
  );
  const typedText = text.slice(0, typedChars);

  const highlightIdx = highlight ? typedText.indexOf(highlight) : -1;
  const hasHighlight = highlightIdx >= 0;
  const preText = hasHighlight ? typedText.slice(0, highlightIdx) : typedText;
  const postText = hasHighlight ? typedText.slice(highlightIdx) : "";

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const cursorOpacity = interpolate(
    frame % CURSOR_BLINK_FRAMES,
    [0, CURSOR_BLINK_FRAMES / 2, CURSOR_BLINK_FRAMES],
    [1, 0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const isDone = typedChars >= text.length;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.colors.background,
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 48,
        padding: theme.spacing.pagePadding,
        fontFamily: theme.fonts.title,
      }}
    >
      {title && (
        <div
          style={{
            opacity: titleOpacity,
            color: theme.colors.accent,
            fontSize: theme.fontSize.title,
            fontWeight: 800,
            textAlign: "center",
            transform: `translateY(${interpolate(titleOpacity, [0, 1], [-20, 0])}px)`,
          }}
        >
          {title}
        </div>
      )}

      <div
        style={{
          fontSize: theme.fontSize.hero - 8,
          fontWeight: 900,
          color: theme.colors.text,
          lineHeight: 1.3,
          textAlign: "center",
          maxWidth: 1600,
        }}
      >
        <span>{preText}</span>
        {hasHighlight && (
          <span style={{ color: theme.colors.primary }}>{postText}</span>
        )}
        {showCursor && !isDone && (
          <span
            style={{
              opacity: cursorOpacity,
              display: "inline-block",
              width: 6,
              height: 72,
              backgroundColor: theme.colors.primary,
              verticalAlign: "middle",
              marginLeft: 8,
            }}
          />
        )}
      </div>
    </AbsoluteFill>
  );
};
