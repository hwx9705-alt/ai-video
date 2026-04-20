import type { ComponentName } from "../types";
import { DataReveal } from "./DataReveal";
import { BarChartAnimated } from "./BarChartAnimated";
import { LineChartAnimated } from "./LineChartAnimated";
import { PieChartAnimated } from "./PieChartAnimated";
import { CompareTwo } from "./CompareTwo";
import { FlowSteps } from "./FlowSteps";
import { KeyPoint } from "./KeyPoint";
import { TitleCard } from "./TitleCard";
import { BulletList } from "./BulletList";
import { ImageWithOverlay } from "./ImageWithOverlay";

export {
  DataReveal,
  BarChartAnimated,
  LineChartAnimated,
  PieChartAnimated,
  CompareTwo,
  FlowSteps,
  KeyPoint,
  TitleCard,
  BulletList,
  ImageWithOverlay,
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const COMPONENT_MAP: Partial<Record<ComponentName, React.FC<any>>> = {
  DataReveal,
  BarChartAnimated,
  LineChartAnimated,
  PieChartAnimated,
  CompareTwo,
  FlowSteps,
  KeyPoint,
  TitleCard,
  BulletList,
  ImageWithOverlay,
};
