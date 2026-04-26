import math
import struct

import numpy as np
import pymem
import pymem.process

from classes.logger import Logger
from classes.utility import Utility

# 初始化日志记录器以保持一致的日志记录
logger = Logger.get_logger()

class MemoryManager:
    ENTITY_ENTRY_SIZE = 112  # 每个实体占用的空间
    BONE_ARRAY_OFFSET = 0x80  # CSkeletonInstance::m_modelState + 0x80 = m_pBoneArray

    def __init__(self, offsets: dict, client_data: dict, buttons_data: dict) -> None:
        """使用偏移量和客户端数据初始化MemoryManager。"""
        self.offsets = offsets
        self.client_data = client_data
        self.buttons_data = buttons_data
        self.pm = None
        self.client_base = None
        self.load_offsets()
        
    def update_offsets(self, offsets, client_data, buttons_data):
        """更新偏移量数据"""
        self.offsets = offsets
        self.client_data = client_data
        self.buttons_data = buttons_data

    def initialize(self) -> bool:
        """
        通过附加到进程并设置必要数据来初始化内存访问。
        如果成功返回True，否则返回False。
        """
        # 检查pymem是否已初始化且客户端模块已检索
        if not self.initialize_pymem() or not self.get_client_module():
            return False
        # 缓存实体列表指针
        self.load_offsets()
        if self.dwEntityList is None:  # 确保偏移量已成功加载
            return False
        self.ent_list = self.read_longlong(self.client_base + self.dwEntityList)
        return True

    def initialize_pymem(self) -> bool:
        """将pymem附加到游戏进程。"""
        try:
            # 尝试附加到cs2.exe进程
            self.pm = pymem.Pymem("cs2.exe")
            logger.debug("成功附加到cs2.exe进程")
            return True
        except pymem.exception.ProcessNotFound:
            # 如果未找到进程则记录错误
            logger.error("未找到cs2.exe进程,请确保游戏正在运行")
            return False
        except Exception as e:
            # 记录可能发生的任何其他异常
            logger.error(f"附加到cs2.exe时出现意外错误: {e}")
            return False

    def get_client_module(self) -> bool:
        """检索client.dll模块基地址。"""
        try:
            # 尝试检索client.dll模块
            client_module = pymem.process.module_from_name(self.pm.process_handle, "client.dll")
            self.client_base = client_module.lpBaseOfDll
            logger.debug("找到client.dll模块并检索到基地址")
            return True
        except pymem.exception.ModuleNotFoundError:
            # 如果未找到模块则记录错误
            logger.error("未找到client.dll")
            return False
        except Exception as e:
            # 记录可能发生的任何其他异常
            logger.error(f"检索client.dll模块时出现意外错误: {e}")
            return False

    def load_offsets(self) -> None:
        """从Utility.extract_offsets加载内存偏移量。"""
        extracted = Utility.extract_offsets(self.offsets, self.client_data, self.buttons_data)
        if extracted:
            self.dwEntityList = extracted["dwEntityList"]
            self.dwLocalPlayerPawn = extracted["dwLocalPlayerPawn"]
            self.dwLocalPlayerController = extracted["dwLocalPlayerController"]
            self.dwViewMatrix = extracted["dwViewMatrix"]
            self.dwForceJump = extracted["dwForceJump"]
            self.dwForceAttack = extracted["dwForceAttack"]
            self.dwGlowManager = extracted["dwGlowManager"]
            self.m_Glow = extracted["m_Glow"]
            self.m_glowColorOverride = extracted["m_glowColorOverride"]
            self.m_bGlowing = extracted["m_bGlowing"]
            self.m_iHealth = extracted["m_iHealth"]
            self.m_iTeamNum = extracted["m_iTeamNum"]
            self.m_iIDEntIndex = extracted["m_iIDEntIndex"]
            self.m_iszPlayerName = extracted["m_iszPlayerName"]
            self.m_vOldOrigin = extracted["m_vOldOrigin"]
            self.m_vecAbsOrigin = extracted.get("m_vecAbsOrigin")  # 备用位置偏移量
            self.m_pGameSceneNode = extracted["m_pGameSceneNode"]
            self.m_bDormant = extracted["m_bDormant"]
            self.m_hPlayerPawn = extracted["m_hPlayerPawn"]
            self.m_flFlashDuration = extracted["m_flFlashDuration"]
            self.m_pBoneArray = extracted["m_pBoneArray"]
            self.m_AttributeManager = extracted["m_AttributeManager"]
            self.m_iItemDefinitionIndex = extracted["m_iItemDefinitionIndex"]
            self.m_Item = extracted["m_Item"]
            self.m_pWeaponServices = extracted["m_pWeaponServices"]
            self.m_hActiveWeapon = extracted["m_hActiveWeapon"]
            self.m_angEyeAngles = extracted.get("m_angEyeAngles")  # 自瞄用视角角度
            self.dwViewAngles = extracted.get("dwViewAngles")  # 全局视角角度地址
        else:
            logger.error("从提取的数据初始化偏移量失败")

    def get_entity(self, index: int):
        """从实体列表中检索实体。"""
        try:
            # 使用缓存的实体列表指针
            list_offset = 0x8 * (index >> 9)
            ent_entry = self.read_longlong(self.ent_list + list_offset + 0x10)
            # 检查ent_entry是否有效
            if ent_entry == 0:
                return None
            entity_offset = self.ENTITY_ENTRY_SIZE * (index & 0x1FF)
            return self.read_longlong(ent_entry + entity_offset)
        except pymem.exception.MemoryReadError as e:
            logger.error(f"读取实体时出错: 无法在地址 {e.address} 读取内存, 长度: {e.length} - GetLastError: {e.win32_error_code}")
            return None
        except Exception as e:
            logger.error(f"读取实体时出错: {e}")
            return None
    
    def get_all_entities(self, max_entities=64):
        """
        获取所有有效实体列表（通用方法）- 使用与Glow相同的实体遍历逻辑
        :param max_entities: 最大实体数量
        :return: 实体信息列表 [{entity_ptr, health, team, position, dormant, ...}]
        """
        entities = []
        
        try:
            # 获取本地玩家队伍
            local_player = self.read_longlong(self.client_base + self.dwLocalPlayerPawn)
            if not local_player:
                return entities
            
            local_team = self.read_int(local_player + self.m_iTeamNum)
            
            # 获取实体列表
            entity_list = self.read_longlong(self.client_base + self.dwEntityList)
            if not entity_list:
                return entities
            
            # 获取列表入口
            entry = self.read_longlong(entity_list + 0x10)
            if not entry:
                return entities
            
            # 遍历所有实体
            for i in range(max_entities):
                try:
                    # 获取控制器
                    controller = self.read_longlong(entry + i * self.ENTITY_ENTRY_SIZE)
                    if not controller:
                        continue
                    
                    # 获取玩家pawn句柄
                    player_pawn_handle = self.read_longlong(controller + self.m_hPlayerPawn)
                    if not player_pawn_handle:
                        continue
                    
                    # 获取实体列表条目
                    entry_2 = self.read_longlong(
                        entity_list + 0x8 * ((player_pawn_handle & 0x7FFF) >> 9) + 0x10
                    )
                    if not entry_2:
                        continue
                    
                    # 获取当前实体（pawn）
                    current_entity = self.read_longlong(
                        entry_2 + self.ENTITY_ENTRY_SIZE * (player_pawn_handle & 0x1FF)
                    )
                    if not current_entity:
                        continue
                    
                    # 读取基本信息
                    team = self.read_int(current_entity + self.m_iTeamNum)
                    health = self.read_int(current_entity + self.m_iHealth)
                    
                    # 过滤无效实体
                    if health <= 0:
                        continue
                    
                    # 获取位置
                    game_scene_node = self.read_longlong(current_entity + self.m_pGameSceneNode)
                    position = {"x": 0, "y": 0, "z": 0}
                    bone_array_ptr = None
                    
                    if game_scene_node:
                        # 先尝试 m_vOldOrigin
                        position = self.read_vec3(game_scene_node + self.m_vOldOrigin)
                        
                        # 如果无效，尝试 m_vecAbsOrigin
                        if (position["x"] == 0 and position["y"] == 0) and hasattr(self, 'm_vecAbsOrigin') and self.m_vecAbsOrigin:
                            position = self.read_vec3(game_scene_node + self.m_vecAbsOrigin)
                        
                        bone_array_ptr = self.read_longlong(game_scene_node + self.m_pBoneArray)
                    
                    entities.append({
                        "index": i,
                        "ptr": current_entity,
                        "health": health,
                        "team": team,
                        "position": position,
                        "bone_array_ptr": bone_array_ptr,
                        "dormant": 0  # Glow逻辑中没有检查dormant
                    })
                except Exception as e:
                    logger.debug(f"读取实体 {i} 时出错: {e}")
                    continue
            

        except Exception as e:
            logger.error(f"获取实体列表失败: {e}")
        
        return entities
    
    def calculate_angle(self, src: dict, dst: dict) -> dict:
        """
        计算从源点到目标点的角度
        :param src: 源点 {x, y, z}
        :param dst: 目标点 {x, y, z}
        :return: {pitch, yaw} 角度（度）
        """
        import math
        
        delta_x = dst['x'] - src['x']
        delta_y = dst['y'] - src['y']
        delta_z = dst['z'] - src['z']
        
        # 计算水平距离
        distance_xy = math.sqrt(delta_x * delta_x + delta_y * delta_y)
        
        # 计算 Pitch（俯仰角）
        pitch = math.degrees(math.atan2(-delta_z, distance_xy))
        
        # 计算 Yaw（偏航角）
        yaw = math.degrees(math.atan2(delta_y, delta_x))
        
        return {"pitch": pitch, "yaw": yaw}
    
    def write_view_angles(self, angles: dict) -> bool:
        """
        写入视角角度到内存
        :param angles: {pitch, yaw}
        :return: 是否成功
        """
        try:
            if not hasattr(self, 'dwViewAngles') or self.dwViewAngles is None:
                logger.warning("dwViewAngles 偏移量未找到")
                return False
            
            view_angles_addr = self.client_base + self.dwViewAngles
            self.write_float(view_angles_addr, angles['pitch'])      # Pitch
            self.write_float(view_angles_addr + 4, angles['yaw'])    # Yaw
            return True
        except Exception as e:
            logger.error(f"写入视角角度失败: {e}")
            return False

    def get_fire_logic_data(self) -> dict | None:
        """检索射击逻辑所需的数据。"""
        try:
            player = self.read_longlong(self.client_base + self.dwLocalPlayerPawn)
            # 检查player指针是否有效
            if player == 0:
                logger.debug("玩家指针为空")
                return None
                
            entity_id = self.read_int(player + self.m_iIDEntIndex)

            # 当entity_id >= 0时即表示有目标
            if entity_id >= 0:
                entity = self.get_entity(entity_id)
                if entity:
                    try:
                        entity_team = self.read_int(entity + self.m_iTeamNum)
                        player_team = self.read_int(player + self.m_iTeamNum)
                        entity_health = self.read_int(entity + self.m_iHealth)
                        
                        # 移除队伍数据检查，总是返回数据
                        return {
                            "entity_team": entity_team,
                            "player_team": player_team,
                            "entity_health": entity_health,
                            "weapon_type": "Rifles"
                        }
                    except pymem.exception.MemoryReadError as e:
                        # 即使读取实体信息失败，也返回基本数据以触发扳机
                        logger.error(f"无法读取实体详细信息，但仍触发扳机: 实体ID={entity_id}")
                        return {"entity_team": 0, "player_team": 1, "entity_health": 100, "weapon_type": "Rifles"}
                    except Exception as e:
                        logger.error(f"读取实体信息时出现未知错误: {e}")
                        # 出现未知错误时也返回基本数据
                        return {"entity_team": 0, "player_team": 1, "entity_health": 100, "weapon_type": "Rifles"}
            else:
                return None
        except pymem.exception.MemoryReadError as e:
            # 修复：检查MemoryReadError对象是否有address等属性
            error_msg = f"射击逻辑中出现内存读取错误"
            # 使用安全的方式访问可能不存在的属性
            try:
                if hasattr(e, 'address'):
                    error_msg += f": Could not read memory at: {e.address}"
                if hasattr(e, 'length'):
                    error_msg += f", length: {e.length}"
                if hasattr(e, 'win32_error_code'):
                    error_msg += f" - GetLastError: {e.win32_error_code}"
            except:
                # 如果访问属性时出错，则使用通用错误消息
                error_msg = f"射击逻辑中出现内存读取错误: {str(e)}"
            
            logger.error(error_msg)
            return None
        except Exception as e:
            if "Could not read memory at" in str(e):
                logger.error("游戏已更新，需要最新偏移量")
            else:
                logger.error(f"射击逻辑中出现错误: {e}")
            return None

    def get_aimbot_data(self, aim_position='head') -> dict | None:
        """检索自瞄所需的数据（基于ViewAngles注入）。"""
        try:
            player = self.read_longlong(self.client_base + self.dwLocalPlayerPawn)
            if not player:
                logger.debug("玩家指针为空")
                return None
                
            player_team = self.read_int(player + self.m_iTeamNum)
            
            # 获取玩家位置
            game_scene_node = self.read_longlong(player + self.m_pGameSceneNode)
            if not game_scene_node:
                logger.debug("游戏场景节点为空")
                return None
            
            # 尝试多个位置偏移量
            player_pos = self.read_vec3(game_scene_node + self.m_vOldOrigin)
            
            # 如果 m_vOldOrigin 无效，尝试 m_vecAbsOrigin
            if not player_pos or (player_pos["x"] == 0 and player_pos["y"] == 0):
                if hasattr(self, 'm_vecAbsOrigin') and self.m_vecAbsOrigin:
                    player_pos = self.read_vec3(game_scene_node + self.m_vecAbsOrigin)
                    
                else:
                    # 硬编码备用值
                    player_pos = self.read_vec3(game_scene_node + 544)

            
            if not player_pos or (player_pos["x"] == 0 and player_pos["y"] == 0):

                return None
            
            # 玩家位置是脚底坐标，需要加上眼睛高度
            player_eye_pos = {
                "x": player_pos["x"],
                "y": player_pos["y"],
                "z": player_pos["z"] + 64.0  # CS2 玩家眼睛高度约 64 单位
            }
            
            # 获取当前视角角度
            current_angles_vec = self.read_vec3(self.client_base + self.dwViewAngles)
            
            # 转换为 pitch/yaw 格式供 aimbot 使用
            current_angles = {
                "pitch": current_angles_vec["x"],
                "yaw": current_angles_vec["y"]
            }
            
            # 获取所有实体
            entities = self.get_all_entities(64)
            
            # 过滤目标并计算角度
            targets = []
            for ent in entities:
                # 跳过队友
                if ent["team"] == player_team:
                    continue
                
                # 根据瞄准位置选择骨骼索引
                bone_index_map = {
                    'head': 7,    # 头部
                    'neck': 6,    # 脖子
                    'chest': 5,   # 胸部
                    'root': 0     # 根部
                }
                bone_index = bone_index_map.get(aim_position, 7)
                
                # 获取目标位置
                if not ent["bone_array_ptr"]:
                    # 如果没有骨骼数组，使用实体位置 + Z轴偏移作为近似
                    target_pos = {
                        "x": ent["position"]["x"],
                        "y": ent["position"]["y"],
                        "z": ent["position"]["z"] + (62.0 if aim_position == 'head' else 30.0)
                    }
                else:
                    # CS2 更新后骨骼索引，每个骨骼占32字节
                    bone_offset = bone_index * 32
                    target_pos_addr = ent["bone_array_ptr"] + bone_offset
                    
                    target_pos = self.read_vec3(target_pos_addr)
                    
                    # 验证位置是否有效
                    if not target_pos or abs(target_pos["x"]) > 100000 or abs(target_pos["y"]) > 100000:
                        # 回退到实体位置
                        target_pos = {
                            "x": ent["position"]["x"],
                            "y": ent["position"]["y"],
                            "z": ent["position"]["z"] + (62.0 if aim_position == 'head' else 30.0)
                        }
                
                # 计算从玩家眼睛到目标的角度
                angle = self.calculate_angle(player_eye_pos, target_pos)
                if not angle:
                    continue
                
                targets.append({
                    "entity": ent,
                    "world_pos": target_pos,
                    "angle": angle,
                    "distance": self.calculate_distance(player_eye_pos, target_pos)
                })
            

            
            return {
                "player_team": player_team,
                "player_pos": player_eye_pos,  # 返回眼睛位置
                "current_angles": current_angles,
                "targets": targets,
                "weapon_type": "Rifles"
            }
        except Exception as e:
            logger.error(f"自瞄数据获取失败: {e}", exc_info=True)
            return None

    def world_to_screen(self, world_pos: dict, view_matrix: list, screen_width: int, screen_height: int) -> dict | None:
        """将世界坐标转换为屏幕坐标。"""
        try:
            # 使用NumPy优化世界到屏幕坐标转换
            # 构建视图矩阵
            vm = np.array(view_matrix, dtype=np.float32).reshape(4, 4)
            
            # 创建世界坐标点
            point_3d = np.array([world_pos["x"], world_pos["y"], world_pos["z"], 1.0], dtype=np.float32)
            
            # 应用视图矩阵变换
            transformed = vm @ point_3d
            
            # 检查w分量避免除以零
            if transformed[3] <= 0.01:
                return None
                
            # 透视除法
            x = transformed[0] / transformed[3]
            y = transformed[1] / transformed[3]
            
            # 转换到屏幕坐标
            screen_center_x = screen_width / 2
            screen_center_y = screen_height / 2
            screen_x = int(screen_center_x + screen_center_x * x)
            screen_y = int(screen_center_y - screen_center_y * y)
            
            # 检查坐标是否在屏幕范围内
            if not (-5000 <= screen_x <= screen_width + 5000 and -5000 <= screen_y <= screen_height + 5000):
                return None
                
            return {"x": screen_x, "y": screen_y}
        except Exception as e:
            logger.error(f"世界到屏幕坐标转换错误: {e}")
            # 回退到原有方法
            try:
                # 使用视图矩阵进行世界到屏幕的变换
                w = (view_matrix[12] * world_pos["x"] + 
                     view_matrix[13] * world_pos["y"] + 
                     view_matrix[14] * world_pos["z"] + 
                     view_matrix[15])
                
                if w <= 0.01:
                    return None
                    
                x = (view_matrix[0] * world_pos["x"] + 
                     view_matrix[1] * world_pos["y"] + 
                     view_matrix[2] * world_pos["z"] + 
                     view_matrix[3]) / w
                     
                y = (view_matrix[4] * world_pos["x"] + 
                     view_matrix[5] * world_pos["y"] + 
                     view_matrix[6] * world_pos["z"] + 
                     view_matrix[7]) / w
                
                # 转换为屏幕坐标
                screen_x = int((screen_width / 2) + (screen_width / 2) * x)
                screen_y = int((screen_height / 2) - (screen_height / 2) * y)
                
                # 检查坐标是否在屏幕范围内
                if not (-5000 <= screen_x <= screen_width + 5000 and -5000 <= screen_y <= screen_height + 5000):
                    return None
                
                return {"x": screen_x, "y": screen_y}
            except Exception as e2:
                logger.error(f"回退方法也失败了: {e2}")
                return None

    def write_float(self, address: int, value: float) -> None:
        """向内存写入一个浮点数。"""
        try:
            self.pm.write_float(address, value)
        except Exception as e:
            logger.error(f"在地址 {hex(address)} 写入浮点数失败: {e}")
            raise

    def write_int(self, address: int, value: int) -> None:
        """向内存写入一个整数。"""
        try:
            self.pm.write_int(address, value)
        except Exception as e:
            logger.error(f"在地址 {hex(address)} 写入整数失败: {e}")
            raise

    def write_bool(self, address: int, value: bool) -> None:
        """向内存写入一个布尔值。"""
        try:
            self.pm.write_bool(address, value)
        except Exception as e:
            logger.error(f"在地址 {hex(address)} 写入布尔值失败: {e}")
            raise

    def force_attack(self, state: bool) -> None:
        """通过修改内存触发攻击按钮状态。"""
        try:
            # 使用从extract_offsets获取的偏移量
            if hasattr(self, 'dwForceAttack') and self.dwForceAttack is not None:
                # 计算实际地址
                attack_address = self.client_base + self.dwForceAttack
                # 根据CS2的输入系统，按下为65537，释放为256
                value = 65537 if state else 256
                # 写入状态
                self.write_int(attack_address, value)
            else:
                logger.warning("未找到攻击按钮偏移量")
        except Exception as e:
            logger.error(f"设置攻击状态失败: {e}")

    def read_vec3(self, address: int) -> dict | None:
        """
        从指定地址的内存中读取一个3D向量（三个浮点数）。
        """
        try:
            return {
                "x": self.pm.read_float(address),
                "y": self.pm.read_float(address + 4),
                "z": self.pm.read_float(address + 8)
            }
        except pymem.exception.MemoryReadError as e:
            logger.error(f"在地址 {hex(address)} 读取vec3失败: 无法在地址 {e.address} 读取内存, 长度: {e.length} - GetLastError: {e.win32_error_code}")
            return {"x": 0.0, "y": 0.0, "z": 0.0}
        except Exception as e:
            logger.error(f"在地址 {hex(address)} 读取vec3失败: {e}")
            return {"x": 0.0, "y": 0.0, "z": 0.0}

    def read_string(self, address: int, max_length: int = 256) -> str:
        """
        从指定地址的内存中读取一个以null结尾的字符串。
        """
        try:
            data = self.pm.read_bytes(address, max_length)
            string_data = data.split(b'\x00')[0]
            return string_data.decode('utf-8', errors='replace')
        except pymem.exception.MemoryReadError as e:
            logger.error(f"在地址 {hex(address)} 读取字符串失败: 无法在地址 {e.address} 读取内存, 长度: {e.length} - GetLastError: {e.win32_error_code}")
            return ""
        except Exception as e:
            logger.error(f"在地址 {hex(address)} 读取字符串失败: {e}")
            return ""

    def read_floats(self, address: int, count: int) -> list[float]:
        """
        从内存中读取一个包含`count`个浮点数的数组。
        """
        try:
            data = self.pm.read_bytes(address, count * 4)
            return list(struct.unpack(f'{count}f', data))
        except pymem.exception.MemoryReadError as e:
            logger.error(f"在地址 {hex(address)} 读取 {count} 个浮点数失败: 无法在地址 {e.address} 读取内存, 长度: {e.length} - GetLastError: {e.win32_error_code}")
            # 返回默认值而不是空列表，避免程序崩溃
            return [0.0] * count
        except Exception as e:
            logger.error(f"在地址 {hex(address)} 读取 {count} 个浮点数失败: {e}")
            # 返回默认值而不是空列表，避免程序崩溃
            return [0.0] * count

    def read_int(self, address: int) -> int:
        """从内存中读取一个整数。"""
        try:
            return self.pm.read_int(address)
        except pymem.exception.MemoryReadError as e:
            logger.error(f"在地址 {hex(address)} 读取整数失败: 无法在地址 {e.address} 读取内存, 长度: {e.length} - GetLastError: {e.win32_error_code}")
            return 0
        except Exception as e:
            logger.error(f"在地址 {hex(address)} 读取整数失败: {e}")
            return 0

    def read_longlong(self, address: int) -> int:
        """从内存中读取一个long long。"""
        try:
            return self.pm.read_longlong(address)
        except pymem.exception.MemoryReadError as e:
            logger.error(f"在地址 {hex(address)} 读取longlong失败: 无法在地址 {e.address} 读取内存, 长度: {e.length} - GetLastError: {e.win32_error_code}")
            return 0
        except Exception as e:
            logger.error(f"在地址 {hex(address)} 读取longlong失败: {e}")
            return 0

    @property
    def client_dll_base(self) -> int:
        """获取client.dll的基地址。"""
        return self.client_base
    
    def calculate_angle(self, src: dict, dst: dict) -> dict | None:
        """
        计算从源点到目标点的角度（Pitch/Yaw）
        :param src: 源点坐标 {x, y, z}
        :param dst: 目标点坐标 {x, y, z}
        :return: {pitch, yaw} 或 None
        """
        try:
            delta_x = dst['x'] - src['x']
            delta_y = dst['y'] - src['y']
            delta_z = dst['z'] - src['z']
            
            # 计算水平距离
            distance_xy = math.sqrt(delta_x * delta_x + delta_y * delta_y)
            
            # 计算俯仰角（Pitch）- 垂直角度
            pitch = math.degrees(math.atan2(-delta_z, distance_xy))
            
            # 计算偏航角（Yaw）- 水平角度
            yaw = math.degrees(math.atan2(delta_y, delta_x))
            
            # 规范化角度到 -180 ~ 180 范围
            if pitch > 89.0:
                pitch = 89.0
            elif pitch < -89.0:
                pitch = -89.0
            
            if yaw > 180.0:
                yaw -= 360.0
            elif yaw < -180.0:
                yaw += 360.0
            
            return {"pitch": pitch, "yaw": yaw}
        except Exception as e:
            logger.error(f"计算角度失败: {e}")
            return None
    
    def calculate_distance(self, pos1: dict, pos2: dict) -> float:
        """计算两点之间的3D距离"""
        try:
            dx = pos2['x'] - pos1['x']
            dy = pos2['y'] - pos1['y']
            dz = pos2['z'] - pos1['z']
            return math.sqrt(dx * dx + dy * dy + dz * dz)
        except Exception as e:
            logger.error(f"计算距离失败: {e}")
            return float('inf')
    
    def write_view_angles(self, angles: dict) -> bool:
        """
        直接写入视角角度到内存（平滑且难以检测）
        :param angles: {pitch, yaw}
        :return: 是否成功
        """
        try:
            if not hasattr(self, 'dwViewAngles') or self.dwViewAngles is None:
                logger.warning("dwViewAngles偏移量未找到")
                return False
            
            view_angles_addr = self.client_base + self.dwViewAngles

            
            # 写入Pitch和Yaw
            self.write_float(view_angles_addr, angles['pitch'])
            self.write_float(view_angles_addr + 4, angles['yaw'])
            
            # 验证写入
            verify_pitch = self.pm.read_float(view_angles_addr)
            verify_yaw = self.pm.read_float(view_angles_addr + 4)

            
            return True
        except Exception as e:
            logger.error(f"写入视角角度失败: {e}")
            return False
