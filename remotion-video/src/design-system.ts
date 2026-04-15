/**
 * 全局设计系统 — 所有组件共享此主题
 */

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
    title: "'Noto Sans CJK SC', 'Noto Sans SC', 'PingFang SC', sans-serif",
    body: "'Noto Sans CJK SC', 'Noto Sans SC', 'PingFang SC', sans-serif",
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
};

export type Theme = typeof theme;
