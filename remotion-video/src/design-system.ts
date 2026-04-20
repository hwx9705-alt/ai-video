/**
 * 全局设计系统 — 所有组件共享此主题
 */

import { Easing } from "remotion";

export const theme = {
  colors: {
    background: "#0f0f1a",
    surface: "#1a1a2e",
    surfaceAlt: "#16213e",
    primary: "#4fc3f7",
    secondary: "#81c784",
    accent: "#ffb74d",
    danger: "#ef5350",
    text: "#ffffff",
    textSecondary: "#b0b0b0",
    textMuted: "#555577",
    border: "#2a2a4a",
  },
  fonts: {
    title: "'Noto Sans SC', 'Noto Sans CJK SC', 'PingFang SC', sans-serif",
    body: "'Noto Sans SC', 'Noto Sans CJK SC', 'PingFang SC', sans-serif",
    data: "'JetBrains Mono', 'Noto Sans Mono CJK SC', 'Courier New', monospace",
  },
  fontSize: {
    hero: 96,
    title: 64,
    subtitle: 42,
    body: 32,
    label: 26,
    small: 20,
  },
  spacing: {
    pagePadding: 80,
    sectionGap: 48,
    itemGap: 24,
  },
  springs: {
    snappy: { damping: 14, stiffness: 120 },
    gentle: { damping: 20, stiffness: 70 },
    impact: { damping: 8, stiffness: 200 },
    smooth: { damping: 18, stiffness: 80 },
  },
  easings: {
    easeOutCubic: Easing.bezier(0.33, 1, 0.68, 1),
    easeInOutCubic: Easing.bezier(0.65, 0, 0.35, 1),
    entrance: Easing.bezier(0.16, 1, 0.3, 1),
    overshoot: Easing.bezier(0.34, 1.56, 0.64, 1),
  },
};

export const glowShadow = (color: string, size = 30): string =>
  `0 0 ${size}px ${color}55`;

export const barGradient = (color: string): string =>
  `linear-gradient(180deg, ${color} 0%, ${color}66 100%)`;

export const pieGradient = (color: string): string =>
  `radial-gradient(circle, ${color}ee 0%, ${color}88 100%)`;

export type Theme = typeof theme;
