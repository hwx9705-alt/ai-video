import { Composition } from "remotion";
import { VideoComposition } from "./VideoComposition";
import type { StoryboardData } from "./types";

// Remotion Zod 泛型绕过
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const AnyComposition = Composition as any;

// Demo 分镜：覆盖全部 9 种组件，主题「智能驾驶」
const DEMO_STORYBOARD: StoryboardData = {
  title: "智能驾驶：驶向未来",
  totalDurationInSeconds: 222,
  fps: 30,
  width: 1920,
  height: 1080,
  segments: [
    {
      id: 1,
      component: "TitleCard",
      props: {
        title: "智能驾驶：驶向未来",
        subtitle: "一场改变出行方式的技术革命",
        sectionNumber: 0,
      },
      durationInSeconds: 8,
      transition: "fade",
    },
    {
      id: 2,
      component: "DataReveal",
      props: {
        number: "3.73亿",
        suffix: "公里",
        subtitle: "2025年春节期间华为智驾累计里程，相当于绕地球9300圈",
        highlightColor: "#4fc3f7",
      },
      durationInSeconds: 12,
      transition: "fade",
    },
    {
      id: 3,
      component: "DataReveal",
      props: {
        number: "92.07%",
        subtitle: "华为问界用户在高速上开启智能驾驶的比例",
        highlightColor: "#ffb74d",
        countUp: true,
      },
      durationInSeconds: 10,
      transition: "fade",
    },
    {
      id: 4,
      component: "TitleCard",
      props: {
        title: "智驾分级：你在哪一层？",
        sectionNumber: 1,
      },
      durationInSeconds: 6,
      transition: "fade",
    },
    {
      id: 5,
      component: "FlowSteps",
      props: {
        title: "SAE 自动驾驶分级（L0→L5）",
        steps: [
          { label: "L0 无自动化", description: "完全人工驾驶" },
          { label: "L1 驾驶辅助", description: "单一功能辅助" },
          { label: "L2 组合辅助", description: "多功能，人监控" },
          { label: "L3 条件自动", description: "特定场景脱手" },
          { label: "L4 高度自动", description: "限定区域全自动" },
        ],
        direction: "horizontal",
      },
      durationInSeconds: 20,
      transition: "fade",
    },
    {
      id: 6,
      component: "TitleCard",
      props: {
        title: "市场格局：谁在领跑？",
        sectionNumber: 2,
      },
      durationInSeconds: 6,
      transition: "fade",
    },
    {
      id: 7,
      component: "BarChartAnimated",
      props: {
        title: "2024年智驾渗透率（搭载L2+新车）",
        data: [
          { label: "问界", value: 98 },
          { label: "理想", value: 92 },
          { label: "小鹏", value: 95 },
          { label: "蔚来", value: 89 },
          { label: "比亚迪", value: 41 },
          { label: "大众", value: 28 },
        ],
        unit: "%",
        highlightIndex: 0,
      },
      durationInSeconds: 18,
      transition: "fade",
    },
    {
      id: 8,
      component: "LineChartAnimated",
      props: {
        title: "L2+渗透率趋势（2021-2025）",
        data: [
          { x: "2021", y: 12 },
          { x: "2022", y: 22 },
          { x: "2023", y: 35 },
          { x: "2024", y: 55 },
          { x: "2025E", y: 70 },
        ],
        unit: "%",
        annotations: [{ x: "2024", text: "政策爆发点" }],
      },
      durationInSeconds: 18,
      transition: "fade",
    },
    {
      id: 9,
      component: "CompareTwo",
      props: {
        title: "端到端 vs 规则-模块化",
        left: {
          label: "端到端大模型",
          color: "#4fc3f7",
          points: [
            "感知→决策→规划一体化",
            "泛化能力强，自动学习",
            "数据驱动，持续进化",
            "特斯拉 FSD v12 代表",
          ],
        },
        right: {
          label: "规则模块化",
          color: "#ef5350",
          points: [
            "各模块独立，可解释性强",
            "已知场景稳定可靠",
            "工程经验可直接复用",
            "传统主机厂偏好路线",
          ],
        },
        vsText: "VS",
      },
      durationInSeconds: 22,
      transition: "fade",
    },
    {
      id: 10,
      component: "TitleCard",
      props: {
        title: "三大核心挑战",
        sectionNumber: 3,
      },
      durationInSeconds: 6,
      transition: "fade",
    },
    {
      id: 11,
      component: "BulletList",
      props: {
        title: "智能驾驶商业化落地的核心挑战",
        items: [
          { text: "长尾问题：极端场景数据稀缺，靠仿真+云端算力训练解决" },
          { text: "法规落后：L3 商业化需等待交规明确，各地进度不一" },
          { text: "成本博弈：激光雷达从 10 万降至 500 元，芯片算力军备竞赛" },
          { text: "信任建立：92% 用户开启智驾，但第一次体验仍需突破心理关口" },
        ],
      },
      durationInSeconds: 22,
      transition: "fade",
    },
    {
      id: 12,
      component: "KeyPoint",
      props: {
        text: "智能驾驶不是代替人，而是让每辆车都拥有一位经验丰富的老司机",
        emphasis: ["代替人", "老司机"],
        style: "highlight",
      },
      durationInSeconds: 12,
      transition: "fade",
    },
    {
      id: 13,
      component: "ImageWithOverlay",
      props: {
        imageSrc: "assets/placeholder.jpg",
        overlayOpacity: 0.6,
        title: "2030：人人享有智慧出行",
        subtitle: "当智能驾驶成为基础设施，城市交通将彻底重塑",
      },
      durationInSeconds: 14,
      transition: "fade",
    },
    {
      id: 13.5,
      component: "FlowSteps",
      props: {
        title: "数据飞轮 — 四步闭环",
        steps: [
          { label: "车辆采集", description: "摄像头雷达记录 Corner Case" },
          { label: "上传云端", description: "加密脱敏传至 GPU 集群" },
          { label: "训练 AI", description: "海量数据喂养模型" },
          { label: "OTA 升级", description: "新模型推送到每辆车" },
        ],
        direction: "circular",
        centerIcon: "↻",
      },
      durationInSeconds: 12,
      transition: "fade",
    },
    {
      id: 14,
      component: "PieChartAnimated",
      props: {
        title: "2025 中国智驾市场份额",
        data: [
          { label: "华为 ADS", value: 28 },
          { label: "特斯拉 FSD", value: 24 },
          { label: "小鹏 XNGP", value: 16 },
          { label: "理想 AD", value: 12 },
          { label: "其他", value: 20 },
        ],
        centerLabel: "总计",
        unit: "%",
      },
      durationInSeconds: 14,
      transition: "fade",
    },
    {
      id: 15,
      component: "TypewriterText",
      props: {
        title: "华为春节战报",
        text: "华为春节狂飙 3.73亿公里！",
        charsPerSecond: 7,
        highlight: "3.73亿公里",
      },
      durationInSeconds: 10,
      transition: "fade",
    },
    {
      id: 16,
      component: "KeyPoint",
      props: {
        text: "未来已来，只是还未均匀分布",
        emphasis: ["未来已来"],
        style: "quote",
      },
      durationInSeconds: 12,
      transition: "fade",
    },
  ],
};

function totalFrames(sb: StoryboardData): number {
  return sb.segments.reduce(
    (sum, seg) => sum + Math.round(seg.durationInSeconds * sb.fps),
    0
  );
}

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <AnyComposition
        id="Main"
        component={VideoComposition}
        durationInFrames={totalFrames(DEMO_STORYBOARD)}
        fps={DEMO_STORYBOARD.fps}
        width={DEMO_STORYBOARD.width}
        height={DEMO_STORYBOARD.height}
        defaultProps={{ storyboard: DEMO_STORYBOARD }}
      />
    </>
  );
};
