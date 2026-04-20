/**
 * FlowSteps — 流程/步骤图
 * 支持 horizontal / vertical / circular 三种排列。
 * 节点 spring 依次点亮，圆周模式中央可选旋转装饰。
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
import type { FlowStepsProps } from "../types";

const STEP_DELAY = 16;

function pickLabelFontSize(
  text: string,
  maxWidth: number,
  baseline: number,
  fallback: number,
): number {
  const w = measureText({ text, fontFamily, fontSize: baseline, fontWeight: "700" }).width;
  return w <= maxWidth ? baseline : fallback;
}

const LinearFlow: React.FC<FlowStepsProps & { isHorizontal: boolean }> = ({
  steps,
  isHorizontal,
}) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();

  // 容器可用宽度计算每步最大宽度
  const availWidth = width - 2 * theme.spacing.pagePadding;
  const arrowBudget = 48 * (steps.length - 1);
  const perStepMaxWidth = isHorizontal
    ? Math.floor((availWidth - arrowBudget) / steps.length) - 20
    : 800;

  const longestLabel = steps.reduce((a, s) => (s.label.length > a.length ? s.label : a), "");
  const longestDesc = steps.reduce(
    (a, s) => (s.description && s.description.length > a.length ? s.description : a),
    "",
  );

  const labelFontSize = pickLabelFontSize(
    longestLabel,
    perStepMaxWidth,
    theme.fontSize.body,
    theme.fontSize.label,
  );
  const descFontSize = pickLabelFontSize(
    longestDesc || "",
    perStepMaxWidth,
    theme.fontSize.label,
    theme.fontSize.small,
  );

  return (
    <div
      style={{
        display: "flex",
        flexDirection: isHorizontal ? "row" : "column",
        alignItems: "center",
        width: "100%",
        justifyContent: "center",
        gap: 0,
      }}
    >
      {steps.map((step, i) => {
        const activateFrame = i * STEP_DELAY + 15;
        const stepAnim = spring({
          frame: frame - activateFrame,
          fps,
          config: theme.springs.snappy,
          durationInFrames: 22,
        });
        const isActive = frame >= activateFrame;
        const nodeOpacity = interpolate(stepAnim, [0, 1], [0.2, 1]);
        const nodeScale = interpolate(stepAnim, [0, 1], [0.8, 1]);
        const nodeColor = isActive ? theme.colors.primary : theme.colors.textMuted;
        const textColor = isActive ? theme.colors.text : theme.colors.textMuted;

        const arrowAnim = spring({
          frame: frame - activateFrame - 8,
          fps,
          config: theme.springs.gentle,
          durationInFrames: 15,
        });
        const arrowOpacity = interpolate(arrowAnim, [0, 1], [0, 0.85]);

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
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 16,
                opacity: nodeOpacity,
                transform: `scale(${nodeScale})`,
                flex: isHorizontal ? 1 : undefined,
                padding: isHorizontal ? "0 8px" : "12px 0",
              }}
            >
              <div
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: "50%",
                  backgroundColor: isActive ? nodeColor : "transparent",
                  border: `3px solid ${nodeColor}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: theme.fontSize.label,
                  fontWeight: 900,
                  color: isActive ? theme.colors.background : nodeColor,
                  boxShadow: isActive ? glowShadow(nodeColor, 24) : "none",
                  flexShrink: 0,
                }}
              >
                {i + 1}
              </div>
              <div style={{ textAlign: "center", maxWidth: perStepMaxWidth }}>
                <div
                  style={{
                    fontSize: labelFontSize,
                    fontWeight: 700,
                    color: textColor,
                    lineHeight: 1.3,
                  }}
                >
                  {step.label}
                </div>
                {step.description && (
                  <div
                    style={{
                      fontSize: descFontSize,
                      color: isActive ? theme.colors.textSecondary : theme.colors.textMuted,
                      marginTop: 8,
                      lineHeight: 1.4,
                    }}
                  >
                    {step.description}
                  </div>
                )}
              </div>
            </div>

            {i < steps.length - 1 && (
              <div
                style={{
                  opacity: arrowOpacity,
                  fontSize: 40,
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
  );
};

const CircularFlow: React.FC<FlowStepsProps> = ({ steps, centerIcon }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const NODE_W = 280;
  const NODE_H_EST = 210;
  const cx = width / 2;
  const cy = height / 2 + 20;
  // 半径：同时保证水平与垂直方向都不超出可视区（顶部 180px 留给标题）
  const hRadius = (width - 2 * theme.spacing.pagePadding - NODE_W) / 2;
  const vRadius = (height - 260 - NODE_H_EST) / 2;
  const radius = Math.min(hRadius, vRadius, 260);

  const colors = [
    theme.colors.primary,
    theme.colors.accent,
    theme.colors.secondary,
    theme.colors.danger,
    "#ce93d8",
    "#80deea",
  ];

  return (
    <div style={{ position: "relative", width: "100%", flex: 1 }}>
      {centerIcon && (
        <div
          style={{
            position: "absolute",
            left: cx - 60,
            top: cy - 60,
            fontSize: 96,
            fontFamily: "'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', sans-serif",
            transform: `rotate(${(frame * 1.5) % 360}deg)`,
          }}
        >
          {centerIcon}
        </div>
      )}

      {steps.map((step, i) => {
        const angle = (i * (360 / steps.length) - 90) * (Math.PI / 180);
        const x = cx + radius * Math.cos(angle);
        const y = cy + radius * Math.sin(angle);
        const delay = i * 14 + 20;
        const color = colors[i % colors.length];

        const sc = spring({
          frame: frame - delay,
          fps,
          config: theme.springs.snappy,
        });
        const opacity = interpolate(frame - delay, [0, 15], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        if (frame < delay) return null;

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x - NODE_W / 2,
              top: y - NODE_H_EST / 2,
              width: NODE_W,
              opacity,
              transform: `scale(${Math.max(0, sc)})`,
              textAlign: "center",
              backgroundColor: theme.colors.surface,
              border: `2px solid ${color}`,
              borderRadius: 16,
              padding: "20px 18px",
              boxShadow: glowShadow(color, 32),
            }}
          >
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: "50%",
                backgroundColor: color,
                color: theme.colors.background,
                fontSize: theme.fontSize.label,
                fontWeight: 900,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 10px",
              }}
            >
              {i + 1}
            </div>
            <div
              style={{
                color,
                fontSize: theme.fontSize.label,
                fontWeight: 700,
                lineHeight: 1.3,
              }}
            >
              {step.label}
            </div>
            {step.description && (
              <div
                style={{
                  color: theme.colors.textMuted,
                  fontSize: theme.fontSize.small,
                  marginTop: 6,
                  lineHeight: 1.4,
                }}
              >
                {step.description}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export const FlowSteps: React.FC<FlowStepsProps> = (props) => {
  const { title, direction = "horizontal", steps } = props;
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const mode = direction === "circular" ? "circular" : steps.length >= 6 ? "vertical" : "horizontal";
  const effectiveDirection = direction === "circular" ? "circular" : mode;

  const titleAnim = spring({ frame, fps, config: theme.springs.gentle, durationInFrames: 25 });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.colors.background,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: effectiveDirection === "circular" ? "flex-start" : "center",
        padding: `60px ${theme.spacing.pagePadding}px`,
        fontFamily: theme.fonts.title,
      }}
    >
      <div
        style={{
          fontSize: theme.fontSize.title,
          fontWeight: 800,
          color: theme.colors.accent,
          marginBottom: effectiveDirection === "circular" ? 24 : 56,
          textAlign: "center",
          opacity: interpolate(titleAnim, [0, 1], [0, 1]),
          transform: `translateY(${interpolate(titleAnim, [0, 1], [-20, 0])}px)`,
        }}
      >
        {title}
      </div>

      {effectiveDirection === "circular" ? (
        <CircularFlow {...props} />
      ) : (
        <LinearFlow {...props} isHorizontal={effectiveDirection === "horizontal"} />
      )}
    </AbsoluteFill>
  );
};
