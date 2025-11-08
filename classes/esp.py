import threading
import time
import pyMeow as overlay
import struct
import numpy as np
from typing import Iterator, Optional, Dict
from classes.config_manager import ConfigManager, Colors
from classes.memory_manager import MemoryManager
from classes.logger import Logger
from classes.utility import Utility

# 设定主循环的休眠时间
MAIN_LOOP_SLEEP = 0
# 需要迭代处理的实体数量
ENTITY_COUNT = 20
# 实体信息更新间隔（单位：秒）
ENTITY_INFO_UPDATE_INTERVAL = 1
# 初始化日志记录器，确保一致的日志记录
logger = Logger.get_logger()

# 骨骼连接定义
SKELETON_BONES = {
    # 躯干核心链
    6: [5],  # 头 -> 脖子
    5: [4],  # 脖子 -> 胸口
    4: [3, 13, 8],  # 胸口 -> 胃, 右肩膀，左肩膀
    3: [2],  # 胃 -> 中间点
    2: [1],  # 中间点 -> 小头
    1: [0],  # 小头 -> 骨盆

    # 右手链
    13: [14],  # 右肩膀 -> 右手肘
    14: [15],  # 右手肘 -> 右手腕
    15: [16],  # 右手腕 -> 右手

    # 左手链
    8: [9],  # 左肩膀 -> 左手肘
    9: [10],  # 左手肘 -> 左手腕
    10: [11],  # 左手腕 -> 左手

    # 双腿链
    0: [22, 25],  # 骨盆 -> 左屁股, 右屁股
    22: [23],  # 左屁股 -> 左膝盖
    23: [24],  # 左膝盖 -> 左脚
    25: [26],  # 右屁股 -> 右膝盖
    26: [27],  # 右膝盖 -> 右脚
}
ALL_BONE_IDS = set(SKELETON_BONES.keys())
for _bones in SKELETON_BONES.values():
    ALL_BONE_IDS.update(_bones)
MAX_BONE_ID = max(ALL_BONE_IDS) if ALL_BONE_IDS else 0

# 创建pyMeow函数的安全包装器，以捕获"2D Position out of bounds"错误
def safe_draw_circle(x, y, radius, color):
    """安全绘制圆形"""
    try:
        # 额外的边界检查
        screen_width = overlay.get_screen_width()
        screen_height = overlay.get_screen_height()
        if not (-5000 <= x <= screen_width + 5000 and -5000 <= y <= screen_height + 5000):
            return
        overlay.draw_circle(x, y, radius, color)
    except Exception as e:
        if "2D Position out of bounds" not in str(e):
            logger.debug(f"绘制圆形时出错: {e}")

def safe_draw_line(start_x, start_y, end_x, end_y, color, thickness=1.0):
    """安全绘制线条"""
    try:
        # 额外的边界检查
        screen_width = overlay.get_screen_width()
        screen_height = overlay.get_screen_height()
        if not (-5000 <= start_x <= screen_width + 5000 and -5000 <= start_y <= screen_height + 5000 and
                -5000 <= end_x <= screen_width + 5000 and -5000 <= end_y <= screen_height + 5000):
            return
        overlay.draw_line(start_x, start_y, end_x, end_y, color, thickness)
    except Exception as e:
        if "2D Position out of bounds" not in str(e):
            logger.debug(f"绘制线条时出错: {e}")

def safe_draw_rectangle(x, y, width, height, color):
    """安全绘制矩形"""
    try:
        # 额外的边界检查
        screen_width = overlay.get_screen_width()
        screen_height = overlay.get_screen_height()
        if not (-5000 <= x <= screen_width + 5000 and -5000 <= y <= screen_height + 5000 and
                -5000 <= x + width <= screen_width + 5000 and -5000 <= y + height <= screen_height + 5000):
            return
        overlay.draw_rectangle(x, y, width, height, color)
    except Exception as e:
        if "2D Position out of bounds" not in str(e):
            logger.debug(f"绘制矩形时出错: {e}")

def safe_draw_rectangle_lines(x, y, width, height, color, thickness=1.0):
    """安全绘制矩形边框"""
    try:
        # 额外的边界检查
        screen_width = overlay.get_screen_width()
        screen_height = overlay.get_screen_height()
        if not (-5000 <= x <= screen_width + 5000 and -5000 <= y <= screen_height + 5000 and
                -5000 <= x + width <= screen_width + 5000 and -5000 <= y + height <= screen_height + 5000):
            return
        overlay.draw_rectangle_lines(x, y, width, height, color, thickness)
    except Exception as e:
        if "2D Position out of bounds" not in str(e):
            logger.debug(f"绘制矩形边框时出错: {e}")

def safe_draw_text(text, x, y, font_size, color):
    """安全绘制文本"""
    try:
        # 额外的边界检查
        screen_width = overlay.get_screen_width()
        screen_height = overlay.get_screen_height()
        text_width = overlay.measure_text(text, font_size)
        if not (-5000 <= x <= screen_width + 5000 - text_width and -5000 <= y <= screen_height + 5000):
            return
        overlay.draw_text(text, x, y, font_size, color)
    except Exception as e:
        if "2D Position out of bounds" not in str(e):
            logger.debug(f"绘制文本时出错: {e}")

class Entity:
    """表示一个游戏实体，其具有缓存数据，以便于高效访问"""
    def __init__(self, controller_ptr: int, pawn_ptr: int, memory_manager: MemoryManager) -> None:
        self.controller_ptr = controller_ptr
        self.pawn_ptr = pawn_ptr
        self.memory_manager = memory_manager
        self.pos2d: Optional[Dict[str, float]] = None
        self.head_pos2d: Optional[Dict[str, float]] = None
        
        # 已存数据
        self.name: str = ""
        self.health: int = 0
        self.team: int = -1
        self.pos: Dict[str, float] = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.dormant: bool = True
        self.all_bones_pos_3d: Optional[Dict[int, Dict[str, float]]] = None
        self.all_bones_pos_3d_array: Optional[np.ndarray] = None  # 用于NumPy优化
        
        # 缓存时间戳，用于更新间隔控制
        self.last_info_update: float = 0.0

    def update(self, use_transliteration: bool, skeleton_enabled: bool) -> bool:
        """一次性更新所有实体数据，以减少内存读取次数"""
        try:
            current_time = time.time()
            
            # 始终更新健康状况、休眠状态和位置信息，以确保准确性
            self.health = self.memory_manager.read_int(self.pawn_ptr + self.memory_manager.m_iHealth)
            if self.health <= 0:
                return False

            self.dormant = bool(self.memory_manager.read_int(self.pawn_ptr + self.memory_manager.m_bDormant))
            if self.dormant:
                return False

            self.pos = self.memory_manager.read_vec3(self.pawn_ptr + self.memory_manager.m_vOldOrigin)
            
            # Update player info (name, team) only at intervals to reduce memory reads
            if current_time - self.last_info_update >= ENTITY_INFO_UPDATE_INTERVAL:
                self.team = self.memory_manager.read_int(self.pawn_ptr + self.memory_manager.m_iTeamNum)
                raw_name = self.memory_manager.read_string(self.controller_ptr + self.memory_manager.m_iszPlayerName)
                self.name = Utility.transliterate(raw_name) if use_transliteration else raw_name
                self.last_info_update = current_time

            # 只有在启用骨骼绘制时才获取骨骼数据，移除距离限制
            if skeleton_enabled:
                # 总是获取骨骼数据，无论距离多远
                self.all_bones_pos_3d = self.all_bone_pos()
            else:
                self.all_bones_pos_3d = None

            return True
        except Exception as e:
            logger.error(f"更新实体数据失败: {e}")
            return False

    def bone_pos(self, bone: int) -> Dict[str, float]:
        """获取特定骨骼的3D位置，如果可用则使用缓存数据。"""
        if self.all_bones_pos_3d and bone in self.all_bones_pos_3d:
            return self.all_bones_pos_3d[bone]
        
        # 如果缓存中没有则回退到直接读取
        try:
            game_scene = self.memory_manager.read_longlong(self.pawn_ptr + self.memory_manager.m_pGameSceneNode)
            bone_array_ptr = self.memory_manager.read_longlong(game_scene + self.memory_manager.m_pBoneArray)
            return self.memory_manager.read_vec3(bone_array_ptr + bone * 32)
        except Exception as e:
            logger.error(f"获取骨骼{bone}的位置失败: {e}")
            return {"x": 0.0, "y": 0.0, "z": 0.0}

    def all_bone_pos(self) -> Optional[Dict[int, Dict[str, float]]]:
        """通过读取骨骼矩阵获取所有骨骼位置。"""
        try:
            game_scene = self.memory_manager.read_longlong(self.pawn_ptr + self.memory_manager.m_pGameSceneNode)
            bone_array_ptr = self.memory_manager.read_longlong(game_scene + self.memory_manager.m_pBoneArray)
            if not bone_array_ptr:
                return None

            num_bones_to_read = MAX_BONE_ID + 1
            data = self.memory_manager.pm.read_bytes(bone_array_ptr, num_bones_to_read * 32)
            if not data:
                return None

            bone_positions = {}
            bone_positions_array = np.empty((MAX_BONE_ID + 1, 3), dtype=np.float32)
            
            for i in ALL_BONE_IDS:
                offset = i * 32
                try:
                    x, y, z = struct.unpack_from('fff', data, offset)
                    bone_positions[i] = {"x": x, "y": y, "z": z}
                    bone_positions_array[i] = [x, y, z]
                except struct.error:
                    # 如果数据比预期的小，这可能会发生
                    bone_positions_array[i] = [0, 0, 0]
                    continue
                    
            # 保存NumPy数组用于优化计算
            self.all_bones_pos_3d_array = bone_positions_array
            return bone_positions
        except Exception as e:
            logger.error(f"获取所有骨骼位置失败: {e}")
            return None

    @staticmethod
    def validate_screen_position(pos: Dict[str, float]) -> bool:
        """验证屏幕位置是否在边界内。"""
        if not pos:
            return False
            
        # 检查坐标是否为有效数值（不是NaN或无穷大）
        if not (isinstance(pos["x"], (int, float)) and isinstance(pos["y"], (int, float))):
            return False
            
        # 检查坐标是否为有限数值
        if not (np.isfinite(pos["x"]) and np.isfinite(pos["y"])):
            return False
            
        screen_width = overlay.get_screen_width()
        screen_height = overlay.get_screen_height()
        # 扩展边界检查，允许一定程度的边界外绘制
        margin = 5000  # 减少边界容差到5000像素，但仍足够大
        # 增加额外检查，确保坐标不会过大导致pyMeow库出错
        max_coordinate = 100000  # 设置最大坐标值限制
        return (-margin <= pos["x"] <= screen_width + margin and 
                -margin <= pos["y"] <= screen_height + margin and
                abs(pos["x"]) <= max_coordinate and abs(pos["y"]) <= max_coordinate)

class CS2Overlay:
    """管理Counter-Strike 2的ESP覆盖层。"""
    
    # 预计算骨骼连接线，避免重复计算
    BONE_CONNECTIONS = [(start_bone, end_bone) 
                       for start_bone, end_bones in SKELETON_BONES.items() 
                       for end_bone in end_bones]

    def __init__(self, memory_manager: MemoryManager) -> None:
        """
        Initialize the Overlay with a shared MemoryManager instance.
        """
        self.config = ConfigManager.load_config()
        self.memory_manager = memory_manager
        self.is_running = False
        self.stop_event = threading.Event()
        self.local_team = None
        self.screen_width = overlay.get_screen_width()
        self.screen_height = overlay.get_screen_height()
        self.load_configuration()
        # 预计算屏幕中心点
        self.screen_center_x = self.screen_width / 2
        self.screen_center_y = self.screen_height / 2

    def load_configuration(self) -> None:
        """加载并应用配置设置。"""
        settings = self.config['Overlay']
        self.enable_box = settings.get('enable_box', True)  # 确保默认值
        self.enable_skeleton = settings.get('enable_skeleton', True)
        self.draw_snaplines = settings.get('draw_snaplines', False)
        self.snaplines_color_hex = settings.get('snaplines_color_hex', "#FFFF00")
        self.box_line_thickness = settings.get('box_line_thickness', 1.0)
        self.box_color_hex = settings.get('box_color_hex', "#FF0000")
        self.text_color_hex = settings.get('text_color_hex', "#FFFFFF")
        self.draw_health_numbers = settings.get('draw_health_numbers', True)
        self.use_transliteration = settings.get('use_transliteration', False)
        self.draw_nicknames = settings.get('draw_nicknames', True)
        self.draw_teammates = settings.get('draw_teammates', False)
        self.teammate_color_hex = settings.get('teammate_color_hex', "#00FF00")
        self.enable_minimap = settings.get('enable_minimap', False)
        self.minimap_size = settings.get('minimap_size', 200)
        self.target_fps = int(settings.get('target_fps', 60))
        # 默认小地图位置
        self.minimap_position = "top_left"  # 选项: top_left, top_right, bottom_left, bottom_right
        self.minimap_positions = {
            "top_left": (10, 10),
            "top_right": (self.screen_width - self.minimap_size - 10, 10),
            "bottom_left": (10, self.screen_height - self.minimap_size - 10),
            "bottom_right": (self.screen_width - self.minimap_size - 10, self.screen_height - self.minimap_size - 10)
        }

    def update_config(self, config: dict) -> None:
        """更新配置设置。"""
        self.config = config
        self.load_configuration()
        logger.debug("覆盖层配置已更新")

    def iterate_entities(self, local_controller_ptr: int) -> Iterator[Entity]:
        """遍历游戏实体并生成有效的实体对象。"""
        try:
            ent_list_ptr = self.memory_manager.read_longlong(self.memory_manager.client_dll_base + self.memory_manager.dwEntityList)
            # 获取本地玩家位置用于距离计算
            local_pawn_ptr = self.memory_manager.read_longlong(self.memory_manager.client_dll_base + self.memory_manager.dwLocalPlayerPawn)
            local_pos = None
            if local_pawn_ptr:
                local_pos = self.memory_manager.read_vec3(local_pawn_ptr + self.memory_manager.m_vOldOrigin)
        except Exception as e:
            # logger.error(f"读取实体列表指针时出错: {e}")
            return

        entity_count = 0
        for i in range(1, ENTITY_COUNT + 1):
            try:
                list_index = (i & 0x7FFF) >> 9
                entity_index = i & 0x1FF
                entry_ptr = self.memory_manager.read_longlong(ent_list_ptr + (8 * list_index) + 16)
                if not entry_ptr: continue

                # 计算实体控制器指针偏移量
                controller_ptr = self.memory_manager.read_longlong(entry_ptr + self.memory_manager.ENTITY_ENTRY_SIZE * entity_index)
                if not controller_ptr or controller_ptr == local_controller_ptr: continue

                controller_pawn_ptr = self.memory_manager.read_longlong(controller_ptr + self.memory_manager.m_hPlayerPawn)
                if not controller_pawn_ptr: continue

                # 计算实体列表条目指针偏移量
                list_entry_ptr = self.memory_manager.read_longlong(ent_list_ptr + 8 * ((controller_pawn_ptr & 0x7FFF) >> 9) + 16)
                if not list_entry_ptr: continue

                # 计算实体pawn指针偏移量
                pawn_ptr = self.memory_manager.read_longlong(list_entry_ptr + self.memory_manager.ENTITY_ENTRY_SIZE * (controller_pawn_ptr & 0x1FF))
                if not pawn_ptr: continue

                entity = Entity(controller_ptr, pawn_ptr, self.memory_manager)
                if entity.update(self.use_transliteration, self.enable_skeleton):
                    entity_count += 1
                    yield entity
            except Exception:
                logger.debug(f"{i}")
                continue

    def draw_skeleton(self, entity: Entity, view_matrix: list, color: tuple, all_bones_pos_3d: Dict[int, Dict[str, float]]) -> None:
        """绘制实体的骨骼。"""
        try:
            if not all_bones_pos_3d:
                return

            # 性能优化：只转换需要绘制的骨骼点
            bone_positions_2d = {}
            
            # 使用NumPy优化矩阵转换
            if entity.all_bones_pos_3d_array is not None and len(entity.all_bones_pos_3d_array) > 0:
                # 构建视图矩阵
                vm = np.array(view_matrix, dtype=np.float32).reshape(4, 4)
                
                # 获取需要的骨骼点
                needed_bones = set()
                for start_bone, end_bone in self.BONE_CONNECTIONS:
                    needed_bones.add(start_bone)
                    needed_bones.add(end_bone)
                
                # 批量转换骨骼点到屏幕坐标
                bone_points_3d = entity.all_bones_pos_3d_array[list(needed_bones)]
                
                # 添加齐次坐标 (w = 1)
                ones = np.ones((bone_points_3d.shape[0], 1), dtype=np.float32)
                bone_points_homogeneous = np.hstack([bone_points_3d, ones])
                
                # 应用视图矩阵变换
                transformed_points = bone_points_homogeneous @ vm.T
                
                # 透视除法和屏幕坐标转换
                with np.errstate(divide='ignore', invalid='ignore'):
                    # 检查w分量避免除以零
                    w = transformed_points[:, 3:4]
                    valid_indices = (w > 0.01).flatten()
                    
                    if np.any(valid_indices):
                        # 透视除法
                        projected = transformed_points[valid_indices] / w[valid_indices]
                        
                        # 转换到屏幕坐标
                        screen_x = (self.screen_center_x + self.screen_center_x * projected[:, 0])
                        screen_y = (self.screen_center_y - self.screen_center_y * projected[:, 1])
                        
                        # 存储有效的2D坐标
                        valid_bone_ids = [bone_id for i, bone_id in enumerate(needed_bones) if valid_indices[i]]
                        for bone_id, x, y in zip(valid_bone_ids, screen_x, screen_y):
                            # 验证坐标是否为有效数值
                            pos = {"x": float(x), "y": float(y)}
                            if np.isfinite(pos["x"]) and np.isfinite(pos["y"]) and Entity.validate_screen_position(pos):
                                bone_positions_2d[bone_id] = pos
            else:
                # 回退到原有的转换方法
                needed_bones = set()
                for start_bone, end_bones in SKELETON_BONES.items():
                    needed_bones.add(start_bone)
                    needed_bones.update(end_bones)
                
                # 只转换需要的骨骼点
                for bone_id in needed_bones:
                    if bone_id in all_bones_pos_3d:
                        pos_3d = all_bones_pos_3d[bone_id]
                        try:
                            pos_2d = overlay.world_to_screen(view_matrix, pos_3d, 1)
                        except Exception:
                            pos_2d = None
                        
                        # 验证坐标是否为有效数值
                        if pos_2d and np.isfinite(pos_2d["x"]) and np.isfinite(pos_2d["y"]) and Entity.validate_screen_position(pos_2d):
                            bone_positions_2d[bone_id] = pos_2d

            # 在头部位置绘制一个圆圈（骨骼ID 6）
            if 6 in bone_positions_2d:
                head_pos = bone_positions_2d[6]
                # 检查坐标是否在屏幕范围内
                if Entity.validate_screen_position(head_pos):
                    safe_draw_circle(head_pos["x"], head_pos["y"], 3, color)

            # 绘制骨骼连接线
            for start_bone, end_bone in self.BONE_CONNECTIONS:
                if start_bone in bone_positions_2d and end_bone in bone_positions_2d:
                    start_pos = bone_positions_2d[start_bone]
                    end_pos = bone_positions_2d[end_bone]
                    
                    # 检查坐标是否在屏幕范围内
                    if (Entity.validate_screen_position(start_pos) and 
                        Entity.validate_screen_position(end_pos)):
                        safe_draw_line(
                            start_pos["x"],
                            start_pos["y"],
                            end_pos["x"],
                            end_pos["y"],
                            color,
                            1.0  # 减小线宽以提高性能
                        )
        except Exception as e:
            logger.error(f"Error drawing skeleton: {e}")

    def draw_snaplines(self, entity: Entity) -> None:
        """绘制到实体的辅助线。"""
        try:
            # 注意：这里我们不再检查self.draw_snaplines，因为调用此方法的前提是已经确认需要绘制snaplines
            # 确保相关参数是正确的类型
            snaplines_color_hex = self.snaplines_color_hex if isinstance(self.snaplines_color_hex, str) else "#FFFF00"
            
            if entity.head_pos2d:
                # 检查坐标是否在屏幕范围内
                if Entity.validate_screen_position(entity.head_pos2d):
                    safe_draw_line(
                        self.screen_center_x,
                        self.screen_center_y,
                        entity.head_pos2d["x"],
                        entity.head_pos2d["y"],
                        overlay.get_color(snaplines_color_hex),
                        2
                    )
        except Exception as e:
            logger.error(f"绘制辅助线时出错: {e}")
            pass

    def draw_entity(self, entity: Entity, view_matrix: list, is_teammate: bool = False) -> None:
        """为给定实体渲染ESP覆盖层。"""
        try:
            head_pos_3d = entity.bone_pos(6)

            # 使用NumPy优化世界到屏幕的坐标转换
            try:
                # 构建视图矩阵
                vm = np.array(view_matrix, dtype=np.float32).reshape(4, 4)
                
                # 批量转换实体位置和头部位置
                positions_3d = np.array([
                    [entity.pos["x"], entity.pos["y"], entity.pos["z"]],
                    [head_pos_3d["x"], head_pos_3d["y"], head_pos_3d["z"]]
                ], dtype=np.float32)
                
                # 添加齐次坐标 (w = 1)
                ones = np.ones((positions_3d.shape[0], 1), dtype=np.float32)
                positions_homogeneous = np.hstack([positions_3d, ones])
                
                # 应用视图矩阵变换
                transformed_positions = positions_homogeneous @ vm.T
                
                # 透视除法和屏幕坐标转换
                with np.errstate(divide='ignore', invalid='ignore'):
                    # 检查w分量避免除以零
                    w = transformed_positions[:, 3:4]
                    valid_indices = (w > 0.01).flatten()
                    
                    if np.all(valid_indices):
                        # 透视除法
                        projected = transformed_positions / w
                        
                        # 转换到屏幕坐标，保留3位小数
                        screen_x = (self.screen_center_x + self.screen_center_x * projected[:, 0])
                        screen_y = (self.screen_center_y - self.screen_center_y * projected[:, 1])
                        
                        pos2d = {"x": round(float(screen_x[0]), 3), "y": round(float(screen_y[0]), 3)}
                        head_pos2d = {"x": round(float(screen_x[1]), 3), "y": round(float(screen_y[1]), 3)}
                        
                        # 验证坐标是否为有效数值
                        if not (np.isfinite(pos2d["x"]) and np.isfinite(pos2d["y"]) and 
                                np.isfinite(head_pos2d["x"]) and np.isfinite(head_pos2d["y"])):
                            # 如果坐标不是有效数值，回退到原有方法
                            pos2d = overlay.world_to_screen(view_matrix, entity.pos, 1)
                            head_pos2d = overlay.world_to_screen(view_matrix, head_pos_3d, 1)
                        # 验证坐标是否在屏幕范围内
                        elif not Entity.validate_screen_position(pos2d) or not Entity.validate_screen_position(head_pos2d):
                            # 如果变换后坐标不在屏幕范围内，则回退到原有方法
                            pos2d = overlay.world_to_screen(view_matrix, entity.pos, 1)
                            head_pos2d = overlay.world_to_screen(view_matrix, head_pos_3d, 1)
                    else:
                        # 如果变换失败，回退到原有方法
                        pos2d = overlay.world_to_screen(view_matrix, entity.pos, 1)
                        head_pos2d = overlay.world_to_screen(view_matrix, head_pos_3d, 1)
            except Exception as e:
                # 如果NumPy方法失败，回退到原有方法
                pos2d = overlay.world_to_screen(view_matrix, entity.pos, 1)
                head_pos2d = overlay.world_to_screen(view_matrix, head_pos_3d, 1)

            # 验证坐标是否有效
            if not pos2d or not head_pos2d:
                return
                
            # 验证坐标是否为有效数值
            if not (np.isfinite(pos2d["x"]) and np.isfinite(pos2d["y"]) and 
                    np.isfinite(head_pos2d["x"]) and np.isfinite(head_pos2d["y"])):
                return

            # 修改验证逻辑，允许一定程度的边界外绘制，特别是对于近距离目标
            if not Entity.validate_screen_position(pos2d) and not Entity.validate_screen_position(head_pos2d):
                # 如果头和身体都不在扩展的屏幕范围内，则检查是否是近距离目标
                local_pawn_ptr = self.memory_manager.read_longlong(self.memory_manager.client_dll_base + self.memory_manager.dwLocalPlayerPawn)
                if local_pawn_ptr:
                    local_pos = self.memory_manager.read_vec3(local_pawn_ptr + self.memory_manager.m_vOldOrigin)
                    # 验证本地位置坐标是否有效
                    if local_pos and np.isfinite(local_pos["x"]) and np.isfinite(local_pos["y"]) and np.isfinite(local_pos["z"]):
                        distance = ((entity.pos["x"] - local_pos["x"]) ** 2 + 
                                   (entity.pos["y"] - local_pos["y"]) ** 2 + 
                                   (entity.pos["z"] - local_pos["z"]) ** 2) ** 0.5
                        # 如果距离很近（例如小于200游戏单位），仍然绘制
                        if distance > 200:
                            return
                    else:
                        return
                else:
                    return

            entity.pos2d = pos2d
            entity.head_pos2d = head_pos2d

            # 验证坐标是否为有效数值后再继续
            if not (np.isfinite(entity.pos2d["x"]) and np.isfinite(entity.pos2d["y"]) and 
                    np.isfinite(entity.head_pos2d["x"]) and np.isfinite(entity.head_pos2d["y"])):
                return

            # 增加额外的坐标范围检查，防止pyMeow库抛出"2D Position out of bounds"错误
            max_coordinate = 50000
            if (abs(entity.pos2d["x"]) > max_coordinate or abs(entity.pos2d["y"]) > max_coordinate or
                abs(entity.head_pos2d["x"]) > max_coordinate or abs(entity.head_pos2d["y"]) > max_coordinate):
                return

            head_y = entity.head_pos2d["y"]
            pos_y = entity.pos2d["y"]
            box_height = pos_y - head_y
            box_width = box_height / 2
            half_width = box_width / 2

            # 确保颜色值是字符串而不是布尔值
            box_color_hex = self.box_color_hex if isinstance(self.box_color_hex, str) else "#FF0000"
            teammate_color_hex = self.teammate_color_hex if isinstance(self.teammate_color_hex, str) else "#00FF00"
            text_color_hex = self.text_color_hex if isinstance(self.text_color_hex, str) else "#FFFFFF"
            snaplines_color_hex = self.snaplines_color_hex if isinstance(self.snaplines_color_hex, str) else "#FFFF00"
            
            outline_color = overlay.get_color(teammate_color_hex if is_teammate else box_color_hex)
            text_color = overlay.get_color(text_color_hex)

            if self.enable_skeleton and entity.all_bones_pos_3d:
                try:
                    self.draw_skeleton(entity, view_matrix, outline_color, entity.all_bones_pos_3d)
                except Exception as e:
                    logger.error(f"绘制骨骼时出错: {e}")
                    pass

            # 使用优化的绘制方法
            # 确保draw_snaplines是布尔值而不是函数或其他类型
            draw_snaplines = self.draw_snaplines if isinstance(self.draw_snaplines, bool) else False
            if draw_snaplines:
                self.draw_snaplines(entity)

            if self.enable_box:
                try:
                    # 绘制前验证盒子尺寸
                    if box_width > 0 and box_height > 0:
                        # 计算盒子坐标，保留3位小数
                        box_x = round(entity.head_pos2d["x"] - half_width, 3)
                        box_y = round(entity.head_pos2d["y"] - half_width / 2, 3)
                        box_width_full = round(box_width, 3)
                        box_height_full = round(box_height + half_width / 2, 3)
                        
                        # 检查盒子坐标是否为有效数字
                        if not (np.isfinite(box_x) and np.isfinite(box_y) and 
                                np.isfinite(box_width_full) and np.isfinite(box_height_full)):
                            return
                        
                        # 增加额外检查，防止坐标过大导致pyMeow库出错
                        if (abs(box_x) > max_coordinate or abs(box_y) > max_coordinate or
                            abs(box_x + box_width_full) > max_coordinate or abs(box_y + box_height_full) > max_coordinate):
                            return
                        
                        # 检查盒子的任何部分是否在屏幕上可见
                        screen_width = overlay.get_screen_width()
                        screen_height = overlay.get_screen_height()
                        if (box_x + box_width_full >= -5000 and box_x <= screen_width + 5000 and 
                            box_y + box_height_full >= -5000 and box_y <= screen_height + 5000):
                            
                            # 绘制盒子轮廓
                            safe_draw_rectangle_lines(
                                box_x,
                                box_y,
                                box_width_full,
                                box_height_full,
                                outline_color,
                                self.box_line_thickness if isinstance(self.box_line_thickness, (int, float)) else 1.0
                            )
                            
                except Exception as e:
                    logger.error(f"绘制盒子时出错: {e}")
                    pass

            if self.draw_nicknames:
                nickname = entity.name
                nickname_font_size = 11
                nickname_width = overlay.measure_text(nickname, nickname_font_size)
                # 确保文本坐标在屏幕范围内，保留3位小数
                nickname_x = round(entity.head_pos2d["x"] - nickname_width // 2, 3)
                nickname_y = round(entity.head_pos2d["y"] - half_width / 2 - 15, 3)
                
                # 检查坐标是否为有效数值
                if not (np.isfinite(nickname_x) and np.isfinite(nickname_y)):
                    return
                
                # 增加额外检查，防止坐标过大导致pyMeow库出错
                if (abs(nickname_x) > max_coordinate or abs(nickname_y) > max_coordinate):
                    return
                
                # 检查文本坐标是否在屏幕范围内
                screen_width = overlay.get_screen_width()
                screen_height = overlay.get_screen_height()
                # 确保文本不会绘制在屏幕外
                if -5000 <= nickname_x <= screen_width + 5000 - nickname_width and -5000 <= nickname_y <= screen_height + 5000:
                    safe_draw_text(
                        nickname,
                        nickname_x,
                        nickname_y,
                        nickname_font_size,
                        text_color
                    )

            bar_width = 4
            bar_margin = 2
            bar_x = round(entity.head_pos2d["x"] - half_width - bar_width - bar_margin, 3)
            bar_y = round(entity.head_pos2d["y"] - half_width / 2, 3)
            bar_height = round(box_height + half_width / 2, 3)
            
            # 检查坐标是否为有效数值
            if not (np.isfinite(bar_x) and np.isfinite(bar_y) and np.isfinite(bar_height)):
                return
                
            # 增加额外检查，防止坐标过大导致pyMeow库出错
            if (abs(bar_x) > max_coordinate or abs(bar_y) > max_coordinate or
                abs(bar_x + bar_width) > max_coordinate or abs(bar_y + bar_height) > max_coordinate):
                return
                
            # 检查坐标是否在屏幕范围内
            screen_width = overlay.get_screen_width()
            screen_height = overlay.get_screen_height()
            
            # 只有当血条在屏幕范围内时才绘制
            if (bar_x + bar_width >= -5000 and bar_x <= screen_width + 5000 and
                bar_y + bar_height >= -5000 and bar_y <= screen_height + 5000):
                
                safe_draw_rectangle(
                    bar_x,
                    bar_y,
                    bar_width,
                    bar_height,
                    overlay.get_color("black")
                )
                health_percent = max(0, min(entity.health, 100))
                fill_height = round((health_percent / 100.0) * bar_height, 3)
                if health_percent <= 20:
                    fill_color = overlay.get_color("red")
                elif health_percent <= 50:
                    fill_color = overlay.get_color("yellow")
                else:
                    fill_color = overlay.get_color("green")
                fill_y = round(bar_y + (bar_height - fill_height), 3)
                
                # 增加额外检查，防止坐标过大导致pyMeow库出错
                if (abs(bar_x) > max_coordinate or abs(fill_y) > max_coordinate or
                    abs(bar_x + bar_width) > max_coordinate or abs(fill_y + fill_height) > max_coordinate):
                    return
                
                safe_draw_rectangle(
                    bar_x,
                    fill_y,
                    bar_width,
                    fill_height,
                    fill_color
                )
            if self.draw_health_numbers:
                health_text = f"{entity.health}"
                # 确保健康值文本坐标在屏幕范围内，保留3位小数
                health_text_x = int(bar_x - 25)
                health_text_y = int(bar_y - 10)
                
                # 检查坐标是否为有效数值
                if not (np.isfinite(health_text_x) and np.isfinite(health_text_y)):
                    return
                
                screen_width = overlay.get_screen_width()
                screen_height = overlay.get_screen_height()
                
                # 增加额外检查，防止坐标过大导致pyMeow库出错
                if (abs(health_text_x) > max_coordinate or abs(health_text_y) > max_coordinate):
                    return
                
                # 检查文本是否在屏幕范围内
                if -5000 <= health_text_x <= screen_width + 5000 - 30 and -5000 <= health_text_y <= screen_height + 5000:
                    safe_draw_text(
                        health_text,
                        health_text_x,
                        health_text_y,
                        10,
                        text_color
                    )
        except Exception as e:
            # 特别处理"2D Position out of bounds"错误，避免记录为严重错误
            if "2D Position out of bounds" in str(e):
                pass
            else:
                logger.error(f"绘制实体时出错: {e}")

    def draw_minimap(self, entities: list[Entity], view_matrix: list) -> None:
        """渲染小地图覆盖层。"""
        try:
            # 确保enable_minimap是布尔值
            enable_minimap = self.enable_minimap if isinstance(self.enable_minimap, bool) else False
            if not enable_minimap:
                return

            map_min = {"x": -4000, "y": -4000}
            map_max = {"x": 4000, "y": 4000}
            map_size = {"x": map_max["x"] - map_min["x"], "y": map_max["y"] - map_min["y"]}

            # 确保minimap_size是数值
            minimap_size = self.minimap_size if isinstance(self.minimap_size, (int, float)) else 200
            minimap_x, minimap_y = self.minimap_positions[self.minimap_position]

            # 确保小地图在屏幕范围内
            screen_width = overlay.get_screen_width()
            screen_height = overlay.get_screen_height()
            
            # 限制小地图位置在屏幕内
            minimap_x = max(0, min(minimap_x, screen_width - minimap_size))
            minimap_y = max(0, min(minimap_y, screen_height - minimap_size))

            safe_draw_rectangle(minimap_x, minimap_y, minimap_size, minimap_size, Colors.grey)
            safe_draw_rectangle_lines(minimap_x, minimap_y, minimap_size, minimap_size, Colors.black, 2)

            # 使用NumPy优化小地图实体绘制
            if entities:
                # 收集所有有效实体的位置和队伍信息
                valid_entities_data = []
                for entity in entities:
                    if entity.health <= 0 or entity.dormant:
                        continue
                    valid_entities_data.append((
                        entity.pos["x"], 
                        entity.pos["y"], 
                        entity.team
                    ))
                
                if valid_entities_data:
                    # 转换为NumPy数组进行批量处理
                    entity_array = np.array(valid_entities_data, dtype=np.float32)
                    
                    # 批量计算小地图坐标
                    map_x_coords = ((entity_array[:, 0] - map_min["x"]) / map_size["x"]) * minimap_size + minimap_x
                    map_y_coords = ((map_max["y"] - entity_array[:, 1]) / map_size["y"]) * minimap_size + minimap_y
                    teams = entity_array[:, 2]
                    
                    # 批量绘制实体点
                    for i in range(len(map_x_coords)):
                        color = Colors.cyan if teams[i] == self.local_team else Colors.red
                        # 确保坐标在小地图范围内
                        point_x = max(minimap_x, min(map_x_coords[i], minimap_x + minimap_size))
                        point_y = max(minimap_y, min(map_y_coords[i], minimap_y + minimap_size))
                        safe_draw_circle(point_x, point_y, 3, color)
        except Exception as e:
            logger.error(f"绘制小地图时出错: {e}")
            pass

    def start(self) -> None:
        """启动覆盖层。"""
        self.is_running = True
        self.stop_event.clear()

        try:
            # 以无限制FPS初始化，让我们的循环处理延迟
            # 首先尝试使用游戏窗口初始化，如果需要则回退到自定义窗口
            overlay_initialized = False
            try:
                overlay.overlay_init("Counter-Strike 2", fps=self.target_fps)
                overlay_initialized = True
                logger.info("覆盖层已使用游戏窗口初始化: Counter-Strike 2")
            except Exception as e:
                logger.warning(f"使用游戏窗口初始化覆盖层失败: {e}")
                
            if not overlay_initialized:
                try:
                    # 回退到自定义窗口名称
                    overlay.overlay_init("jian2486 Overlay", fps=self.target_fps)
                    overlay_initialized = True
                    logger.info("覆盖层已使用自定义窗口初始化: jian2486 Overlay")
                except Exception as e:
                    logger.error(f"使用自定义窗口初始化覆盖层失败: {e}")
                    
            if not overlay_initialized:
                # 最后的选择 - 尝试在桌面上创建覆盖层
                try:
                    overlay.overlay_init(fps=self.target_fps)  # Initialize on desktop
                    logger.info("覆盖层已在桌面上初始化")
                except Exception as e:
                    logger.error(f"在桌面上初始化覆盖层失败: {e}")
                    raise Exception("Unable to initialize overlay on any window or desktop")
        except Exception as e:
            logger.error(f"覆盖层初始化错误: {e}")
            self.is_running = False
            return

        frame_time = 1.0 / self.target_fps
        is_game_active = Utility.is_game_active
        sleep = time.sleep

        while not self.stop_event.is_set():
            start_time = time.time()
            
            try:
                # 实时重新加载配置以支持热更新
                current_config = ConfigManager.load_config()
                if current_config != self.config:
                    self.config = current_config
                    self.load_configuration()
                    logger.debug("配置已重新加载并应用")
                
                # 每帧更新屏幕尺寸以处理分辨率变化
                current_screen_width = overlay.get_screen_width()
                current_screen_height = overlay.get_screen_height()
                
                # 仅在屏幕尺寸发生变化时更新
                if current_screen_width != self.screen_width or current_screen_height != self.screen_height:
                    self.screen_width = current_screen_width
                    self.screen_height = current_screen_height
                    # 根据新屏幕尺寸更新小地图位置
                    self.minimap_positions = {
                        "top_left": (10, 10),
                        "top_right": (self.screen_width - self.minimap_size - 10, 10),
                        "bottom_left": (10, self.screen_height - self.minimap_size - 10),
                        "bottom_right": (self.screen_width - self.minimap_size - 10, self.screen_height - self.minimap_size - 10)
                    }
                    # 更新屏幕中心点
                    self.screen_center_x = self.screen_width / 2
                    self.screen_center_y = self.screen_height / 2
                
                # 检查游戏是否处于活动状态，但允许覆盖层在任何界面上运行
                # 仅在无法读取内存时跳过绘制
                try:
                    view_matrix = self.memory_manager.read_floats(self.memory_manager.client_dll_base + self.memory_manager.dwViewMatrix, 16)
                except Exception:
                    # 如果无法读取内存，仍然绘制覆盖层但不包含实体
                    view_matrix = None
                
                local_controller_ptr = None
                try:
                    local_controller_ptr = self.memory_manager.read_longlong(self.memory_manager.client_dll_base + self.memory_manager.dwLocalPlayerController)
                    if local_controller_ptr:
                        local_pawn_ptr = self.memory_manager.read_longlong(self.memory_manager.client_dll_base + self.memory_manager.dwLocalPlayerPawn)
                        if local_pawn_ptr:
                            self.local_team = self.memory_manager.read_int(local_pawn_ptr + self.memory_manager.m_iTeamNum)
                        else:
                            self.local_team = None
                    else:
                        self.local_team = None
                except Exception:
                    # 如果无法读取玩家信息，则继续使用None值
                    pass

                entities = []
                if local_controller_ptr:
                    try:
                        entities = list(self.iterate_entities(local_controller_ptr))
                                    
                        # 按距离排序，优先绘制距离近的实体
                        if local_pawn_ptr and len(entities) > 0:
                            local_pos = self.memory_manager.read_vec3(local_pawn_ptr + self.memory_manager.m_vOldOrigin)
                                        
                            def distance_to_local(entity):
                                try:
                                    return ((entity.pos["x"] - local_pos["x"]) ** 2 + 
                                           (entity.pos["y"] - local_pos["y"]) ** 2 + 
                                           (entity.pos["z"] - local_pos["z"]) ** 2) ** 0.5
                                except:
                                    return float('inf')
                                        
                            entities.sort(key=distance_to_local)
                    except Exception:
                        # If we can't iterate entities, continue with empty list
                        pass

                # 传递实体信息给TriggerBot和Glow功能
                if hasattr(self, 'triggerbot_instance') and self.triggerbot_instance:
                    try:
                        # 移除对update_from_esp的调用，TriggerBot现在独立处理实体数据
                        pass
                    except Exception as e:
                        logger.error(f"传递实体到TriggerBot时出错: {e}")
                
                # Glow功能现在独立获取实体信息，不再需要传递实体列表
                pass

                if overlay.overlay_loop():
                    overlay.begin_drawing()
                    overlay.draw_fps(0, 0)
                    
                    if view_matrix is not None:
                        self.draw_minimap(entities, view_matrix)
                    
                    if view_matrix is not None:
                        for entity in entities:
                            is_teammate = self.local_team is not None and entity.team == self.local_team
                            if is_teammate and not self.draw_teammates:
                                continue
                            self.draw_entity(entity, view_matrix, is_teammate)
                        
                    overlay.end_drawing()

                elapsed_time = time.time() - start_time
                sleep_time = frame_time - elapsed_time
                if sleep_time > 0:
                    sleep(sleep_time)
            except Exception as e:
                logger.error(f"主循环中出现意外错误: {e}", exc_info=True)
                sleep(MAIN_LOOP_SLEEP)

        overlay.overlay_close()
        logger.debug("覆盖层循环已结束")

    def stop(self) -> None:
        """停止覆盖层循环"""
        self.is_running = False
        self.stop_event.set()
        time.sleep(0.1)
        logger.debug("覆盖层已停止")
