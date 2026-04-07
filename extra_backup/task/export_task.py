from mcdreforged.api.all import *
from pathlib import Path
from typing import Callable, Optional, Any

from extra_backup.pb.export import PBExporter
from extra_backup.config.main_config import Config

class ExportTask:
    def __init__(self, id: int, output_path: Path | None = None):
        self.server: PluginServerInterface= Config().server
        self.id = id
        self.output_path = output_path

    def export(
        self,
        source: CommandSource,
        callback: Optional[Callable[[Optional[Path], Optional[list], Any], None]] = None,
        async_run: bool = True,
    ):
        return PBExporter(self.server, source).export(
            ident=self.id,
            fmt='tar',
            verify_blob=False,
            output=self.output_path,
            async_run=async_run,
            callback=callback  # 导出完成后回调
        )