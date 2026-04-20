import { Config } from "@remotion/cli/config";

// 渲染中间格式：png 无损（jpeg 会每帧有损压缩，导致成片清晰度下降）
Config.setVideoImageFormat("png");

// 输出编码：CRF 18 ≈ 视觉无损（取值 0~51，数字越小质量越高；18 为推荐上限）
Config.setCrf(18);

// 像素格式：不手动设置，让 Remotion 默认给 yuvj420p（带完整 color_range）
// 之前设成 yuv420p 导致 color_range=unknown，部分浏览器拒绝播放

// 允许覆盖已有输出文件
Config.setOverwriteOutput(true);

// 并发：使用逻辑核数的一半，避免内存压力
Config.setConcurrency(null);
