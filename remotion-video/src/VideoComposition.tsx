/**
 * VideoComposition — 主合成
 * 读取 StoryboardData，按 segments 依次渲染组件，段间淡入淡出
 */
import { AbsoluteFill, Audio, Sequence, Series, staticFile } from "remotion";
import { COMPONENT_MAP } from "./components";
import { FadeIn, FadeOverlay } from "./components/Transition";
import { theme } from "./design-system";
import type { Segment, StoryboardData } from "./types";

interface Props {
  storyboard: StoryboardData;
}

const FADE_FRAMES = 12; // 0.4s

function segFrames(seg: Segment, fps: number): number {
  return Math.round(seg.durationInSeconds * fps);
}

function getSegmentBackground(seg: Segment): string {
  if (!seg.background) return theme.colors.background;
  if (seg.background.type === "solid") return seg.background.value;
  if (seg.background.type === "gradient") return seg.background.value;
  return theme.colors.background;
}

function renderSegment(seg: Segment): React.ReactNode {
  const Component = COMPONENT_MAP[seg.component];
  if (!Component) {
    // 未知组件：渲染错误提示
    return (
      <AbsoluteFill
        style={{
          backgroundColor: theme.colors.danger,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 32,
          color: "#fff",
          fontFamily: theme.fonts.title,
        }}
      >
        未知组件：{seg.component}
      </AbsoluteFill>
    );
  }
  return <Component {...seg.props} />;
}

export const VideoComposition: React.FC<Props> = ({ storyboard }) => {
  const fps = storyboard.fps || 30;

  return (
    <AbsoluteFill>
      {/* 背景音频 */}
      {storyboard.audioPath && (
        <Audio src={staticFile(storyboard.audioPath)} />
      )}

      <Series>
        {storyboard.segments.map((seg) => {
          const frames = segFrames(seg, fps);
          const bg = getSegmentBackground(seg);

          return (
            <Series.Sequence key={seg.id} durationInFrames={frames}>
              <AbsoluteFill style={{ backgroundColor: bg }}>
                {renderSegment(seg)}

                {/* 淡入 */}
                <FadeIn durationInFrames={FADE_FRAMES} color={bg} />

                {/* 淡出（仅最后 FADE_FRAMES 帧） */}
                <Sequence from={frames - FADE_FRAMES} durationInFrames={FADE_FRAMES}>
                  <FadeOverlay durationInFrames={FADE_FRAMES} color={bg} />
                </Sequence>
              </AbsoluteFill>
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
