import os
import psutil
import sys
import pygetwindow as gw
import orjson
import requests
import urllib3
# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from pathlib import Path

class Utility:
    @staticmethod
    def download_offsets():
        """
        从GitHub下载偏移量文件到Offsets目录
        """
        # 延迟导入 Logger 以避免循环导入
        from classes.logger import Logger
        logger = Logger.get_logger()
        
        # 确保Offsets目录存在
        offsets_dir = Path("CS2-external-cheating/Offsets")
        offsets_dir.mkdir(parents=True, exist_ok=True)
        
        # 定义需要下载的文件
        files_to_download = {
            "offsets.json": "https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json",
            "client_dll.json": "https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json",
            "buttons.json": "https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/buttons.json"
        }
        
        success = True
        for filename, url in files_to_download.items():
            try:
                logger.info(f"正在下载 {filename}...")
                # 添加超时和SSL验证参数
                response = requests.get(url, timeout=30, verify=False)
                response.raise_for_status()
                
                file_path = offsets_dir / filename
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                    
                logger.info(f"成功下载 {filename}")
            except Exception as e:
                logger.error(f"下载 {filename} 失败: {e}")
                success = False
                
        return success

    @staticmethod
    def fetch_offsets():
        """
        根据配置从远程URL或本地文件获取JSON数据。
        - 从CS2-external-cheating/Offsets目录加载偏移量文件
        - 支持从'offsets.json'、'client_dll.json'和'buttons.json'检索数据
        - 如果请求失败或服务器返回非200状态码，则记录错误。
        - 优雅地处理异常，确保没有未处理的错误导致应用程序崩溃。
        """
        # 延迟导入 Logger 以避免循环导入
        from classes.logger import Logger
        logger = Logger.get_logger()
        
        # 从新的Offsets目录加载
        offsets_dir = Path("CS2-external-cheating/Offsets")
        offsets_dir.mkdir(parents=True, exist_ok=True)  # 确保目录存在
        
        # 检查偏移量文件
        offsets_file = offsets_dir / "offsets.json"
        client_file = offsets_dir / "client_dll.json" 
        buttons_file = offsets_dir / "buttons.json"
        
        # 添加偏移量验证标志，确保只验证一次
        if not hasattr(Utility, '_offsets_validated'):
            Utility._offsets_validated = False
            
        # 检查文件是否存在
        if not all(f.exists() for f in [offsets_file, client_file, buttons_file]):
            logger.info("未找到偏移量文件,正在尝试从网络下载...")
            if not Utility.download_offsets():
                logger.error("无法下载偏移量文件")
                return None, None, None
        
        # 再次检查文件是否存在
        if all(f.exists() for f in [offsets_file, client_file, buttons_file]):
            try:
                offset_bytes = offsets_file.read_bytes()
                client_bytes = client_file.read_bytes()
                buttons_bytes = buttons_file.read_bytes()
                
                offset = orjson.loads(offset_bytes)
                client = orjson.loads(client_bytes)
                buttons = orjson.loads(buttons_bytes)
                
                # 通过尝试提取偏移量进行验证
                extracted = Utility.extract_offsets(offset, client, buttons)
                if extracted is not None:
                    # 只在第一次验证时打印日志
                    if not Utility._offsets_validated:
                        logger.info("已加载偏移量")
                        Utility._offsets_validated = True  # 标记偏移量已验证
                    return offset, client, buttons
                else:
                    logger.error("偏移量文件无效：缺少必需的偏移量")
            except (orjson.JSONDecodeError, IOError) as e:
                logger.error(f"加载偏移量文件失败: {e}")
            except Exception as e:
                logger.exception(f"加载偏移量文件时出现意外错误: {e}")
        else:
            missing = [f.name for f in [offsets_file, client_file, buttons_file] if not f.exists()]
            logger.error(f"缺少偏移量文件: {', '.join(missing)}")
        
        logger.error("未找到有效的偏移量")
        return None, None, None

    @staticmethod
    def resource_path(relative_path):
        """返回资源路径，支持正常启动和冻结的.exe。"""
        # 延迟导入以避免循环导入
        from classes.logger import Logger
        logger = Logger.get_logger()
        
        try:
            if hasattr(sys, '_MEIPASS'):
                return os.path.join(sys._MEIPASS, relative_path)
            
            # 获取当前工作目录
            base_path = os.getcwd()
            full_path = os.path.join(base_path, relative_path)
            return full_path
        except Exception as e:
            logger.error(f"获取资源路径失败: {e}")
            return None

    @staticmethod
    def is_game_active():
        """使用 pygetwindow 检查游戏窗口是否处于活动状态。"""
        # 延迟导入以避免循环导入
        from classes.logger import Logger
        logger = Logger.get_logger()
        
        windows = gw.getWindowsWithTitle('Counter-Strike 2')
        return any(window.isActive for window in windows)

    @staticmethod
    def is_game_running():
        """使用 psutil 检查游戏进程是否正在运行。"""
        # 延迟导入以避免循环导入
        from classes.logger import Logger
        logger = Logger.get_logger()
        
        return any(proc.info['name'] == 'cs2.exe' for proc in psutil.process_iter(attrs=['name']))
    
    @staticmethod
    def extract_offsets(offsets: dict, client_data: dict, buttons_data: dict) -> dict | None:
        """加载游戏功能的内存偏移量。"""
        # 延迟导入以避免循环导入
        from classes.logger import Logger
        logger = Logger.get_logger()
        
        try:
            client = offsets.get("client.dll", {})
            buttons = buttons_data.get("client.dll", {})
            classes = client_data.get("client.dll", {}).get("classes", {})

            def get_field(class_name, field_name):
                """递归搜索类及其父类中的字段。"""
                class_info = classes.get(class_name)
                if not class_info:
                    raise KeyError(f"类 '{class_name}' 未找到")

                field = class_info.get("fields", {}).get(field_name)
                if field is not None:
                    return field
                
                parent_class_name = class_info.get("parent")
                if parent_class_name:
                    return get_field(parent_class_name, field_name)
                    
                raise KeyError(f"在 '{class_name}' 或其父类中未找到 '{field_name}'")

            extracted_offsets = {
                "dwEntityList": client.get("dwEntityList"),
                "dwLocalPlayerPawn": client.get("dwLocalPlayerPawn"),
                "dwLocalPlayerController": client.get("dwLocalPlayerController"),
                "dwViewMatrix": client.get("dwViewMatrix"),
                "dwGlowManager": client.get("dwGlowManager"),
                "dwForceJump": buttons.get("jump"),
                "m_Glow": get_field("C_BaseModelEntity", "m_Glow"),
                "m_glowColorOverride": 64,  # 这个值在GlowProperty中是固定的
                "m_bGlowing": 81,  # 这个值在GlowProperty中是固定的
                "m_iHealth": get_field("C_BaseEntity", "m_iHealth"),
                "m_iTeamNum": get_field("C_BaseEntity", "m_iTeamNum"),
                "m_pGameSceneNode": get_field("C_BaseEntity", "m_pGameSceneNode"),
                "m_vOldOrigin": get_field("C_BasePlayerPawn", "m_vOldOrigin"),
                "m_vecAbsOrigin": get_field("CGameSceneNode", "m_vecAbsOrigin"),
                "m_pWeaponServices": get_field("C_BasePlayerPawn", "m_pWeaponServices"),
                "m_iIDEntIndex": get_field("C_CSPlayerPawn", "m_iIDEntIndex"),
                "m_flFlashDuration": get_field("C_CSPlayerPawnBase", "m_flFlashDuration"),
                "m_pClippingWeapon": get_field("C_CSPlayerPawn", "m_pClippingWeapon"),
                "m_hPlayerPawn": get_field("CCSPlayerController", "m_hPlayerPawn"),
                "m_iszPlayerName": get_field("CBasePlayerController", "m_iszPlayerName"),
                "m_hActiveWeapon": get_field("CPlayer_WeaponServices", "m_hActiveWeapon"),
                "m_bDormant": get_field("CGameSceneNode", "m_bDormant"),
                "m_AttributeManager": get_field("C_EconEntity", "m_AttributeManager"),
                "m_Item": get_field("C_AttributeContainer", "m_Item"),
                "m_iItemDefinitionIndex": get_field("C_EconItemView", "m_iItemDefinitionIndex"),
                "m_pBoneArray": 528
            }

            missing_keys = [k for k, v in extracted_offsets.items() if v is None]
            if missing_keys:
                logger.error(f"偏移量初始化错误: 缺少顶级键 {missing_keys}")
                return None

            return extracted_offsets

        except KeyError as e:
            logger.error(f"偏移量初始化错误: 缺少键 {e}")
            return None
        
    @staticmethod
    def reset_offsets_validation():
        """
        重置偏移量验证状态，允许重新验证偏移量。
        """
        Utility._offsets_validated = False
    
    @staticmethod
    def get_color_name_from_hex(hex_color: str) -> str:
        """根据十六进制值获取颜色名称。"""
        # 延迟导入以避免循环导入
        from classes.config_manager import COLOR_CHOICES
        
        for name, hex_code in COLOR_CHOICES.items():
            if hex_code == hex_color:
                return name
        return "Black"
    
    @staticmethod
    def transliterate(text: str) -> str:
        """将给定文本中的西里尔字符转换为拉丁字符。"""
        mapping = {
            'А': 'A',  'а': 'a',
            'Б': 'B',  'б': 'b',
            'В': 'V',  'в': 'v',
            'Г': 'G',  'г': 'g',
            'Д': 'D',  'д': 'd',
            'Е': 'E',  'е': 'e',
            'Ё': 'Yo', 'ё': 'yo',
            'Ж': 'Zh', 'ж': 'zh',
            'З': 'Z',  'з': 'z',
            'И': 'I',  'и': 'i',
            'Й': 'I',  'й': 'i',
            'К': 'K',  'к': 'k',
            'Л': 'L',  'л': 'l',
            'М': 'M',  'м': 'm',
            'Н': 'N',  'н': 'n',
            'О': 'O',  'о': 'o',
            'П': 'P',  'п': 'p',
            'Р': 'R',  'р': 'r',
            'С': 'S',  'с': 's',
            'Т': 'T',  'т': 't',
            'У': 'U',  'у': 'u',
            'Ф': 'F',  'ф': 'f',
            'Х': 'Kh', 'х': 'kh',
            'Ц': 'Ts', 'ц': 'ts',
            'Ч': 'Ch', 'ч': 'ch',
            'Ш': 'Sh', 'ш': 'sh',
            'Щ': 'Shch', 'щ': 'shch',
            'Ъ': '',   'ъ': '',
            'Ы': 'Y',  'ы': 'y',
            'Ь': '',   'ь': '',
            'Э': 'E',  'э': 'e',
            'Ю': 'Yu', 'ю': 'yu',
            'Я': 'Ya', 'я': 'ya'
        }
        return "".join(mapping.get(char, char) for char in text)

    @staticmethod
    def get_vk_code(key: str) -> int:
        """将按键字符串转换为其对应的虚拟键码。"""
        key = key.lower()
        vk_codes = {
            # 鼠标按钮
            "mouse1": 0x01,        # 左鼠标按钮
            "mouse2": 0x02,        # 右鼠标按钮
            "mouse3": 0x04,        # 中鼠标按钮
            "mouse4": 0x05,        # X1鼠标按钮
            "mouse5": 0x06,        # X2鼠标按钮
            # 常用键盘按键
            "space": 0x20,         # 空格键
            "enter": 0x0D,         # 回车键
            "shift": 0x10,         # Shift键
            "ctrl": 0x11,          # Control键
            "alt": 0x12,           # Alt键
            "tab": 0x09,           # Tab键
            "backspace": 0x08,     # 退格键
            "esc": 0x1B,           # Escape键
            # 字母键
            "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45, "f": 0x46,
            "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A, "k": 0x4B, "l": 0x4C,
            "m": 0x4D, "n": 0x4E, "o": 0x4F, "p": 0x50, "q": 0x51, "r": 0x52,
            "s": 0x53, "t": 0x54, "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58,
            "y": 0x59, "z": 0x5A,
            # 数字键
            "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
            "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
            # 功能键
            "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74,
            "f6": 0x75, "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79,
            "f11": 0x7A, "f12": 0x7B
        }
        return vk_codes.get(key, 0x20)  # 默认为空格键