/**
 * ImageWithOverlay — 图片全屏展示 + 文字叠层
 * Ken Burns 慢缩放，暗色渐变遮罩，文字从底部滑入
 */
import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { theme } from "../design-system";
import type { ImageWithOverlayProps } from "../types";

export const ImageWithOverlay: React.FC<ImageWithOverlayProps> = ({
  imageSrc,
  overlayOpacity = 0.55,
  title,
  subtitle,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // 图片淡入
  const imgAnim = spring({
    frame,
    fps,
    config: { damping: 20, stiffness: 50 },
    durationInFrames: 40,
  });
  const imgOpacity = interpolate(imgAnim, [0, 1], [0, 1]);

  // Ken Burns：整个 segment 时长内缓慢放大 100% → 108%
  const kenBurnsScale = interpolate(frame, [0, durationInFrames], [1.0, 1.08]);

  // 文字从底部滑入（延迟 20 帧）
  const textAnim = spring({
    frame: frame - 20,
    fps,
    config: { damping: 16, stiffness: 80 },
    durationInFrames: 35,
  });
  const textY = interpolate(textAnim, [0, 1], [60, 0]);
  const textOpacity = interpolate(textAnim, [0, 1], [0, 1]);

  // 判断是否为网络图片
  const isRemote = imageSrc.startsWith("http://") || imageSrc.startsWith("https://");
  const imgSrc = isRemote ? imageSrc : staticFile(imageSrc);

  return (
    <AbsoluteFill style={{ backgroundColor: "#000", overflow: "hidden" }}>
      {/* 背景图 */}
      <AbsoluteFill style={{ transform: `scale(${kenBurnsScale})`, transformOrigin: "center" }}>
        <Img
          src={imgSrc}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            opacity: imgOpacity,
          }}
        />
      </AbsoluteFill>

      {/* 渐变遮罩 */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(to top, rgba(0,0,0,${overlayOpacity + 0.3}) 0%, rgba(0,0,0,${overlayOpacity}) 40%, rgba(0,0,0,0.1) 100%)`,
        }}
      />

      {/* 文字叠层 */}
      <div
        style={{
          position: "absolute",
          bottom: 80,
          left: 80,
          right: 80,
          opacity: textOpacity,
          transform: `translateY(${textY}px)`,
          fontFamily: theme.fonts.title,
        }}
      >
        <div
          style={{
            fontSize: 64,
            fontWeight: 900,
            color: "#ffffff",
            textShadow: "0 3px 16px rgba(0,0,0,0.9)",
            lineHeight: 1.3,
          }}
        >
          {title}
        </div>
        {subtitle && (
          <div
            style={{
              fontSize: 34,
              color: "rgba(255,255,255,0.85)",
              marginTop: 16,
              lineHeight: 1.5,
              textShadow: "0 2px 8px rgba(0,0,0,0.8)",
            }}
          >
            {subtitle}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
