import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

interface TransitionProps {
  durationInFrames: number;
  color: string;
}

/** 段落开头：从背景色淡入到透明 */
export const FadeIn: React.FC<TransitionProps> = ({ durationInFrames, color }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, durationInFrames], [1, 0], {
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      style={{ backgroundColor: color, opacity, pointerEvents: "none" }}
    />
  );
};

/** 段落末尾：从透明淡出到背景色 */
export const FadeOverlay: React.FC<TransitionProps> = ({ durationInFrames, color }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      style={{ backgroundColor: color, opacity, pointerEvents: "none" }}
    />
  );
};
