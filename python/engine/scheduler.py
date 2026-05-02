"""
节点调度系统: 管理任务队列、优先级和并发执行
"""

from __future__ import annotations
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class TaskPriority(int, Enum):
    LOW = 0
    NORMAL = 5
    HIGH = 10
    URGENT = 20


@dataclass(order=True)
class ScheduledTask:
    priority: int
    task_id: str = field(compare=False)
    dsl: str = field(compare=False)
    callback: Optional[Callable] = field(compare=False, default=None)
    created_at: float = field(compare=False, default_factory=time.time)
    metadata: Dict[str, Any] = field(compare=False, default_factory=dict)


class TaskScheduler:
    """
    优先级任务调度器
    - 支持任务队列 + 优先级
    - 支持任务取消
    - 支持任务状态追踪
    - 发布执行进度事件
    """

    def __init__(self, executor, max_workers: int = 1):
        self._executor = executor
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._running: Dict[str, ScheduledTask] = {}
        self._history: List[dict] = []
        self._cancelled: set = set()
        self._lock = threading.Lock()
        self._worker_thread: Optional[threading.Thread] = None
        self._running_flag = False
        self._on_complete_callbacks: List[Callable] = []

    def start(self):
        self._running_flag = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def stop(self):
        self._running_flag = False
        self._executor.stop()

    def submit(
        self,
        task_id: str,
        dsl: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        callback: Optional[Callable] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        task = ScheduledTask(
            priority=-priority.value,  # PriorityQueue是最小堆，取反实现最大优先级
            task_id=task_id,
            dsl=dsl,
            callback=callback,
            metadata=metadata or {},
        )
        self._queue.put(task)
        return task_id

    def cancel(self, task_id: str):
        self._cancelled.add(task_id)
        # 如果正在运行则停止
        with self._lock:
            if task_id in self._running:
                self._executor.stop()

    def get_queue_status(self) -> dict:
        return {
            "queued": self._queue.qsize(),
            "running": list(self._running.keys()),
            "history": self._history[-20:],
        }

    def on_complete(self, callback: Callable):
        self._on_complete_callbacks.append(callback)

    def _worker_loop(self):
        while self._running_flag:
            try:
                task = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if task.task_id in self._cancelled:
                self._cancelled.discard(task.task_id)
                continue

            with self._lock:
                self._running[task.task_id] = task

            start = time.time()
            try:
                self._executor.run_dsl_sync(task.dsl)
                status = "success"
                error = None
            except Exception as e:
                status = "error"
                error = str(e)
            finally:
                elapsed = time.time() - start
                with self._lock:
                    self._running.pop(task.task_id, None)
                    self._history.append(
                        {
                            "task_id": task.task_id,
                            "status": status,
                            "elapsed": round(elapsed, 2),
                            "error": error,
                        }
                    )

                if task.callback:
                    try:
                        task.callback(status=status, error=error, elapsed=elapsed)
                    except Exception:
                        pass

                for cb in self._on_complete_callbacks:
                    try:
                        cb(task_id=task.task_id, status=status)
                    except Exception:
                        pass

                self._queue.task_done()
