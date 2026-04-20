import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { theme } from "../design-system";

interface TransitionProps {
  durationInFrames: number;
  color: string;
}

/** 段落开头：从背景色淡入到透明 */
export const FadeIn: React.FC<TransitionProps> = ({ durationInFrames, color }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, durationInFrames], [1, 0], {
    extrapolateRight: "clamp",
    easing: theme.easings.easeOutCubic,
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
    easing: theme.easings.easeInOutCubic,
  });
  return (
    <AbsoluteFill
      style={{ backgroundColor: color, opacity, pointerEvents: "none" }}
    />
  );
};

/** 段落开头：从右侧滑入（覆盖层从左向右消失） */
export const SlideIn: React.FC<TransitionProps> = ({ durationInFrames, color }) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateRight: "clamp",
    easing: theme.easings.entrance,
  });
  // 覆盖层从 translateX(0) 滑出到 translateX(-100%)
  return (
    <AbsoluteFill
      style={{
        backgroundColor: color,
        transform: `translateX(${-progress * 100}%)`,
        pointerEvents: "none",
      }}
    />
  );
};

/** 段落末尾：从右侧覆盖进来 */
export const SlideOverlay: React.FC<TransitionProps> = ({ durationInFrames, color }) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateRight: "clamp",
    easing: theme.easings.easeInOutCubic,
  });
  return (
    <AbsoluteFill
      style={{
        backgroundColor: color,
        transform: `translateX(${100 - progress * 100}%)`,
        pointerEvents: "none",
      }}
    />
  );
};
