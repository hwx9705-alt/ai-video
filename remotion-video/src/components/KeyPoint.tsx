/**
 * KeyPoint — 金句/核心观点全屏强调
 * 字号 fitText 自适应；emphasis 词高亮；
 * style=highlight 时用擦除扫光（scaleX 0→1）强调 emphasis 词。
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
import type { KeyPointProps } from "../types";

type KeyPointStyle = "quote" | "statement" | "question" | "highlight";

function splitByEmphasis(
  text: string,
  emphasis: string[],
): Array<{ text: string; emph: boolean }> {
  if (!emphasis || emphasis.length === 0) return [{ text, emph: false }];
  const parts: Array<{ text: string; emph: boolean }> = [];
  let remaining = text;

  while (remaining.length > 0) {
    let earliest = -1;
    let matched = "";
    for (const word of emphasis) {
      const idx = remaining.indexOf(word);
      if (idx !== -1 && (earliest === -1 || idx < earliest)) {
        earliest = idx;
        matched = word;
      }
    }
    if (earliest === -1) {
      parts.push({ text: remaining, emph: false });
      break;
    }
    if (earliest > 0) parts.push({ text: remaining.slice(0, earliest), emph: false });
    parts.push({ text: matched, emph: true });
    remaining = remaining.slice(earliest + matched.length);
  }
  return parts;
}

export const KeyPoint: React.FC<KeyPointProps> = ({
  text,
  emphasis = [],
  style: rawStyle = "statement",
}) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const pointStyle = rawStyle as KeyPointStyle;

  const mainAnim = spring({
    frame,
    fps,
    config: theme.springs.smooth,
    durationInFrames: 35,
  });
  const opacity = interpolate(mainAnim, [0, 1], [0, 1]);
  const scale = interpolate(mainAnim, [0, 1], [0.85, 1]);

  const decoAnim = spring({
    frame: frame - 20,
    fps,
    config: theme.springs.gentle,
    durationInFrames: 25,
  });

  // fitText：给两侧各 160px 余量
  const availWidth = width - 320;
  const fit = fitText({
    text,
    withinWidth: availWidth,
    fontFamily,
    fontWeight: "800",
  });
  // 金句往往字数不多，字号可达到 hero 的 1.2x
  const mainFontSize = Math.min(fit.fontSize, theme.fontSize.hero * 1.2);

  const parts = splitByEmphasis(text, emphasis);

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
      {pointStyle === "quote" && (
        <div
          style={{
            fontSize: mainFontSize * 1.4,
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

      {pointStyle === "question" && (
        <div
          style={{
            fontSize: mainFontSize * 0.9,
            color: theme.colors.primary,
            opacity: interpolate(decoAnim, [0, 1], [0, 0.6]),
            marginBottom: 24,
            transform: `scale(${interpolate(decoAnim, [0, 1], [0.3, 1])}) rotate(${interpolate(decoAnim, [0, 1], [-15, 0])}deg)`,
          }}
        >
          ?
        </div>
      )}

      <div
        style={{
          fontSize: mainFontSize,
          fontWeight: 800,
          color: theme.colors.text,
          textAlign: "center",
          lineHeight: 1.5,
          opacity,
          transform: `scale(${scale})`,
          maxWidth: availWidth,
          position: "relative",
        }}
      >
        {pointStyle === "highlight"
          ? parts.map((p, i) => {
              if (!p.emph) return <span key={i}>{p.text}</span>;
              // highlight 擦除：单调 0→1，避免 spring 过冲回撤造成视觉卡顿
              const emphFrame = 40 + i * 18;
              const wipe = interpolate(frame, [emphFrame, emphFrame + 18], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: theme.easings.easeOutCubic,
              });
              return (
                <span
                  key={i}
                  style={{
                    position: "relative",
                    display: "inline-block",
                    color: theme.colors.text,
                    fontWeight: 900,
                  }}
                >
                  {/* 扫光背景 */}
                  <span
                    style={{
                      position: "absolute",
                      inset: 0,
                      backgroundColor: theme.colors.accent,
                      transform: `scaleX(${wipe})`,
                      transformOrigin: "left",
                      zIndex: -1,
                      borderRadius: 4,
                      opacity: 0.85,
                    }}
                  />
                  <span style={{ position: "relative", padding: "0 6px" }}>{p.text}</span>
                </span>
              );
            })
          : parts.map((p, i) =>
              p.emph ? (
                <span key={i} style={{ color: theme.colors.accent, fontWeight: 900 }}>
                  {p.text}
                </span>
              ) : (
                <span key={i}>{p.text}</span>
              ),
            )}
      </div>

      {pointStyle === "statement" && (
        <div
          style={{
            height: 4,
            backgroundColor: theme.colors.accent,
            borderRadius: 2,
            marginTop: 40,
            width: interpolate(decoAnim, [0, 1], [0, 320]),
            opacity: interpolate(decoAnim, [0, 1], [0, 0.85]),
          }}
        />
      )}
    </AbsoluteFill>
  );
};
