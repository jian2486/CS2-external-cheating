import ctypes
import threading
import time
from classes.logger import Logger
from ctypes import wintypes

logger = Logger.get_logger()

class DisplayAffinityManager:
    """窗口显示亲和力管理器，用于控制窗口的防截屏设置"""
    
    def __init__(self):
        """初始化显示亲和力管理器"""
        self.WDA_NONE = 0x00000000
        self.WDA_MONITOR = 0x00000001
        self.WDA_EXCLUDEFROMCAPTURE = 0x00000011
        
        # 初始化user32.dll中的函数
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        
        # 设置函数参数和返回类型
        self._setup_function_signatures()
        
        # 线程控制变量
        self.affinity_thread = None
        self.affinity_thread_running = False
        self.target_hwnd = None
        self.target_affinity = self.WDA_NONE
        
        # 防截屏功能开关状态
        self.anti_screenshot_enabled = False
        
        # 获取当前进程ID
        self.current_process_id = ctypes.windll.kernel32.GetCurrentProcessId()
        
        # 防止重复应用的标志
        self.last_applied_affinity = None
        
    def _setup_function_signatures(self):
        """设置Windows API函数的参数和返回类型"""
        # SetWindowDisplayAffinity
        self.user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
        self.user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
        
        # GetWindowDisplayAffinity
        self.user32.GetWindowDisplayAffinity.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user32.GetWindowDisplayAffinity.restype = wintypes.BOOL
        
        # GetCurrentProcessId
        self.kernel32.GetCurrentProcessId.argtypes = []
        self.kernel32.GetCurrentProcessId.restype = wintypes.DWORD
        
        # GetWindowThreadProcessId
        self.user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        
        # FindWindowEx
        self.user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
        self.user32.FindWindowExW.restype = wintypes.HWND
        
        # IsWindowVisible
        self.user32.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user32.IsWindowVisible.restype = wintypes.BOOL
        
        # GetWindowTextW
        self.user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetWindowTextW.restype = ctypes.c_int
        
    def set_window_affinity(self, hwnd, affinity):
        """
        设置窗口的显示亲和力
        
        Args:
            hwnd: 窗口句柄
            affinity: 亲和力值 (WDA_NONE, WDA_MONITOR, WDA_EXCLUDEFROMCAPTURE)
            
        Returns:
            bool: 设置是否成功
        """
        try:
            result = self.user32.SetWindowDisplayAffinity(hwnd, affinity)
            if result:
                affinity_name = {
                    self.WDA_NONE: "WDA_NONE",
                    self.WDA_MONITOR: "WDA_MONITOR", 
                    self.WDA_EXCLUDEFROMCAPTURE: "WDA_EXCLUDEFROMCAPTURE"
                }.get(affinity, "UNKNOWN")
                logger.debug(f"成功设置窗口 {hwnd} 的显示亲和力为 {affinity_name}")
                return True
            else:
                error_code = ctypes.windll.kernel32.GetLastError()
                logger.warning(f"设置窗口 {hwnd} 的显示亲和力失败，错误码: {error_code}")
                return False
        except Exception as e:
            logger.error(f"设置窗口显示亲和力时发生异常: {e}")
            return False
            
    def get_window_affinity(self, hwnd):
        """
        获取窗口的显示亲和力
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            int: 当前的亲和力值，失败时返回-1
        """
        try:
            affinity = wintypes.DWORD()
            result = self.user32.GetWindowDisplayAffinity(hwnd, ctypes.byref(affinity))
            if result:
                return affinity.value
            else:
                error_code = ctypes.windll.kernel32.GetLastError()
                logger.warning(f"获取窗口 {hwnd} 的显示亲和力失败，错误码: {error_code}")
                return -1
        except Exception as e:
            logger.error(f"获取窗口显示亲和力时发生异常: {e}")
            return -1
            
    def apply_affinity_to_process_windows(self, process_id, affinity):
        """
        为指定进程的所有窗口应用显示亲和力
        
        Args:
            process_id: 进程ID
            affinity: 要应用的亲和力值
            
        Returns:
            int: 成功设置的窗口数量
        """
        # 如果防截屏功能未启用且要设置的不是WDA_NONE，则不执行操作
        if not self.anti_screenshot_enabled and affinity != self.WDA_NONE:
            return 0
            
        # 避免重复应用相同的亲和力设置
        if self.last_applied_affinity == affinity:
            return 0
            
        self.last_applied_affinity = affinity
            
        try:
            modified_count = 0
            hwnd = self.user32.FindWindowExW(None, None, None, None)
            
            while hwnd:
                # 获取窗口所属的进程ID
                window_pid = wintypes.DWORD()
                self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
                
                # 检查是否是目标进程且窗口可见
                if window_pid.value == process_id and self.user32.IsWindowVisible(hwnd):
                    # 获取窗口标题
                    title_buffer = ctypes.create_unicode_buffer(256)
                    self.user32.GetWindowTextW(hwnd, title_buffer, 256)
                    title = title_buffer.value or "<无标题>"
                    
                    # 应用显示亲和力
                    if self.set_window_affinity(hwnd, affinity):
                        modified_count += 1
                        logger.debug(f"为窗口 '{title}' (句柄: {hwnd}) 设置显示亲和力")
                    else:
                        logger.warning(f"无法为窗口 '{title}' (句柄: {hwnd}) 设置显示亲和力")
                        
                # 查找下一个窗口
                hwnd = self.user32.FindWindowExW(None, hwnd, None, None)
                
            if modified_count > 0:
                logger.info(f"为进程 {process_id} 的 {modified_count} 个窗口设置显示亲和力")
            return modified_count
            
        except Exception as e:
            logger.error(f"为进程窗口应用显示亲和力时发生异常: {e}")
            return 0
            
    def _affinity_worker(self):
        """反截屏管理线程的工作函数"""
        while self.affinity_thread_running:
            try:
                # 只有在防截屏功能启用时才执行操作
                if self.anti_screenshot_enabled:
                    if self.target_hwnd and self.target_affinity is not None:
                        # 为特定窗口设置亲和力
                        self.set_window_affinity(self.target_hwnd, self.target_affinity)
                        # 清除目标，避免重复设置
                        self.clear_target_window_affinity()
                    elif self.target_affinity is not None:
                        # 为当前进程的所有窗口设置亲和力
                        self.apply_affinity_to_process_windows(self.current_process_id, self.target_affinity)
                        # 清除目标亲和力值以避免重复应用
                        self.target_affinity = None
                        
                # 线程休眠一段时间以避免过度占用CPU
                time.sleep(2.0)
                
            except Exception as e:
                logger.error(f"反截屏管理线程发生异常: {e}")
                time.sleep(1)  # 出错时等待更长时间
        
    def start_affinity_thread(self):
        """启动显示亲和力管理线程"""
        if not self.affinity_thread or not self.affinity_thread.is_alive():
            self.affinity_thread_running = True
            self.affinity_thread = threading.Thread(target=self._affinity_worker, daemon=True)
            self.affinity_thread.start()
            logger.info("已启动反截屏管理线程")

    def stop_affinity_thread(self):
        """停止反截屏管理线程"""
        self.affinity_thread_running = False
        if self.affinity_thread and self.affinity_thread.is_alive():
            self.affinity_thread.join(timeout=2.0)
            logger.info("已停止反截屏管理线程")
            
    def set_target_window_affinity(self, hwnd, affinity):
        """
        设置要管理的目标窗口和亲和力值
        
        Args:
            hwnd: 目标窗口句柄
            affinity: 要设置的亲和力值
        """
        # 只有在反截屏功能启用时才设置目标
        if self.anti_screenshot_enabled:
            self.target_hwnd = hwnd
            self.target_affinity = affinity
        
    def clear_target_window_affinity(self):
        """清除目标窗口设置"""
        self.target_hwnd = None
        self.target_affinity = None
        
    def set_anti_screenshot_enabled(self, enabled):
        """
        设置防截屏功能开关状态
        
        Args:
            enabled: 是否启用防截屏功能
        """
        # 只有在状态真正改变时才进行操作
        if self.anti_screenshot_enabled != enabled:
            self.anti_screenshot_enabled = enabled
            # 确定要应用的亲和力值
            affinity = self.WDA_EXCLUDEFROMCAPTURE if enabled else self.WDA_NONE
            # 立即应用一次
            self.apply_affinity_to_process_windows(self.current_process_id, affinity)
            logger.info(f"防截屏功能已{'启用' if enabled else '禁用'}")
            
            # 重置last_applied_affinity以便下次可以再次应用
            if not enabled:
                self.last_applied_affinity = None