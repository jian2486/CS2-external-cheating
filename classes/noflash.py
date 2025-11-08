import threading
import time
from typing import Optional

from classes.config_manager import ConfigManager
from classes.memory_manager import MemoryManager
from classes.logger import Logger
from classes.utility import Utility

# 初始化日志记录器以保持日志一致性
logger = Logger.get_logger()
# 定义NoFlash的主循环休眠时间
NOFLASH_LOOP_SLEEP = 0

class CS2NoFlash:
    """管理Counter-Strike 2的NoFlash功能"""
    def __init__(self, memory_manager: MemoryManager) -> None:
        """
        使用共享的MemoryManager实例初始化NoFlash
        """
        # 加载配置设置
        self.config = ConfigManager.load_config()
        self.memory_manager = memory_manager
        self.is_running = False
        self.stop_event = threading.Event()
        self.local_player_address: Optional[int] = None
        self.load_configuration()

    def load_configuration(self):
        """加载并应用配置设置"""
        self.flash_suppression_strength = self.config.get("NoFlash", {}).get("FlashSuppressionStrength", 0.0)

    def update_config(self, config):
        """更新配置设置"""
        self.config = config
        self.load_configuration()
        logger.debug("NoFlash配置已更新")

    def initialize_local_player(self) -> bool:
        """初始化本地玩家地址"""
        if self.memory_manager.dwLocalPlayerPawn is None or self.memory_manager.m_flFlashDuration is None:
            logger.error("dwLocalPlayerPawn或m_flFlashDuration偏移量未初始化")
            return False
        try:
            self.local_player_address = self.memory_manager.client_base + self.memory_manager.dwLocalPlayerPawn
            return True
        except Exception as e:
            logger.error(f"设置本地玩家地址时出错: {e}")
            return False

    def disable_flash(self) -> None:
        """根据抑制强度设置闪光持续时间"""
        try:
            player_position = self.memory_manager.read_longlong(self.local_player_address)
            if player_position:
                self.memory_manager.write_float(player_position + self.memory_manager.m_flFlashDuration, self.flash_suppression_strength)
        except Exception as e:
            logger.error(f"禁用闪光效果时出错: {e}")

    def start(self) -> None:
        """启动NoFlash功能"""
        if not self.initialize_local_player():
            logger.error("初始化本地玩家地址失败")
            return

        self.is_running = True

        is_game_active = Utility.is_game_active
        sleep = time.sleep

        while not self.stop_event.is_set():
            try:
                if not is_game_active():
                    sleep(NOFLASH_LOOP_SLEEP)
                    continue

                self.disable_flash()
                sleep(NOFLASH_LOOP_SLEEP)
            except Exception as e:
                logger.error(f"主循环中出现意外错误: {e}", exc_info=True)
                sleep(NOFLASH_LOOP_SLEEP)

    def stop(self) -> None:
        """停止NoFlash并清理资源"""
        self.is_running = False
        self.stop_event.set()
        logger.debug("NoFlash已停止")