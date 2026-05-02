"""
执行层: 状态机驱动的DSL执行器
支持: 暂停/恢复/停止, 循环, 条件, 子流程, 事件回调
"""

from __future__ import annotations
import time
import threading
import traceback
from enum import Enum
from typing import Callable, Dict, Optional, Any
from dataclasses import dataclass, field

from engine.dsl_parser import ASTNode, NodeType, DSLParser


class ExecutorState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    FINISHED = "finished"


@dataclass
class ExecutionContext:
    variables: Dict[str, Any] = field(default_factory=dict)
    loop_count: Dict[str, int] = field(default_factory=dict)
    max_loops: int = 9999
    retry_limit: int = 3
    timeout: float = 30.0


class ExecutionError(Exception):
    pass


class DSLExecutor:
    """
    状态机执行器
    事件系统: on_node_start, on_node_done, on_error, on_state_change
    """

    def __init__(self, action_handler=None):
        self._state = ExecutorState.IDLE
        self._pause_event = threading.Event()
        self._pause_event.set()          # 默认不暂停
        self._stop_flag = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._action_handler = action_handler  # 实际操作模块

        # 事件回调
        self._callbacks: Dict[str, list[Callable]] = {
            "node_start": [],
            "node_done": [],
            "error": [],
            "state_change": [],
            "log": [],
        }

    # ── 公开控制 API ─────────────────────────────────────────────
    def run_dsl(self, source: str, ctx: Optional[ExecutionContext] = None):
        """解析并异步执行DSL"""
        if self._state == ExecutorState.RUNNING:
            raise ExecutionError("执行器已在运行中")
        ast = DSLParser.from_string(source)
        ctx = ctx or ExecutionContext()
        self._stop_flag.clear()
        self._pause_event.set()
        self._set_state(ExecutorState.RUNNING)
        self._thread = threading.Thread(
            target=self._run_thread, args=(ast, ctx), daemon=True
        )
        self._thread.start()

    def run_dsl_sync(self, source: str, ctx: Optional[ExecutionContext] = None):
        """同步执行DSL（阻塞）"""
        ast = DSLParser.from_string(source)
        ctx = ctx or ExecutionContext()
        self._stop_flag.clear()
        self._pause_event.set()
        self._set_state(ExecutorState.RUNNING)
        self._execute_node(ast, ctx)
        self._set_state(ExecutorState.FINISHED)

    def pause(self):
        if self._state == ExecutorState.RUNNING:
            self._pause_event.clear()
            self._set_state(ExecutorState.PAUSED)

    def resume(self):
        if self._state == ExecutorState.PAUSED:
            self._pause_event.set()
            self._set_state(ExecutorState.RUNNING)

    def stop(self):
        self._stop_flag.set()
        self._pause_event.set()   # 解除暂停以便线程退出
        self._set_state(ExecutorState.STOPPED)

    @property
    def state(self) -> ExecutorState:
        return self._state

    # ── 事件注册 ─────────────────────────────────────────────────
    def on(self, event: str, callback: Callable):
        self._callbacks[event].append(callback)

    def _emit(self, event: str, **kwargs):
        for cb in self._callbacks.get(event, []):
            try:
                cb(**kwargs)
            except Exception:
                pass

    # ── 内部执行 ─────────────────────────────────────────────────
    def _run_thread(self, ast: ASTNode, ctx: ExecutionContext):
        try:
            self._execute_node(ast, ctx)
            if not self._stop_flag.is_set():
                self._set_state(ExecutorState.FINISHED)
        except Exception as e:
            self._emit("error", message=str(e), traceback=traceback.format_exc())
            self._set_state(ExecutorState.ERROR)

    def _check_control(self):
        """检查暂停/停止信号"""
        self._pause_event.wait()
        if self._stop_flag.is_set():
            raise ExecutionError("执行已被用户停止")

    def _execute_node(self, node: ASTNode, ctx: ExecutionContext):
        self._check_control()

        if node.type == NodeType.SEQUENCE:
            for child in node.children:
                self._execute_node(child, ctx)

        elif node.type == NodeType.CLICK:
            self._exec_click(node, ctx)

        elif node.type == NodeType.WAIT:
            self._exec_wait(node, ctx)

        elif node.type == NodeType.LOOP:
            self._exec_loop(node, ctx)

        elif node.type == NodeType.IF:
            self._exec_if(node, ctx)

        elif node.type == NodeType.RUN:
            self._exec_run(node, ctx)

    def _exec_click(self, node: ASTNode, ctx: ExecutionContext):
        self._emit("node_start", node_type="CLICK", args=node.args, line=node.line)
        self._log(f"CLICK: {node.args}")
        self._call_action("click", target=node.args, ctx=ctx)
        self._emit("node_done", node_type="CLICK", args=node.args, line=node.line)

    def _exec_wait(self, node: ASTNode, ctx: ExecutionContext):
        self._emit("node_start", node_type="WAIT", args=node.args, line=node.line)
        self._log(f"WAIT: {node.args}")
        self._call_action("wait", condition=node.args, timeout=ctx.timeout, ctx=ctx)
        self._emit("node_done", node_type="WAIT", args=node.args, line=node.line)

    def _exec_loop(self, node: ASTNode, ctx: ExecutionContext):
        tag = node.args or "_default"
        ctx.loop_count[tag] = 0
        self._emit("node_start", node_type="LOOP", args=node.args, line=node.line)
        self._log(f"LOOP 开始: {tag}")

        while ctx.loop_count[tag] < ctx.max_loops:
            self._check_control()
            ctx.loop_count[tag] += 1
            self._log(f"  LOOP [{tag}] 第 {ctx.loop_count[tag]} 次")
            try:
                for child in node.children:
                    self._execute_node(child, ctx)
            except BreakLoop:
                break

        self._emit("node_done", node_type="LOOP", args=node.args, line=node.line)

    def _exec_if(self, node: ASTNode, ctx: ExecutionContext):
        self._emit("node_start", node_type="IF", args=node.args, line=node.line)
        self._log(f"IF: {node.args}")
        result = self._call_action("check_condition", condition=node.args, ctx=ctx)
        branch = node.children if result else node.else_children
        for child in branch:
            self._execute_node(child, ctx)
        self._emit("node_done", node_type="IF", args=node.args, line=node.line)

    def _exec_run(self, node: ASTNode, ctx: ExecutionContext):
        self._emit("node_start", node_type="RUN", args=node.args, line=node.line)
        self._log(f"RUN 宏: {node.args}")
        self._call_action("run_macro", macro_name=node.args, ctx=ctx)
        self._emit("node_done", node_type="RUN", args=node.args, line=node.line)

    def _call_action(self, action: str, **kwargs) -> Any:
        """调用感知/交互层，带重试"""
        if self._action_handler is None:
            self._log(f"  [模拟] {action}({kwargs})")
            return True
        retry_limit = kwargs.pop("retry_limit", 3)
        ctx = kwargs.get("ctx")
        retry_limit = ctx.retry_limit if ctx else retry_limit
        last_err = None
        for attempt in range(1, retry_limit + 1):
            try:
                return self._action_handler(action, **kwargs)
            except Exception as e:
                last_err = e
                self._log(f"  [重试 {attempt}/{retry_limit}] {action} 失败: {e}")
                time.sleep(0.5 * attempt)
        raise ExecutionError(f"动作 '{action}' 在 {retry_limit} 次重试后失败: {last_err}")

    def _set_state(self, state: ExecutorState):
        self._state = state
        self._emit("state_change", state=state.value)

    def _log(self, msg: str):
        self._emit("log", message=msg)


class BreakLoop(Exception):
    """用于从LOOP内部跳出的控制流异常"""
    pass
