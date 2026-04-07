import os
import time

from mcdreforged.api.all import *

from extra_backup.config.backup_config import BackupConfig
from extra_backup.config.main_config import Config
from extra_backup.config.main_config import DefaultConfig
from extra_backup.lang.lang_processor import tr
from extra_backup.task.schedule_task import Scheduler
from extra_backup.file_manager.local_processor import LocalProcessor as LP

class Pruner:
    @staticmethod
    def _iter_files_if_exists(path: str, source: CommandSource, label: str) -> list[str]:
        if not os.path.isdir(path):
            source.reply(RText(tr("prune_skip_missing_path", label=label, path=path), RColor.yellow))
            return []
        return os.listdir(path)

    @staticmethod
    @new_thread
    def prune(source: CommandSource):
        source.reply(tr("prune_start", id=""))
        max_lifetime = Scheduler.time_loader(Config().get("schedule_prune")["max_lifetime"])

        if Config().get("schedule_prune")["prune_downloads"] == "true":
            for file in Pruner._iter_files_if_exists(DefaultConfig().download_path, source, tr("exb_downloads")):
                if time.time() - os.path.getmtime(os.path.join(DefaultConfig().download_path, file)) > max_lifetime:
                    LP.delete(file,
                              {"address":DefaultConfig().download_path},
                              tr("exb_downloads"),
                              source)

        for backup_path in BackupConfig().backup_list:
            if BackupConfig().backup_list[backup_path]["enable"] == "true":
                match BackupConfig().backup_list[backup_path]["mode"]:
                    case "local":
                        backup_dir = BackupConfig().backup_list[backup_path]["address"]
                        for file in Pruner._iter_files_if_exists(backup_dir, source, backup_path):
                            if time.time() - os.path.getmtime(os.path.join(backup_dir, file)) > max_lifetime:
                                LP.delete(file,
                                          BackupConfig().backup_list[backup_path],
                                          backup_path,
                                          source)
                    case "ftp":
                        ...
                    case "smb":
                        ...
                    case "sftp":
                        ...
                    case _:
                        ...
        source.reply(RText(tr("prune_complete"), RColor.green))

    @staticmethod
    @new_thread
    def delete(filename: str, backup_path: str, source: CommandSource):
        source.reply(tr("delete_start", id=filename, backup_path=backup_path))
        if backup_path in BackupConfig().backup_list.keys():
            if BackupConfig().backup_list[backup_path]["enable"] == "true":
                match BackupConfig().backup_list[backup_path]["mode"]:
                    case "local":
                        LP.delete(filename,
                                  BackupConfig().backup_list[backup_path],
                                  backup_path,
                                  source)
                    case "ftp":
                        ...
                    case "smb":
                        ...
                    case "sftp":
                        ...
                    case _:
                        ...
            else:
                source.reply(RText(tr("unusable_backup_path", backup_path = backup_path), RColor.red))
        else:
            source.reply(RText(tr("unusable_backup_path", backup_path = backup_path), RColor.red))