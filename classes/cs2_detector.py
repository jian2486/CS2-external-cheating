import os
import psutil
import winreg
from pathlib import Path
from classes.logger import Logger

# 缓存日志记录器实例
logger = Logger.get_logger()


class CS2Detector:
    """CS2安装目录自动检测器"""
    
    @staticmethod
    def find_cs2_process():
        """查找正在运行的CS2进程"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['name'].lower() == 'cs2.exe':
                        exe_path = proc.info['exe']
                        if exe_path and os.path.exists(exe_path):
                            logger.debug(f"找到CS2进程: {exe_path}")
                            return exe_path
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            logger.error(f"查找CS2进程时出错: {e}")
        return None
    
    @staticmethod
    def get_steam_install_path():
        """从注册表获取Steam安装路径"""
        try:
            # 尝试64位注册表
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                   r"SOFTWARE\WOW6432Node\Valve\Steam") as key:
                    steam_path = winreg.QueryValueEx(key, "InstallPath")[0]
                    if os.path.exists(steam_path):
                        logger.debug(f"从注册表找到Steam路径: {steam_path}")
                        return steam_path
            except FileNotFoundError:
                pass
            
            # 尝试32位注册表
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                   r"SOFTWARE\Valve\Steam") as key:
                    steam_path = winreg.QueryValueEx(key, "InstallPath")[0]
                    if os.path.exists(steam_path):
                        logger.debug(f"从注册表找到Steam路径: {steam_path}")
                        return steam_path
            except FileNotFoundError:
                pass
                
        except Exception as e:
            logger.error(f"读取注册表获取Steam路径失败: {e}")
        
        return None
    
    @staticmethod
    def find_cs2_install_path():
        """自动查找CS2安装目录"""
        # 方法1: 通过正在运行的CS2进程获取
        cs2_exe_path = CS2Detector.find_cs2_process()
        if cs2_exe_path:
            # 从exe路径推导安装目录 (处理\game\bin\win64\cs2.exe结构)
            cs2_exe_path_obj = Path(cs2_exe_path)
            # 向上三级目录: game -> common -> Counter-Strike Global Offensive
            cs2_install_dir = cs2_exe_path_obj.parent.parent.parent.parent
            if cs2_install_dir.name == "Counter-Strike Global Offensive":
                logger.info(f"通过进程找到CS2安装目录: {cs2_install_dir}")
                return str(cs2_install_dir)
        
        # 方法2: 通过Steam路径查找
        steam_path = CS2Detector.get_steam_install_path()
        if steam_path:
            # 检查标准Steam目录
            cs2_common_path = Path(steam_path) / "steamapps" / "common" / "Counter-Strike Global Offensive"
            if cs2_common_path.exists():
                logger.info(f"通过Steam路径找到CS2安装目录: {cs2_common_path}")
                return str(cs2_common_path)
            
            # 检查SteamLibrary目录
            steam_library_path = Path(steam_path) / "steamapps" / "libraryfolders.vdf"
            if steam_library_path.exists():
                library_paths = CS2Detector._parse_steam_libraries(steam_library_path)
                for lib_path in library_paths:
                    cs2_path = Path(lib_path) / "steamapps" / "common" / "Counter-Strike Global Offensive"
                    if cs2_path.exists():
                        logger.info(f"通过SteamLibrary找到CS2安装目录: {cs2_path}")
                        return str(cs2_path)
        
        # 注意：已移除硬编码的默认目录查找方式
        # 系统现在完全依赖进程检测和Steam注册表查找
        
        logger.warning("未能找到CS2安装目录")
        return None
    
    @staticmethod
    def _parse_steam_libraries(library_vdf_path):
        """解析Steam的libraryfolders.vdf文件获取额外的库路径"""
        library_paths = []
        try:
            with open(library_vdf_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 简单的正则匹配路径
                import re
                # 匹配 "path"\t\t"D:\\SteamLibrary" 这样的格式
                path_matches = re.findall(r'"path"\s+"([^"]+)"', content)
                for path in path_matches:
                    if os.path.exists(path):
                        library_paths.append(path)
                        logger.debug(f"发现Steam库路径: {path}")
        except Exception as e:
            logger.error(f"解析Steam库文件失败: {e}")
        
        return library_paths
    
    @staticmethod
    def get_cs2_version_info():
        """获取CS2完整版本信息（日期+时间）"""
        cs2_path = CS2Detector.find_cs2_install_path()
        if not cs2_path:
            return None
        
        steam_inf_path = Path(cs2_path) / "game" / "csgo" / "steam.inf"
        
        if not steam_inf_path.exists():
            logger.warning(f"未找到steam.inf文件: {steam_inf_path}")
            return None
        
        try:
            with open(steam_inf_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            import re
            # 获取版本日期
            date_match = re.search(r'VersionDate=([A-Za-z]+ \d{1,2} \d{4})', content)
            # 获取版本时间
            time_match = re.search(r'VersionTime=(\d{1,2}:\d{2}:\d{2})', content)
            
            if date_match:
                version_date_str = date_match.group(1)
                version_time_str = time_match.group(1) if time_match else "00:00:00"
                
                # 转换为中国日期格式 (YYYY年MM月DD日 HH:MM:SS)
                try:
                    import datetime
                    date_obj = datetime.datetime.strptime(version_date_str, "%b %d %Y")
                    chinese_date = date_obj.strftime("%Y年%m月%d日")
                    full_version_info = f"{chinese_date} {version_time_str}"
                    logger.debug(f"CS2版本信息: {version_date_str} {version_time_str} -> {full_version_info}")
                    return full_version_info
                except ValueError as e:
                    logger.error(f"解析日期失败: {version_date_str}, 错误: {e}")
                    return f"{version_date_str} {version_time_str}" if time_match else version_date_str
            else:
                logger.warning("未在steam.inf中找到VersionDate字段")
                return None
                
        except Exception as e:
            logger.error(f"读取steam.inf文件失败: {e}")
            return None