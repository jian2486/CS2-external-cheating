import customtkinter as ctk
from pathlib import Path
from classes.logger import Logger
from classes.config_manager import ConfigManager
from gui.font_manager import *

# 缓存日志记录器实例
logger = Logger.get_logger()

def populate_dashboard(main_window, frame):
    """填充仪表板框架，包含状态卡片、控制按钮"""
    # 仪表板内容的可滚动容器
    dashboard = ctk.CTkScrollableFrame(
        frame,
        fg_color="transparent"
    )
    dashboard.pack(fill="both", expand=True, padx=40, pady=40)
    
    # 页面标题和副标题框架
    title_frame = ctk.CTkFrame(dashboard, fg_color="transparent")
    title_frame.pack(fill="x", pady=(0, 30))
    
    # 仪表板标题带图标
    title_label = ctk.CTkLabel(
        title_frame,
        text="仪表板",
        font=(MAIN_FONT, TITLE_FONT_SIZE, "bold"),
        text_color=("#FF0000", "#FF0000")
    )
    title_label.pack(side="left")
    
    # 提供上下文的副标题
    subtitle_label = ctk.CTkLabel(
        title_frame,
        text="监控和控制您的 CS2 客户端",
        font=(SECONDARY_FONT, SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8")
    )
    subtitle_label.pack(side="left", padx=(20, 0), pady=(10, 0))
    
    # 创建一个水平框架来放置版本卡片和控制面板
    top_frame = ctk.CTkFrame(dashboard, fg_color="transparent")
    top_frame.pack(fill="x", pady=(0, 40))
    
    # 配置网格行列
    top_frame.grid_columnconfigure(0, weight=1)
    top_frame.grid_columnconfigure(1, weight=2)
    top_frame.grid_rowconfigure(0, weight=1)
    
    # 版本卡片框架
    version_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
    version_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    
    # 版本卡片
    version_card, version_value_label = create_stat_card(
        main_window,
        version_frame,
        "版本",
        f"{ConfigManager.VERSION}",
        "#D5006D",
        "当前应用程序版本"
    )
    version_card.pack(fill="both", expand=True)
    
    # 控制面板部分
    control_panel = ctk.CTkFrame(
        top_frame,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=3,
        border_color=("#e2e8f0", "#2d3748")
    )
    control_panel.grid(row=0, column=1, sticky="ew", padx=(10, 0))
    
    # 控制面板标题
    control_header = ctk.CTkFrame(control_panel, fg_color="transparent")
    control_header.pack(fill="x", padx=40, pady=(40, 30))
    
    # 控制中心标题
    ctk.CTkLabel(
        control_header,
        text="控制中心",
        font=(MAIN_FONT, SECTION_SUBTITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff")
    ).pack(side="left")
    
    # 控制按钮框架
    control_buttons = ctk.CTkFrame(control_panel, fg_color="transparent")
    control_buttons.pack(fill="x", padx=40, pady=(0, 40))
    
    # 创建更新偏移量按钮和启动/停止按钮的容器
    buttons_container = ctk.CTkFrame(control_buttons, fg_color="transparent")
    buttons_container.pack(fill="x", expand=True)
    
    # 第一行：更新偏移量按钮
    update_frame = ctk.CTkFrame(buttons_container, fg_color="transparent")
    update_frame.pack(fill="x", pady=(0, 10))
    
    # 检查output目录中offsets文件的最后修改时间
    last_update_text = "从未"
    try:
        import datetime as dt
        offsets_dir = Path("CS2-external-cheating/Offsets")
        offsets_file = offsets_dir / "offsets.json"
        if offsets_file.exists():
            mtime = offsets_file.stat().st_mtime
            last_update = dt.datetime.fromtimestamp(mtime)
            last_update_text = last_update.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        logger.warning(f"获取偏移量文件更新时间失败: {e}")

    # 更新偏移量按钮
    main_window.update_offsets_button = ctk.CTkButton(
        update_frame,
        text="更新偏移量",
        command=main_window.update_offsets,
        height=40,
        corner_radius=0,
        fg_color=("#2563eb", "#3b82f6"),
        hover_color=("#1d4ed8", "#2563eb"),
        font=(MAIN_FONT, INPUT_BOLD_FONT_SIZE, "bold")
    )
    main_window.update_offsets_button.pack(side="left", padx=(0, 10))
    
    # 上次更新时间标签
    main_window.last_update_label = ctk.CTkLabel(
        update_frame,
        text="上次更新:",
        font=(THIRDLY_FONT, SETTING_DESCRIPTION_FONT_SIZE),
        text_color=("#64748b", "#94a3b8")
    )
    main_window.last_update_label.pack(side="left", pady=(3, 0))
    
    # 更新时间标签（显示具体时间）
    main_window.update_time_label = ctk.CTkLabel(
        update_frame,
        text=last_update_text,
        font=(MAIN_FONT, SLIDER_VALUE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff")
    )
    main_window.update_time_label.pack(side="left", pady=(5, 0))
    
    # 第二行：启动和停止按钮
    action_frame = ctk.CTkFrame(buttons_container, fg_color="transparent")
    action_frame.pack(fill="x", pady=(10, 0))
    
    # 带播放图标的启动按钮
    start_button = ctk.CTkButton(
        action_frame,
        text="启动客户端",
        command=main_window.start_client,
        width=190,
        height=40,
        corner_radius=0,
        fg_color=("#22c55e", "#16a34a"),
        hover_color=("#16a34a", "#15803d"),
        font=(MAIN_FONT, INPUT_BOLD_FONT_SIZE, "bold"),
        border_width=2,
        border_color=("#16a34a", "#15803d")
    )
    start_button.pack(side="left", padx=(0, 20))
    
    # 带停止图标的停止按钮
    stop_button = ctk.CTkButton(
        action_frame,
        text="停止客户端",
        command=main_window.stop_client,
        width=190,
        height=40,
        corner_radius=0,
        fg_color=("#ef4444", "#dc2626"),
        hover_color=("#dc2626", "#b91c1c"),
        font=(MAIN_FONT, INPUT_BOLD_FONT_SIZE, "bold"),
        border_width=2,
        border_color=("#dc2626", "#b91c1c")
    )
    stop_button.pack(side="left")
    
    # 使用注意事项部分
    disclaimer_section = ctk.CTkFrame(
        dashboard,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=3,
        border_color=("#e2e8f0", "#2d3748")
    )
    disclaimer_section.pack(fill="x", pady=(0, 20))
    
    # 注意事项标题
    disclaimer_header = ctk.CTkFrame(disclaimer_section, fg_color="transparent")
    disclaimer_header.pack(fill="x", padx=40, pady=(30, 20))
    
    ctk.CTkLabel(
        disclaimer_header,
        text="使用注意事项",
        font=(MAIN_FONT, SECTION_SUBTITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff")
    ).pack(side="left")
    
    # 注意事项内容
    disclaimer_content = ctk.CTkFrame(disclaimer_section, fg_color="transparent")
    disclaimer_content.pack(fill="x", padx=40, pady=(0, 30))
    
    # 注意事项列表
    disclaimer_items = [
        "视觉效果类功能（如发光效果）涉及到外部程序修改游戏内存，可能会增大被反作弊系统检测的风险",
        "骨骼绘制功能会显著增加系统资源消耗，可能导致游戏帧率明显下降以及cpu占用率增加",
        "视觉效果无法反截屏，他们通过直接修改游戏内存改变游戏逻辑，属于游戏内部，因此无法反截屏"
    ]
    
    for item in disclaimer_items:
        ctk.CTkLabel(
            disclaimer_content,
            text=item,
            font=(SECONDARY_FONT, SETTING_DESCRIPTION_FONT_SIZE),
            text_color=("#64748b", "#94a3b8"),
            anchor="w",  # 左对齐
            wraplength=1200,  # 增加换行长度，避免单字换行
            justify="left"  # 文本左对齐
        ).pack(fill="x", pady=(5, 0))

    # 免责声明部分
    disclaimer_section = ctk.CTkFrame(
        dashboard,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=3,
        border_color=("#e2e8f0", "#2d3748")
    )
    disclaimer_section.pack(fill="x", pady=(0, 20))

    disclaimer_header = ctk.CTkFrame(disclaimer_section, fg_color="transparent")
    disclaimer_header.pack(fill="x", padx=40, pady=(30, 20))

    ctk.CTkLabel(
        disclaimer_header,
        text="该程序仅用于学习和研究目的，不在多人游戏中使用该作弊\n"
             "任何使用和分发该程序的行为导致的后果均由用户承担责任",
        font=(MAIN_FONT, 22, "bold"),
        text_color=("#ef4444", "#dc2626"),
        justify="left",
    ).pack(side="left")





def create_stat_card(main_window, parent, title, value, color, subtitle):
    """创建现代状态卡片并返回卡片和数值标签"""
    # 具有增强现代样式的卡片框架
    card = ctk.CTkFrame(
        parent,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=3,
        border_color=("#e2e8f0", "#2d3748")
    )
    
    # 卡片内具有更多填充的内容框架
    content = ctk.CTkFrame(card, fg_color="transparent")
    content.pack(fill="both", expand=True, padx=30, pady=30)
    
    # 具有改进样式的卡片标题
    ctk.CTkLabel(
        content,
        text=title,
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#64748b", "#94a3b8"),
        anchor="w"
    ).pack(fill="x", pady=(0, 15))
    
    # 具有增强字体和动态颜色的数值标签
    value_label = ctk.CTkLabel(
        content,
        text=value,
        font=(MAIN_FONT, TITLE_FONT_SIZE, "bold"),
        text_color=color,
        anchor="w"
    )
    value_label.pack(fill="x", pady=(0, 10))
    
    # 提供上下文的副标题，具有改进的样式
    ctk.CTkLabel(
        content,
        text=subtitle,
        font=(SECONDARY_FONT, SUBTITLE_FONT_SIZE),
        text_color=("#94a3b8", "#64748b"),
        anchor="w"
    ).pack(fill="x")
    
    return card, value_label

# 注意：此函数当前未使用，因为主要的update_client_status在main_window.py中
def update_client_status(self, status, color):
    """更新仪表板中的客户端状态指示器"""
    # 更新标题状态标签
    self.status_label.configure(text=status, text_color=color)

    # 更新标题中的状态点颜色
    for widget in self.status_frame.winfo_children():
        if isinstance(widget, ctk.CTkFrame) and widget.cget("width") == 12:
            widget.configure(fg_color=color)
            break