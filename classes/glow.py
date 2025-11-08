import threading
import time
import struct
from classes.config_manager import ConfigManager
from classes.memory_manager import MemoryManager
from classes.logger import Logger

# 初始化日志记录器，确保一致的日志记录
logger = Logger.get_logger()

class CS2Glow:
    """通过修改游戏内存来管理Counter-Strike 2的发光效果。"""
    
    def __init__(self, memory_manager: MemoryManager) -> None:
        """
        使用共享的MemoryManager实例初始化发光效果。
        """
        self.config = ConfigManager.load_config()
        self.memory_manager = memory_manager
        self.is_running = False
        self.stop_event = threading.Event()
        self.local_team = None

    def load_configuration(self) -> None:
        """加载并应用配置设置。"""
        settings = self.config['Overlay']
        self.enable_glow = settings.get('enable_glow', False)
        self.glow_exclude_dead = settings.get('glow_exclude_dead', True)
        self.glow_teammates = settings.get('glow_teammates', False)
        self.glow_color_hex = settings.get('glow_color_hex', "#FF00FF")
        self.glow_teammate_color_hex = settings.get('glow_teammate_color_hex', "#00FFFF")
        
        # 将十六进制颜色转换为RGBA格式 (0x800000FF)
        # 默认为洋红色，带一定透明度
        if self.glow_color_hex.startswith('#'):
            hex_value = self.glow_color_hex[1:]
            if len(hex_value) == 6:
                r = int(hex_value[0:2], 16)
                g = int(hex_value[2:4], 16)
                b = int(hex_value[4:6], 16)
                # 使用0x80作为alpha值（50%透明度）
                self.glow_color_rgba = (0x80 << 24) | (b << 16) | (g << 8) | r
            else:
                self.glow_color_rgba = 0x800000FF  # 默认洋红色
        else:
            self.glow_color_rgba = 0x800000FF  # 默认洋红色
            
        # 将十六进制队友颜色转换为RGBA格式
        if self.glow_teammate_color_hex.startswith('#'):
            hex_value = self.glow_teammate_color_hex[1:]
            if len(hex_value) == 6:
                r = int(hex_value[0:2], 16)
                g = int(hex_value[2:4], 16)
                b = int(hex_value[4:6], 16)
                # 使用0x80作为alpha值（50%透明度）
                self.glow_teammate_color_rgba = (0x80 << 24) | (b << 16) | (g << 8) | r
            else:
                self.glow_teammate_color_rgba = 0x80FFFF00  # 默认青色
        else:
            self.glow_teammate_color_rgba = 0x80FFFF00  # 默认青色

    def update_config(self, config: dict) -> None:
        """更新配置设置。"""
        self.config = config
        self.load_configuration()
        logger.debug("发光配置已更新")

    def apply_glow_to_entity(self, entity_address: int, is_teammate: bool = False) -> None:
        """对特定实体应用发光效果。"""
        try:
            # 计算Glow属性的偏移量
            # C_BaseModelEntity::m_Glow + CGlowProperty::m_glowColorOverride
            glow_color_offset = self.memory_manager.m_Glow + self.memory_manager.m_glowColorOverride
            # C_BaseModelEntity::m_Glow + CGlowProperty::m_bGlowing
            glow_enabled_offset = self.memory_manager.m_Glow + self.memory_manager.m_bGlowing
            
            # 根据是否为队友选择颜色
            color_rgba = self.glow_teammate_color_rgba if is_teammate else self.glow_color_rgba
            
            # 写入颜色值
            color_bytes = struct.pack("<I", color_rgba)
            self.memory_manager.pm.write_bytes(entity_address + glow_color_offset, color_bytes, 4)
            
            # 启用发光效果
            self.memory_manager.pm.write_bool(entity_address + glow_enabled_offset, True)
            
        except Exception as e:
            logger.error(f"应用发光效果到实体时出错: {e}")

    def process_entities(self, entities=None) -> None:
        """处理所有实体并对敌人应用发光效果。"""
        try:
            # 总是使用独立的处理逻辑
            self._process_entities_original()
        except Exception as e:
            logger.error(f"处理实体时出错: {e}")

    def _process_entities_from_list(self, entities) -> None:
        """使用ESP提供的实体列表处理发光效果"""
        try:
            for entity in entities:
                # 检查实体是否有效
                if not hasattr(entity, 'pawn_ptr') or not entity.pawn_ptr:
                    continue
                
                # 检查实体是否为尸体（生命值为0）
                entity_health = entity.health
                if self.glow_exclude_dead and entity_health <= 0:
                    continue
                
                # 判断是否为队友
                is_teammate = self.local_team is not None and entity.team == self.local_team
                
                # 如果是敌人且（不排除尸体或实体仍有生命值），则应用发光效果
                if not is_teammate and (not self.glow_exclude_dead or entity_health > 0):
                    self.apply_glow_to_entity(entity.pawn_ptr, False)
                
                # 如果启用了队友发光且是队友且（不排除尸体或实体仍有生命值），则应用发光效果
                elif self.glow_teammates and is_teammate and (not self.glow_exclude_dead or entity_health > 0):
                    self.apply_glow_to_entity(entity.pawn_ptr, True)
                    
        except Exception as e:
            logger.error(f"从列表处理实体时出错: {e}")

    def _process_entities_original(self) -> None:
        """原始的实体处理逻辑"""
        try:
            # 获取本地玩家
            local_player = self.memory_manager.read_longlong(
                self.memory_manager.client_dll_base + self.memory_manager.dwLocalPlayerPawn)
            
            if not local_player:
                return
            
            # 获取本地玩家队伍
            local_team = self.memory_manager.read_int(local_player + self.memory_manager.m_iTeamNum)
            
            # 获取实体列表
            entity_list = self.memory_manager.read_longlong(
                self.memory_manager.client_dll_base + self.memory_manager.dwEntityList)
            
            if not entity_list:
                return
            
            # 获取列表入口
            entry = self.memory_manager.read_longlong(entity_list + 0x10)
            
            if not entry:
                return
            
            # 遍历所有实体
            for i in range(64):
                try:
                    # 获取控制器
                    controller = self.memory_manager.read_longlong(entry + i * self.memory_manager.ENTITY_ENTRY_SIZE)
                    
                    if not controller:
                        continue
                    
                    # 获取玩家pawn句柄
                    player_pawn_handle = self.memory_manager.read_longlong(
                        controller + self.memory_manager.m_hPlayerPawn)
                    
                    if not player_pawn_handle:
                        continue
                    
                    # 获取实体列表条目
                    entry_2 = self.memory_manager.read_longlong(
                        entity_list + 0x8 * ((player_pawn_handle & 0x7FFF) >> 9) + 0x10)
                    
                    if not entry_2:
                        continue
                    
                    # 获取当前实体
                    current_entity = self.memory_manager.read_longlong(
                        entry_2 + self.memory_manager.ENTITY_ENTRY_SIZE * (player_pawn_handle & 0x1FF))
                    
                    if not current_entity:
                        continue
                    
                    # 获取实体队伍
                    entity_team = self.memory_manager.read_int(current_entity + self.memory_manager.m_iTeamNum)
                    
                    # 检查实体是否为尸体（生命值为0）
                    entity_health = 0
                    if self.glow_exclude_dead:
                        entity_health = self.memory_manager.read_int(current_entity + self.memory_manager.m_iHealth)
                    
                    # 如果是敌人且（不排除尸体或实体仍有生命值），则应用发光效果
                    if entity_team != local_team and (not self.glow_exclude_dead or entity_health > 0):
                        self.apply_glow_to_entity(current_entity, False)
                    
                    # 如果启用了队友发光且是队友且不是本地玩家且（不排除尸体或实体仍有生命值），则应用发光效果
                    elif self.glow_teammates and entity_team == local_team and current_entity != local_player and (not self.glow_exclude_dead or entity_health > 0):
                        self.apply_glow_to_entity(current_entity, True)
                        
                except Exception as e:
                    # 安全地处理异常，避免访问可能不存在的属性
                    error_msg = f"处理实体{i}时出错: {e}"
                    try:
                        # 尝试安全访问MemoryReadError的属性
                        if hasattr(e, 'address'):
                            error_msg += f" 无法在地址 {e.address} 读取内存"
                        if hasattr(e, 'length'):
                            error_msg += f", 长度: {e.length}"
                        if hasattr(e, 'win32_error_code'):
                            error_msg += f" - GetLastError: {e.win32_error_code}"
                    except:
                        # 如果访问属性时出错，就使用基本错误消息
                        pass
                    
                    logger.debug(error_msg)
                    continue
                    
        except Exception as e:
            # 安全地处理异常，避免访问可能不存在的属性
            error_msg = f"处理实体时出错: {e}"
            try:
                # 尝试安全访问MemoryReadError的属性
                if hasattr(e, 'address'):
                    error_msg += f" 无法在地址 {e.address} 读取内存"
                if hasattr(e, 'length'):
                    error_msg += f", 长度: {e.length}"
                if hasattr(e, 'win32_error_code'):
                    error_msg += f" - GetLastError: {e.win32_error_code}"
            except:
                # 如果访问属性时出错，就使用基本错误消息
                pass
            
            logger.error(error_msg)

    def start(self) -> None:
        """启动发光效果。"""
        self.is_running = True
        self.stop_event.clear()
        self.load_configuration()
        
        # 运行独立的处理循环
        while not self.stop_event.is_set():
            try:
                # 实时重新加载配置以支持热更新
                current_config = ConfigManager.load_config()
                if current_config != self.config:
                    self.config = current_config
                    self.load_configuration()
                    logger.debug("发光配置已重新加载")
                
                # 如果启用了发光效果，则处理实体
                if self.enable_glow:
                    self.process_entities()
                
                # 短暂休眠以避免过度占用CPU
                time.sleep(0.01)  # 10ms延迟
                
            except Exception as e:
                logger.error(f"发光循环中出错: {e}")
                break
                
        self.is_running = False
        logger.debug("发光效果已停止")

    def stop(self) -> None:
        """停止发光效果。"""
        self.stop_event.set()
        self.is_running = False
        logger.debug("发光效果已停止")