/**
 * FlowSteps — 流程/步骤图
 * 节点依次点亮（暗色→高亮），箭头随之出现
 */
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../design-system";
import type { FlowStepsProps } from "../types";

const STEP_DELAY = 18; // 每个步骤的激活延迟

export const FlowSteps: React.FC<FlowStepsProps> = ({
  title,
  steps,
  direction = "horizontal",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const isHorizontal = direction === "horizontal" || steps.length <= 4;

  const titleAnim = spring({ frame, fps, config: { damping: 20, stiffness: 80 }, durationInFrames: 25 });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.colors.background,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: `60px ${theme.spacing.pagePadding}px`,
        fontFamily: theme.fonts.title,
      }}
    >
      {/* 标题 */}
      <div
        style={{
          fontSize: theme.fontSize.title,
          fontWeight: 800,
          color: theme.colors.accent,
          marginBottom: 56,
          textAlign: "center",
          opacity: interpolate(titleAnim, [0, 1], [0, 1]),
          transform: `translateY(${interpolate(titleAnim, [0, 1], [-20, 0])}px)`,
        }}
      >
        {title}
      </div>

      {/* 步骤列 */}
      <div
        style={{
          display: "flex",
          flexDirection: isHorizontal ? "row" : "column",
          alignItems: "center",
          gap: 0,
          width: "100%",
          justifyContent: "center",
        }}
      >
        {steps.map((step, i) => {
          const activateFrame = i * STEP_DELAY + 15;
          const stepAnim = spring({
            frame: frame - activateFrame,
            fps,
            config: { damping: 16, stiffness: 100 },
            durationInFrames: 20,
          });
          const isActive = frame >= activateFrame;
          const nodeOpacity = interpolate(stepAnim, [0, 1], [0.2, 1]);
          const nodeScale = interpolate(stepAnim, [0, 1], [0.8, 1]);
          const nodeColor = isActive ? theme.colors.primary : theme.colors.textMuted;
          const textColor = isActive ? theme.colors.text : theme.colors.textMuted;

          // 箭头动画（在当前步骤和下一步之间）
          const arrowAnim = spring({
            frame: frame - activateFrame - 10,
            fps,
            config: { damping: 20, stiffness: 80 },
            durationInFrames: 15,
          });
          const arrowOpacity = interpolate(arrowAnim, [0, 1], [0, 0.8]);

          return (
            <div
              key={i}
              style={{
                display: "flex",
                flexDirection: isHorizontal ? "row" : "column",
                alignItems: "center",
                flex: isHorizontal ? 1 : undefined,
                width: isHorizontal ? undefined : "100%",
              }}
            >
              {/* 步骤节点 */}
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 14,
                  opacity: nodeOpacity,
                  transform: `scale(${nodeScale})`,
                  flex: isHorizontal ? 1 : undefined,
                  padding: isHorizontal ? "0 8px" : "8px 0",
                  minWidth: isHorizontal ? 0 : "auto",
                }}
              >
                {/* 圆形编号 */}
                <div
                  style={{
                    width: 64,
                    height: 64,
                    borderRadius: "50%",
                    backgroundColor: isActive ? nodeColor : "transparent",
                    border: `3px solid ${nodeColor}`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 26,
                    fontWeight: 900,
                    color: isActive ? theme.colors.background : nodeColor,
                    boxShadow: isActive ? `0 0 20px ${nodeColor}66` : "none",
                    flexShrink: 0,
                  }}
                >
                  {i + 1}
                </div>
                {/* 步骤文字 */}
                <div style={{ textAlign: "center", maxWidth: isHorizontal ? 200 : 800 }}>
                  <div style={{ fontSize: 26, fontWeight: 700, color: textColor, lineHeight: 1.3 }}>
                    {step.label}
                  </div>
                  {step.description && (
                    <div style={{ fontSize: 20, color: theme.colors.textMuted, marginTop: 6, lineHeight: 1.4 }}>
                      {step.description}
                    </div>
                  )}
                </div>
              </div>

              {/* 箭头（最后一个步骤不显示） */}
              {i < steps.length - 1 && (
                <div
                  style={{
                    opacity: arrowOpacity,
                    fontSize: 32,
                    color: theme.colors.primary,
                    padding: isHorizontal ? "0 8px" : "8px 0",
                    flexShrink: 0,
                    transform: isHorizontal ? "none" : "rotate(90deg)",
                  }}
                >
                  →
                </div>
              )}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
