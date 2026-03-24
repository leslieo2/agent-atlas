from __future__ import annotations

import threading
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from queue import Queue
from uuid import UUID


TaskFn = Callable[[], None]


@dataclass
class _ScheduledTask:
    run_id: UUID
    fn: TaskFn


class RunScheduler:
    def __init__(self, workers: int = 2) -> None:
        self._queue: Queue[_ScheduledTask] = Queue()
        self._workers = max(1, workers)
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        for worker_id in range(self._workers):
            thread = threading.Thread(
                target=self._worker_loop,
                name=f"afr-run-scheduler-{worker_id+1}",
                daemon=True,
            )
            thread.start()
        self._started = True

    def submit(self, run_id: UUID, fn: TaskFn) -> None:
        if not self._started:
            self.start()
        self._queue.put(_ScheduledTask(run_id=run_id, fn=fn))

    def _worker_loop(self) -> None:
        while True:
            task = self._queue.get()
            try:
                task.fn()
            except Exception:
                traceback.print_exc()
            finally:
                self._queue.task_done()

    def pending_count(self) -> int:
        return self._queue.qsize()


run_scheduler = RunScheduler()
