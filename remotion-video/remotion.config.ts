import { Config } from "@remotion/cli/config";

// 渲染中间格式：jpeg（+ CRF 18 编码 = 播放兼容性最好）
// 之前试过 png 无损中间格式，但 png 源 → h264 输出会变成 yuv420p + color_range=unknown，
// 导致部分浏览器（如 Chrome 某些版本）直接拒绝播放。
// jpeg 源 → h264 输出为 yuvj420p（完整色域），广泛兼容。
// 质量损失由 CRF 18 编码阶段部分弥补。
Config.setVideoImageFormat("jpeg");

// 输出编码：CRF 18 ≈ 视觉无损（取值 0~51，数字越小质量越高；18 为推荐上限）
Config.setCrf(18);

// 像素格式：不手动设置，让 Remotion 默认给 yuvj420p（带完整 color_range）
// 之前设成 yuv420p 导致 color_range=unknown，部分浏览器拒绝播放

// 允许覆盖已有输出文件
Config.setOverwriteOutput(true);

// 并发：使用逻辑核数的一半，避免内存压力
Config.setConcurrency(null);
