import time
from mcdreforged.api.all import *

from extra_backup.lang.lang_processor import tr
from extra_backup.lang.lang_processor import Language
from extra_backup.config.main_config import Config
from extra_backup.config.backup_config import BackupConfig
from extra_backup.mcdr.commands import CommandManager
from extra_backup.task.schedule_task import Scheduler
from extra_backup.task.main_task import States


def main():
    pass

@new_thread
def start_schedule_thread(server: PluginServerInterface):
    commands = CommandManager(server)
    scheduler = Scheduler()
    scheduler.register_task(
        "backup",
        commands.cmd_upload,
        source=server.get_plugin_command_source(),
        ctx={"id": "latest", "sync": "true"},
    )
    scheduler.register_task(
        "prune",
        commands.cmd_prune,
        source=server.get_plugin_command_source(),
        ctx={"sync": "true"},
    )
    scheduler.start()

def on_load(server: PluginServerInterface , old):
    server.logger.info(tr("Plugin_loading"))
    config = Config(server)
    BackupConfig()
    if config.get("enable") == "true":
        lang = Language()
        lang.load(config.get("language"))
        commands = CommandManager(server)
        commands.command_register()
        start_schedule_thread(server)
    else:
        server.logger.error(config.get("enable"))
        server.logger.error(tr("Plugin_is_not_enabled"))

def on_unload(server:PluginServerInterface):
    for key in States().schedule_task_state:
        States().schedule_task_state[key]="false"
    Scheduler().stop()
    time.sleep(1)
    server.logger.info(tr("Plugin_unloaded"))