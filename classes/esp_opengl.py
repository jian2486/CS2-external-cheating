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

# Initialize the logger for consistent logging
logger = Logger.get_logger()
# Define the main loop sleep time for reduced CPU usage
MAIN_LOOP_SLEEP = 0.05
# Number of entities to iterate over
ENTITY_COUNT = 64
# Size of each entity entry in memory
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
    """Represents a game entity with cached data for efficient access."""
    def __init__(self, controller_ptr: int, pawn_ptr: int, memory_manager: MemoryManager) -> None:
        self.controller_ptr = controller_ptr
        self.pawn_ptr = pawn_ptr
        self.memory_manager = memory_manager
        self.pos2d: Optional[Dict[str, float]] = None
        self.head_pos2d: Optional[Dict[str, float]] = None
        
        # Cached data
        self.name: str = ""
        self.health: int = 0
        self.team: int = -1
        self.pos: Dict[str, float] = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.dormant: bool = True
        self.all_bones_pos_3d: Optional[Dict[int, Dict[str, float]]] = None

    def update(self, use_transliteration: bool, skeleton_enabled: bool) -> bool:
        """Update all entity data at once to minimize memory reads."""
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
        """Get the 3D position of a specific bone, using cached data if available."""
        if self.all_bones_pos_3d and bone in self.all_bones_pos_3d:
            return self.all_bones_pos_3d[bone]
        
        # Fallback to direct read if not in cache
        try:
            game_scene = self.memory_manager.read_longlong(self.pawn_ptr + self.memory_manager.m_pGameSceneNode)
            bone_array_ptr = self.memory_manager.read_longlong(game_scene + self.memory_manager.m_pBoneArray)
            return self.memory_manager.read_vec3(bone_array_ptr + bone * 32)
        except Exception as e:
            return {"x": 0.0, "y": 0.0, "z": 0.0}

    def all_bone_pos(self) -> Optional[Dict[int, Dict[str, float]]]:
        """Get all bone positions by reading the bone matrix."""
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
        """Validate if a screen position is within bounds."""
        return 0 <= pos["x"] <= screen_width and 0 <= pos["y"] <= screen_height

class CS2OverlayOpenGL:
    """Manages the ESP overlay for Counter-Strike 2 using OpenGL."""
    def __init__(self, memory_manager: MemoryManager) -> None:
        """
        Initialize the OpenGL Overlay with a shared MemoryManager instance.
        """
        self.config = ConfigManager.load_config()
        self.memory_manager = memory_manager
        self.is_running = False
        self.stop_event = threading.Event()
        self.local_team = None
        self.screen_width = 0
        self.screen_height = 0
        # Removed anti-screenshot protection
        self.load_configuration()
        
        # Pygame/OpenGL attributes
        self.display = None
        self.clock = None
        self.font_cache = {}  # Cache for font textures

    def load_configuration(self) -> None:
        """Load and apply configuration settings."""
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
        """Update the configuration settings."""
        self.config = config
        self.load_configuration()
        logger.debug("Overlay configuration updated.")

    def iterate_entities(self, local_controller_ptr: int) -> Iterator[Entity]:
        """Iterate over game entities and yield valid Entity objects."""
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
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        # Check if the color is the transparency color (bright pink) and adjust if needed
        if hex_color.upper() == 'FF00FF':
            # Change to a similar color that won't be transparent
            hex_color = 'FF00FE'  # Almost identical but not the transparency color
        return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))

    def draw_line(self, x1: float, y1: float, x2: float, y2: float, color: tuple, thickness: float = 1.0) -> None:
        """Draw a line with specified color and thickness."""
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
        """Draw a filled rectangle."""
        try:
            # Validate inputs
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
            
            # Check for OpenGL errors after drawing
            error = glGetError()
            if error != GL_NO_ERROR:
                logger.error(f"OpenGL error in draw_rectangle: {error}")
        except Exception as e:
            error = glGetError()
            if error != GL_NO_ERROR:
                logger.error(f"OpenGL error in draw_rectangle: {error}")
            raise e

    def draw_rectangle_lines(self, x: float, y: float, width: float, height: float, color: tuple, thickness: float = 1.0) -> None:
        """Draw a rectangle outline."""
        self.draw_line(x, y, x + width, y, color, thickness)  # Top
        self.draw_line(x + width, y, x + width, y + height, color, thickness)  # Right
        self.draw_line(x + width, y + height, x, y + height, color, thickness)  # Bottom
        self.draw_line(x, y + height, x, y, color, thickness)  # Left

    def draw_circle(self, x: float, y: float, radius: float, color: tuple, segments: int = 20) -> None:
        """Draw a circle."""
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
        """Draw the skeleton of an entity."""
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

            # Draw a circle at the head position (bone ID 6)
            if 6 in bone_positions_2d:
                head_pos = bone_positions_2d[6]
                self.draw_circle(head_pos["x"], head_pos["y"], 3, color + (1.0,))  # Add alpha
            
            for start_bone, end_bones in SKELETON_BONES.items():
                if start_bone in bone_positions_2d:
                    for end_bone in end_bones:
                        if end_bone in bone_positions_2d:
                            self.draw_line(
                                bone_positions_2d[start_bone]["x"],
                                bone_positions_2d[start_bone]["y"],
                                bone_positions_2d[end_bone]["x"],
                                bone_positions_2d[end_bone]["y"],
                                color + (1.0,),  # Add alpha
                                1.5
                            )
        except Exception as e:
            logger.error(f"Error drawing skeleton: {e}")

    def world_to_screen(self, view_matrix: list, pos: dict) -> Optional[Dict[str, float]]:
        """Convert world coordinates to screen coordinates."""
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
        """Draw text at the specified position using Pygame font rendering."""
        try:
            # Create a unique key for the font cache
            font_key = (text, size, color)
            if font_key in self.font_cache:
                texture_id, text_width, text_height = self.font_cache[font_key]
            else:
                # Create a surface with the text
                font = pygame.font.SysFont('Microsoft Yahei', int(size))  # Use Microsoft Yahei as per project spec
                text_surface = font.render(text, True, (int(color[0]*255), int(color[1]*255), int(color[2]*255)))
                
                # Get accurate dimensions
                text_width = text_surface.get_width()
                text_height = text_surface.get_height()
                
                # Convert surface to OpenGL texture
                texture_data = pygame.image.tostring(text_surface, "RGBA", True)
                
                # Generate texture
                texture_id = glGenTextures(1)
                glBindTexture(GL_TEXTURE_2D, texture_id)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_width, text_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
                
                # Cache the texture
                self.font_cache[font_key] = (texture_id, text_width, text_height)
            
            # Calculate correct position (centered)
            centered_x = x - text_width / 2
            centered_y = y - text_height / 2
            
            # Draw textured quad
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
            # Fallback to rectangle if font rendering fails
            text_width = len(text) * size * 0.6  # Adjusted width calculation
            text_height = size
            
            self.draw_rectangle(
                x - text_width/2,  # Center the rectangle
                y - text_height/2,
                text_width,
                text_height,
                color + (0.7,) if len(color) == 3 else color
            )

    def draw_entity(self, entity: Entity, view_matrix: list, is_teammate: bool = False) -> None:
        """Render the ESP overlay for a given entity."""
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
                    self.hex_to_rgb(self.snaplines_color_hex) + (1.0,),  # Add alpha
                    2
                )

            if self.enable_box:
                # Draw box fill with configurable alpha if enabled
                box_fill_alpha = self.config['Overlay'].get('box_fill_alpha', 0.0)
                if box_fill_alpha > 0.0:
                    try:
                        fill_color = self.hex_to_rgb(self.box_color_hex)
                        # Apply alpha to the fill color
                        fill_color_with_alpha = fill_color + (box_fill_alpha,)
                        # Validate box dimensions before drawing
                        fill_x = entity.head_pos2d["x"] - half_width
                        fill_y = entity.head_pos2d["y"] - half_width / 2
                        fill_width = box_width
                        fill_height = box_height + half_width / 2
                        
                        if fill_width > 0 and fill_height > 0:
                            # Draw filled box
                            self.draw_rectangle(
                                fill_x,
                                fill_y,
                                fill_width,
                                fill_height,
                                fill_color_with_alpha
                            )
                    except Exception as e:
                        # Get OpenGL error if any
                        error = glGetError()
                        if error != GL_NO_ERROR:
                            logger.error(f"Error drawing box fill: {error} (OpenGL error code)")
                        else:
                            logger.error(f"Error drawing box fill: {e}")
                        # Continue execution even if box fill fails
                        pass
                # Draw box outline
                self.draw_rectangle_lines(
                    entity.head_pos2d["x"] - half_width,
                    entity.head_pos2d["y"] - half_width / 2,
                    box_width,
                    box_height + half_width / 2,
                    outline_color + (1.0,),  # Add alpha
                    self.box_line_thickness
                )

            # Health bar
            bar_width = 4
            bar_margin = 2
            bar_x = entity.head_pos2d["x"] - half_width - bar_width - bar_margin
            bar_y = entity.head_pos2d["y"] - half_width / 2
            bar_height = box_height + half_width / 2
            
            # Background
            self.draw_rectangle(
                bar_x,
                bar_y,
                bar_width,
                bar_height,
                (0, 0, 0, 1)  # Black with alpha
            )
            
            # Health fill
            health_percent = max(0, min(entity.health, 100))
            fill_height = (health_percent / 100.0) * bar_height
            
            if health_percent <= 20:
                fill_color = (1, 0, 0)  # Red
            elif health_percent <= 50:
                fill_color = (1, 1, 0)  # Yellow
            else:
                fill_color = (0, 1, 0)  # Green
                
            fill_y = bar_y + (bar_height - fill_height)
            self.draw_rectangle(
                bar_x,
                fill_y,
                bar_width,
                fill_height,
                fill_color + (1.0,)  # Add alpha
            )

            # Draw health number
            if self.draw_health_numbers:
                health_text = str(entity.health)
                self.draw_text(
                    health_text,
                    bar_x - 15,  # Position to the left of health bar
                    bar_y + bar_height / 2,
                    12,
                    text_color
                )

            if self.draw_nicknames:
                # Draw text with proper centering
                self.draw_text(
                    entity.name,
                    entity.head_pos2d["x"],  # Center on entity's x position
                    entity.head_pos2d["y"] - half_width / 2 - 15,  # Position above the box
                    12,  # Font size
                    text_color
                )

        except Exception as e:
            logger.error(f"Error drawing entity: {e}")

    def setup_opengl(self):
        """Setup OpenGL context and display."""
        # Initialize pygame
        pygame.init()
        
        # Get screen info
        info = pygame.display.Info()
        self.screen_width = info.current_w
        self.screen_height = info.current_h

        # Create fullscreen window using pygame
        self.display = pygame.display.set_mode(
            (self.screen_width, self.screen_height),
            pygame.DOUBLEBUF | pygame.OPENGL | pygame.NOFRAME
        )
        
        # Get window handle
        hwnd = pygame.display.get_wm_info()["window"]
        import win32gui
        import win32con
        import ctypes
        from ctypes import wintypes
        
        # Set window to always on top
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOPMOST,
            0, 0, self.screen_width, self.screen_height,
            win32con.SWP_SHOWWINDOW
        )
        
        # Make window transparent using color key and enable mouse穿透
        extended_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(
            hwnd,
            win32con.GWL_EXSTYLE,
            extended_style | win32con.WS_EX_LAYERED
        )
        # Use color key transparency - set bright pink (0xFF00FF) as transparent color
        win32gui.SetLayeredWindowAttributes(hwnd, 0xFF00FF, 255, win32con.LWA_COLORKEY)
        
        # Anti-screenshot protection has been removed
        
        pygame.display.set_caption("CS2 Overlay")
        
        # Setup OpenGL
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_DEPTH_TEST)
        # Use bright pink as clear color for transparency
        glClearColor(1.0, 0.0, 1.0, 0.0)  # Bright pink background with alpha=0 for transparency
        
        # Setup projection
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, self.screen_width, self.screen_height, 0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        self.clock = pygame.time.Clock()

    def start(self) -> None:
        """Start the OpenGL Overlay."""
        self.is_running = True
        self.stop_event.clear()

        try:
            # Setup OpenGL context
            self.setup_opengl()
        except Exception as e:
            logger.error(f"OpenGL overlay initialization error: {e}")
            self.is_running = False
            return

        frame_time = 1.0 / self.target_fps
        is_game_active = Utility.is_game_active
        sleep = time.sleep

        while not self.stop_event.is_set():
            start_time = time.time()
            
            try:
                # Handle pygame events
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

                # Clear screen with transparent background
                glClear(GL_COLOR_BUFFER_BIT)
                
                # Draw FPS counter
                glColor4f(1, 1, 1, 1)
                # In a full implementation, you would draw text here
                
                # Draw entities
                for entity in entities:
                    is_teammate = self.local_team is not None and entity.team == self.local_team
                    if is_teammate and not self.draw_teammates:
                        continue
                    self.draw_entity(entity, view_matrix, is_teammate)
                
                # Swap buffers
                pygame.display.flip()
                glFlush()  # Force OpenGL commands to be executed
                
                # Control FPS
                self.clock.tick(self.target_fps)
                
                elapsed_time = time.time() - start_time
                sleep_time = frame_time - elapsed_time
                if sleep_time > 0:
                    sleep(sleep_time)
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                sleep(MAIN_LOOP_SLEEP)

        # Clean up font cache
        for texture_id, _, _ in self.font_cache.values():
            glDeleteTextures([texture_id])
        self.font_cache.clear()
        
        pygame.quit()
        logger.debug("OpenGL overlay loop ended.")

    def stop(self) -> None:
        """Stop the Overlay and clean up resources."""
        self.is_running = False
        self.stop_event.set()
        time.sleep(0.1)
        logger.debug("OpenGL overlay stopped.")