import re
import time
import threading
from mcdreforged.api.all import *

from extra_backup.config.main_config import Config
from extra_backup.lang.lang_processor import tr
from extra_backup.task.main_task import States
from extra_backup.utils.Singleton import singleton

@singleton
class Scheduler:
    _initialized = False

    def __init__(self):
        if self._initialized:
            return
        self.server: PluginServerInterface = Config().server
        self._tasks: dict[str, dict] = {}
        self._lock = threading.RLock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._initialized = True

    @staticmethod
    def time_loader(s: str) -> int:
        # 把类似 "1h30m", "2d3h15m20s" 转换成总秒数
        units = {
            "s": 1,
            "m": 60,
            "h": 3600,
            "d": 86400
        }
        matches = re.findall(r"(\d+)([smhd])", s.strip().lower())
        if not matches:
            raise ValueError(tr("schedule_invalid_time", time=s))
        total_seconds = sum(int(num) * units[unit] for num, unit in matches)
        return total_seconds

    def register_task(self, task_name: str, function, **kwargs):
        if States().schedule_task_state.get(task_name) == "true":
            seconds = self.time_loader(Config().get("schedule_" + task_name)["interval"])
            with self._lock:
                self._tasks[task_name] = {
                    "interval": seconds,
                    "next_run": time.time() + seconds,
                    "running": False,
                    "function": function,
                    "kwargs": kwargs,
                }
            self.server.logger.info(tr("schedule_enabled", task=tr(task_name)))
        else:
            self.server.logger.info(tr("schedule_disabled", task=tr(task_name)))

    def reset_task(self, task_name: str):
        with self._lock:
            task = self._tasks.get(task_name)
            if task is None:
                return
            task["next_run"] = time.time() + task["interval"]

    def _run_task(self, task_name: str):
        with self._lock:
            task = self._tasks.get(task_name)
            if task is None:
                return
            function = task["function"]
            kwargs = task["kwargs"]

        try:
            function(**kwargs)
        except Exception as e:
            self.server.logger.error(tr("schedule_fail", task=tr(task_name), error=e))
        finally:
            with self._lock:
                task = self._tasks.get(task_name)
                if task is not None:
                    task["running"] = False
                    task["next_run"] = time.time() + task["interval"]

    @new_thread
    def _loop(self):
        while self._running:
            with self._lock:
                now = time.time()
                due_tasks = []
                for task_name, task in self._tasks.items():
                    if States().schedule_task_state.get(task_name) != "true":
                        continue
                    if task["running"]:
                        continue
                    if now >= task["next_run"]:
                        task["running"] = True
                        due_tasks.append(task_name)

            for task_name in due_tasks:
                threading.Thread(
                    target=self._run_task,
                    args=(task_name,),
                    name=f"ExtraBackup-Schedule-{task_name}",
                    daemon=True,
                ).start()

            time.sleep(0.5)

        self.server.logger.info(tr("schedule_stopped", task="all"))

    def start(self):
        if self._running:
            return
        self._running = True
        self._loop()

    def stop(self):
        self._running = False