import ctypes
import keyboard
import random
import threading
import time
import winsound

from pynput.keyboard import Listener as KeyboardListener
from pynput.mouse import Controller, Button, Listener as MouseListener
from typing import Optional, Dict, Any

from classes.config_manager import ConfigManager
from classes.logger import Logger
from classes.memory_manager import MemoryManager
from classes.utility import Utility

# 初始化鼠标控制器和日志记录器
mouse = Controller()
# 初始化日志记录器以确保一致的日志记录
logger = Logger.get_logger()
# 定义主循环休眠时间以减少 CPU 使用（改进为 0.001 以提高响应速度）
MAIN_LOOP_SLEEP = 0.001

class CS2TriggerBot:
    def __init__(self, memory_manager: MemoryManager) -> None:
        """
        使用共享的 MemoryManager 实例初始化 TriggerBot。
        """
        # 加载配置设置
        self.config = ConfigManager.load_config()
        self.memory_manager = memory_manager
        self.is_running, self.stop_event = False, threading.Event()
        self.trigger_active = False
        self.toggle_state = False 
            
        # 武器设置缓存（性能优化）
        self.current_weapon_settings: Optional[Dict[str, Any]] = None
        self.last_weapon_type: Optional[str] = None
        self.weapon_settings_cache: Dict[str, Any] = {}
            
        # VK 代码缓存（性能优化）
        self._vk_code_cache = {}
            
        # 初始化配置设置
        self.load_configuration()
        self.update_config(self.config)
    
        # 设置监听器
        self.keyboard_listener = KeyboardListener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.mouse_listener = MouseListener(on_click=self.on_mouse_click)
        self.keyboard_listener.start()
        self.mouse_listener.start()

    def load_configuration(self) -> None:
        """加载并应用配置设置。"""
        settings = self.config['Trigger']
        self.trigger_key = settings['TriggerKey']
        self.toggle_mode = settings['ToggleMode']
        self.attack_on_teammates = settings['AttackOnTeammates']
        # 添加内存射击模式配置
        self.memory_shoot = settings.get('MemoryShoot', False)
        
        # 缓存武器设置
        self.weapon_settings_cache = settings.get("WeaponSettings", {})
        
        # 重置武器缓存以强制重新查找
        self.current_weapon_settings = None
        self.last_weapon_type = None
        
        self.mouse_button_map = {
            "mouse3": Button.middle,
            "mouse4": Button.x1,
            "mouse5": Button.x2,
        }

        # 检查触发键是否是鼠标按钮
        self.is_mouse_trigger = self.trigger_key in self.mouse_button_map
        
        # 缓存键盘触发键的 VK 代码（性能优化）
        if not self.is_mouse_trigger:
            self._trigger_vk_code = Utility.get_vk_code(self.trigger_key)

    def update_config(self, config):
        """更新配置设置。"""
        self.config = config
        self.load_configuration()
        logger.debug("TriggerBot 配置已更新。")

    def play_toggle_sound(self, state: bool) -> None:
        """按下切换键时播放声音（异步执行，不阻塞主线程）。"""
        import threading
        sound_thread = threading.Thread(target=self._play_sound, args=(state,), daemon=True)
        sound_thread.start()
    
    def _play_sound(self, state: bool) -> None:
        """实际播放声音的方法（在独立线程中运行）"""
        try:
            if state:
                # 激活声音：频率1000Hz，持续时间100毫秒
                winsound.Beep(1000, 100)
            else:
                # 停用声音：频率500Hz，持续时间100毫秒
                winsound.Beep(500, 100)
        except Exception as e:
            logger.error(f"播放切换声音时出错: {e}")

    def check_mouse_pressed(self):
        """检查鼠标触发键是否被按下"""
        try:
            # 直接返回trigger_active状态，因为我们依赖鼠标监听器来设置这个状态
            return self.trigger_active
        except Exception as e:
            logger.error(f"查询鼠标触发键状态时出错: {e}")
            return False

    def on_key_press(self, key) -> None:
        """处理按键事件。"""
        if not self.is_mouse_trigger:
            try:
                # 检查按下的键是否是触发键
                if hasattr(key, 'char') and key.char == self.trigger_key:
                    if self.toggle_mode:
                        self.toggle_state = not self.toggle_state
                        self.play_toggle_sound(self.toggle_state)
                    else:
                        self.trigger_active = True
            except AttributeError:
                pass
            except Exception as e:
                logger.error(f"on_key_press中出现错误: {e}")
                pass

    def on_key_release(self, key) -> None:
        """处理按键释放事件。"""
        if not self.is_mouse_trigger:
            try:
                if hasattr(key, 'char') and key.char == self.trigger_key and not self.toggle_mode:
                    self.trigger_active = False
            except AttributeError:
                pass
            except Exception as e:
                logger.error(f"on_key_release中出现错误: {e}")
                pass

    def on_mouse_click(self, x, y, button, pressed) -> None:
        """处理鼠标点击事件。"""
        if not self.is_mouse_trigger:
            return

        try:
            expected_btn = self.mouse_button_map.get(self.trigger_key)
            if button == expected_btn:
                if self.toggle_mode and pressed:
                    self.toggle_state = not self.toggle_state
                    self.play_toggle_sound(self.toggle_state)
                elif not self.toggle_mode:
                    self.trigger_active = pressed
        except Exception as e:
            logger.error(f"on_mouse_click中出现错误: {e}")
            pass

    def should_trigger(self, entity_team: int, player_team: int, entity_health: int) -> bool:
        """确定机器人是否应该开火。"""
        # 简化的队伍检测逻辑（与 VioletWing-main 一致）
        return (self.attack_on_teammates or entity_team != player_team) and entity_health > 0
        
    def get_weapon_settings(self, weapon_type: str) -> Dict[str, Any]:
        """获取武器设置，带缓存机制以提高性能。"""
        # 武器类型映射（英文到中文）以兼容旧配置
        weapon_type_map = {
            "Pistols": "手枪",
            "Rifles": "步枪",
            "Snipers": "狙击枪",
            "SMGs": "冲锋枪",
            "Heavy": "重武器"
        }
            
        # 尝试原始武器类型和映射后的中文类型
        possible_types = [weapon_type]
        if weapon_type in weapon_type_map:
            possible_types.append(weapon_type_map[weapon_type])
            
        # 当武器类型变化时总是更新缓存
        if weapon_type != self.last_weapon_type:
            # 首先尝试原始类型，然后尝试映射的中文类型
            for wtype in possible_types:
                if wtype in self.weapon_settings_cache:
                    self.current_weapon_settings = self.weapon_settings_cache[wtype]
                    break
            else:
                # 如果都没找到，使用默认的 "Rifles" 或 "步枪"
                self.current_weapon_settings = self.weapon_settings_cache.get(
                    "Rifles", self.weapon_settings_cache.get("步枪", {})
                )
                
            self.last_weapon_type = weapon_type
            logger.debug(f"武器类型已变更为：{weapon_type}，使用设置：{self.current_weapon_settings}")
            
        return self.current_weapon_settings
        
    def is_trigger_key_pressed(self) -> bool:
        """使用优化方法检查触发键是否被按下。"""
        if self.is_mouse_trigger:
            return self.trigger_active
        else:
            # 使用 Windows API 直接调用以获得更好的性能
            return bool(ctypes.windll.user32.GetAsyncKeyState(self._trigger_vk_code) & 0x8000)

    def start(self) -> None:
        """启动TriggerBot。"""
        # 设置运行标志为True并记录TriggerBot已启动
        self.is_running = True

        # 定义实用函数的局部变量（性能优化）
        is_game_active = Utility.is_game_active
        sleep = time.sleep
        get_fire_logic_data = self.memory_manager.get_fire_logic_data
        mouse_click = mouse.click
        
        # 预计算随机值以减少循环中的计算
        last_shot_time = 0
        min_shot_interval = 0.01  # 最小射击间隔以防止滥用

        while not self.stop_event.is_set():
            try:
                # 快速退出条件
                if not is_game_active():
                    sleep(MAIN_LOOP_SLEEP)
                    continue
                
                # 检查触发器激活状态
                trigger_ready = False
                if self.toggle_mode:
                    trigger_ready = self.toggle_state
                else:
                    trigger_ready = self.trigger_active or self.is_trigger_key_pressed()
                
                if not trigger_ready:
                    sleep(MAIN_LOOP_SLEEP)
                    continue
                
                # 获取游戏数据
                data = get_fire_logic_data()
                if not data:
                    sleep(MAIN_LOOP_SLEEP)
                    continue
                
                # 检查是否应该触发
                if not self.should_trigger(data["entity_team"], data["player_team"], data["entity_health"]):
                    sleep(MAIN_LOOP_SLEEP)
                    continue
                
                # 速率限制以防止过度射击
                current_time = time.time()
                if current_time - last_shot_time < min_shot_interval:
                    sleep(MAIN_LOOP_SLEEP)
                    continue
                
                # 获取固定武器设置（不再根据武器类型判断）
                weapon_settings = self.weapon_settings_cache.get("步枪", self.weapon_settings_cache.get("Rifles", {}))
                                
                # 确保武器设置有效
                if not weapon_settings:
                    logger.warning(f"未找到武器设置，使用默认值")
                    weapon_settings = self.weapon_settings_cache.get("步枪", self.weapon_settings_cache.get("Rifles", {}))
                                
                shot_delay_min = weapon_settings.get('ShotDelayMin', 0.0)
                shot_delay_max = weapon_settings.get('ShotDelayMax', 0.0)
                post_shot_delay = weapon_settings.get('PostShotDelay', 0.0)
                
                # 射击前延迟
                if shot_delay_max > shot_delay_min:
                    delay = random.uniform(shot_delay_min, shot_delay_max)
                    sleep(delay)
                
                # 开火
                if self.memory_shoot:
                    # 使用内存射击
                    self.memory_manager.force_attack(True)
                    sleep(0.01)  # 短暂延迟
                    self.memory_manager.force_attack(False)
                else:
                    # 使用鼠标点击
                    mouse_click(Button.left)
                                
                last_shot_time = time.time()
                                
                # 射击后延迟
                if post_shot_delay > 0:
                    sleep(post_shot_delay)
            except Exception as e:
                logger.error(f"主循环中出现意外错误: {e}", exc_info=True)
                sleep(MAIN_LOOP_SLEEP)

    def stop(self) -> None:
        """停止 TriggerBot 并清理资源。"""
        self.is_running = False
        self.stop_event.set()
            
        # 给线程时间进行清理
        sleep_time = 0.1
        time.sleep(sleep_time)
            
        try:
            if hasattr(self.keyboard_listener, 'running') and self.keyboard_listener.running:
                self.keyboard_listener.stop()
            if hasattr(self.mouse_listener, 'running') and self.mouse_listener.running:
                self.mouse_listener.stop()
            logger.debug("TriggerBot 已停止。")
        except Exception as e:
            logger.error(f"停止 TriggerBot 时出错：{e}")