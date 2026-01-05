import keyboard
import random
import threading
import time
import winsound

from pynput.keyboard import Listener as KeyboardListener
from pynput.mouse import Controller, Button, Listener as MouseListener

from classes.config_manager import ConfigManager
from classes.logger import Logger
from classes.memory_manager import MemoryManager
from classes.utility import Utility

# 初始化鼠标控制器和日志记录器
mouse = Controller()
# 初始化日志记录器以确保一致的日志记录
logger = Logger.get_logger()
# 定义主循环休眠时间以减少CPU使用
MAIN_LOOP_SLEEP = 0

class CS2TriggerBot:
    def __init__(self, memory_manager: MemoryManager) -> None:
        """
        使用共享的MemoryManager实例初始化TriggerBot。
        """
        # 加载配置设置
        self.config = ConfigManager.load_config()
        self.memory_manager = memory_manager
        self.is_running, self.stop_event = False, threading.Event()
        self.trigger_active = False
        self.toggle_state = False 
        self.update_config(self.config)

        # 初始化配置设置
        self.load_configuration()

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
        
        active_weapon = settings.get("active_weapon_type", "AK47")
        weapon_settings = settings["WeaponSettings"].get(active_weapon, settings["WeaponSettings"].get("AK47", settings["WeaponSettings"].get("Rifles", {
            "ShotDelayMin": 0.02, "ShotDelayMax": 0.04, "PostShotDelay": 0.02
        })))
        
        self.shot_delay_min = weapon_settings['ShotDelayMin']
        self.shot_delay_max = weapon_settings['ShotDelayMax']
        self.post_shot_delay = weapon_settings['PostShotDelay']
        
        self.mouse_button_map = {
            "mouse3": Button.middle,
            "mouse4": Button.x1,
            "mouse5": Button.x2,
        }

        # 检查触发键是否是鼠标按钮
        self.is_mouse_trigger = self.trigger_key in self.mouse_button_map

    def update_config(self, config):
        """更新配置设置。"""
        self.config = config
        self.load_configuration()
        # 已移除调试日志

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
        # 检查队伍ID是否在合理范围内（通常是1或2）
        valid_team_ids = [1, 2, 3]  # 有时可能有3个队伍
        teams_valid = (entity_team in valid_team_ids) and (player_team in valid_team_ids)
        
        result = teams_valid and (self.attack_on_teammates or entity_team != player_team) and entity_health > 0
        return result

    def start(self) -> None:
        """启动TriggerBot。"""
        # 设置运行标志为True并记录TriggerBot已启动
        self.is_running = True

        # 定义实用函数的局部变量
        is_game_active = Utility.is_game_active
        sleep = time.sleep

        while not self.stop_event.is_set():
            try:
                # 检查游戏是否处于活动状态
                if not is_game_active():
                    sleep(MAIN_LOOP_SLEEP)
                    continue

                # 在切换模式下，仅根据toggle_state决定是否触发
                if self.toggle_mode and not self.toggle_state:
                    sleep(MAIN_LOOP_SLEEP)
                    continue

                # 在非切换模式下，检查按键是否被按下
                is_key_pressed = False
                if not self.toggle_mode:
                    if self.is_mouse_trigger:
                        is_key_pressed = self.trigger_active
                    else:
                        is_key_pressed = keyboard.is_pressed(self.trigger_key)

                if not self.toggle_mode and not is_key_pressed:
                    sleep(MAIN_LOOP_SLEEP)
                    continue

                data = self.memory_manager.get_fire_logic_data()
                
                # 输出当前检测到的武器
                #if data and "weapon_type" in data:
                #    weapon_type = data.get("weapon_type", "Unknown")
                #    logger.info(f"当前检测到的武器: {weapon_type}")
                
                # 修改条件判断，确保data存在且有效
                if data and "entity_team" in data and "player_team" in data and "entity_health" in data:
                    if self.should_trigger(data["entity_team"], data["player_team"], data["entity_health"]):
                        weapon_type = data.get("weapon_type", "Rifles")
                        weapon_settings = self.config['Trigger']['WeaponSettings'].get(weapon_type, self.config['Trigger']['WeaponSettings'].get('AK47', self.config['Trigger']['WeaponSettings'].get('Rifles', {
                            'ShotDelayMin': 0.02, 'ShotDelayMax': 0.04, 'PostShotDelay': 0.02
                        })))
                        
                        shot_delay_min = weapon_settings['ShotDelayMin']
                        shot_delay_max = weapon_settings['ShotDelayMax']
                        post_shot_delay = weapon_settings['PostShotDelay']

                        delay = random.uniform(shot_delay_min, shot_delay_max)
                        # 已移除调试日志
                        sleep(delay)
                        
                        # 根据配置决定使用内存射击还是鼠标点击
                        if self.memory_shoot:
                            # 使用内存射击
                            self.memory_manager.force_attack(True)
                            sleep(0.01)  # 短暂延迟
                            self.memory_manager.force_attack(False)
                        else:
                            # 使用鼠标点击
                            mouse.click(Button.left)
                        sleep(post_shot_delay)
                else:
                    sleep(MAIN_LOOP_SLEEP)
            except Exception as e:
                logger.error(f"主循环中出现意外错误: {e}", exc_info=True)
                sleep(MAIN_LOOP_SLEEP)

    def stop(self) -> None:
        """停止TriggerBot并清理资源。"""
        self.is_running = False
        self.stop_event.set()
        try:
            if hasattr(self.keyboard_listener, 'running') and self.keyboard_listener.running:
                self.keyboard_listener.stop()
            if hasattr(self.mouse_listener, 'running') and self.mouse_listener.running:
                self.mouse_listener.stop()
            # 已移除调试日志
        except Exception as e:
            logger.error(f"停止TriggerBot时出错: {e}")