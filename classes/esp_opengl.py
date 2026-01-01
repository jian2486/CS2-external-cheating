import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import threading
import time
import struct
import numpy as np
from typing import Iterator, Optional, Dict
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

from classes.config_manager import ConfigManager
from classes.memory_manager import MemoryManager
from classes.logger import Logger
from classes.utility import Utility

# 初始化日志记录器，以确保一致的日志记录
logger = Logger.get_logger()
# 定义主循环睡眠时间以减少CPU使用率
MAIN_LOOP_SLEEP = 0.05
# 遍历的实体数量
ENTITY_COUNT = 64
# 每个实体条目在内存中的大小
ENTITY_ENTRY_SIZE = 120

# 骨骼连接定义
# 骨骼ID: [连接的骨骼ID列表]
SKELETON_BONES = {
    # 头部和躯干
    6: [5],          # 头部 -> 颈部
    5: [4],          # 颈部 -> 胸部
    4: [3],          # 胸部 -> 腹部
    3: [2],          # 腹部 -> 后背
    2: [1],          # 后背 -> 腰部
    1: [0],          # 腰部 -> 骨盆
    0: [22, 25],     # 骨盆 -> 左臀和右臀
    
    # 右臂
    5: [11],         # 颈部 -> 右肩
    11: [12],        # 右肩 -> 右肘
    12: [13],        # 右肘 -> 右手
    
    # 左臂
    4: [8],          # 胸部 -> 左肩
    8: [9],          # 左肩 -> 左肘
    9: [10],         # 左肘 -> 左手
    
    # 右腿
    25: [26],        # 右臀 -> 右膝
    26: [27],        # 右膝 -> 右脚
    
    # 左腿
    22: [23],        # 左臀 -> 左膝
    23: [24],        # 左膝 -> 左脚
}
ALL_BONE_IDS = set(SKELETON_BONES.keys())
for _bones in SKELETON_BONES.values():
    ALL_BONE_IDS.update(_bones)
MAX_BONE_ID = max(ALL_BONE_IDS) if ALL_BONE_IDS else 0

class Entity:
    """表示一个具有缓存数据的游戏实体，以实现高效访问。"""
    def __init__(self, controller_ptr: int, pawn_ptr: int, memory_manager: MemoryManager) -> None:
        self.controller_ptr = controller_ptr
        self.pawn_ptr = pawn_ptr
        self.memory_manager = memory_manager
        self.pos2d: Optional[Dict[str, float]] = None
        self.head_pos2d: Optional[Dict[str, float]] = None
        
        # 缓存数据
        self.name: str = ""
        self.health: int = 0
        self.team: int = -1
        self.pos: Dict[str, float] = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.dormant: bool = True
        self.all_bones_pos_3d: Optional[Dict[int, Dict[str, float]]] = None

    def update(self, use_transliteration: bool, skeleton_enabled: bool) -> bool:
        """一次更新所有实体数据以最小化内存读取。"""
        try:
            self.health = self.memory_manager.read_int(self.pawn_ptr + self.memory_manager.m_iHealth)
            if self.health <= 0:
                return False

            self.dormant = bool(self.memory_manager.read_int(self.pawn_ptr + self.memory_manager.m_bDormant))
            if self.dormant:
                return False

            self.team = self.memory_manager.read_int(self.pawn_ptr + self.memory_manager.m_iTeamNum)
            self.pos = self.memory_manager.read_vec3(self.pawn_ptr + self.memory_manager.m_vOldOrigin)
            
            raw_name = self.memory_manager.read_string(self.controller_ptr + self.memory_manager.m_iszPlayerName)
            self.name = Utility.transliterate(raw_name) if use_transliteration else raw_name

            # 只有在启用骨骼绘制且实体在玩家附近时才获取骨骼数据
            if skeleton_enabled:
                # 计算实体与玩家的距离
                local_player_ptr = self.memory_manager.read_longlong(
                    self.memory_manager.client_dll_base + self.memory_manager.dwLocalPlayerPawn)
                if local_player_ptr:
                    local_pos = self.memory_manager.read_vec3(local_player_ptr + self.memory_manager.m_vOldOrigin)
                    distance = ((self.pos["x"] - local_pos["x"]) ** 2 + 
                               (self.pos["y"] - local_pos["y"]) ** 2 + 
                               (self.pos["z"] - local_pos["z"]) ** 2) ** 0.5
                    
                    # 只有在合理距离内才获取骨骼数据（例如1000游戏单位以内）
                    if distance <= 1000:
                        self.all_bones_pos_3d = self.all_bone_pos()
                    else:
                        self.all_bones_pos_3d = None
                else:
                    self.all_bones_pos_3d = self.all_bone_pos()
            else:
                self.all_bones_pos_3d = None

            return True
        except Exception as e:
            return False

    def bone_pos(self, bone: int) -> Dict[str, float]:
        """获取特定骨骼的3D位置，如果可用则使用缓存数据。"""
        if self.all_bones_pos_3d and bone in self.all_bones_pos_3d:
            return self.all_bones_pos_3d[bone]
        
        # 如果不在缓存中则回退到直接读取
        try:
            game_scene = self.memory_manager.read_longlong(self.pawn_ptr + self.memory_manager.m_pGameSceneNode)
            bone_array_ptr = self.memory_manager.read_longlong(game_scene + self.memory_manager.m_pBoneArray)
            return self.memory_manager.read_vec3(bone_array_ptr + bone * 32)
        except Exception as e:
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
            for i in ALL_BONE_IDS:
                offset = i * 32
                try:
                    x, y, z = struct.unpack_from('fff', data, offset)
                    bone_positions[i] = {"x": x, "y": y, "z": z}
                except struct.error:
                    continue
            return bone_positions
        except Exception as e:
            return None

    @staticmethod
    def validate_screen_position(pos: Dict[str, float], screen_width: int, screen_height: int) -> bool:
        """验证屏幕位置是否在边界内。"""
        return 0 <= pos["x"] <= screen_width and 0 <= pos["y"] <= screen_height

class CS2OverlayOpenGL:
    """管理使用OpenGL的Counter-Strike 2的ESP覆盖层。"""
    def __init__(self, memory_manager: MemoryManager) -> None:
        """
        使用共享的MemoryManager实例初始化OpenGL覆盖层。
        """
        self.config = ConfigManager.load_config()
        self.memory_manager = memory_manager
        self.is_running = False
        self.stop_event = threading.Event()
        self.local_team = None
        self.screen_width = 0
        self.screen_height = 0
        # 已移除反截图保护
        self.load_configuration()
        
        # Pygame/OpenGL属性
        self.display = None
        self.clock = None
        self.font_cache = {}  # 字体纹理缓存

    def load_configuration(self) -> None:
        """加载并应用配置设置。"""
        settings = self.config['Overlay']
        self.enable_box = settings['enable_box']
        self.enable_skeleton = settings.get('enable_skeleton', True)
        self.draw_snaplines = settings['draw_snaplines']
        self.snaplines_color_hex = settings['snaplines_color_hex']
        self.box_line_thickness = settings['box_line_thickness']
        self.box_color_hex = settings['box_color_hex']
        self.text_color_hex = settings['text_color_hex']
        self.draw_health_numbers = settings['draw_health_numbers']
        self.use_transliteration = settings['use_transliteration']
        self.draw_nicknames = settings['draw_nicknames']
        self.draw_teammates = settings['draw_teammates']
        self.teammate_color_hex = settings['teammate_color_hex']
        self.enable_minimap = settings['enable_minimap']
        self.minimap_size = settings['minimap_size']
        self.target_fps = int(settings['target_fps'])

    def update_config(self, config: dict) -> None:
        """更新配置设置。"""
        self.config = config
        self.load_configuration()
        logger.debug("覆盖层配置已更新。")

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
            return

        entity_count = 0
        for i in range(1, ENTITY_COUNT + 1):
            # 性能优化：限制处理的实体数量
            if entity_count >= 15:  # 最多处理15个实体
                break
                
            try:
                list_index = (i & 0x7FFF) >> 9
                entity_index = i & 0x1FF
                entry_ptr = self.memory_manager.read_longlong(ent_list_ptr + (8 * list_index) + 16)
                if not entry_ptr: continue

                controller_ptr = self.memory_manager.read_longlong(entry_ptr + ENTITY_ENTRY_SIZE * entity_index)
                if not controller_ptr or controller_ptr == local_controller_ptr: continue

                controller_pawn_ptr = self.memory_manager.read_longlong(controller_ptr + self.memory_manager.m_hPlayerPawn)
                if not controller_pawn_ptr: continue

                list_entry_ptr = self.memory_manager.read_longlong(ent_list_ptr + 8 * ((controller_pawn_ptr & 0x7FFF) >> 9) + 16)
                if not list_entry_ptr: continue

                pawn_ptr = self.memory_manager.read_longlong(list_entry_ptr + ENTITY_ENTRY_SIZE * (controller_pawn_ptr & 0x1FF))
                if not pawn_ptr: continue

                # 性能优化：检查实体是否在合理距离内
                if local_pos and pawn_ptr:
                    try:
                        entity_pos = self.memory_manager.read_vec3(pawn_ptr + self.memory_manager.m_vOldOrigin)
                        distance = ((entity_pos["x"] - local_pos["x"]) ** 2 + 
                                   (entity_pos["y"] - local_pos["y"]) ** 2 + 
                                   (entity_pos["z"] - local_pos["z"]) ** 2) ** 0.5
                        # 如果距离太远则跳过
                        if distance > 2000:  # 2000游戏单位以外的实体不处理
                            continue
                    except:
                        pass

                entity = Entity(controller_ptr, pawn_ptr, self.memory_manager)
                if entity.update(self.use_transliteration, self.enable_skeleton):
                    entity_count += 1
                    yield entity
            except Exception:
                continue

    def hex_to_rgb(self, hex_color: str) -> tuple:
        """将十六进制颜色转换为RGB元组。"""
        hex_color = hex_color.lstrip('#')
        # 检查颜色是否为透明色（亮粉色）并根据需要调整
        if hex_color.upper() == 'FF00FF':
            # 更改为不会透明的相似颜色
            hex_color = 'FF00FE'  # 几乎相同但不是透明色
        return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))

    def draw_line(self, x1: float, y1: float, x2: float, y2: float, color: tuple, thickness: float = 1.0) -> None:
        """绘制指定颜色和厚度的线条。"""
        glLineWidth(thickness)
        if len(color) == 4:
            glColor4f(*color)
        else:
            glColor3f(*color)
        glBegin(GL_LINES)
        glVertex2f(x1, y1)
        glVertex2f(x2, y2)
        glEnd()

    def draw_rectangle(self, x: float, y: float, width: float, height: float, color: tuple) -> None:
        """绘制填充矩形。"""
        try:
            # 验证输入
            if width <= 0 or height <= 0:
                return
                
            if len(color) == 4:
                glColor4f(*color)
            else:
                glColor3f(*color)
            glBegin(GL_QUADS)
            glVertex2f(x, y)
            glVertex2f(x + width, y)
            glVertex2f(x + width, y + height)
            glVertex2f(x, y + height)
            glEnd()
            
            # 绘制后检查OpenGL错误
            error = glGetError()
            if error != GL_NO_ERROR:
                logger.error(f"draw_rectangle中的OpenGL错误: {error}")
        except Exception as e:
            error = glGetError()
            if error != GL_NO_ERROR:
                logger.error(f"draw_rectangle中的OpenGL错误: {error}")
            raise e

    def draw_rectangle_lines(self, x: float, y: float, width: float, height: float, color: tuple, thickness: float = 1.0) -> None:
        """绘制矩形轮廓。"""
        self.draw_line(x, y, x + width, y, color, thickness)  # 顶部
        self.draw_line(x + width, y, x + width, y + height, color, thickness)  # 右侧
        self.draw_line(x + width, y + height, x, y + height, color, thickness)  # 底部
        self.draw_line(x, y + height, x, y, color, thickness)  # 左侧

    def draw_circle(self, x: float, y: float, radius: float, color: tuple, segments: int = 20) -> None:
        """绘制圆形。"""
        if len(color) == 4:
            glColor4f(*color)
        else:
            glColor3f(*color)
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(x, y)
        for i in range(segments + 1):
            angle = 2 * 3.14159 * i / segments
            glVertex2f(x + radius * np.cos(angle), y + radius * np.sin(angle))
        glEnd()

    def draw_skeleton(self, entity: Entity, view_matrix: list, color: tuple, all_bones_pos_3d: Dict[int, Dict[str, float]]) -> None:
        """绘制实体的骨骼。"""
        try:
            if not all_bones_pos_3d:
                return

            bone_positions_2d = {}
            for bone_id in ALL_BONE_IDS:
                if bone_id in all_bones_pos_3d:
                    pos_3d = all_bones_pos_3d[bone_id]
                    try:
                        pos_2d = self.world_to_screen(view_matrix, pos_3d)
                    except Exception:
                        pos_2d = None
                    
                    if pos_2d and entity.validate_screen_position(pos_2d, self.screen_width, self.screen_height):
                        bone_positions_2d[bone_id] = pos_2d

            # 在头部位置绘制一个圆圈（骨骼ID 6）
            if 6 in bone_positions_2d:
                head_pos = bone_positions_2d[6]
                self.draw_circle(head_pos["x"], head_pos["y"], 3, color + (1.0,))  # 添加alpha
            
            for start_bone, end_bones in SKELETON_BONES.items():
                if start_bone in bone_positions_2d:
                    for end_bone in end_bones:
                        if end_bone in bone_positions_2d:
                            self.draw_line(
                                bone_positions_2d[start_bone]["x"],
                                bone_positions_2d[start_bone]["y"],
                                bone_positions_2d[end_bone]["x"],
                                bone_positions_2d[end_bone]["y"],
                                color + (1.0,),  # 添加alpha
                                1.5
                            )
        except Exception as e:
            logger.error(f"绘制骨骼时出错: {e}")

    def world_to_screen(self, view_matrix: list, pos: dict) -> Optional[Dict[str, float]]:
        """将世界坐标转换为屏幕坐标。"""
        try:
            screen_w = (view_matrix[12] * pos["x"]) + (view_matrix[13] * pos["y"]) + (view_matrix[14] * pos["z"]) + view_matrix[15]
            
            if screen_w > 0.001:
                screen_x = (view_matrix[0] * pos["x"]) + (view_matrix[1] * pos["y"]) + (view_matrix[2] * pos["z"]) + view_matrix[3]
                screen_y = (view_matrix[4] * pos["x"]) + (view_matrix[5] * pos["y"]) + (view_matrix[6] * pos["z"]) + view_matrix[7]
                
                x = (self.screen_width / 2) * (1 + screen_x / screen_w)
                y = (self.screen_height / 2) * (1 - screen_y / screen_w)
                
                return {"x": x, "y": y}
            else:
                return None
        except Exception:
            return None

    def draw_text(self, text: str, x: float, y: float, size: float, color: tuple) -> None:
        """使用Pygame字体渲染在指定位置绘制文本。"""
        try:
            # 为字体缓存创建唯一键
            font_key = (text, size, color)
            if font_key in self.font_cache:
                texture_id, text_width, text_height = self.font_cache[font_key]
            else:
                # 创建包含文本的表面
                font = pygame.font.SysFont('Microsoft Yahei', int(size))  # 按项目规范使用Microsoft Yahei
                text_surface = font.render(text, True, (int(color[0]*255), int(color[1]*255), int(color[2]*255)))
                
                # 获取准确的尺寸
                text_width = text_surface.get_width()
                text_height = text_surface.get_height()
                
                # 将表面转换为OpenGL纹理
                texture_data = pygame.image.tostring(text_surface, "RGBA", True)
                
                # 生成纹理
                texture_id = glGenTextures(1)
                glBindTexture(GL_TEXTURE_2D, texture_id)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_width, text_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
                
                # 缓存纹理
                self.font_cache[font_key] = (texture_id, text_width, text_height)
            
            # 计算正确位置（居中）
            centered_x = x - text_width / 2
            centered_y = y - text_height / 2
            
            # 绘制纹理四边形
            glEnable(GL_TEXTURE_2D)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glColor4f(1, 1, 1, 1 if len(color) < 4 else color[3])
            
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0)
            glVertex2f(centered_x, centered_y)
            glTexCoord2f(1, 0)
            glVertex2f(centered_x + text_width, centered_y)
            glTexCoord2f(1, 1)
            glVertex2f(centered_x + text_width, centered_y + text_height)
            glTexCoord2f(0, 1)
            glVertex2f(centered_x, centered_y + text_height)
            glEnd()
            
            glDisable(GL_TEXTURE_2D)
        except Exception as e:
            # 如果字体渲染失败则回退到矩形
            text_width = len(text) * size * 0.6  # 调整宽度计算
            text_height = size
            
            self.draw_rectangle(
                x - text_width/2,  # 居中矩形
                y - text_height/2,
                text_width,
                text_height,
                color + (0.7,) if len(color) == 3 else color
            )

    def draw_entity(self, entity: Entity, view_matrix: list, is_teammate: bool = False) -> None:
        """为给定实体渲染ESP覆盖层。"""
        try:
            head_pos_3d = entity.bone_pos(6)
            pos2d = self.world_to_screen(view_matrix, entity.pos)
            head_pos2d = self.world_to_screen(view_matrix, head_pos_3d)

            if not pos2d or not head_pos2d:
                return

            if not entity.validate_screen_position(pos2d, self.screen_width, self.screen_height) or \
               not entity.validate_screen_position(head_pos2d, self.screen_width, self.screen_height):
                return

            entity.pos2d = pos2d
            entity.head_pos2d = head_pos2d

            head_y = entity.head_pos2d["y"]
            pos_y = entity.pos2d["y"]
            box_height = pos_y - head_y
            box_width = box_height / 2
            half_width = box_width / 2

            outline_color = self.hex_to_rgb(self.teammate_color_hex if is_teammate else self.box_color_hex)
            text_color = self.hex_to_rgb(self.text_color_hex)

            if self.enable_skeleton and entity.all_bones_pos_3d:
                self.draw_skeleton(entity, view_matrix, outline_color, entity.all_bones_pos_3d)

            if self.draw_snaplines:
                self.draw_line(
                    self.screen_width / 2,
                    self.screen_height / 2,
                    entity.head_pos2d["x"],
                    entity.head_pos2d["y"],
                    self.hex_to_rgb(self.snaplines_color_hex) + (1.0,),  # 添加alpha
                    2
                )

            if self.enable_box:
                # 绘制带有可配置alpha的框填充（如果启用）
                box_fill_alpha = self.config['Overlay'].get('box_fill_alpha', 0.0)
                if box_fill_alpha > 0.0:
                    try:
                        fill_color = self.hex_to_rgb(self.box_color_hex)
                        # 将alpha应用到填充颜色
                        fill_color_with_alpha = fill_color + (box_fill_alpha,)
                        # 绘制前验证框的尺寸
                        fill_x = entity.head_pos2d["x"] - half_width
                        fill_y = entity.head_pos2d["y"] - half_width / 2
                        fill_width = box_width
                        fill_height = box_height + half_width / 2
                        
                        if fill_width > 0 and fill_height > 0:
                            # 绘制填充框
                            self.draw_rectangle(
                                fill_x,
                                fill_y,
                                fill_width,
                                fill_height,
                                fill_color_with_alpha
                            )
                    except Exception as e:
                        # 获取OpenGL错误（如果有的话）
                        error = glGetError()
                        if error != GL_NO_ERROR:
                            logger.error(f"绘制框填充时出错: {error} (OpenGL错误代码)")
                        else:
                            logger.error(f"绘制框填充时出错: {e}")
                        # 即使框填充失败也继续执行
                        pass
                # 绘制框轮廓
                self.draw_rectangle_lines(
                    entity.head_pos2d["x"] - half_width,
                    entity.head_pos2d["y"] - half_width / 2,
                    box_width,
                    box_height + half_width / 2,
                    outline_color + (1.0,),  # 添加alpha
                    self.box_line_thickness
                )

            # 血条
            bar_width = 4
            bar_margin = 2
            bar_x = entity.head_pos2d["x"] - half_width - bar_width - bar_margin
            bar_y = entity.head_pos2d["y"] - half_width / 2
            bar_height = box_height + half_width / 2
            
            # 背景
            self.draw_rectangle(
                bar_x,
                bar_y,
                bar_width,
                bar_height,
                (0, 0, 0, 1)  # 带alpha的黑色
            )
            
            # 血量填充
            health_percent = max(0, min(entity.health, 100))
            fill_height = (health_percent / 100.0) * bar_height
            
            if health_percent <= 20:
                fill_color = (1, 0, 0)  # 红色
            elif health_percent <= 50:
                fill_color = (1, 1, 0)  # 黄色
            else:
                fill_color = (0, 1, 0)  # 绿色
                
            fill_y = bar_y + (bar_height - fill_height)
            self.draw_rectangle(
                bar_x,
                fill_y,
                bar_width,
                fill_height,
                fill_color + (1.0,)  # 添加alpha
            )

            # 绘制血量数字
            if self.draw_health_numbers:
                health_text = str(entity.health)
                self.draw_text(
                    health_text,
                    bar_x - 15,  # 位于血条左侧
                    bar_y + bar_height / 2,
                    12,
                    text_color
                )

            if self.draw_nicknames:
                # 绘制居中的文本
                self.draw_text(
                    entity.name,
                    entity.head_pos2d["x"],  # 在实体的x位置居中
                    entity.head_pos2d["y"] - half_width / 2 - 15,  # 位于框上方
                    12,  # 字体大小
                    text_color
                )

        except Exception as e:
            logger.error(f"绘制实体时出错: {e}")

    def setup_opengl(self):
        """设置OpenGL上下文和显示。"""
        # 初始化pygame
        pygame.init()
        
        # 获取屏幕信息
        info = pygame.display.Info()
        self.screen_width = info.current_w
        self.screen_height = info.current_h

        # 使用pygame创建全屏窗口
        self.display = pygame.display.set_mode(
            (self.screen_width, self.screen_height),
            pygame.DOUBLEBUF | pygame.OPENGL | pygame.NOFRAME
        )
        
        # 获取窗口句柄
        hwnd = pygame.display.get_wm_info()["window"]
        import win32gui
        import win32con
        import ctypes
        from ctypes import wintypes
        
        # 设置窗口始终在最上层
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOPMOST,
            0, 0, self.screen_width, self.screen_height,
            win32con.SWP_SHOWWINDOW
        )
        
        # 使用颜色键设置窗口透明并启用鼠标穿透
        extended_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(
            hwnd,
            win32con.GWL_EXSTYLE,
            extended_style | win32con.WS_EX_LAYERED
        )
        # 使用颜色键透明 - 设置亮粉色(0xFF00FF)为透明色
        win32gui.SetLayeredWindowAttributes(hwnd, 0xFF00FF, 255, win32con.LWA_COLORKEY)
        
        # 已移除反截图保护
        
        pygame.display.set_caption("CS2覆盖层")
        
        # 设置OpenGL
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_DEPTH_TEST)
        # 使用亮粉色作为透明背景色
        glClearColor(1.0, 0.0, 1.0, 0.0)  # 亮粉色背景，alpha=0表示透明
        
        # 设置投影
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, self.screen_width, self.screen_height, 0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        self.clock = pygame.time.Clock()

    def start(self) -> None:
        """启动OpenGL覆盖层。"""
        self.is_running = True
        self.stop_event.clear()

        try:
            # 设置OpenGL上下文
            self.setup_opengl()
        except Exception as e:
            logger.error(f"OpenGL覆盖层初始化错误: {e}")
            self.is_running = False
            return

        frame_time = 1.0 / self.target_fps
        is_game_active = Utility.is_game_active
        sleep = time.sleep

        while not self.stop_event.is_set():
            start_time = time.time()
            
            try:
                # 处理pygame事件
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.stop_event.set()
                        break
                
                if not is_game_active():
                    sleep(MAIN_LOOP_SLEEP)
                    continue

                view_matrix = self.memory_manager.read_floats(self.memory_manager.client_dll_base + self.memory_manager.dwViewMatrix, 16)
                
                local_controller_ptr = self.memory_manager.read_longlong(self.memory_manager.client_dll_base + self.memory_manager.dwLocalPlayerController)
                if local_controller_ptr:
                    local_pawn_ptr = self.memory_manager.read_longlong(self.memory_manager.client_dll_base + self.memory_manager.dwLocalPlayerPawn)
                    if local_pawn_ptr:
                        self.local_team = self.memory_manager.read_int(local_pawn_ptr + self.memory_manager.m_iTeamNum)
                    else:
                        self.local_team = None
                else:
                    self.local_team = None

                entities = list(self.iterate_entities(local_controller_ptr))

                # 使用透明背景清除屏幕
                glClear(GL_COLOR_BUFFER_BIT)
                
                # 绘制FPS计数器
                glColor4f(1, 1, 1, 1)
                # 在完整实现中，这里会绘制文本
                
                # 绘制实体
                for entity in entities:
                    is_teammate = self.local_team is not None and entity.team == self.local_team
                    if is_teammate and not self.draw_teammates:
                        continue
                    self.draw_entity(entity, view_matrix, is_teammate)
                
                # 交换缓冲区
                pygame.display.flip()
                glFlush()  # 强制执行OpenGL命令
                
                # 控制FPS
                self.clock.tick(self.target_fps)
                
                elapsed_time = time.time() - start_time
                sleep_time = frame_time - elapsed_time
                if sleep_time > 0:
                    sleep(sleep_time)
            except Exception as e:
                logger.error(f"主循环中出现意外错误: {e}", exc_info=True)
                sleep(MAIN_LOOP_SLEEP)

        # 清理字体缓存
        for texture_id, _, _ in self.font_cache.values():
            glDeleteTextures([texture_id])
        self.font_cache.clear()
        
        pygame.quit()
        logger.debug("OpenGL覆盖层循环结束。")

    def stop(self) -> None:
        """停止覆盖层并清理资源。"""
        self.is_running = False
        self.stop_event.set()
        time.sleep(0.1)
        logger.debug("OpenGL覆盖层已停止。")