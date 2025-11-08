import threading
import time
import ctypes
from typing import Optional

from classes.config_manager import ConfigManager
from classes.memory_manager import MemoryManager
from classes.logger import Logger
from classes.utility import Utility

# 初始化日志记录器以确保一致的日志记录
logger = Logger.get_logger()
# 定义主循环休眠时间以减少CPU使用率
MAIN_LOOP_SLEEP = 0.001  # 减少以获得更好的时间精度
# 连跳常量
FORCE_JUMP_ACTIVE = 65537
FORCE_JUMP_INACTIVE = 256

class CS2Bunnyhop:
    """管理Counter-Strike 2的连跳功能。"""
    def __init__(self, memory_manager: MemoryManager) -> None:
        """
        使用共享的MemoryManager实例初始化连跳功能。
        """
        # 加载配置设置
        self.config = ConfigManager.load_config()
        self.memory_manager = memory_manager
        self.is_running = False
        self.stop_event = threading.Event()
        self.force_jump_address: Optional[int] = None
        self.load_configuration()

    def load_configuration(self):
        """加载并应用配置设置。"""
        self.bunnyhop_enabled = self.config.get("General", {}).get("Bunnyhop", False)
        self.jump_key = self.config.get("Bunnyhop", {}).get("JumpKey", "space").lower()
        self.jump_delay = self.config.get("Bunnyhop", {}).get("JumpDelay", 0.01)

    def update_config(self, config):
        """更新配置设置。"""
        self.config = config
        self.load_configuration()
        logger.debug("连跳配置已更新")

    def initialize_force_jump(self) -> bool:
        """初始化强制跳跃地址。"""
        if self.memory_manager.dwForceJump is None:
            logger.error("dwForceJump偏移量未初始化")
            return False
        try:
            self.force_jump_address = self.memory_manager.client_base + self.memory_manager.dwForceJump
            return True
        except Exception as e:
            logger.error(f"设置强制跳跃地址时出错: {e}")
            return False

    def start(self) -> None:
        """启动连跳功能。"""
        if not self.initialize_force_jump():
            logger.error("初始化强制跳跃地址失败")
            return

        self.is_running = True

        is_game_active = Utility.is_game_active
        sleep = time.sleep
        
        # 简单的时间变量
        last_action_time = 0
        jump_active = False
        
        while not self.stop_event.is_set():
            try:
                if not is_game_active():
                    sleep(MAIN_LOOP_SLEEP)
                    continue

                current_time = time.time()
                key_pressed = ctypes.windll.user32.GetAsyncKeyState(Utility.get_vk_code(self.jump_key)) & 0x8000

                if key_pressed:
                    # 按键被按下 - 处理跳跃时机
                    if current_time - last_action_time >= self.jump_delay:
                        if not jump_active:
                            # 激活跳跃
                            try:
                                self.memory_manager.write_int(self.force_jump_address, FORCE_JUMP_ACTIVE)
                                jump_active = True
                                last_action_time = current_time
                            except Exception as e:
                                logger.error(f"激活跳跃时出错: {e}")
                        else:
                            # 停用跳跃
                            try:
                                self.memory_manager.write_int(self.force_jump_address, FORCE_JUMP_INACTIVE)
                                jump_active = False
                                last_action_time = current_time
                            except Exception as e:
                                logger.error(f"停用跳跃时出错: {e}")
                else:
                    # 按键未被按下 - 确保跳跃处于非激活状态
                    if jump_active:
                        try:
                            self.memory_manager.write_int(self.force_jump_address, FORCE_JUMP_INACTIVE)
                            jump_active = False
                        except Exception as e:
                            logger.error(f"停用跳跃时出错: {e}")

                sleep(MAIN_LOOP_SLEEP)
                
            except Exception as e:
                logger.error(f"主循环中出现意外错误: {e}", exc_info=True)
                sleep(MAIN_LOOP_SLEEP)

    def stop(self) -> None:
        """停止连跳功能并清理资源。"""
        self.is_running = False
        self.stop_event.set()
        
        # 确保在停止时跳跃被停用
        if self.force_jump_address:
            try:
                self.memory_manager.write_int(self.force_jump_address, FORCE_JUMP_INACTIVE)
            except Exception as e:
                logger.error(f"停止时停用跳跃出错: {e}")
        
        logger.debug("连跳已停止")