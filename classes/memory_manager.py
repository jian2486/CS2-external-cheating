import pymem
import pymem.process
import struct
import numpy as np
from classes.logger import Logger
from classes.utility import Utility

# 初始化日志记录器以保持一致的日志记录
logger = Logger.get_logger()

class MemoryManager:
    ENTITY_ENTRY_SIZE = 112

    def __init__(self, offsets: dict, client_data: dict, buttons_data: dict) -> None:
        """使用偏移量和客户端数据初始化MemoryManager。"""
        self.offsets = offsets
        self.client_data = client_data
        self.buttons_data = buttons_data
        
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
            self.dwGlowManager = extracted["dwGlowManager"]
            self.m_Glow = extracted["m_Glow"]
            self.m_glowColorOverride = extracted["m_glowColorOverride"]
            self.m_bGlowing = extracted["m_bGlowing"]
            self.m_iHealth = extracted["m_iHealth"]
            self.m_iTeamNum = extracted["m_iTeamNum"]
            self.m_iIDEntIndex = extracted["m_iIDEntIndex"]
            self.m_iszPlayerName = extracted["m_iszPlayerName"]
            self.m_vOldOrigin = extracted["m_vOldOrigin"]
            self.m_pGameSceneNode = extracted["m_pGameSceneNode"]
            self.m_bDormant = extracted["m_bDormant"]
            self.m_hPlayerPawn = extracted["m_hPlayerPawn"]
            self.m_flFlashDuration = extracted["m_flFlashDuration"]
            self.m_pBoneArray = extracted["m_pBoneArray"]
            self.m_pClippingWeapon = extracted["m_pClippingWeapon"]
            self.m_AttributeManager = extracted["m_AttributeManager"]
            self.m_iItemDefinitionIndex = extracted["m_iItemDefinitionIndex"]
            self.m_Item = extracted["m_Item"]
            self.m_pWeaponServices = extracted["m_pWeaponServices"]
            self.m_hActiveWeapon = extracted["m_hActiveWeapon"]
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
                        weapon_type = self.get_weapon_type()
                        
                        # 移除队伍数据检查，总是返回数据
                        return {
                            "entity_team": entity_team,
                            "player_team": player_team,
                            "entity_health": entity_health,
                            "weapon_type": weapon_type
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

    def get_aimbot_data(self) -> dict | None:
        """检索自瞄所需的数据。"""
        try:
            player = self.read_longlong(self.client_base + self.dwLocalPlayerPawn)
            if not player:
                return None
                
            player_team = self.read_int(player + self.m_iTeamNum)
            
            # 获取实际屏幕尺寸
            import tkinter
            root = tkinter.Tk()
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            root.destroy()
            
            # 获取用于世界到屏幕转换的视图矩阵
            view_matrix = self.read_floats(self.client_base + self.dwViewMatrix, 16)
            
            # 检查view_matrix是否有效
            if not view_matrix or all(v == 0.0 for v in view_matrix):
                logger.warning("视图矩阵无效，可能是由于偏移量过期")
                return None
            
            # 收集目标
            targets = []
            for i in range(64):  # Check up to 64 entities
                entity = self.get_entity(i)
                if not entity:
                    continue
                    
                # 跳过休眠实体
                dormant = self.read_int(entity + self.m_bDormant)
                if dormant:
                    continue
                    
                entity_health = self.read_int(entity + self.m_iHealth)
                if entity_health <= 0:
                    continue
                    
                entity_team = self.read_int(entity + self.m_iTeamNum)
                
                # 获取实体位置（头部骨骼位置）
                game_scene_node = self.read_longlong(entity + self.m_pGameSceneNode)
                if not game_scene_node:
                    continue
                    
                bone_array = self.read_longlong(game_scene_node + self.m_pBoneArray)
                if not bone_array:
                    continue
                    
                # 获取头部骨骼位置（通常是第6个骨骼）
                head_pos = self.read_vec3(bone_array + 6 * 32)  # 6th bone (head)
                
                # 验证头部位置
                if head_pos["x"] == 0 and head_pos["y"] == 0 and head_pos["z"] == 0:
                    continue
                
                # 将世界位置转换为屏幕位置
                screen_pos = self.world_to_screen(head_pos, view_matrix, screen_width, screen_height)
                if screen_pos:
                    targets.append({
                        "x": screen_pos["x"],
                        "y": screen_pos["y"],
                        "team": entity_team,
                        "health": entity_health
                    })
            
            weapon_type = self.get_weapon_type()
            
            return {
                "player_team": player_team,
                "targets": targets,
                "weapon_type": weapon_type,
                "screen_width": screen_width,
                "screen_height": screen_height
            }
        except pymem.exception.MemoryReadError as e:
            logger.error(f"自瞄逻辑中出现内存读取错误: 无法在地址 {e.address} 读取内存, 长度: {e.length} - GetLastError: {e.win32_error_code}")
            return None
        except Exception as e:
            if "Could not read memory at" in str(e):
                logger.error("需要新的偏移量")
            else:
                logger.error(f"自瞄逻辑中出现错误: {e}")
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

    def get_weapon_type(self) -> str:
        """获取当前装备武器的类型。"""
        try:
            player = self.read_longlong(self.client_base + self.dwLocalPlayerPawn)
            if not player: return "Rifles"

            weapon_services_ptr = self.read_longlong(player + self.m_pWeaponServices)
            if not weapon_services_ptr: return "Rifles"

            weapon_handle = self.read_longlong(weapon_services_ptr + self.m_hActiveWeapon)
            if not weapon_handle: return "Rifles"

            weapon_id = weapon_handle & 0xFFFF
            list_entry = self.read_longlong(self.ent_list + 8 * ((weapon_id & 0x7FFF) >> 9) + 16)
            if not list_entry: return "Rifles"

            weapon_entity_ptr = self.read_longlong(list_entry + 112 * (weapon_id & 0x1FF))
            if not weapon_entity_ptr: return "Rifles"

            attribute_manager_ptr = self.read_longlong(weapon_entity_ptr + self.m_AttributeManager)
            if not attribute_manager_ptr: return "Rifles"

            item_ptr = self.read_longlong(attribute_manager_ptr + self.m_Item)
            if not item_ptr: return "Rifles"

            item_id = self.read_int(item_ptr + self.m_iItemDefinitionIndex)

            weapon_map = {
                1: "Pistols", 2: "Pistols", 3: "Pistols", 4: "Pistols", 30: "Pistols", 32: "Pistols", 36: "Pistols", 61: "Pistols", 63: "Pistols", 64: "Pistols",
                7: "Rifles", 8: "Rifles", 10: "Rifles", 13: "Rifles", 16: "Rifles", 39: "Rifles", 60: "Rifles",
                9: "Snipers", 11: "Snipers", 38: "Snipers", 40: "Snipers",
                17: "SMGs", 19: "SMGs", 23: "SMGs", 24: "SMGs", 26: "SMGs", 33: "SMGs", 34: "SMGs",
                14: "Heavy", 25: "Heavy", 27: "Heavy", 28: "Heavy", 35: "Heavy"
            }
            return weapon_map.get(item_id, "Rifles")
        except Exception as e:
            # logger.error(f"获取武器类型时出错: {e}")
            return "Rifles"
        
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
            # 获取按钮偏移量
            if hasattr(self, 'buttons_data') and self.buttons_data:
                # 查找"attack"按钮的偏移量
                client_buttons = self.buttons_data.get("client.dll", {})
                attack_offset = client_buttons.get("attack")
                
                if attack_offset is not None:
                    # 计算实际地址
                    attack_address = self.client_base + attack_offset
                    # 写入状态
                    self.write_int(attack_address, 1 if state else 0)
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
