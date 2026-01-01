import os
import threading
from watchdog.events import FileSystemEventHandler

from classes.config_manager import ConfigManager
from classes.logger import Logger

# 初始化日志记录器以确保一致的日志记录
logger = Logger.get_logger()

class ConfigFileChangeHandler(FileSystemEventHandler):
    """
    用于监控配置文件更改的文件系统事件处理器。
    当配置文件被修改时，自动更新所有功能的配置。
    """
    def __init__(self, main_window, debounce_interval=1.0):
        """
        使用对主窗口实例的引用初始化文件更改处理器。
        为了提高效率，缓存配置文件路径。

        Args:
            main_window: 管理所有功能的MainWindow实例。
            debounce_interval: 防抖动文件更改事件的时间（秒）。
        """
        self.main_window = main_window
        self.debounce_interval = debounce_interval
        self.debounce_timer = None
        self.config_path = ConfigManager.CONFIG_FILE

    def on_modified(self, event):
        """当文件或目录被修改时调用。"""
        if event.src_path and os.path.exists(self.config_path) and os.path.samefile(event.src_path, self.config_path):
            if self.debounce_timer is not None:
                self.debounce_timer.cancel()
            self.debounce_timer = threading.Timer(self.debounce_interval, self.reload_config)
            self.debounce_timer.start()

    def reload_config(self):
        """重新加载配置文件并更新所有功能配置。"""
        try:
            # 重新加载更新后的配置文件
            new_config = ConfigManager.load_config()
            
            # 更新所有功能的配置
            self.main_window.triggerbot.config = new_config
            self.main_window.overlay.config = new_config
            self.main_window.bunnyhop.config = new_config
            self.main_window.noflash.config = new_config
            
            # 在主线程中更新UI以反映新配置
            self.main_window.root.after(0, self.main_window.update_ui_from_config)
        except Exception as e:
            logger.exception("从 %s 重新加载配置失败: %s", self.config_path, e)