import tkinter as tk
from tkinter import ttk
from typing import List

# 导入字体管理器
from gui.font_manager import SECONDARY_FONT, INPUT_FONT_SIZE


class DraggableWindow:
    """
    一个带有自定义拖动栏的无边框窗口，显示当前运行的功能列表
    """
    def __init__(self, main_window_ref=None):
        self.main_window_ref = main_window_ref
        self.root = tk.Tk()
        self.root.title("功能状态")
        self.root.geometry("300x200")
        self.root.configure(bg='#2d2d2d')
        
        # 设置无边框窗口
        self.root.overrideredirect(True)
        
        # 设置窗口属性
        self.root.attributes('-topmost', True)
        
        # 设置窗口为最高层级并隐藏在任务栏中的显示（仅Windows系统）
        try:
            import platform
            if platform.system() == 'Windows':
                # 使用tkinter内置方法设置为工具窗口，使其不在任务栏中显示
                self.root.wm_attributes("-toolwindow", True)
                
                # 设置窗口为顶层并保持在所有窗口之上
                self.root.wm_attributes("-topmost", True)
                
                # 尝试使用Windows API设置为UIAccess层级，并防止随主窗口隐藏
                try:
                    import ctypes
                    from ctypes import wintypes
                    
                    # 定义必要的Windows API常量
                    HWND_TOPMOST = -1
                    HWND_NOTOPMOST = -2
                    SWP_NOSIZE = 0x0001
                    SWP_NOMOVE = 0x0002
                    SWP_NOACTIVATE = 0x0010
                    SWP_SHOWWINDOW = 0x0040
                    
                    # 获取窗口句柄
                    hwnd = self.root.winfo_id()
                    
                    # 确保窗口句柄有效
                    if hwnd:
                        # 使用SetWindowPos设置窗口位置和层级，确保窗口独立显示
                        user32 = ctypes.windll.user32
                        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, 
                                           SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
                        
                        # 设置窗口样式，防止随主窗口最小化
                        GWL_EXSTYLE = -20
                        WS_EX_NOACTIVATE = 0x08000000
                        
                        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                        # 添加不激活样式，使窗口不会干扰用户操作
                        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_NOACTIVATE)
                except Exception as api_error:
                    print(f"使用Windows API设置窗口层级时出错: {api_error}")
        except Exception as e:
            print(f"设置窗口属性时出错: {e}")
        
        # 初始化拖动相关变量
        self.start_x = 0
        self.start_y = 0
        
        # 创建UI
        self.create_ui()
        
        # 绑定事件
        self.bind_events()
        
        # 运行功能列表
        self.running_features = []
        
        # 窗口可见性控制
        self.visible = True
        
        # 启动状态更新循环
        self.update_status_loop()

    def create_ui(self):
        """创建用户界面"""
        # 创建拖动栏
        self.drag_bar = tk.Frame(self.root, bg='#4a4a4a', height=30, relief='raised', bd=1)
        self.drag_bar.pack(fill='x', padx=1, pady=(1, 0))
        self.drag_bar.pack_propagate(False)  # 防止框架调整大小
        
        # 拖动栏内容
        drag_label = tk.Label(
            self.drag_bar, 
            text="功能状态", 
            bg='#4a4a4a', 
            fg='white',
            font=(SECONDARY_FONT, INPUT_FONT_SIZE, 'bold')
        )
        drag_label.pack(side='left', padx=10, pady=5)

        # 功能列表框架
        self.list_frame = tk.Frame(self.root, bg='#2d2d2d')
        self.list_frame.pack(fill='both', expand=True, padx=1, pady=1)
        
        # 创建Canvas和Scrollbar用于滚动
        self.canvas = tk.Canvas(self.list_frame, bg='#2d2d2d', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='#2d2d2d')
        
        # 绑定滚动
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 功能标签列表
        self.feature_labels = []

    def bind_events(self):
        """绑定事件"""
        # 拖动事件
        self.drag_bar.bind("<Button-1>", self.start_drag)
        self.drag_bar.bind("<B1-Motion>", self.drag_window)
        
        # 鼠标进入拖动栏改变光标
        self.drag_bar.bind("<Enter>", lambda e: self.root.config(cursor="fleur"))
        self.drag_bar.bind("<Leave>", lambda e: self.root.config(cursor=""))
        
        # 窗口点击事件
        self.root.bind("<Button-1>", self.on_window_click)

    def start_drag(self, event):
        """开始拖动"""
        self.start_x = event.x
        self.start_y = event.y

    def drag_window(self, event):
        """拖动窗口"""
        x = self.root.winfo_x() + (event.x - self.start_x)
        y = self.root.winfo_y() + (event.y - self.start_y)
        self.root.geometry(f"+{x}+{y}")

    def on_window_click(self, event):
        """窗口点击事件"""
        # 如果点击了窗口但不是拖动栏，保持窗口置顶
        self.root.attributes('-topmost', True)
        self.root.after(2000, lambda: self.root.attributes('-topmost', False))

    def update_running_features(self, features: List[str]):
        """更新运行中的功能列表"""
        self.running_features = features
        # 在主线程中更新UI
        self.root.after(0, self._update_ui)

    def _update_ui(self):
        """更新UI显示"""
        # 清除现有标签
        for label in self.feature_labels:
            label.destroy()
        self.feature_labels.clear()
        
        # 添加新的功能标签
        for i, feature in enumerate(self.running_features):
            label = tk.Label(
                self.scrollable_frame,
                text=f"• {feature}",
                bg='#2d2d2d',
                fg='#4ade80',  # 绿色
                font=(SECONDARY_FONT, INPUT_FONT_SIZE),
                anchor='w'
            )
            label.pack(fill='x', padx=10, pady=2)
            self.feature_labels.append(label)
        
        # 更新滚动区域
        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # 根据功能数量动态调整窗口大小
        self._adjust_window_size()

    def update_status_loop(self):
        """定期更新状态的循环"""
        if self.main_window_ref:
            try:
                # 从主窗口获取当前运行的功能
                running_features = []
                
                # 检查各个功能是否正在运行
                if hasattr(self.main_window_ref, 'triggerbot') and self._is_triggerbot_running():
                    running_features.append("扳机")
                if hasattr(self.main_window_ref, 'aimbot') and getattr(self.main_window_ref.aimbot, 'is_running', False):
                    running_features.append("自瞄")
                if hasattr(self.main_window_ref, 'overlay') and getattr(self.main_window_ref.overlay, 'is_running', False):
                    running_features.append("透视")
                if hasattr(self.main_window_ref, 'bunnyhop') and getattr(self.main_window_ref.bunnyhop, 'is_running', False):
                    running_features.append("连跳")
                if hasattr(self.main_window_ref, 'noflash') and getattr(self.main_window_ref.noflash, 'is_running', False):
                    running_features.append("防闪")
                if hasattr(self.main_window_ref, 'glow') and self._is_glow_running():
                    running_features.append("发光")
                
                # 更新显示
                self.update_running_features(running_features)
            except Exception as e:
                print(f"更新状态时出错: {e}")
        
        # 每秒更新一次
        self.root.after(1000, self.update_status_loop)
    
    def _is_triggerbot_running(self):
        """检查扳机功能是否实际在运行中（考虑切换模式和按键状态）"""
        triggerbot = self.main_window_ref.triggerbot
        if not getattr(triggerbot, 'is_running', False):
            return False
        
        # 检查配置是否启用
        if not self.main_window_ref.config.get("General", {}).get("Trigger", False):
            return False
        
        # 如果是切换模式，检查toggle_state是否为True
        if getattr(triggerbot, 'toggle_mode', False):
            return getattr(triggerbot, 'toggle_state', False)
        else:
            # 非切换模式下，检查触发键是否被按下
            return getattr(triggerbot, 'trigger_active', False) or \
                   (hasattr(triggerbot, 'is_mouse_trigger') and triggerbot.is_mouse_trigger and triggerbot.check_mouse_pressed())
    
    def _is_glow_running(self):
        """检查发光功能是否实际在运行中（根据配置判断）"""
        glow = self.main_window_ref.glow
        if not getattr(glow, 'is_running', False):
            return False
        
        # 检查配置是否启用
        if not self.main_window_ref.config.get("General", {}).get("Glow", False):
            return False
        
        # 检查具体的发光选项是否启用
        overlay_config = self.main_window_ref.config.get("Overlay", {})
        enable_glow = overlay_config.get("enable_glow", False)
        
        return enable_glow

    def _adjust_window_size(self):
        """根据功能数量动态调整窗口大小"""
        # 计算功能数量
        feature_count = len(self.running_features)
        
        # 设置最小和最大高度
        min_height = 60  # 最小高度，包括拖动栏（拖动栏30 + 一些边距）
        max_height = 400  # 最大高度，超过此值需要滚动
        item_height = 30  # 每个功能项的高度
        drag_bar_height = 30  # 拖动栏高度
        
        # 计算所需高度 (拖动栏 + 功能项)
        calculated_height = drag_bar_height + (feature_count * item_height)
        
        # 限制在最小和最大高度之间
        final_height = max(min_height, min(calculated_height, max_height))
        
        # 获取当前窗口位置
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        
        # 更新窗口大小
        new_width = 300  # 保持固定宽度
        self.root.geometry(f"{new_width}x{final_height}")
        
        # 如果窗口位置有效，保持位置不变
        if x > 0 and y > 0:
            self.root.geometry(f"{new_width}x{final_height}+{x}+{y}")

    def show_window(self):
        """显示窗口"""
        self.visible = True
        self.root.deiconify()

    def hide_window(self):
        """隐藏窗口"""
        self.visible = False
        self.root.withdraw()

    def set_visibility(self, visible):
        """设置窗口可见性"""
        if visible:
            self.show_window()
        else:
            self.hide_window()

    def toggle_visibility(self):
        """切换窗口可见性"""
        if self.root.winfo_viewable():
            self.hide_window()
        else:
            self.show_window()

    def run(self):
        """运行窗口主循环"""
        self.root.mainloop()

    def destroy(self):
        """销毁窗口"""
        # 先隐藏窗口，然后销毁
        self.root.withdraw()
        self.root.destroy()


if __name__ == "__main__":
    # 示例用法
    app = DraggableWindow()
    app.run()