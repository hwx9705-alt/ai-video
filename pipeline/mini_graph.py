"""
轻量级状态图执行引擎

模拟 LangGraph 的核心概念：
- StateGraph：有向图定义
- 节点（Node）：执行函数
- 固定边（Edge）：A → B
- 条件边（Conditional Edge）：A → 路由函数 → B/C/D
- 中断（Interrupt）：在指定节点前暂停执行
- 检查点（Checkpoint）：保存/恢复执行状态

当你的机器可以安装 LangGraph 时，只需修改 orchestrator.py 的 import，
将 MiniStateGraph 替换为 langgraph.graph.StateGraph，接口基本一致。
"""

from __future__ import annotations

from typing import Callable, Any
import json
import copy


END = "__end__"


class MiniStateGraph:
    """
    轻量级状态图。

    用法与 LangGraph 的 StateGraph 一致：
        graph = MiniStateGraph(state_type)
        graph.add_node("name", func)
        graph.add_edge("a", "b")
        graph.add_conditional_edges("a", router_fn, mapping)
        graph.set_entry_point("start")
        app = graph.compile(interrupt_before=["gate_1"])
        result = app.run(initial_state)
    """

    def __init__(self, state_type: type = dict):
        self.state_type = state_type
        self.nodes: dict[str, Callable] = {}
        self.edges: dict[str, str | None] = {}            # node → next_node
        self.conditional_edges: dict[str, tuple] = {}      # node → (router_fn, mapping)
        self.entry_point: str = ""

    def add_node(self, name: str, func: Callable) -> None:
        self.nodes[name] = func

    def add_edge(self, source: str, target: str) -> None:
        self.edges[source] = target

    def add_conditional_edges(
        self,
        source: str,
        router: Callable,
        mapping: dict[str, str],
    ) -> None:
        self.conditional_edges[source] = (router, mapping)

    def set_entry_point(self, name: str) -> None:
        self.entry_point = name

    def compile(
        self,
        checkpointer=None,
        interrupt_before: list[str] | None = None,
    ) -> "CompiledGraph":
        return CompiledGraph(
            graph=self,
            checkpointer=checkpointer,
            interrupt_before=interrupt_before or [],
        )


class CompiledGraph:
    """
    编译后的可执行图。

    支持两种运行模式：
    1. run(state) - 一次性执行到结束或中断
    2. stream(state) - 逐节点执行，yield 每个节点的输出
    """

    def __init__(
        self,
        graph: MiniStateGraph,
        checkpointer=None,
        interrupt_before: list[str] | None = None,
    ):
        self.graph = graph
        self.checkpointer = checkpointer or InMemoryCheckpointer()
        self.interrupt_before = interrupt_before or []

    def get_next_node(self, current_node: str, state: dict) -> str | None:
        """根据当前节点和状态，确定下一个节点"""
        # 先检查条件边
        if current_node in self.graph.conditional_edges:
            router, mapping = self.graph.conditional_edges[current_node]
            route_key = router(state)
            next_node = mapping.get(route_key, route_key)
            return next_node if next_node != END else None

        # 再检查固定边
        if current_node in self.graph.edges:
            target = self.graph.edges[current_node]
            return target if target != END else None

        return None

    def stream(self, state: dict | None, config: dict | None = None):
        """
        逐节点执行，在 interrupt_before 节点前暂停。

        参数：
          state: 初始状态（首次调用）或 None（恢复执行）
          config: {"configurable": {"thread_id": "..."}}

        yield: {node_name: updated_state}
        """
        thread_id = (config or {}).get("configurable", {}).get("thread_id", "default")
        resuming = False

        if state is not None:
            # 首次调用，从入口开始
            current_state = dict(state)
            current_node = self.graph.entry_point
        else:
            # 恢复执行
            checkpoint = self.checkpointer.get(thread_id)
            if checkpoint is None:
                return
            current_state = checkpoint["state"]
            current_node = checkpoint["next_node"]
            resuming = checkpoint.get("interrupted", False)

        while current_node is not None:
            # 检查中断点（恢复执行时跳过第一个节点的中断检查）
            if current_node in self.interrupt_before and not resuming:
                # 保存检查点，暂停执行
                self.checkpointer.save(thread_id, {
                    "state": copy.deepcopy(current_state),
                    "next_node": current_node,
                    "interrupted": True,
                })
                return  # 暂停

            # 恢复标志只对第一个节点生效
            resuming = False

            # 执行节点
            if current_node not in self.graph.nodes:
                print(f"[警告] 节点 '{current_node}' 未注册")
                return

            node_fn = self.graph.nodes[current_node]
            current_state = node_fn(current_state)

            yield {current_node: current_state}

            # 确定下一个节点
            next_node = self.get_next_node(current_node, current_state)
            current_node = next_node

        # 执行完毕，清理检查点
        self.checkpointer.save(thread_id, {
            "state": copy.deepcopy(current_state),
            "next_node": None,
            "interrupted": False,
        })

    def get_state(self, config: dict) -> "StateSnapshot":
        """获取当前状态快照"""
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint = self.checkpointer.get(thread_id)
        if checkpoint is None:
            return StateSnapshot(values={}, next=())
        next_nodes = (checkpoint["next_node"],) if checkpoint.get("next_node") else ()
        return StateSnapshot(values=checkpoint["state"], next=next_nodes)

    def update_state(self, config: dict, update: dict) -> None:
        """从外部更新状态（用于注入审核结果）"""
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint = self.checkpointer.get(thread_id)
        if checkpoint:
            checkpoint["state"].update(update)
            self.checkpointer.save(thread_id, checkpoint)

    def run(self, state: dict, config: dict | None = None) -> dict:
        """一次性执行到结束（忽略中断点）"""
        final_state = dict(state)
        for event in self.stream(state, config):
            for node_name, node_state in event.items():
                final_state = node_state
        return final_state


class StateSnapshot:
    """状态快照"""
    def __init__(self, values: dict, next: tuple):
        self.values = values
        self.next = next


class InMemoryCheckpointer:
    """内存中的检查点存储（进程重启后丢失）"""

    def __init__(self):
        self._storage: dict[str, dict] = {}

    def save(self, thread_id: str, data: dict) -> None:
        self._storage[thread_id] = copy.deepcopy(data)

    def get(self, thread_id: str) -> dict | None:
        data = self._storage.get(thread_id)
        return copy.deepcopy(data) if data else None


class FileCheckpointer:
    """
    磁盘持久化检查点存储。

    每个 thread_id 对应一个 JSON 文件，进程重启后可恢复。
    文件路径：{checkpoints_dir}/{thread_id}.json
    """

    def __init__(self, checkpoints_dir: str = "./checkpoints"):
        import os
        self._dir = checkpoints_dir
        os.makedirs(self._dir, exist_ok=True)

    def _path(self, thread_id: str) -> str:
        # 把斜杠等非法字符替换掉，保证文件名合法
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in thread_id)
        return f"{self._dir}/{safe_id}.json"

    def save(self, thread_id: str, data: dict) -> None:
        import json as _json
        snapshot = copy.deepcopy(data)
        with open(self._path(thread_id), "w", encoding="utf-8") as f:
            _json.dump(snapshot, f, ensure_ascii=False, indent=2)

    def get(self, thread_id: str) -> dict | None:
        import json as _json
        path = self._path(thread_id)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return _json.load(f)
        except (FileNotFoundError, Exception):
            return None

    def delete(self, thread_id: str) -> None:
        import os
        path = self._path(thread_id)
        if os.path.exists(path):
            os.remove(path)
