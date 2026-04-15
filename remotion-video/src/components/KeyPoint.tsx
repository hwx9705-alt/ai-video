/**
 * KeyPoint — 金句/核心观点全屏强调
 * emphasis 中的词以高亮色显示，按 style 有不同动画效果
 */
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../design-system";
import type { KeyPointProps } from "../types";

function highlightText(text: string, emphasis: string[], color: string): React.ReactNode {
  if (!emphasis || emphasis.length === 0) return text;

  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    let earliest = -1;
    let matchedWord = "";

    for (const word of emphasis) {
      const idx = remaining.indexOf(word);
      if (idx !== -1 && (earliest === -1 || idx < earliest)) {
        earliest = idx;
        matchedWord = word;
      }
    }

    if (earliest === -1) {
      parts.push(<span key={key++}>{remaining}</span>);
      break;
    }

    if (earliest > 0) {
      parts.push(<span key={key++}>{remaining.slice(0, earliest)}</span>);
    }
    parts.push(
      <span key={key++} style={{ color, fontWeight: 900 }}>
        {matchedWord}
      </span>
    );
    remaining = remaining.slice(earliest + matchedWord.length);
  }

  return <>{parts}</>;
}

export const KeyPoint: React.FC<KeyPointProps> = ({
  text,
  emphasis = [],
  style: pointStyle = "statement",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const mainAnim = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 80, mass: 1 },
    durationInFrames: 35,
  });
  const opacity = interpolate(mainAnim, [0, 1], [0, 1]);
  const scale = interpolate(mainAnim, [0, 1], [0.85, 1]);

  // 装饰线/符号动画
  const decoAnim = spring({
    frame: frame - 20,
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
        padding: `60px 120px`,
        fontFamily: theme.fonts.title,
      }}
    >
      {/* 引号装饰（quote 风格） */}
      {pointStyle === "quote" && (
        <div
          style={{
            fontSize: 120,
            color: theme.colors.accent,
            opacity: interpolate(decoAnim, [0, 1], [0, 0.3]),
            lineHeight: 0.8,
            marginBottom: 20,
            alignSelf: "flex-start",
            transform: `scale(${interpolate(decoAnim, [0, 1], [0.5, 1])})`,
          }}
        >
          "
        </div>
      )}

      {/* 问号装饰（question 风格） */}
      {pointStyle === "question" && (
        <div
          style={{
            fontSize: 80,
            color: theme.colors.primary,
            opacity: interpolate(decoAnim, [0, 1], [0, 0.6]),
            marginBottom: 24,
            transform: `scale(${interpolate(decoAnim, [0, 1], [0.3, 1])}) rotate(${interpolate(decoAnim, [0, 1], [-15, 0])}deg)`,
          }}
        >
          ?
        </div>
      )}

      {/* 主文字 */}
      <div
        style={{
          fontSize: 58,
          fontWeight: 800,
          color: theme.colors.text,
          textAlign: "center",
          lineHeight: 1.55,
          opacity,
          transform: `scale(${scale})`,
          maxWidth: 1200,
        }}
      >
        {highlightText(text, emphasis, theme.colors.accent)}
      </div>

      {/* statement 风格：底部强调线 */}
      {pointStyle === "statement" && (
        <div
          style={{
            height: 4,
            backgroundColor: theme.colors.accent,
            borderRadius: 2,
            marginTop: 32,
            width: interpolate(decoAnim, [0, 1], [0, 280]),
            opacity: interpolate(decoAnim, [0, 1], [0, 0.8]),
          }}
        />
      )}
    </AbsoluteFill>
  );
};
