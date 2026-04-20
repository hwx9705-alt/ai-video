/**
 * StoryboardData — Python pipeline 与 Remotion 渲染器之间的数据契约
 */

export type ComponentName =
  | "DataReveal"
  | "BarChartAnimated"
  | "LineChartAnimated"
  | "PieChartAnimated"
  | "CompareTwo"
  | "FlowSteps"
  | "KeyPoint"
  | "TitleCard"
  | "BulletList"
  | "ImageWithOverlay"
  | "TypewriterText";

export interface SegmentBackground {
  type: "solid" | "gradient" | "image";
  value: string; // CSS color, CSS gradient string, or image path
}

export interface Segment {
  id: number;
  component: ComponentName;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  props: Record<string, any>;
  durationInSeconds: number;
  transition?: "fade" | "slide" | "cut";
  background?: SegmentBackground;
  narrationText?: string; // 旁白文字（不渲染，仅参考）
}

export interface StoryboardData {
  title: string;
  totalDurationInSeconds: number;
  fps: number;
  width: number;
  height: number;
  audioPath?: string; // 相对 public/ 的路径
  segments: Segment[];
}

// ---- 各组件 Props 接口 ----

export interface DataRevealProps {
  number: string; // "206%" "3.73亿" "$1.2T"
  prefix?: string;
  suffix?: string;
  subtitle: string;
  highlightColor?: string;
  countUp?: boolean; // 默认 true
}

export interface BarChartAnimatedProps {
  title: string;
  data: Array<{ label: string; value: number; color?: string }>;
  unit?: string;
  highlightIndex?: number;
}

export interface LineChartAnimatedProps {
  title: string;
  data: Array<{ x: string; y: number }>;
  unit?: string;
  annotations?: Array<{ x: string; text: string }>;
}

export interface PieChartAnimatedProps {
  title: string;
  data: Array<{ label: string; value: number; color?: string }>;
  centerLabel?: string;
  unit?: string;
}

export interface CompareTwoProps {
  title: string;
  left: { label: string; points: string[]; color?: string };
  right: { label: string; points: string[]; color?: string };
  vsText?: string;
}

export interface FlowStepsProps {
  title: string;
  steps: Array<{ label: string; description?: string }>;
  direction?: "horizontal" | "vertical" | "circular";
  centerIcon?: string; // direction=circular 时中央装饰字符（emoji 等）
}

export interface KeyPointProps {
  text: string;
  emphasis?: string[];
  style?: "quote" | "statement" | "question" | "highlight";
}

export interface TitleCardProps {
  title: string;
  subtitle?: string;
  sectionNumber?: number;
}

export interface BulletListProps {
  title: string;
  items: Array<{ text: string }>;
}

export interface ImageWithOverlayProps {
  imageSrc: string;
  overlayOpacity?: number; // 0~1，默认 0.5
  title: string;
  subtitle?: string;
}

export interface TypewriterTextProps {
  text: string;
  title?: string;
  charsPerSecond?: number; // 默认 8
  highlight?: string; // 可选高亮子串，打到该处变色
  showCursor?: boolean; // 默认 true
}
