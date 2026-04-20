/**
 * ImageWithOverlay — 图片全屏展示 + 文字叠层
 * Ken Burns 慢缩放；title/subtitle 字号 fitText 自适应容器宽。
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
import { fitText } from "@remotion/layout-utils";
import { theme } from "../design-system";
import { fontFamily } from "../fonts";
import type { ImageWithOverlayProps } from "../types";

export const ImageWithOverlay: React.FC<ImageWithOverlayProps> = ({
  imageSrc,
  overlayOpacity = 0.55,
  title,
  subtitle,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width } = useVideoConfig();

  const imgAnim = spring({
    frame,
    fps,
    config: theme.springs.gentle,
    durationInFrames: 40,
  });
  const imgOpacity = interpolate(imgAnim, [0, 1], [0, 1]);

  // Ken Burns：整 segment 缓慢放大 1.0 → 1.1
  const kenBurnsScale = interpolate(frame, [0, durationInFrames], [1.0, 1.1]);

  const textAnim = spring({
    frame: frame - 20,
    fps,
    config: theme.springs.smooth,
    durationInFrames: 35,
  });
  const textY = interpolate(textAnim, [0, 1], [60, 0]);
  const textOpacity = interpolate(textAnim, [0, 1], [0, 1]);

  // fitText
  const availWidth = width - 160;
  const titleFit = fitText({
    text: title,
    withinWidth: availWidth,
    fontFamily,
    fontWeight: "900",
  });
  const titleFontSize = Math.min(titleFit.fontSize, theme.fontSize.hero);
  const subtitleFontSize = Math.round(titleFontSize * 0.55);

  const isRemote = imageSrc.startsWith("http://") || imageSrc.startsWith("https://");
  const imgSrc = isRemote ? imageSrc : staticFile(imageSrc);

  return (
    <AbsoluteFill style={{ backgroundColor: "#000", overflow: "hidden" }}>
      <AbsoluteFill
        style={{ transform: `scale(${kenBurnsScale})`, transformOrigin: "center" }}
      >
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

      <AbsoluteFill
        style={{
          background: `linear-gradient(to top, rgba(0,0,0,${overlayOpacity + 0.3}) 0%, rgba(0,0,0,${overlayOpacity}) 40%, rgba(0,0,0,0.1) 100%)`,
        }}
      />

      <div
        style={{
          position: "absolute",
          bottom: 100,
          left: 80,
          right: 80,
          opacity: textOpacity,
          transform: `translateY(${textY}px)`,
          fontFamily: theme.fonts.title,
        }}
      >
        <div
          style={{
            fontSize: titleFontSize,
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
              fontSize: subtitleFontSize,
              color: "rgba(255,255,255,0.88)",
              marginTop: 20,
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
