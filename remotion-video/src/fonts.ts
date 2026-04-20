/**
 * 字体集中加载 — @remotion/google-fonts/NotoSansSC（latin 子集）
 *
 * 说明：NotoSansSC 的中文字符被分成编号子集 [4]~[119]，若全部加载会
 * 下载数百个 woff2 文件。本项目只显式加载 latin 子集拿到 fontFamily 名，
 * 中文字符由系统安装的 Noto Sans CJK SC 通过 CSS fallback 渲染。
 *
 * 必须在 registerRoot 前 waitUntilDone，确保 @remotion/layout-utils 的
 * measureText / fitText 能精确测量（测量依赖 canvas 的字体就绪状态）。
 */
import { loadFont } from "@remotion/google-fonts/NotoSansSC";

const loaded = loadFont("normal", {
  weights: ["400", "500", "700", "900"],
  subsets: ["latin"],
});

export const fontFamily = loaded.fontFamily;
export const waitUntilDone = loaded.waitUntilDone;
