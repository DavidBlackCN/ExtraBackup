from mcdreforged.api.all import *
from prime_backup.utils.backup_id_parser import BackupIdParser

from extra_backup.config.backup_config import BackupConfig
from extra_backup.config.main_config import Config
from extra_backup.task.upload_task import Uploader
from extra_backup.task.prune_task import Pruner
from extra_backup.lang.lang_processor import tr, Language
from extra_backup.file_manager.local_processor import LocalProcessor as LP
from extra_backup.file_manager.ftp_processor import FTPProcessor as FP
from extra_backup.task.download_task import Downloader


class CommandManager:
    def __init__(self, server: PluginServerInterface):
        self.server = server

    @staticmethod
    def _get_str_from_ctx(ctx: CommandContext, key: str) -> str:
        """
        兼容两种情况：
        - ctx[key] 是 Operator → 调用 get_value()
        - ctx[key] 已经是 str/int → 直接转成 str
        """
        value = ctx.get(key)

        # 如果是 Operator，就取它的值
        if hasattr(value, "get_value"):
            value = value.get_value()

        # 最后统一成 str
        return str(value) if value is not None else ""

    @staticmethod
    def _bool_text(value: str) -> str:
        return tr("status_enabled") if value == "true" else tr("status_disabled")

    def _collect_backup_files(self, source: CommandSource, location: str | None = None) -> dict[int, tuple[str, str]]:
        index_map: dict[int, tuple[str, str]] = {}
        index = 1
        backup_items = sorted(BackupConfig().backup_list.items(), key=lambda item: item[0])

        for backup_name, backup_cfg in backup_items:
            if backup_cfg.get("enable") != "true":
                continue
            if location is not None and backup_name != location:
                continue

            files: list[str] = []
            mode = backup_cfg.get("mode")
            if mode == "local":
                listed = LP().list(backup_cfg, source)
                files = listed if listed is not None else []
            elif mode == "ftp":
                ftp = FP(backup_name, backup_cfg, source)
                try:
                    if ftp.connect():
                        files = ftp.list()
                finally:
                    ftp.disconnect()
            else:
                continue

            for filename in sorted(files):
                index_map[index] = (backup_name, filename)
                index += 1

        return index_map

    def cmd_status_help(self, source: CommandSource):
        schedule_backup = Config().get("schedule_backup")
        schedule_prune = Config().get("schedule_prune")
        enabled_count = sum(1 for item in BackupConfig().backup_list.values() if item.get("enable") == "true")
        total_count = len(BackupConfig().backup_list)

        source.reply(tr("command_help_title"))
        source.reply(tr("command_status", plugin=self._bool_text(Config().get("enable"))))
        source.reply(
            tr(
                "command_status_schedule_backup",
                enabled=self._bool_text(schedule_backup["enable"]),
                interval=schedule_backup["interval"],
            )
        )
        source.reply(
            tr(
                "command_status_schedule_prune",
                enabled=self._bool_text(schedule_prune["enable"]),
                interval=schedule_prune["interval"],
            )
        )
        source.reply(tr("command_status_paths", enabled=enabled_count, total=total_count))
        source.reply(tr("command_help_upload"))
        source.reply(tr("command_help_download"))
        source.reply(tr("command_help_list"))
        source.reply(tr("command_help_prune"))
        source.reply(tr("command_help_delete"))
        source.reply(tr("command_help_lang"))
        source.reply(tr("command_help_abort"))

    def cmd_upload(self, source: CommandSource, ctx: CommandContext):
        raw_id = self._get_str_from_ctx(ctx, "id")
        if raw_id == "":
            raw_id = "latest"
        try:
            backup_id = BackupIdParser(allow_db_access=True).parse(raw_id)
        except Exception:
            source.reply(RText(tr("invalid_backup_id", id=raw_id), RColor.red))
            return

        source.reply(tr("upload_start", id=backup_id))
        Uploader.upload(backup_id=backup_id, source=source)

    def cmd_download(self, source: CommandSource, ctx: CommandContext):
        filename = ctx.get("filename")
        from_where = ctx.get("from")
        Downloader.download(filename, from_where, source)


    def cmd_prune(self, source: CommandSource, ctx: CommandContext):
        Pruner.prune(source)

    def cmd_list(self, source: CommandSource, ctx: CommandContext):
        location = self._get_str_from_ctx(ctx, "location")
        if location == "":
            location = None
        if location is not None and location not in BackupConfig().backup_list:
            source.reply(RText(tr("unusable_backup_path", backup_path=location), RColor.red))
            return

        index_map = self._collect_backup_files(source, location)
        if not index_map:
            source.reply(tr("no_files"))
            return

        source.reply(tr("list_header"))
        for index in sorted(index_map.keys()):
            backup_name, filename = index_map[index]
            source.reply(f"{index}. {backup_name} :: {filename}")

    def cmd_delete(self, source: CommandSource, ctx: CommandContext):
        delete_index = self._get_str_from_ctx(ctx, "id")
        try:
            index_value = int(delete_index)
        except ValueError:
            source.reply(RText(tr("invalid_delete_index", id=delete_index), RColor.red))
            return

        index_map = self._collect_backup_files(source)
        if index_value not in index_map:
            source.reply(RText(tr("invalid_delete_index", id=index_value), RColor.red))
            return

        backup_name, filename = index_map[index_value]
        Pruner.delete(filename, backup_name, source)

    def cmd_change_language(self, source: CommandSource, ctx: CommandContext):
        _language = ctx["language"]
        try:
            Language().load(_language)
            Config().dump("language", _language)
            source.reply(RText(tr("change_language_success",language=_language), RColor.green))
        except Exception as e:
            source.reply(RText(tr("change_language_failed", language=_language), RColor.red))


    def cmd_abort(self, source: CommandSource):
        ...

    def command_register(self):
        builder = SimpleCommandBuilder()
        builder.command("!!exb", self.cmd_status_help)
        builder.command("!!exb upload", self.cmd_upload)
        builder.command("!!exb upload <id>", self.cmd_upload)
        builder.command("!!exb download <filename>", self.cmd_download)
        builder.command("!!exb download <filename> <from>", self.cmd_download)
        builder.command("!!exb prune", self.cmd_prune)
        builder.command("!!exb delete <id>", self.cmd_delete)
        builder.command("!!exb list", self.cmd_list)
        builder.command("!!exb list <location>", self.cmd_list)
        builder.command("!!exb lang <language>", self.cmd_change_language)
        builder.command("!!exb abort", self.cmd_abort)

        builder.arg("id", Text)
        builder.arg("location", Text)
        builder.arg("language", Text)
        builder.arg("from", Text)
        builder.arg("filename", Text)

        builder.register(self.server)
