import threading, time, keyboard, winsound
import math
from pynput.mouse import Controller, Button, Listener as MouseListener
from pynput.keyboard import Listener as KeyboardListener
import win32api
import win32con

from classes.config_manager import ConfigManager
from classes.memory_manager import MemoryManager
from classes.logger import Logger
from classes.utility import Utility

# 初始化鼠标控制器和日志记录器
mouse = Controller()
# 初始化日志记录器以确保一致的日志记录
logger = Logger.get_logger()
# 定义主循环休眠时间以减少CPU使用率
MAIN_LOOP_SLEEP = 0.05

class CS2Aimbot:
    def __init__(self, memory_manager: MemoryManager) -> None:
        """
        使用共享的MemoryManager实例初始化自动瞄准。
        """
        # 加载配置设置
        self.config = ConfigManager.load_config()
        self.memory_manager = memory_manager
        self.is_running, self.stop_event = False, threading.Event()
        self.aim_active = False
        self.toggle_state = False 
        self.update_config(self.config)

        # 初始化配置设置
        self.load_configuration()
        
        # 用于粘性目标跟踪
        self.last_target = None
        self.last_target_time = 0
        self.target_stickiness = 0.1  # 粘性持续时间（秒）

        # 设置监听器
        self.keyboard_listener = KeyboardListener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.mouse_listener = MouseListener(on_click=self.on_mouse_click)
        self.keyboard_listener.start()
        self.mouse_listener.start()

    def load_configuration(self) -> None:
        """加载并应用配置设置。"""
        settings = self.config['Aimbot']
        self.aim_key = settings['AimKey']
        self.toggle_mode = settings['ToggleMode']
        self.attack_on_teammates = settings['AttackOnTeammates']
        
        active_weapon = settings.get("active_weapon_type", "Rifles")
        weapon_settings = settings["WeaponSettings"].get(active_weapon, settings["WeaponSettings"]["Rifles"])
        
        self.fov = weapon_settings['FOV']
        self.smooth = weapon_settings['Smooth']
        
        self.mouse_button_map = {
            "mouse3": Button.middle,
            "mouse4": Button.x1,
            "mouse5": Button.x2,
        }

        # 检查瞄准键是否为鼠标按键
        self.is_mouse_aim = self.aim_key in self.mouse_button_map

    def update_config(self, config):
        """更新配置设置。"""
        self.config = config
        self.load_configuration()
        logger.debug("自动瞄准配置已更新")

    def play_toggle_sound(self, state: bool) -> None:
        """当切换键被按下时播放声音。"""
        try:
            if state:
                # 激活声音：频率1200 Hz，持续时间200毫秒
                winsound.Beep(1200, 200)
            else:
                # 停用声音：频率600 Hz，持续时间200毫秒
                winsound.Beep(600, 200)
        except Exception as e:
            logger.error("播放切换声音时出错: {e}")

    def on_key_press(self, key) -> None:
        """处理按键按下事件。"""
        if not self.is_mouse_aim:
            try:
                # 检查按下的键是否为瞄准键
                if hasattr(key, 'char') and key.char == self.aim_key:
                    if self.toggle_mode:
                        self.toggle_state = not self.toggle_state
                        self.play_toggle_sound(self.toggle_state)
                    else:
                        self.aim_active = True
            except AttributeError:
                pass
            except Exception as e:
                logger.error(f"处理按键按下事件时出错: {e}")
                pass

    def on_key_release(self, key) -> None:
        """处理按键释放事件。"""
        if not self.is_mouse_aim:
            try:
                if hasattr(key, 'char') and key.char == self.aim_key and not self.toggle_mode:
                    self.aim_active = False
            except AttributeError:
                pass
            except Exception as e:
                logger.error(f"处理按键释放事件时出错: {e}")
                pass

    def on_mouse_click(self, x, y, button, pressed) -> None:
        """处理鼠标点击事件。"""
        if not self.is_mouse_aim:
            return

        try:
            expected_btn = self.mouse_button_map.get(self.aim_key)
            if button == expected_btn:
                if self.toggle_mode and pressed:
                    self.toggle_state = not self.toggle_state
                    self.play_toggle_sound(self.toggle_state)
                elif not self.toggle_mode:
                    self.aim_active = pressed
        except Exception as e:
            logger.error(f"处理鼠标点击事件时出错: {e}")
            pass

    def should_aim(self, entity_team: int, player_team: int, entity_health: int) -> bool:
        """确定机器人是否应该瞄准该实体。"""
        return (self.attack_on_teammates or entity_team != player_team) and entity_health > 0

    def calculate_distance(self, x1, y1, x2, y2):
        """计算两点之间的欧几里得距离。"""
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

    def move_mouse_to_target(self, target_x, target_y, smooth_factor):
        """将鼠标光标平滑移动到目标位置。"""
        # 使用Windows API获取当前鼠标位置以获得更好的准确性
        current_x, current_y = win32api.GetCursorPos()
        
        # 计算到目标的距离
        distance_x = target_x - current_x
        distance_y = target_y - current_y
        
        # 应用平滑因子并保持最小移动以避免抖动
        move_x = distance_x / max(smooth_factor, 1.0)
        move_y = distance_y / max(smooth_factor, 1.0)
        
        # 使用Windows API移动鼠标以获得更好的精度
        new_x = int(current_x + move_x)
        new_y = int(current_y + move_y)
        win32api.SetCursorPos((new_x, new_y))
        
    def start(self) -> None:
        """启动自动瞄准。"""
        # 将运行标志设置为True并记录自动瞄准已启动
        self.is_running = True

        # 为工具函数定义局部变量
        is_game_active = Utility.is_game_active
        sleep = time.sleep

        while not self.stop_event.is_set():
            try:
                # 检查游戏是否处于活动状态
                if not is_game_active():
                    sleep(MAIN_LOOP_SLEEP)
                    continue

                # 在切换模式下，仅根据toggle_state决定是否瞄准
                if self.toggle_mode and not self.toggle_state:
                    sleep(MAIN_LOOP_SLEEP)
                    continue

                # 在非切换模式下，检查按键是否被按下
                if not self.toggle_mode and not self.aim_active and not (not self.is_mouse_aim and keyboard.is_pressed(self.aim_key)):
                    sleep(MAIN_LOOP_SLEEP)
                    continue

                # 从内存管理器获取自动瞄准数据
                data = self.memory_manager.get_aimbot_data()
                if data and data["targets"]:
                    # 寻找最佳目标（最接近准星的）
                    best_target = None
                    best_distance = float('inf')
                    screen_center_x, screen_center_y = data["screen_width"] // 2, data["screen_height"] // 2
                    
                    current_time = time.time()
                    
                    # 首先检查是否应该继续跟踪上一个目标
                    if (self.last_target and 
                        current_time - self.last_target_time < self.target_stickiness and
                        self.should_aim(self.last_target["team"], data["player_team"], self.last_target["health"])):
                        # 计算上一个目标的距离
                        last_target_distance = self.calculate_distance(
                            screen_center_x, screen_center_y, 
                            self.last_target["x"], self.last_target["y"]
                        )
                        # 如果上一个目标仍在视野内且距离不远，则继续跟踪
                        if last_target_distance <= self.fov * 1.5:
                            best_target = self.last_target
                            best_distance = last_target_distance
                    
                    # 如果没有跟踪上一个目标，则寻找新的目标
                    if not best_target:
                        for target in data["targets"]:
                            if self.should_aim(target["team"], data["player_team"], target["health"]):
                                # Calculate distance from screen center to target
                                distance = self.calculate_distance(screen_center_x, screen_center_y, target["x"], target["y"])
                                
                                # Check if target is within FOV and closer than previous targets
                                if distance <= self.fov and distance < best_distance:
                                    best_target = target
                                    best_distance = distance
                    
                    # 更新最后目标信息
                    if best_target:
                        self.last_target = best_target
                        self.last_target_time = current_time
                    
                    # 如果找到了目标，则瞄准它
                    if best_target:
                        # 检查目标是否在视野范围内
                        if best_distance <= self.fov:
                            # 根据距离调整平滑度 - 距离越远，平滑度越高
                            dynamic_smooth = self.smooth * (1.0 + best_distance / self.fov)
                            self.move_mouse_to_target(best_target["x"], best_target["y"], dynamic_smooth)
                            # 添加小延迟以确保鼠标移动完成
                            sleep(0.005)

                sleep(MAIN_LOOP_SLEEP)
            except Exception as e:
                logger.error(f"主循环中出现意外错误: {e}", exc_info=True)
                sleep(MAIN_LOOP_SLEEP)

    def stop(self) -> None:
        """停止自动瞄准并清理资源。"""
        self.is_running = False
        self.stop_event.set()
        time.sleep(0.05)  # 短暂延迟以允许线程处理停止事件
        try:
            if hasattr(self.keyboard_listener, 'running') and self.keyboard_listener.running:
                self.keyboard_listener.stop()
            if hasattr(self.mouse_listener, 'running') and self.mouse_listener.running:
                self.mouse_listener.stop()
            logger.debug(f"自动瞄准已停止")
        except Exception as e:
            logger.error(f"停止自动瞄准时出错: {e}")