from pathlib import Path
import os
import re
from datetime import datetime

from mcdreforged.api.all import *

from extra_backup.task.main_task import States
from extra_backup.config.backup_config import BackupConfig
from extra_backup.config.main_config import DefaultConfig
from extra_backup.file_manager.local_processor import LocalProcessor as LP
from extra_backup.file_manager.ftp_processor import FTPProcessor as FTP
from extra_backup.lang.lang_processor import tr
from extra_backup.task.export_task import ExportTask

class Uploader:
    @staticmethod
    def _next_backup_filename(existing_files: list[str]) -> str:
        today = datetime.now().strftime("%Y_%m_%d")
        pattern = re.compile(r"^backup-(\d{4}_\d{2}_\d{2})_(\d+)\.tar$")
        max_seq = 0
        for file_name in existing_files:
            match = pattern.match(file_name)
            if match is None:
                continue
            file_date, file_seq = match.group(1), match.group(2)
            if file_date == today:
                max_seq = max(max_seq, int(file_seq))
        return f"backup-{today}_{max_seq + 1}.tar"

    @staticmethod
    def _upload_local(backup_id: int, backup_name: str, backup: dict, source: CommandSource):
        try:
            target_dir = Path(backup["address"])
            target_dir.mkdir(parents=True, exist_ok=True)
            existing_files = os.listdir(target_dir)
            target_file = target_dir / Uploader._next_backup_filename(existing_files)
            exported_file = ExportTask(backup_id, output_path=target_file).export(source, async_run=False)
            if exported_file is not None and Path(exported_file).exists():
                source.reply(RText(tr("upload_file_success", backup_name=backup_name), RColor.green))
                return True
            source.reply(RText(tr("upload_file_failed", backup_name=backup_name, error=tr("export_failed")), RColor.red))
            return False
        except Exception as e:
            source.reply(RText(tr("upload_file_failed", backup_name=backup_name, error=str(e)), RColor.red))
            return False

    @staticmethod
    def _upload_ftp(backup_id: int, backup_name: str, backup: dict, source: CommandSource):
        temp_dir = Path(DefaultConfig().download_path) / ".exb_temp_exports"
        temp_dir.mkdir(parents=True, exist_ok=True)
        exported_file = None
        ftp_uploader = FTP(backup_name, backup, source)
        try:
            if not ftp_uploader.connect():
                return False

            remote_files = ftp_uploader.list()
            filename = Uploader._next_backup_filename(remote_files)
            exported_file = ExportTask(backup_id, output_path=temp_dir / filename).export(source, async_run=False)
            if exported_file is None or not Path(exported_file).exists():
                source.reply(RText(tr("upload_file_failed", backup_name=backup_name, error=tr("export_failed")), RColor.red))
                return False

            return ftp_uploader.upload(str(exported_file))
        except Exception as e:
            source.reply(RText(tr("upload_file_failed", backup_name=backup_name, error=str(e)), RColor.red))
            return False
        finally:
            ftp_uploader.disconnect()
            if exported_file is not None:
                try:
                    Path(exported_file).unlink(missing_ok=True)
                except Exception:
                    pass
            try:
                if temp_dir.exists() and len(os.listdir(temp_dir)) == 0:
                    temp_dir.rmdir()
            except Exception:
                pass

    @staticmethod
    @new_thread
    def upload(backup_id: int, source: CommandSource):
        if States().Uploading:
            source.reply(RText(tr("another_uploader_is_running"), RColor.yellow))
            return
        States().Uploading = True
        success_backup_count = 0
        success_backups = []
        failure_backup_count = 0
        failure_backups = []
        skipped_backup_count = 0
        skipped_backups = []
        try:
            backup_list= BackupConfig().backup_list
            total_backups = len(backup_list)
            for backup_path in backup_list:
                backup = backup_list[backup_path]
                if backup.get("enable") != "true":
                    skipped_backup_count += 1
                    skipped_backups.append(backup_path)
                    continue

                mode = backup.get("mode")
                match mode:
                    case "local":
                        result = Uploader._upload_local(backup_id, backup_path, backup, source)
                    case "ftp":
                        result = Uploader._upload_ftp(backup_id, backup_path, backup, source)
                    case "smb":
                        result = False
                    case "sftp":
                        result = False
                    case _:
                        source.reply(RText(tr("backup_config_wrong_mode", mode=mode), RColor.red))
                        result = False

                if result is True:
                    success_backup_count += 1
                    success_backups.append(backup_path)
                elif result is None:
                    skipped_backup_count += 1
                    skipped_backups.append(backup_path)
                else:
                    failure_backup_count += 1
                    failure_backups.append(backup_path)

            source.reply(RText(tr("upload_complete",
                                  total_count     = total_backups,
                                  success_count   = success_backup_count,
                                  success_backups = success_backups,
                                  failure_count   = failure_backup_count,
                                  failure_backups = ", ".join(map(str, failure_backups)) if failure_backups else "",
                                  skipped_count = skipped_backup_count,
                                  skipped_backups = ", ".join(map(str, skipped_backups)),),
                                RColor.blue))
        finally:
            States().Uploading = False