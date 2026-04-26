import keyboard
import math
import threading
import time
import winsound

import win32api
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
# 定义主循环睡眠时间以减少CPU使用率
MAIN_LOOP_SLEEP = 0

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
        self.target_stickiness = 0  # 粘性持续时间（秒）

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
        
        # 直接使用固定的FOV和平滑度配置
        self.fov = settings.get('FOV', 50)
        self.smooth = settings.get('Smooth', 0)  # 降低默认平滑度，使视角更流畅
        
        # 瞄准位置配置（头部/脖子/胸部/根部）
        aim_position_map = {
            '头部': 'head',
            '脖子': 'neck',
            '胸部': 'chest',
            '根部': 'root'
        }
        self.aim_position = aim_position_map.get(settings.get('AimPosition', '头部'), 'head')
        
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
                # 激活声音：频率1500 Hz，持续时间100毫秒
                winsound.Beep(1500, 100)
            else:
                # 停用声音：频率400 Hz，持续时间100毫秒
                winsound.Beep(400, 100)
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

    def aim_at_target(self, target_angle: dict, smooth_factor: float) -> None:
        """
        使用ViewAngles注入平滑瞄准目标
        :param target_angle: 目标角度 {pitch, yaw}
        :param smooth_factor: 平滑因子（越大越平滑）
        """
        try:
            # 读取当前视角角度
            # 读取当前视角角度
            current_angles_vec = self.memory_manager.read_vec3(
                self.memory_manager.client_base + self.memory_manager.dwViewAngles
            )
            
            if not current_angles_vec:
                logger.warning("无法读取当前视角角度")
                return
            
            # 转换为 pitch/yaw 格式
            current_angles = {
                'pitch': current_angles_vec['x'],
                'yaw': current_angles_vec['y']
            }
            
            # 计算角度差
            delta_pitch = target_angle['pitch'] - current_angles['pitch']
            delta_yaw = target_angle['yaw'] - current_angles['yaw']
            
            # 规范化Yaw到 -180 ~ 180
            while delta_yaw > 180:
                delta_yaw -= 360
            while delta_yaw < -180:
                delta_yaw += 360
            
            # 应用平滑因子
            new_pitch = current_angles['pitch'] + (delta_pitch / max(smooth_factor, 1.0))
            new_yaw = current_angles['yaw'] + (delta_yaw / max(smooth_factor, 1.0))
            
            # 规范化Pitch范围
            if new_pitch > 89.0:
                new_pitch = 89.0
            elif new_pitch < -89.0:
                new_pitch = -89.0
            
            # 规范化Yaw范围
            if new_yaw > 180.0:
                new_yaw -= 360.0
            elif new_yaw < -180.0:
                new_yaw += 360.0
            
            # 写入新的视角角度
            success = self.memory_manager.write_view_angles({
                'pitch': new_pitch,
                'yaw': new_yaw
            })
            
            if not success:
                logger.error("写入视角角度失败")
        except Exception as e:
            logger.error(f"瞄准目标时出错: {e}", exc_info=True)
        
    def calculate_angle_distance(self, current_angle: dict, target_angle: dict) -> float:
        """计算两个角度之间的距离（度）"""
        try:
            delta_pitch = abs(target_angle['pitch'] - current_angle['pitch'])
            delta_yaw = abs(target_angle['yaw'] - current_angle['yaw'])
            
            # 规范化Yaw
            if delta_yaw > 180:
                delta_yaw = 360 - delta_yaw
            
            # 返回欧几里得距离
            return math.sqrt(delta_pitch**2 + delta_yaw**2)
        except Exception as e:
            logger.error(f"计算角度距离失败: {e}")
            return float('inf')
    
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
                data = self.memory_manager.get_aimbot_data(self.aim_position)
                if data and data["targets"]:
                    # 寻找最佳目标（角度距离最近的）
                    best_target = None
                    best_angle_distance = float('inf')
                    
                    current_time = time.time()
                    
                    # 首先检查是否应该继续跟踪上一个目标
                    if (self.last_target and 
                        current_time - self.last_target_time < self.target_stickiness):
                        # 查找上一个目标在 targets 中
                        for target in data["targets"]:
                            if (target["entity"]["ptr"] == self.last_target["entity_ptr"]):
                                best_target = target
                                best_angle_distance = self.calculate_angle_distance(
                                    data.get("current_angles", {"pitch": 0, "yaw": 0}),
                                    target["angle"]
                                )
                                break
                    
                    # 如果没有跟踪上一个目标，则寻找新的目标
                    if not best_target:
                        for target in data["targets"]:
                            # 计算角度距离（用于FOV判断）
                            angle_distance = self.calculate_angle_distance(
                                data.get("current_angles", {"pitch": 0, "yaw": 0}),
                                target["angle"]
                            )
                            
                            # 检查目标是否在视野内且比之前的目标更近
                            if angle_distance <= self.fov and angle_distance < best_angle_distance:
                                best_target = target
                                best_angle_distance = angle_distance
                    
                    # 更新最后目标信息
                    if best_target:
                        self.last_target = {
                            "entity_ptr": best_target["entity"]["ptr"],
                            "angle": best_target["angle"]
                        }
                        self.last_target_time = current_time
                        
                        # 如果找到了目标，则瞄准它
                        if best_angle_distance <= self.fov:
                            # 使用固定平滑度，避免卡顿
                            self.aim_at_target(best_target["angle"], self.smooth)
                else:
                    pass


                sleep(MAIN_LOOP_SLEEP)
            except Exception as e:
                logger.error(f"主循环中出现意外错误: {e}", exc_info=True)
                sleep(MAIN_LOOP_SLEEP)

    def stop(self) -> None:
        """停止自动瞄准并清理资源。"""
        self.is_running = False
        self.stop_event.set()

        try:
            if hasattr(self.keyboard_listener, 'running') and self.keyboard_listener.running:
                self.keyboard_listener.stop()
            if hasattr(self.mouse_listener, 'running') and self.mouse_listener.running:
                self.mouse_listener.stop()
            logger.debug(f"自动瞄准已停止")
        except Exception as e:
            logger.error(f"停止自动瞄准时出错: {e}")