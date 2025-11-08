import customtkinter as ctk
from classes.config_manager import ConfigManager
from gui.font_manager import *
from gui.additional_settings_tab import create_settings_grid, start_bunnyhop_key_detection

def populate_movement_settings(main_window, frame):
    """使用连跳配置选项填充移动设置标签页。"""
    # 为设置创建可滚动的容器
    settings = ctk.CTkScrollableFrame(
        frame,
        fg_color="transparent"
    )
    settings.pack(fill="both", expand=True, padx=40, pady=40)

    # 页面标题和副标题框架
    title_frame = ctk.CTkFrame(settings, fg_color="transparent")
    title_frame.pack(fill="x", pady=(0, 40))

    # 带图标的页面标题
    title_label = ctk.CTkLabel(
        title_frame,
        text="移动设置",
        font=(MAIN_FONT, TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    )
    title_label.pack(side="left")

    # 提供上下文的副标题
    subtitle_label = ctk.CTkLabel(
        title_frame,
        text="配置移动相关功能",
        font=(SECONDARY_FONT, SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="w"
    )
    subtitle_label.pack(side="left", padx=(20, 0), pady=(10, 0))

    # 创建具有现代样式的连跳设置部分
    bunnyhop_section = ctk.CTkFrame(
        settings,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    bunnyhop_section.pack(fill="x", pady=(0, 30))

    # 部分标题和描述的框架
    bunnyhop_header = ctk.CTkFrame(bunnyhop_section, fg_color="transparent")
    bunnyhop_header.pack(fill="x", padx=40, pady=(40, 30))

    # 带图标的部分标题
    ctk.CTkLabel(
        bunnyhop_header,
        text="连跳配置",
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).pack(side="left")

    # 部分目的的描述
    ctk.CTkLabel(
        bunnyhop_header,
        text="控制连跳行为",
        font=(SECONDARY_FONT, SECTION_SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).pack(side="right")

    # 连跳配置的设置列表
    bunnyhop_settings_list = [
        ("跳跃键", "entry", "JumpKey", "激活连跳的按键 (如:'space'或'mouse4')"),
        ("跳跃延迟", "entry", "JumpDelay", "跳跃之间的延迟（秒）(0.01-0.5)")
    ]

    # 在网格中创建每个设置项
    create_settings_grid(
        bunnyhop_section,
        bunnyhop_settings_list,
        main_window
    )

def create_settings_grid(parent, settings_list, main_window):
    """创建每行2项设置的网格。"""
    # 设置项网格的框架
    grid_frame = ctk.CTkFrame(parent, fg_color="transparent")
    grid_frame.pack(fill="x", padx=40, pady=(0, 30))
    
    # 在网格中创建设置项（每行2项）
    for i, (label_text, widget_type, key, description) in enumerate(settings_list):
        row = i // 2
        col = i % 2
        
        # 创建设置项
        create_setting_item(
            grid_frame,
            label_text,
            description,
            widget_type,
            key,
            main_window,
            row,
            col
        )
        
def create_setting_item(parent, label_text, description, widget_type, key, main_window, row, col):
    """创建具有改进样式的标准化设置项。"""
    # 带悬停效果的容器
    container = ctk.CTkFrame(
        parent,
        corner_radius=0,
        fg_color=("#f8fafc", "#252830"),
        border_width=1,
        border_color=("#e2e8f0", "#374151")
    )
    container.grid(row=row, column=col, padx=(0, 15) if col == 0 else (15, 0), pady=(0, 15), sticky="ew")
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_columnconfigure(1, weight=1)

    # 容器内内容的框架
    content_frame = ctk.CTkFrame(container, fg_color="transparent")
    content_frame.pack(fill="x", padx=15, pady=10)
    content_frame.grid_columnconfigure(0, weight=1)

    # 设置名称的标签
    ctk.CTkLabel(
        content_frame,
        text=label_text,
        font=(MAIN_FONT, SETTING_LABEL_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).grid(row=0, column=0, sticky="w")

    # 设置的描述
    ctk.CTkLabel(
        content_frame,
        text=description,
        font=(SECONDARY_FONT, SETTING_DESCRIPTION_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="w"
    ).grid(row=1, column=0, sticky="w", pady=(2, 0))

    # 输入控件的框架
    widget_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    widget_frame.grid(row=0, column=1, rowspan=2, padx=(10, 0))

    # 根据类型创建控件
    if widget_type == "entry":
        var = ctk.StringVar()
        config_section = "Bunnyhop"  # 连跳配置部分
        current_value = main_window.bunnyhop.config.get(config_section, {}).get(key, "")
        var.set(str(current_value))
        widget = ctk.CTkEntry(
            widget_frame,
            textvariable=var,
            width=100,
            height=25,
            corner_radius=0,
            border_width=2,
            border_color=("#d1d5db", "#374151"),
            fg_color=("#ffffff", "#1f2937"),
            text_color=("#1f2937", "#ffffff"),
            font=(MAIN_FONT, INPUT_FONT_SIZE),
            justify="center"
        )
        
        if key == "JumpKey":
            # 为跳跃键设置特殊处理
            main_window.jump_key_entry = widget
            widget.configure(state="disabled")  # 禁用输入功能
            # 绑定点击事件开始按键检测
            widget.bind("<Button-1>", lambda e: start_bunnyhop_key_detection(main_window))
        else:
            # 为其他输入框绑定失去焦点事件
            widget.bind("<FocusOut>", lambda e, k=key, v=var: save_entry_setting(main_window, k, v.get()))
        
        widget.pack()
        main_window.__setattr__(f"{key}_entry", widget)
                    
def save_entry_setting(main_window, key, value):
    """将输入设置保存到配置中。"""
    try:
        # 尝试将数值转换为浮点数
        if "." in value:
            value = float(value)
        else:
            value = int(value)
    except ValueError:
        # 如果转换失败则保持为字符串
        pass
    
    main_window.bunnyhop.config["Bunnyhop"][key] = value
    main_window.save_settings()