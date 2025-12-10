import os
import threading
import platform
import customtkinter as ctk
from tkinter import messagebox
import keyboard  # 添加键盘库导入
from PIL import Image, ImageTk
from pathlib import Path

# Windows系统防截屏功能的特定导入
if platform.system() == "Windows":
    import ctypes
from classes.utility import Utility
from classes.trigger_bot import CS2TriggerBot
from classes.aimbot import CS2Aimbot
from classes.esp import CS2Overlay
from classes.esp_opengl import CS2OverlayOpenGL
from classes.esp_vulkan import CS2OverlayVulkan
from classes.bunnyhop import CS2Bunnyhop
from classes.noflash import CS2NoFlash
from classes.glow import CS2Glow
from classes.config_manager import ConfigManager, COLOR_CHOICES
from classes.file_watcher import ConfigFileChangeHandler
from classes.logger import Logger
from classes.memory_manager import MemoryManager

from gui.home_tab import populate_dashboard
from gui.general_settings_tab import populate_general_settings
from gui.trigger_settings_tab import populate_trigger_settings
from gui.aimbot_settings_tab import populate_aimbot_settings
from gui.overlay_settings_tab import populate_overlay_settings
from gui.additional_settings_tab import populate_additional_settings
from gui.visual_settings_tab import populate_visual_settings
from gui.movement_settings_tab import populate_movement_settings
from gui.font_manager import *
from classes.display_affinity_manager import DisplayAffinityManager

# 缓存日志记录器实例，以便在整个应用程序中保持一致的日志记录
logger = Logger.get_logger()

class MainWindow:
    def __init__(self):
        """初始化主应用程序窗口并设置UI组件"""
        # 初始化线程、观察器和日志计时器为None，直到设置完成
        self.trigger_thread = None
        self.overlay_thread = None
        self.bunnyhop_thread = None
        self.noflash_thread = None
        self.observer = None
        # 添加清理标志，防止重复清理
        self.cleaned_up = False

        # 配置CustomTkinter使用现代深色主题
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # 获取偏移量和客户端数据
        self.offsets, self.client_data, self.buttons_data = self.fetch_offsets_or_warn()

        # 创建单个MemoryManager实例
        self.memory_manager = MemoryManager(self.offsets, self.client_data, self.buttons_data)

        # 初始化配置
        self.config = ConfigManager.load_config()

        # 初始化功能实例
        self.initialize_features()
        
        # 初始化显示亲和力管理器
        self.affinity_manager = DisplayAffinityManager()
        # 检查配置并根据配置决定是否启用防截屏功能
        anti_screenshot_enabled = self.config.get("General", {}).get("AntiScreenshot", False)
        self.affinity_manager.set_anti_screenshot_enabled(anti_screenshot_enabled)
        self.affinity_manager.start_affinity_thread()
        
        # 创建具有标题和初始大小的主窗口
        self.root = ctk.CTk()
        self.root.title(f"已停止 | jian2486的魔改作弊 {ConfigManager.VERSION}")
        self.root.geometry("1400x800")
        self.root.resizable(True, True)
        self.root.minsize(1400, 800)


        # 在屏幕上居中窗口
        x = (self.root.winfo_screenwidth() // 2) - (1400 // 2)
        y = (self.root.winfo_screenheight() // 2) - (800 // 2)
        self.root.geometry(f"1400x800+{x}+{y}")
        
        # 使用资源路径工具设置窗口图标
        self.set_window_icon('src/img/black_icon.png')
        
        # 在Windows系统上加载自定义字体
        if platform.system() == "Windows":
            import ctypes
            gdi32 = ctypes.WinDLL('gdi32')
            font_files = [
                'src/fonts/Chivo-Regular.ttf',
                'src/fonts/Chivo-Bold.ttf',
                'src/fonts/Gambetta-Regular.ttf',
                'src/fonts/Gambetta-Bold.ttf'
            ]
        
        # 配置网格布局使UI具有响应性
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # 初始化UI组件，如标题和内容
        self.setup_ui()
        
        # 设置配置文件监视器和日志更新计时器
        self.init_config_watcher()
        
        # 绑定窗口关闭事件以清理资源
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 注册Insert键呼出窗口的热键
        self.register_hotkey()

    def register_hotkey(self):
        """注册Insert键作为呼出主窗口的热键"""
        try:
            self.insert_hotkey = keyboard.add_hotkey('insert', self.toggle_window_visibility)
        except Exception as e:
            logger.error(f"注册热键失败: {e}")

    def toggle_window_visibility(self):
        """切换主窗口的可见性，并在显示时短暂置顶"""
        try:
            if self.root.winfo_viewable():
                # 如果窗口可见，则隐藏它
                self.root.withdraw()
                logger.debug("主窗口已隐藏")
            else:
                # 如果窗口隐藏，则显示它
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                # 设置窗口短暂置顶
                self.root.wm_attributes('-topmost', True)
                # 计划在500毫秒后取消置顶
                self.root.after(500, lambda: self.root.wm_attributes('-topmost', False))
                logger.debug("主窗口已显示并短暂置顶")
        except Exception as e:
            logger.error(f"切换窗口可见性时出错: {e}")

    def initialize_features(self):
        """使用共享的MemoryManager初始化所有功能实例"""
        try:
            self.triggerbot = CS2TriggerBot(self.memory_manager)
            self.aimbot = CS2Aimbot(self.memory_manager)
            self.overlay = CS2Overlay(self.memory_manager)
            self.overlay_opengl = CS2OverlayOpenGL(self.memory_manager)  # 添加OpenGL渲染器
            self.overlay_vulkan = CS2OverlayVulkan(self.memory_manager)
            self.bunnyhop = CS2Bunnyhop(self.memory_manager)
            self.noflash = CS2NoFlash(self.memory_manager)
            self.glow = CS2Glow(self.memory_manager)
            
            # 将TriggerBot和Glow实例传递给Overlay，以便共享实体信息
            self.overlay.triggerbot_instance = self.triggerbot
            self.overlay.glow_instance = self.glow
            
            logger.info("所有功能初始化成功")
        except Exception as e:
            logger.error(f"初始化功能失败: {e}")
            messagebox.showerror("初始化错误", f"初始化功能失败: {str(e)}")

    def setup_ui(self):
        """设置现代化用户界面组件"""
        # 创建主要内容区域，并包含侧边栏导航栏
        self.create_main_content()

    def create_modern_header(self):
        """创建具有渐变外观的时尚现代标题"""
        # 具有固定高度和深色背景的主标题容器
        header_container = ctk.CTkFrame(
            self.root, 
            height=80,
            corner_radius=0,
            fg_color=("#1a1a1a", "#0d1117")
        )
        header_container.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_container.grid_propagate(False)
        header_container.grid_columnconfigure(1, weight=1)
        
        # 左侧框架用于logo和标题
        left_frame = ctk.CTkFrame(header_container, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="w", padx=30, pady=15)
        
        # 标题组件框架
        title_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        title_frame.pack(side="left")
        
        # 带有强调色的主标题"Violet"
        main_title = ctk.CTkLabel(
            title_frame,
            text="Violet",
            font=("Chivo", 28, "bold"),
            text_color="#D5006D"
        )
        main_title.pack(side="left")
        
        # 白色的副标题"Wing"
        sub_title = ctk.CTkLabel(
            title_frame,
            text="Wing",
            font=("Chivo", 28, "bold"),
            text_color="#E0E0E0"
        )
        sub_title.pack(side="left", padx=(5, 0))
        
        # 字体较小且为灰色的版本标签
        version_label = ctk.CTkLabel(
            title_frame,
            text=f"{ConfigManager.VERSION}",
            font=("Gambetta", 16),
            text_color="#6b7280"
        )
        version_label.pack(side="left", padx=(10, 0), pady=(8, 0))
        
        # 右侧框架用于状态指示器
        right_frame = ctk.CTkFrame(header_container, fg_color="transparent")
        right_frame.grid(row=0, column=2, sticky="e", padx=30, pady=15)
        
        # 状态指示器框架
        self.status_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        self.status_frame.pack(side="right", padx=(20, 0))
        
    def create_update_offsets_button(self, parent):
        """创建更新偏移量按钮"""
        # 检查output目录中offsets文件的最后修改时间
        last_update_text = "从未"
        try:
            import datetime
            offsets_dir = Path("CS2-external-cheating/Offsets")
            offsets_file = offsets_dir / "offsets.json"
            if offsets_file.exists():
                mtime = offsets_file.stat().st_mtime
                last_update = datetime.datetime.fromtimestamp(mtime)
                last_update_text = last_update.strftime("%Y-%m-%d %H:%M")
        except Exception as e:
            logger.warning(f"获取偏移量文件更新时间失败: {e}")
        
        # 更新偏移量按钮框架
        update_frame = ctk.CTkFrame(parent, fg_color="transparent")
        update_frame.pack(side="right", padx=(0, 20))
        
        # 更新偏移量按钮
        self.update_offsets_button = ctk.CTkButton(
            update_frame,
            text="更新偏移量",
            command=self.update_offsets,
            font=(MAIN_FONT, SETTING_LABEL_FONT_SIZE, "bold"),
            corner_radius=0,
            fg_color=("#2563eb", "#3b82f6"),
            hover_color=("#1d4ed8", "#2563eb"),
            height=35
        )
        self.update_offsets_button.pack(side="top")
        
        # 上次更新时间标签
        self.last_update_label = ctk.CTkLabel(
            update_frame,
            text=f"上次更新: {last_update_text}",
            font=(SECONDARY_FONT, SETTING_DESCRIPTION_FONT_SIZE),
            text_color=("#64748b", "#94a3b8")
        )
        self.last_update_label.pack(side="top", pady=(5, 0))
        
    def update_offsets(self):
        """更新偏移量文件"""
        # 禁用按钮防止重复点击
        self.update_offsets_button.configure(state="disabled", text="更新中...")
        self.root.update()
        
        try:
            # 重置偏移量验证状态
            from classes.utility import Utility
            Utility.reset_offsets_validation()
            
            # 在后台线程中下载偏移量文件
            def run_update():
                success = Utility.download_offsets()
                # 在主线程中更新UI
                self.root.after(0, lambda: self.finish_update(success))
            
            # 启动更新线程
            update_thread = threading.Thread(target=run_update, daemon=True)
            update_thread.start()
        except Exception as e:
            logger.error(f"启动偏移量更新时出错: {e}")
            self.finish_update(False)
            
    def finish_update(self, success):
        """完成偏移量更新并更新UI"""
        # 重新启用按钮
        self.update_offsets_button.configure(state="normal", text="更新偏移量")
        
        if success:
            # 更新成功，更新时间标签
            try:
                import datetime
                offsets_dir = Path("CS2-external-cheating/Offsets")
                offsets_file = offsets_dir / "offsets.json"
                if offsets_file.exists():
                    mtime = offsets_file.stat().st_mtime
                    last_update = datetime.datetime.fromtimestamp(mtime)
                    last_update_text = last_update.strftime("%Y-%m-%d %H:%M")
                    # 只更新仪表板页面上的更新时间标签（如果存在）
                    if hasattr(self, 'update_time_label') and self.update_time_label.winfo_exists():
                        self.update_time_label.configure(text=last_update_text)
                    
                # 重新加载偏移量
                self.offsets, self.client_data, self.buttons_data = self.fetch_offsets_or_warn()
                self.memory_manager.update_offsets(self.offsets, self.client_data, self.buttons_data)
            except Exception as e:
                logger.error(f"更新偏移量后处理失败: {e}")
        else:
            # 显示错误消息
            messagebox.showerror("更新失败", "无法更新偏移量")

    def create_main_content(self):
        """创建具有现代布局的主内容区域"""
        # 内容和侧边栏的主容器
        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        main_container.grid_columnconfigure(1, weight=1)
        main_container.grid_rowconfigure(0, weight=1)
        
        # 创建侧边栏导航
        self.create_sidebar(main_container)
        
        # 内容区域框架
        self.content_frame = ctk.CTkFrame(
            main_container,
            corner_radius=0,
            fg_color=("#f8fafc", "#161b22")
        )
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        
        # 每个标签页的框架
        self.dashboard_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.general_settings_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.trigger_settings_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.aimbot_settings_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.overlay_settings_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.visual_settings_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.movement_settings_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.additional_settings_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")

        # 在初始化期间填充标签页框架
        self.populate_dashboard()
        self.populate_general_settings()
        self.populate_trigger_settings()
        self.populate_aimbot_settings()
        self.populate_overlay_settings()
        self.populate_visual_settings()
        self.populate_movement_settings()
        self.populate_additional_settings()
        
        # 默认显示仪表板视图
        self.dashboard_frame.pack(fill="both", expand=True)
        self.current_view = "dashboard"

    def create_sidebar(self, parent):
        """创建现代化侧边栏导航"""
        # 具有固定宽度的侧边栏框架
        sidebar = ctk.CTkFrame(
            parent,
            width=280,
            corner_radius=0,
            fg_color=("#ffffff", "#0d1117")
        )
        sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        sidebar.grid_propagate(False)
        
        # 导航项标签
        nav_items = [
            ("控制界面", "dashboard"),
            ("通用设置", "general_settings"),
            ("扳机设置", "trigger_settings"),
            ("自瞄设置", "aimbot_settings"),
            ("透视设置", "overlay_settings"),
            ("视觉效果", "visual_settings"),
            ("移动功能", "movement_settings"),
            ("附加设置", "additional_settings")
        ]
        
        # 存储导航按钮的字典
        self.nav_buttons = {}
        
        # 在侧边栏顶部添加填充
        ctk.CTkFrame(sidebar, height=30, fg_color="transparent").pack(fill="x")
        
        # 创建导航按钮
        for name, key in nav_items:
            btn = ctk.CTkButton(
                sidebar,
                text=name,
                command=lambda k=key: self.switch_view(k),
                width=240,
                height=50,
                corner_radius=0,
                fg_color="transparent",
                hover_color=("#e5e7eb", "#21262d"),
                text_color=("#374151", "#d1d5db"),
                font=(MAIN_FONT, SETTING_LABEL_FONT_SIZE),
                anchor="w"
            )
            btn.pack(pady=(0, 8), padx=20, fill="x")
            self.nav_buttons[key] = btn
        
        # 将仪表板按钮默认设置为激活状态
        self.set_active_nav("dashboard")

    def set_active_nav(self, active_key):
        """设置活动导航按钮，显示视觉反馈"""
        for key, btn in self.nav_buttons.items():
            if key == active_key:
                # 突出显示活动按钮
                btn.configure(
                    fg_color=("#D5006D", "#D5006D"),
                    text_color="#ffffff"
                )
            else:
                # 将未激活的按钮恢复为默认样式
                btn.configure(
                    fg_color="transparent",
                    text_color=("#374151", "#d1d5db")
                )

    def switch_view(self, view_key):
        """切换不同视图，显示适当的框架"""
        # 避免重复切换
        if self.current_view == view_key:
            return
        self.current_view = view_key
        self.set_active_nav(view_key)
        
        # 隐藏所有框架
        self.dashboard_frame.pack_forget()
        self.general_settings_frame.pack_forget()
        self.trigger_settings_frame.pack_forget()
        self.aimbot_settings_frame.pack_forget()
        self.overlay_settings_frame.pack_forget()
        self.visual_settings_frame.pack_forget()
        self.movement_settings_frame.pack_forget()
        self.additional_settings_frame.pack_forget()
        
        # 切换视图时重置按键检测显示
        self.reset_key_detection_display()
        
        # 显示选定的框架并在必要时更新
        if view_key == "dashboard":
            self.dashboard_frame.pack(fill="both", expand=True)
        elif view_key == "general_settings":
            self.general_settings_frame.pack(fill="both", expand=True)
        elif view_key == "trigger_settings":
            self.trigger_settings_frame.pack(fill="both", expand=True)
        elif view_key == "aimbot_settings":
            self.aimbot_settings_frame.pack(fill="both", expand=True)
        elif view_key == "overlay_settings":
            self.overlay_settings_frame.pack(fill="both", expand=True)
        elif view_key == "visual_settings":
            self.visual_settings_frame.pack(fill="both", expand=True)
        elif view_key == "movement_settings":
            self.movement_settings_frame.pack(fill="both", expand=True)
        elif view_key == "additional_settings":
            self.additional_settings_frame.pack(fill="both", expand=True)

    def populate_dashboard(self):
        """在仪表板框架中填入控件和统计信息"""
        populate_dashboard(self, self.dashboard_frame)

    def populate_general_settings(self):
        """在通用设置框中填入配置选项"""
        populate_general_settings(self, self.general_settings_frame)

    def populate_trigger_settings(self):
        """在自动扳机设置框中填入配置选项"""
        populate_trigger_settings(self, self.trigger_settings_frame)

    def populate_aimbot_settings(self):
        """在自瞄设置框中填入配置选项"""
        populate_aimbot_settings(self, self.aimbot_settings_frame)

    def populate_overlay_settings(self):
        """在叠加层设置框中填入配置选项"""
        populate_overlay_settings(self, self.overlay_settings_frame)

    def populate_movement_settings(self):
        """填充移动设置标签页"""
        populate_movement_settings(self, self.movement_settings_frame)

    def populate_additional_settings(self):
        """在附加设置框中填入"无动画"功能的配置选项"""
        populate_additional_settings(self, self.additional_settings_frame)

    def populate_visual_settings(self):
        """填充视觉设置标签页"""
        populate_visual_settings(self, self.visual_settings_frame)

    

    def fetch_offsets_or_warn(self):
        """尝试获取偏移量；失败时警告用户并返回空字典"""
        try:
            offsets, client_data, buttons_data = Utility.fetch_offsets()
            if offsets is None or client_data is None or buttons_data is None:
                raise ValueError("无法加载偏移量")
            return offsets, client_data, buttons_data
        except Exception as e:
            logger.error("偏移量获取错误: %s", e)
            messagebox.showerror("偏移量错误", f"无法加载偏移量: {str(e)}")
            return {}, {}, {}

    def update_client_status(self, status, color):
        """更新标题和仪表板中的客户端状态"""
        # 如果存在则更新标题状态标签
        if hasattr(self, 'status_label'):
            self.status_label.configure(text=status, text_color=color)
    
        # 更新标题状态点颜色
        if hasattr(self, 'status_dot'):
            self.status_dot.configure(fg_color=color)
        
        # 如果存在则更新仪表板状态标签
        # 注意：bot_status_label当前未在UI中实现
            
        # 根据状态更新窗口标题
        if status == "运行中":
            self.root.title(f"运行中 | jian2486的魔改作弊 {ConfigManager.VERSION}")
            # 将窗口图标更新为绿点
            self.set_window_icon('src/img/green_dot.png')
        else:
            self.root.title(f"已停止 | jian2486的魔改作弊 {ConfigManager.VERSION}")
            # 将窗口图标更新为红点
            self.set_window_icon('src/img/red_dot.png')
            
    def set_window_icon(self, icon_path):
        """使用PhotoImage设置窗口图标以获得更好的兼容性"""
        try:
            icon_full_path = Utility.resource_path(icon_path)
            if icon_full_path and os.path.exists(icon_full_path):
                icon_image = Image.open(icon_full_path)
                self.root.iconphoto(False, ImageTk.PhotoImage(icon_image))
            else:
                logger.warning(f"窗口图标文件不存在: {icon_full_path}")
        except Exception as e:
            logger.warning(f"无法将窗口图标更新为 {icon_path}: {e}")

    def _start_feature(self, feature_name, feature_obj, config):
        """启动单个功能的辅助方法"""
        if not getattr(feature_obj, 'is_running', False):
            try:
                # 确保功能对象具有最新的配置
                feature_obj.config = config
                feature_obj.is_running = True
                thread = threading.Thread(target=feature_obj.start, daemon=True)
                thread.start()
                setattr(self, f'{feature_name.lower()}线程', thread)
                logger.info(f"{feature_name} 已启动")
                return True
            except Exception as e:
                # 失败时重置运行状态
                feature_obj.is_running = False
                logger.error(f"无法启动 {feature_name}: {e}")
                messagebox.showerror(f"{feature_name} 错误", f"无法启动 {feature_name}: {str(e)}")
        return False

    def _stop_feature(self, feature_name, feature_obj):
        """停止单个功能的辅助方法"""
        if feature_obj and getattr(feature_obj, 'is_running', False):
            try:
                feature_obj.stop()
                thread = getattr(self, f'{feature_name.lower()}线程', None)
                if thread and thread.is_alive():
                    # 使用1.0秒的标准超时
                    thread.join(timeout=1.0)
                    if thread.is_alive():
                        logger.warning(f"{feature_name} 线程未正常终止")
                    else:
                        logger.info(f"{feature_name} 线程已成功终止")
                setattr(self, f'{feature_name.lower()}_thread', None)
                feature_obj.is_running = False
                logger.debug(f"{feature_name} 已停止")
                return True
            except Exception as e:
                logger.error(f"无法停止 {feature_name}: {e}", exc_info=True)
                # 即使停止失败也强制重置运行状态
                feature_obj.is_running = False
        return False

    def start_client(self):
        """根据常规设置启动选定的功能，确保无重复启动"""
        # 移除了游戏运行检查，允许在任何界面启动叠加层
        # 如果游戏未运行则显示错误
        #     messagebox.showerror("游戏未运行", "找不到 cs2.exe 进程。请确保游戏正在运行。")
        #     return

        # 在启动任何功能之前初始化MemoryManager一次
        # 对于叠加层功能，即使游戏未运行也可以启动
        if not self.memory_manager.initialize():
            # 仅为非叠加层功能显示错误
            enabled_non_overlay = any([
                self.triggerbot.config["General"]["Trigger"],
                self.aimbot.config["General"]["Aimbot"],
                self.bunnyhop.config["General"]["Bunnyhop"],
                self.noflash.config["General"]["Noflash"]
            ])
            
            if enabled_non_overlay:
                messageVbox.showerror("初始化错误", "无法初始化内存管理器。请查看日志了解详细信息")
                return

        # 即使内存管理器失败也继续启动功能
        # (Overlay can still run without memory access)

        config = ConfigManager.load_config()
        any_feature_started = False

        # 获取渲染模式
        render_mode = config["General"].get("RenderMode", "默认(pyMeow)")
        
        # 根据渲染模式决定启用哪个ESP功能（但只在用户启用了Overlay时）
        overlay_features = []
        if config["General"]["Overlay"]:
            if render_mode == "Vulkan":
                overlay_features = [("OverlayVulkan", "OverlayVulkan", self.overlay_vulkan)]
            elif render_mode == "OpenGL":
                # 当选择OpenGL时，使用OpenGL渲染器
                overlay_features = [("Overlay", "Overlay", self.overlay_opengl)]
            else:
                # 对于默认(pyMeow)模式使用标准overlay
                overlay_features = [("Overlay", "Overlay", self.overlay)]
        
        # 确保根据渲染模式正确设置叠加层功能开关
        # 但不要覆盖用户手动设置的Overlay开关状态
        if render_mode == "Vulkan":
            config["General"]["OverlayVulkan"] = True
        elif render_mode == "OpenGL":
            # 当选择OpenGL时，使用OpenGL渲染器
            config["General"]["OverlayVulkan"] = False
        else:
            # 对于默认(pyMeow)模式使用标准overlay
            config["General"]["OverlayVulkan"] = False

        # 定义要启动的功能
        features = [
            ("TriggerBot", "Trigger", self.triggerbot),
            ("Aimbot", "Aimbot", self.aimbot),
            ("Bunnyhop", "Bunnyhop", self.bunnyhop),
            ("NoFlash", "Noflash", self.noflash)
        ]
        
        # 添加选定的ESP功能
        features.extend(overlay_features)
        
        # 添加Glow功能
        if config["Overlay"].get("enable_glow", False):
            features.append(("Glow", "Glow", self.glow))

        # 根据常规设置启动功能
        for feature_name, config_key, feature_obj in features:
            # 对于Glow功能，我们检查其自身的启用设置而不是General设置
            if config_key == "Glow":
                should_start = config["Overlay"].get("enable_glow", False)
            else:
                should_start = config["General"][config_key]
                
            if should_start:
                # 检查功能是否尚未运行
                if not getattr(feature_obj, 'is_running', False):
                    if self._start_feature(feature_name, feature_obj, config):
                        any_feature_started = True
                else:
                    logger.info(f"{feature_name} 已在运行中")
                    any_feature_started = True

        if any_feature_started:
            self.update_client_status("运行中", "#22c55e")
        else:
            logger.warning("常规设置中未启用任何功能")
            messagebox.showwarning("未启用功能", "请在常规设置中至少启用一个功能")

    def stop_client(self):
        """停止所有运行中的功能并确保线程已终止"""
        features_stopped = False

        # 定义要停止的功能
        features = [
            ("TriggerBot", self.triggerbot),
            ("Aimbot", self.aimbot),
            ("Bunnyhop", self.bunnyhop),
            ("NoFlash", self.noflash),
            ("Glow", self.glow)
        ]
        
        # 根据当前配置添加正确的Overlay实现
        config = ConfigManager.load_config()
        render_mode = config["General"].get("RenderMode", "默认(pyMeow)")
        
        if render_mode == "Vulkan":
            features.append(("OverlayVulkan", self.overlay_vulkan))
        elif render_mode == "OpenGL":
            features.append(("OverlayOpenGL", self.overlay_opengl))
        else:
            features.append(("Overlay", self.overlay))

        # 停止所有功能
        for feature_name, feature_obj in features:
            if self._stop_feature(feature_name, feature_obj):
                features_stopped = True

        if features_stopped:
            self.update_client_status("已停止", "#ef4444")
        else:
            logger.debug("没有正在运行的功能需要停止")

    def update_weapon_settings_display(self):
        """根据选定的武器类型更新UI字段"""
        weapon_type = self.active_weapon_type.get()
        settings = self.config['Trigger']['WeaponSettings'].get(weapon_type, {})
        
        if hasattr(self, 'min_delay_entry'):
            self.min_delay_entry.delete(0, "end")
            self.min_delay_entry.insert(0, str(settings.get('ShotDelayMin', 0.01)))
        if hasattr(self, 'max_delay_entry'):
            self.max_delay_entry.delete(0, "end")
            self.max_delay_entry.insert(0, str(settings.get('ShotDelayMax', 0.03)))
        if hasattr(self, 'post_shot_delay_entry'):
            self.post_shot_delay_entry.delete(0, "end")
            self.post_shot_delay_entry.insert(0, str(settings.get('PostShotDelay', 0.1)))

    def update_aimbot_weapon_settings_display(self):
        """根据选定的武器类型更新自瞄UI字段"""
        weapon_type = self.active_aimbot_weapon_type.get()
        settings = self.config['Aimbot']['WeaponSettings'].get(weapon_type, {})
        
        if hasattr(self, 'fov_entry'):
            self.fov_entry.delete(0, "end")
            self.fov_entry.insert(0, str(settings.get('FOV', 50)))
        if hasattr(self, 'smooth_entry'):
            self.smooth_entry.delete(0, "end")
            self.smooth_entry.insert(0, str(settings.get('Smooth', 2.0)))

    def save_settings(self, show_message=False):
        """保存配置设置并实时应用到相关功能"""
        try:
            self.validate_inputs()
            old_config = ConfigManager.load_config().copy()
            self.update_config_from_ui()
            new_config = self.config
            ConfigManager.save_config(new_config, log_info=False)


            # 定义功能及其线程
            features = {
                "Trigger": (self.triggerbot, "TriggerBot"),
                "Aimbot": (self.aimbot, "Aimbot"),
                "Overlay": (self.overlay, "Overlay"),
                "OverlayVulkan": (self.overlay_vulkan, "OverlayVulkan"),
                "Bunnyhop": (self.bunnyhop, "Bunnyhop"),
                "Noflash": (self.noflash, "NoFlash"),
                "Glow": (self.glow, "Glow")
            }

            any_feature_running = False

            # 只更新正在运行的功能的配置，不启动新功能
            for feature_key, (feature_obj, feature_name) in features.items():
                is_running = getattr(feature_obj, 'is_running', False)
                
                # 更新运行中功能的配置
                if is_running:
                    feature_obj.update_config(new_config)
                    logger.debug(f"配置已更新为 {feature_name}.")
                    any_feature_running = True

            # 更新UI状态
            self.update_client_status("运行中" if any_feature_running else "已停止", 
                                    "#22c55e" if any_feature_running else "#ef4444")

            if show_message:
                messagebox.showinfo("设置已保存", "配置已成功保存")
        except ValueError as e:
            logger.error(f"无效输入: {e}")
            messagebox.showerror("无效输入", str(e))
        except Exception as e:
            logger.error(f"发生意外错误: {e}")
            # 使用不依赖UI元素的安全错误报告
            try:
                messagebox.showerror("错误", f"发生意外错误: {str(e)}")
            except:
                # 如果消息框失败，只记录错误
                logger.error(f"未能显示错误消息: {str(e)}")

    def _restart_feature(self, feature_name, feature_obj, feature_class, config_section, new_config):
        """重启单个功能的辅助方法"""
        try:
            # 停止功能
            feature_obj.stop()
            thread = getattr(self, f'{feature_name.lower()}_thread', None)
            if thread and thread.is_alive():
                thread.join(timeout=1.0)
            setattr(self, f'{feature_name.lower()}_thread', None)
            
            # 如果在常规配置中启用则重启
            if new_config["General"][config_section]:
                new_feature = feature_class(self.memory_manager)
                new_feature.config = new_config
                setattr(self, feature_name.lower(), new_feature)
                
                new_thread = threading.Thread(target=new_feature.start, daemon=True)
                new_thread.start()
                setattr(self, f'{feature_name.lower()}_thread', new_thread)
                logger.info(f"{feature_name} 已重新启动，使用新配置")
            
            return True
        except Exception as e:
            logger.error(f"未能成功重新启动 {feature_name}: {e}")
            return False

    def restart_affected_features(self, old_config, new_config):
        """仅重新启动受配置更改影响的功能。"""
        any_feature_running = False

        # 检查配置部分是否已更改的辅助函数
        def config_changed(section):
            return old_config.get(section, {}) != new_config.get(section, {})

        # 定义功能及其类和配置部分
        features = [
            ("TriggerBot", self.triggerbot, "CS2TriggerBot", "Trigger"),
            ("Aimbot", self.aimbot, "CS2Aimbot", "Aimbot"),
            ("Overlay", self.overlay, "CS2Overlay", "Overlay"),
            ("OverlayOpenGL", self.overlay_opengl, "CS2OverlayOpenGL", "Overlay"),  # 添加OpenGL渲染器支持
            ("OverlayVulkan", self.overlay_vulkan, "CS2OverlayVulkan", "OverlayVulkan"), 
            ("Bunnyhop", self.bunnyhop, "CS2Bunnyhop", "Bunnyhop"),
            ("NoFlash", self.noflash, "CS2NoFlash", "Noflash"),
            ("Glow", self.glow, "CS2Glow", "Glow")
        ]

        # 如果配置更改且功能正在运行则重启
        for feature_name, feature_obj, class_name, config_section in features:
            if (hasattr(feature_obj, 'is_running') and feature_obj.is_running and 
                (config_changed(config_section) or config_changed("General"))):
                
                # 从全局变量或导入中获取实际类
                feature_class = globals().get(class_name)
                if feature_class and self._restart_feature(feature_name, feature_obj, feature_class, config_section, new_config):
                    any_feature_running = True

        # 更新UI状态
        if any_feature_running:
            self.update_client_status("运行中", "#22c55e")
        else:
            self.update_client_status("已停止", "#ef4444")

    def update_config_from_ui(self):
        """根据UI元素更新配置。"""
        # 更新常规设置
        general_settings = self.config["General"]
        if hasattr(self, 'trigger_var'):
            general_settings["Trigger"] = self.trigger_var.get()
        if hasattr(self, 'overlay_var'):
            general_settings["Overlay"] = self.overlay_var.get()
        if hasattr(self, 'bunnyhop_var'):
            general_settings["Bunnyhop"] = self.bunnyhop_var.get()
        if hasattr(self, 'noflash_var'):
            general_settings["Noflash"] = self.noflash_var.get()
        if hasattr(self, 'render_mode_var'):
            render_mode = self.render_mode_var.get()
            general_settings["RenderMode"] = render_mode
            # 根据渲染模式设置OverlayVulkan开关，但不改变用户设置的Overlay开关
            if render_mode == "Vulkan":
                general_settings["OverlayVulkan"] = True
            else:
                general_settings["OverlayVulkan"] = False
        if hasattr(self, 'AntiScreenshot_var'):
            general_settings["AntiScreenshot"] = self.AntiScreenshot_var.get()

        # 更新触发器设置
        trigger_settings = self.config["Trigger"]
        if hasattr(self, 'trigger_key_entry'):
            trigger_settings["TriggerKey"] = self.trigger_key_entry.get().strip()
        if hasattr(self, 'toggle_mode_var'):
            trigger_settings["ToggleMode"] = self.toggle_mode_var.get()
        if hasattr(self, 'attack_teammates_var'):
            trigger_settings["AttackOnTeammates"] = self.attack_teammates_var.get()
        # 添加内存射击模式设置
        if hasattr(self, 'memory_shoot_var'):
            trigger_settings["MemoryShoot"] = self.memory_shoot_var.get()
        if hasattr(self, 'min_delay_entry'):
            try:
                trigger_settings["ShotDelayMin"] = float(self.min_delay_entry.get())
            except ValueError:
                pass
        if hasattr(self, 'max_delay_entry'):
            try:
                trigger_settings["ShotDelayMax"] = float(self.max_delay_entry.get())
            except ValueError:
                pass
        if hasattr(self, 'post_shot_delay_entry'):
            try:
                trigger_settings["PostShotDelay"] = float(self.post_shot_delay_entry.get())
            except ValueError:
                pass
        
        if hasattr(self, 'active_weapon_type'):
            weapon_type = self.active_weapon_type.get()
            trigger_settings['active_weapon_type'] = weapon_type
            weapon_settings = trigger_settings['WeaponSettings'].get(weapon_type, {})
            
            if hasattr(self, 'min_delay_entry'): weapon_settings['ShotDelayMin'] = float(self.min_delay_entry.get())
            if hasattr(self, 'max_delay_entry'): weapon_settings['ShotDelayMax'] = float(self.max_delay_entry.get())
            if hasattr(self, 'post_shot_delay_entry'): weapon_settings['PostShotDelay'] = float(self.post_shot_delay_entry.get())
            
            trigger_settings['WeaponSettings'][weapon_type] = weapon_settings

        # 更新自瞄设置
        aimbot_settings = self.config["Aimbot"]
        if hasattr(self, 'aim_key_entry'):
            aimbot_settings["AimKey"] = self.aim_key_entry.get().strip()
        if hasattr(self, 'aimbot_toggle_mode_var'):
            aimbot_settings["ToggleMode"] = self.aimbot_toggle_mode_var.get()
        if hasattr(self, 'aimbot_attack_teammates_var'):
            aimbot_settings["AttackOnTeammates"] = self.aimbot_attack_teammates_var.get()
        if hasattr(self, 'fov_entry'):
            try:
                aimbot_settings["FOV"] = float(self.fov_entry.get())
            except ValueError:
                pass
        if hasattr(self, 'smooth_entry'):
            try:
                aimbot_settings["Smooth"] = float(self.smooth_entry.get())
            except ValueError:
                pass
        
        if hasattr(self, 'active_aimbot_weapon_type'):
            weapon_type = self.active_aimbot_weapon_type.get()
            aimbot_settings['active_weapon_type'] = weapon_type
            weapon_settings = aimbot_settings['WeaponSettings'].get(weapon_type, {})
            
            if hasattr(self, 'fov_entry'): weapon_settings['FOV'] = float(self.fov_entry.get())
            if hasattr(self, 'smooth_entry'): weapon_settings['Smooth'] = float(self.smooth_entry.get())
            
            aimbot_settings['WeaponSettings'][weapon_type] = weapon_settings

        # 更新叠加层设置
        overlay_settings = self.config["Overlay"]
        if hasattr(self, 'enable_box_var'):
            overlay_settings["enable_box"] = self.enable_box_var.get()
        if hasattr(self, 'enable_skeleton_var'):
            overlay_settings["enable_skeleton"] = self.enable_skeleton_var.get()
        if hasattr(self, 'box_line_thickness_slider'):
            overlay_settings["box_line_thickness"] = self.box_line_thickness_slider.get()
            if hasattr(self, 'box_line_thickness_value_label'):
                self.box_line_thickness_value_label.configure(text=f"{overlay_settings['box_line_thickness']:.1f}")
        if hasattr(self, 'box_color_hex_combo'):
            overlay_settings["box_color_hex"] = COLOR_CHOICES.get(self.box_color_hex_combo.get(), "#FFA500")
        if hasattr(self, 'draw_snaplines_var'):
            overlay_settings["draw_snaplines"] = self.draw_snaplines_var.get()
        if hasattr(self, 'snaplines_color_hex_combo'):
            overlay_settings["snaplines_color_hex"] = COLOR_CHOICES.get(self.snaplines_color_hex_combo.get(), "#FFFFFF")
        if hasattr(self, 'text_color_hex_combo'):
            overlay_settings["text_color_hex"] = COLOR_CHOICES.get(self.text_color_hex_combo.get(), "#FFFFFF")
        if hasattr(self, 'draw_health_numbers_var'):
            overlay_settings["draw_health_numbers"] = self.draw_health_numbers_var.get()
        if hasattr(self, 'draw_nicknames_var'):
            overlay_settings["draw_nicknames"] = self.draw_nicknames_var.get()
        if hasattr(self, 'use_transliteration_var'):
            overlay_settings["use_transliteration"] = self.use_transliteration_var.get()
        if hasattr(self, 'draw_teammates_var'):
            overlay_settings["draw_teammates"] = self.draw_teammates_var.get()
        if hasattr(self, 'teammate_color_hex_combo'):
            overlay_settings["teammate_color_hex"] = COLOR_CHOICES.get(self.teammate_color_hex_combo.get(), "#00FFFF")
        if hasattr(self, 'enable_minimap_var'):
            overlay_settings["enable_minimap"] = self.enable_minimap_var.get()
        if hasattr(self, 'minimap_size_slider'):
            overlay_settings["minimap_size"] = int(self.minimap_size_slider.get())
            if hasattr(self, 'minimap_size_value_label'):
                self.minimap_size_value_label.configure(text=f"{overlay_settings['minimap_size']:.0f}")
        if hasattr(self, 'target_fps_slider'):
            overlay_settings["target_fps"] = self.target_fps_slider.get()
            if hasattr(self, 'target_fps_value_label'):
                self.target_fps_value_label.configure(text=f"{overlay_settings['target_fps']:.0f}")
        # 更新发光效果设置
        if hasattr(self, 'enable_glow_var'):
            overlay_settings["enable_glow"] = self.enable_glow_var.get()
        if hasattr(self, 'glow_exclude_dead_var'):
            overlay_settings["glow_exclude_dead"] = self.glow_exclude_dead_var.get()
        if hasattr(self, 'glow_teammates_var'):
            overlay_settings["glow_teammates"] = self.glow_teammates_var.get()
        if hasattr(self, 'glow_thickness_slider'):
            overlay_settings["glow_thickness"] = self.glow_thickness_slider.get()
        if hasattr(self, 'glow_color_hex_combo'):
            overlay_settings["glow_color_hex"] = COLOR_CHOICES.get(self.glow_color_hex_combo.get(), "#FF00FF")
        if hasattr(self, 'glow_teammate_color_hex_combo'):
            overlay_settings["glow_teammate_color_hex"] = COLOR_CHOICES.get(self.glow_teammate_color_hex_combo.get(), "#00FFFF")

        # 更新连跳设置
        bunnyhop_settings = self.config.get("Bunnyhop", {})
        if hasattr(self, 'jump_key_entry'):
            bunnyhop_settings["JumpKey"] = self.jump_key_entry.get().strip()
        if hasattr(self, 'jump_delay_entry'):
            try:
                bunnyhop_settings["JumpDelay"] = float(self.jump_delay_entry.get())
            except ValueError:
                pass

        # 更新无闪光效果设置
        noflash_settings = self.config.get("NoFlash", {})
        if hasattr(self, 'FlashSuppressionStrength_slider'):
            noflash_settings["FlashSuppressionStrength"] = self.FlashSuppressionStrength_slider.get()

    def validate_inputs(self):
        """验证用户输入字段。"""
        # 验证触发器设置
        if hasattr(self, 'trigger_key_entry'):
            trigger_key = self.trigger_key_entry.get().strip()
            if not trigger_key:
                raise ValueError("触发键不能为空")

        # 验证延迟字段为数字
        if hasattr(self, 'min_delay_entry'):
            try:
                min_delay = float(self.min_delay_entry.get())
            except ValueError:
                raise ValueError("最小射击延迟必须是一个有效的数字")
            if min_delay < 0:
                raise ValueError("最小射击延迟必须非负")
        else:
            min_delay = None

        if hasattr(self, 'max_delay_entry'):
            try:
                max_delay = float(self.max_delay_entry.get())
            except ValueError:
                raise ValueError("最大射击延迟必须是一个有效的数字")
            if max_delay < 0:
                raise ValueError("最大射击延迟必须非负")
            if min_delay is not None and min_delay > max_delay:
                raise ValueError("最小射击延迟不能大于最大射击延迟")
        else:
            max_delay = None

        if hasattr(self, 'post_shot_delay_entry'):
            try:
                post_delay = float(self.post_shot_delay_entry.get())
            except ValueError:
                raise ValueError("后射击延迟必须是一个有效的数字")
            if post_delay < 0:
                raise ValueError("后射击延迟必须非负")

        # 验证自瞄设置
        if hasattr(self, 'aim_key_entry'):
            aim_key = self.aim_key_entry.get().strip()
            if not aim_key:
                raise ValueError("自瞄键不能为空")

        if hasattr(self, 'fov_entry'):
            try:
                fov = float(self.fov_entry.get())
                if fov < 0 or fov > 1000:
                    raise ValueError("视野必须在 0 和 1000 之间")
            except ValueError:
                raise ValueError("视野必须是一个有效的数字")

        if hasattr(self, 'smooth_entry'):
            try:
                smooth = float(self.smooth_entry.get())
                if smooth < 0.1 or smooth > 10:
                    raise ValueError("平滑度必须在 0.1 和 10 之间")
            except ValueError:
                raise ValueError("平滑度必须是一个有效的数字")

        # 验证叠加层设置
        if hasattr(self, 'minimap_size_slider'):
            minimap_size = int(self.minimap_size_slider.get())
            if not (100 <= minimap_size <= 500):
                raise ValueError("小地图大小必须在 100 和 500之间")
            
        if hasattr(self, 'target_fps_slider'):
            try:
                target_fps = float(self.target_fps_slider.get())
                if not (60 <= target_fps <= 420):
                    raise ValueError("目标 FPS 必须在 60 和 420 之间")
            except ValueError:
                raise ValueError("目标 FPS 必须是一个有效的数字")
            
        # 验证连跳设置
        if hasattr(self, 'jump_key_entry'):
            jump_key = self.jump_key_entry.get().strip()
            if not jump_key:
                raise ValueError("跳跃键不能为空")

        if hasattr(self, 'jump_delay_entry'):
            try:
                jump_delay = float(self.jump_delay_entry.get())
            except ValueError:
                raise ValueError("跳跃延迟必须是一个有效的数字")
            if jump_delay < 0.01 or jump_delay > 0.5:
                raise ValueError("跳跃延迟必须在 0.01 秒和 0.5 秒之间")

        # 验证无闪光效果设置
        if hasattr(self, 'FlashSuppressionStrength_slider'):
            strength = self.FlashSuppressionStrength_slider.get()
            if not (0.0 <= strength <= 1.0):
                raise ValueError("闪光弹抑制强度必须在 0.0 和 1.0 之间")

    def reset_to_default_settings(self):
        """将所有设置重置为默认值"""
        if not messagebox.askyesno("重置设置", "您确定要将所有设置重置为默认值吗？这将停止所有活动功能"):
            return

        try:
            # 停止所有运行中的功能以确保干净的状态
            self.stop_client()

            # 获取默认配置的新副本
            new_config = ConfigManager.DEFAULT_CONFIG.copy()
            
            # 更新所有功能实例的配置
            self.config = new_config
            self.triggerbot.config = new_config
            self.aimbot.config = new_config
            self.overlay.config = new_config
            self.bunnyhop.config = new_config
            self.noflash.config = new_config
            
            # 更新UI以反映新的默认设置
            self.update_ui_from_config()

            # 将新的默认配置保存到文件
            ConfigManager.save_config(new_config)
            
            messagebox.showinfo("设置已重置", "所有设置已重置为默认值。您现在可以重新启动客户端")
        except Exception as e:
            logger.error(f"重置设置失败: {e}")
            messagebox.showerror("错误", f"重置设置失败: {str(e)}")

    def update_ui_from_config(self):
        """根据配置更新UI元素"""
        # 更新常规设置UI
        general_settings = self.config["General"]
        if hasattr(self, 'trigger_var'):
            self.trigger_var.set(general_settings["Trigger"])
        if hasattr(self, 'overlay_var'):
            self.overlay_var.set(general_settings["Overlay"])
        if hasattr(self, 'bunnyhop_var'):
            self.bunnyhop_var.set(general_settings["Bunnyhop"])
        if hasattr(self, 'noflash_var'):
            self.noflash_var.set(general_settings["Noflash"])
        if hasattr(self, 'AntiScreenshot_var'):
            self.AntiScreenshot_var.set(general_settings.get("AntiScreenshot", True))

        # 更新触发器设置UI
        trigger_settings = self.triggerbot.config["Trigger"]
        if hasattr(self, 'trigger_key_entry'):
            self.trigger_key_entry.delete(0, "end")
            self.trigger_key_entry.insert(0, trigger_settings["TriggerKey"])
        if hasattr(self, 'toggle_mode_var'):
            self.toggle_mode_var.set(trigger_settings["ToggleMode"])
        if hasattr(self, 'attack_teammates_var'):
            self.attack_teammates_var.set(trigger_settings["AttackOnTeammates"])
        # 添加内存射击模式UI更新
        if hasattr(self, 'memory_shoot_var'):
            self.memory_shoot_var.set(trigger_settings.get("MemoryShoot", False))

        if hasattr(self, 'active_weapon_type'):
            self.active_weapon_type.set(trigger_settings.get('active_weapon_type', 'Rifles'))
            self.update_weapon_settings_display()

        # 更新自瞄设置UI
        aimbot_settings = self.aimbot.config["Aimbot"]
        if hasattr(self, 'aim_key_entry'):
            self.aim_key_entry.delete(0, "end")
            self.aim_key_entry.insert(0, aimbot_settings["AimKey"])
        if hasattr(self, 'aimbot_toggle_mode_var'):
            self.aimbot_toggle_mode_var.set(aimbot_settings["ToggleMode"])
        if hasattr(self, 'aimbot_attack_teammates_var'):
            self.aimbot_attack_teammates_var.set(aimbot_settings["AttackOnTeammates"])

        if hasattr(self, 'active_aimbot_weapon_type'):
            self.active_aimbot_weapon_type.set(aimbot_settings.get('active_weapon_type', 'Rifles'))
            self.update_aimbot_weapon_settings_display()

        # 更新叠加层设置UI
        overlay_settings = self.config["Overlay"]
        if hasattr(self, 'enable_box_var'):
            self.enable_box_var.set(overlay_settings["enable_box"])
        if hasattr(self, 'enable_skeleton_var'):
            self.enable_skeleton_var.set(overlay_settings.get("enable_skeleton", True))
        if hasattr(self, 'box_line_thickness_slider'):
            self.box_line_thickness_slider.set(overlay_settings["box_line_thickness"])
            if hasattr(self, 'box_line_thickness_value_label'):
                self.box_line_thickness_value_label.configure(text=f"{overlay_settings['box_line_thickness']:.1f}")
        if hasattr(self, 'box_color_hex_combo'):
            self.box_color_hex_combo.set(Utility.get_color_name_from_hex(overlay_settings["box_color_hex"]))
        if hasattr(self, 'draw_snaplines_var'):
            self.draw_snaplines_var.set(overlay_settings["draw_snaplines"])
        if hasattr(self, 'snaplines_color_hex_combo'):
            self.snaplines_color_hex_combo.set(Utility.get_color_name_from_hex(overlay_settings["snaplines_color_hex"]))
        if hasattr(self, 'text_color_hex_combo'):
            self.text_color_hex_combo.set(Utility.get_color_name_from_hex(overlay_settings["text_color_hex"]))
        if hasattr(self, 'draw_health_numbers_var'):
            self.draw_health_numbers_var.set(overlay_settings["draw_health_numbers"])
        if hasattr(self, 'draw_nicknames_var'):
            self.draw_nicknames_var.set(overlay_settings["draw_nicknames"])
        if hasattr(self, 'use_transliteration_var'):
            self.use_transliteration_var.set(overlay_settings["use_transliteration"])
        if hasattr(self, 'draw_teammates_var'):
            self.draw_teammates_var.set(overlay_settings["draw_teammates"])
        if hasattr(self, 'teammate_color_hex_combo'):
            self.teammate_color_hex_combo.set(Utility.get_color_name_from_hex(overlay_settings["teammate_color_hex"]))
        if hasattr(self, 'enable_minimap_var'):
            self.enable_minimap_var.set(overlay_settings["enable_minimap"])
        if hasattr(self, 'minimap_size_slider'):
            self.minimap_size_slider.set(overlay_settings["minimap_size"])
            if hasattr(self, 'minimap_size_value_label'):
                self.minimap_size_value_label.configure(text=f"{overlay_settings['minimap_size']:.0f}")
        if hasattr(self, 'target_fps_slider'):
            self.target_fps_slider.set(overlay_settings["target_fps"])
            if hasattr(self, 'target_fps_value_label'):
                self.target_fps_value_label.configure(text=f"{overlay_settings['target_fps']:.0f}")
        # 更新发光效果设置UI
        if hasattr(self, 'enable_glow_var'):
            self.enable_glow_var.set(overlay_settings.get("enable_glow", False))
        if hasattr(self, 'glow_exclude_dead_var'):
            self.glow_exclude_dead_var.set(overlay_settings.get("glow_exclude_dead", True))
        if hasattr(self, 'glow_teammates_var'):
            self.glow_teammates_var.set(overlay_settings.get("glow_teammates", False))
        if hasattr(self, 'glow_thickness_slider'):
            self.glow_thickness_slider.set(overlay_settings.get("glow_thickness", 1.0))
        if hasattr(self, 'glow_color_hex_combo'):
            self.glow_color_hex_combo.set(Utility.get_color_name_from_hex(overlay_settings.get("glow_color_hex", "#FF00FF")))
        if hasattr(self, 'glow_teammate_color_hex_combo'):
            self.glow_teammate_color_hex_combo.set(Utility.get_color_name_from_hex(overlay_settings.get("glow_teammate_color_hex", "#00FFFF")))

        # 更新连跳设置UI
        bunnyhop_settings = self.config.get("Bunnyhop", {})
        if hasattr(self, 'jump_key_entry'):
            self.jump_key_entry.delete(0, "end")
            self.jump_key_entry.insert(0, bunnyhop_settings.get("JumpKey", "space"))
        if hasattr(self, 'jump_delay_entry'):
            self.jump_delay_entry.delete(0, "end")
            self.jump_delay_entry.insert(0, str(bunnyhop_settings.get("JumpDelay", 0.01)))

        # 更新无闪光效果设置UI
        noflash_settings = self.config.get("NoFlash", {})
        if hasattr(self, 'FlashSuppressionStrength_slider'):
            self.FlashSuppressionStrength_slider.set(noflash_settings.get("FlashSuppressionStrength", 0.0))
            if hasattr(self, 'FlashSuppressionStrength_value_label'):
                self.FlashSuppressionStrength_value_label.configure(text=f"{noflash_settings.get('FlashSuppressionStrength', 0.0):.2f}")

    def open_config_directory(self):
        """在文件资源管理器中打开配置目录"""
        path = ConfigManager.CONFIG_DIRECTORY
        if platform.system() == "Windows":
            os.startfile(path)

    def init_config_watcher(self):
        """为配置更改初始化文件监视器"""
        try:
            # 为配置文件更改设置监视器
            from watchdog.observers import Observer
            self.observer = Observer()
            event_handler = ConfigFileChangeHandler(self)
            self.observer.schedule(event_handler, path=ConfigManager.CONFIG_DIRECTORY, recursive=False)
            self.observer.start()
            logger.info("配置文件监视器已成功启动")
        except Exception as e:
            logger.error("初始化配置监视器失败: %s", e)

    def run(self):
        """启动应用程序主循环"""
        self.root.mainloop()

    def on_closing(self):
        """通过清理资源处理窗口关闭事件"""
        self.cleanup()
        self.root.destroy()

    def cleanup(self):
        """在关闭应用程序前清理资源"""
        # 检查是否已经清理过
        if self.cleaned_up:
            return
            
        # 标记已清理
        self.cleaned_up = True
        
        try:
            # 停止所有运行中的功能
            self.stop_client()
            
            # 停止显示亲和力管理线程
            if hasattr(self, 'affinity_manager'):
                self.affinity_manager.stop_affinity_thread()
            
            # 如果存在则停止文件监视器
            if hasattr(self, 'observer') and self.observer:
                self.observer.stop()
                self.observer.join(timeout=1.0)
                
            # 移除所有热键注册
            try:
                keyboard.unhook_all_hotkeys()
                logger.info("所有热键已移除")
            except Exception as e:
                logger.error(f"移除热键时出错: {e}")
        except Exception as e:
            logger.error("清理过程中出错: %s", e)

    def reset_key_detection_display(self):
        """重置按键检测显示状态"""
        # 重置触发器按键显示
        if hasattr(self, 'trigger_key_entry'):
            self.trigger_key_entry.configure(state="normal")
            current_key = self.triggerbot.config['Trigger'].get('TriggerKey', '')
            self.trigger_key_entry.delete(0, "end")
            self.trigger_key_entry.insert(0, current_key)
            self.trigger_key_entry.configure(state="disabled")
        
        # 重置自瞄按键显示
        if hasattr(self, 'aim_key_entry'):
            self.aim_key_entry.configure(state="normal")
            current_key = self.aimbot.config['Aimbot'].get('AimKey', '')
            self.aim_key_entry.delete(0, "end")
            self.aim_key_entry.insert(0, current_key)
            self.aim_key_entry.configure(state="disabled")