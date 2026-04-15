"""
AI 科普视频自动化生产系统 - 主入口

CLI 模式：通过命令行交互完成整个流水线。
审核门会暂停等待你的输入。

用法：
  python main.py                    # 交互式创建新项目
  python main.py --topic "美联储"   # 直接指定主题
  python main.py --list             # 查看所有项目
  python main.py --resume <id>      # 恢复未完成的项目
  python main.py --dry-run          # 干跑测试（不调用 LLM API）
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from state import ProjectState, Stage, StageStatus, ReviewAction, create_initial_state
from config import load_config
from project_manager import ProjectManager
from orchestrator import create_app, build_workflow
from mini_graph import InMemoryCheckpointer as MemorySaver


# ============================================================
# 审核交互
# ============================================================

def collect_review_input(gate_name: str, state: ProjectState) -> tuple[str, str]:
    """
    在审核门收集创作者的审核意见。
    返回 (action, feedback)。
    """
    gate_actions = {
        "gate_1": ["approve", "revise", "change_direction"],
        "gate_2a": ["approve", "revise", "rewrite"],
        "gate_2b": ["approve", "revise", "rewrite"],
        "gate_3": ["approve", "revise"],
        "gate_4": ["approve", "revise"],
    }

    valid_actions = gate_actions.get(gate_name, ["approve", "revise"])

    print(f"\n可选操作：{' / '.join(valid_actions)}")

    while True:
        action = input("你的决定 > ").strip().lower()
        if action in valid_actions:
            break
        print(f"  无效输入，请选择：{' / '.join(valid_actions)}")

    feedback = ""
    if action != "approve":
        print("请输入修改意见（直接回车跳过，输入 END 结束多行输入）：")
        lines = []
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            if line == "" and not lines:
                break
            lines.append(line)
        feedback = "\n".join(lines)

    return action, feedback


# ============================================================
# 流水线执行
# ============================================================

def display_gate_content(gate_name: str, state: ProjectState):
    """在 main 中直接显示审核门内容（不依赖 gate 节点）"""
    print("\n" + "=" * 60)

    if gate_name == "gate_1":
        print("🔒 审核门 1：选题主旨确认")
        print("=" * 60)
        print("\n📋 选题提案：")
        print(state.get("topic_proposal", "（空）")[:500])
        print("\n审核要点：")
        print("  • 角度/时效性/账号匹配度")
        print("  可选操作：approve / revise / change_direction")

    elif gate_name == "gate_2a":
        print("🔒 审核门 2a：脚本大纲确认")
        print("=" * 60)
        print("\n📋 脚本大纲：")
        print(state.get("script_outline", "（空）")[:800])
        print("\n审核要点：叙事结构/段落节奏")
        print("  可选操作：approve / revise / rewrite")

    elif gate_name == "gate_2b":
        print("🔒 审核门 2b：完整脚本确认 + 口播预演")
        print("=" * 60)
        print("\n📋 完整脚本（前800字）：")
        print(state.get("script_full", "（空）")[:800])
        print("\n  🎤 请把脚本念一遍，确认读起来顺畅")
        print("  可选操作：approve / revise / rewrite")

    elif gate_name == "gate_3":
        print("🔒 审核门 3：分镜方案确认")
        print("=" * 60)
        print("\n📋 分镜表（前800字）：")
        print(state.get("storyboard", "（空）")[:800])
        print("  可选操作：approve / revise")

    elif gate_name == "gate_4":
        print("🔒 审核门 4：成片确认")
        print("=" * 60)
        print(f"\n📋 成片：{state.get('draft_video_path', '（未生成）')}")
        print("  可选操作：approve / revise")

    print("=" * 60)


# 审核门名称 ↔ 中断节点的映射
GATE_NODE_MAP = {
    "gate_1": "gate_1",
    "gate_2a": "gate_2a",
    "gate_2b": "gate_2b",
    "gate_3": "gate_3",
    "gate_4": "gate_4",
}

# 中断节点 → 它前面那个 Agent 产出后应该显示的审核门
NODE_TO_GATE = {v: k for k, v in GATE_NODE_MAP.items()}


def run_pipeline(
    topic_direction: str,
    raw_materials: list[str] | None = None,
    dry_run: bool = False,
    auto_approve: bool = False,
):
    """
    执行完整的视频生产流水线。

    核心循环逻辑：
    1. stream(state) → 执行到 interrupt_before 的节点前暂停
    2. 在 main 中显示审核门内容
    3. 收集创作者反馈
    4. 将反馈注入 State
    5. stream(None) → gate 节点执行（带着反馈），路由函数读取反馈决定走向
    6. 继续执行直到下一个中断或结束
    """
    config = load_config()
    pm = ProjectManager(config.projects_root)
    checkpointer = MemorySaver()
    app = create_app(checkpointer=checkpointer)

    state = pm.create_project(
        topic_direction=topic_direction,
        raw_materials=raw_materials,
    )

    print(f"\n✨ 项目已创建：{state['project_id']}")
    print(f"📁 项目目录：{state['project_dir']}")
    print(f"🎯 主题方向：{topic_direction}")
    if dry_run:
        print("🧪 DRY RUN 模式")
    if auto_approve:
        print("🤖 AUTO APPROVE 模式")
    print("\n" + "─" * 50)

    thread_config = {"configurable": {"thread_id": state["project_id"]}}

    try:
        input_state = state

        while True:
            # ---- 执行直到中断 ----
            for event in app.stream(input_state, thread_config):
                for node_name, node_state in event.items():
                    print(f"  ✓ [{node_name}] 完成")
                    if isinstance(node_state, dict):
                        state.update(node_state)

            input_state = None  # 后续都用 None 恢复

            # ---- 检查是否结束 ----
            snapshot = app.get_state(thread_config)
            if not snapshot.next:
                print("\n🎉 流水线执行完毕！")
                break

            next_node = snapshot.next[0]
            gate_name = NODE_TO_GATE.get(next_node, "")

            if not gate_name:
                # 不是审核门，不应该中断，继续
                continue

            # ---- 显示审核门内容 ----
            display_gate_content(gate_name, state)

            # ---- 收集反馈 ----
            if auto_approve:
                action, feedback = "approve", ""
                print(f"\n  🤖 自动通过 [{gate_name}]")
            else:
                action, feedback = collect_review_input(gate_name, state)

            # ---- 注入反馈到 State ----
            history = list(state.get("review_history", []))
            history.append({
                "gate": gate_name,
                "action": action,
                "feedback": feedback,
                "timestamp": datetime.now().isoformat(),
            })
            update = {
                "review_action": action,
                "review_feedback": feedback,
                "review_history": history,
            }
            app.update_state(thread_config, update)
            state.update(update)

            # stream(None) 恢复 → gate 节点执行（带着反馈）→ 路由正确分发
            print("─" * 50)

    except KeyboardInterrupt:
        print(f"\n\n⏹️  手动中断 | 阶段：{state.get('current_stage', '?')}")

    except Exception as e:
        print(f"\n❌ 出错：{e}")
        state["error_message"] = str(e)
        import traceback
        traceback.print_exc()

    finally:
        pm.save_state(state)
        print(f"\n💾 状态已保存")


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="AI 科普视频自动化生产系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--topic", type=str, help="主题方向")
    parser.add_argument("--materials", nargs="*", help="原始素材路径/链接")
    parser.add_argument("--list", action="store_true", help="查看所有项目")
    parser.add_argument("--resume", type=str, help="恢复项目（项目ID）")
    parser.add_argument("--dry-run", action="store_true", help="干跑测试")
    parser.add_argument("--auto-approve", action="store_true", help="自动通过所有审核门（测试用）")
    parser.add_argument("--projects-root", type=str, default="./projects", help="项目根目录")

    args = parser.parse_args()

    if args.list:
        pm = ProjectManager(args.projects_root)
        projects = pm.list_projects()
        if not projects:
            print("暂无项目。")
        else:
            print(f"\n{'项目ID':<40} {'主题':<20} {'阶段':<15} {'更新时间'}")
            print("─" * 100)
            for p in projects:
                print(f"{p['project_id']:<40} {p['topic']:<20} {p['stage']:<15} {p['updated_at']}")
        return

    if args.resume:
        print(f"[TODO] 恢复项目：{args.resume}")
        print("恢复功能将在后续版本实现。")
        return

    # 交互式或命令行指定主题
    topic = args.topic
    if not topic:
        topic = input("请输入主题方向：").strip()
        if not topic:
            print("主题不能为空。")
            return

    run_pipeline(
        topic_direction=topic,
        raw_materials=args.materials,
        dry_run=args.dry_run,
        auto_approve=args.auto_approve,
    )


if __name__ == "__main__":
    main()
