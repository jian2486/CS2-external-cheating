import customtkinter as ctk
from tkinter import messagebox
from classes.config_manager import ConfigManager
from gui.font_manager import *

def populate_general_settings(main_window, frame):
    """
    填充常规设置选项卡，包含用于配置主应用程序功能的 UI 元素
    所有更改都会实时保存到配置中
    """
    # 为设置创建可滚动的容器
    settings = ctk.CTkScrollableFrame(
        frame,
        fg_color="transparent"
    )
    settings.pack(fill="both", expand=True, padx=40, pady=40)

    # 页面标题和副标题框架
    title_frame = ctk.CTkFrame(settings, fg_color="transparent")
    title_frame.pack(fill="x", pady=(0, 40))

    # 带图标的设置标题
    title_label = ctk.CTkLabel(
        title_frame,
        text="常规设置",
        font=(MAIN_FONT, TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    )
    title_label.pack(side="left")

    # 提供上下文的副标题
    subtitle_label = ctk.CTkLabel(
        title_frame,
        text="配置主应用程序功能",
        font=(SECONDARY_FONT, SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="w"
    )
    subtitle_label.pack(side="left", padx=(20, 0), pady=(10, 0))

    # 创建常规功能设置部分
    create_features_section(main_window, settings)
    # 创建重置部分
    create_reset_section(main_window, settings)


def create_features_section(main_window, parent):
    """创建常规功能切换部分"""
    # 具有现代样式的部分框架
    section = ctk.CTkFrame(
        parent,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    section.pack(fill="x", pady=(0, 30))

    # 部分标题和描述的标题框架
    header = ctk.CTkFrame(section, fg_color="transparent")
    header.pack(fill="x", padx=40, pady=(40, 30))

    # 带图标的章节标题
    ctk.CTkLabel(
        header,
        text="功能控制",
        font=(MAIN_FONT, SECTION_SUBTITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).pack(side="left")

    # 部分目的的描述
    ctk.CTkLabel(
        header,
        text="启用或禁用主应用程序功能",
        font=(SECONDARY_FONT, SETTING_DESCRIPTION_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).pack(side="right")

    # 带描述的功能切换开关
    features = [
        ("触发机器人", "Trigger", "当准星对准目标时自动瞄准并射击敌人"),
        ("自瞄", "Aimbot", "按下按键时自动瞄准最近的敌人头部"),
        ("ESP 叠加层", "Overlay", "显示玩家信息、方框和其他视觉辅助"),
        ("连跳", "Bunnyhop", "自动跳跃以保持动量和速度"),
        ("无闪光", "Noflash", "减少或消除屏幕上的闪光弹效果"),
        ("发光模块", "Glow", "启用或禁用发光效果")
    ]

    # 创建每个功能切换项
    create_settings_grid(
        section,
        features,
        main_window
    )

def create_settings_grid(parent, settings_list, main_window):
    """创建每行包含2个设置项的网格"""
    # 设置项网格的框架
    grid_frame = ctk.CTkFrame(parent, fg_color="transparent")
    grid_frame.pack(fill="x", padx=40, pady=(0, 30))
    
    # 在网格中创建设置项（每行2个）
    for i, (label_text, key, description) in enumerate(settings_list):
        row = i // 2
        col = i % 2
        
        # 创建设置项
        create_toggle_item(
            grid_frame,
            label_text,
            description,
            key,
            main_window,
            row,
            col
        )

def create_toggle_item(parent, label_text, description, key, main_window, row, col):
    """创建单个功能切换项，包含标签、开关和描述"""
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

    # 标签和开关的框架
    content_frame = ctk.CTkFrame(container, fg_color="transparent")
    content_frame.pack(fill="x", padx=15, pady=10)
    content_frame.grid_columnconfigure(0, weight=1)

    # 功能标签
    label = ctk.CTkLabel(
        content_frame,
        text=label_text,
        font=(MAIN_FONT, SETTING_LABEL_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff")
    )
    label.grid(row=0, column=0, sticky="w")

    # 切换功能的开关
    var = ctk.BooleanVar(value=main_window.config.get("General", {}).get(key, False))
    switch = ctk.CTkSwitch(
        content_frame,
        text="",
        variable=var,
        onvalue=True,
        offvalue=False,
        command=lambda: toggle_feature(main_window, key, var.get()),
        fg_color=("#cbd5e1", "#475569"),
        progress_color=("#D5006D", "#E91E63"),
        width=35,
        height=18
    )
    switch.grid(row=0, column=1, padx=(10, 0))

    # 功能描述
    ctk.CTkLabel(
        content_frame,
        text=description,
        font=(SECONDARY_FONT, SETTING_DESCRIPTION_FONT_SIZE),
        text_color=("#64748b", "#94a3b8")
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

    # 存储引用以供后续使用
    setattr(main_window, f"{key.lower()}_var", var)
    setattr(main_window, f"{key.lower()}_switch", switch)

def toggle_feature(main_window, feature_key, state):
    """切换功能的开启或关闭并保存配置"""
    main_window.config["General"][feature_key] = state
    main_window.save_settings()

    # 直接控制功能的启动和停止，而不仅仅是保存配置
    if feature_key == "Overlay":
        if state:
            # 如果功能正在运行则停止它
            if hasattr(main_window, 'overlay') and getattr(main_window.overlay, 'is_running', False):
                main_window._stop_feature("Overlay", main_window.overlay)
            # 启动功能
            main_window._start_feature("Overlay", main_window.overlay, main_window.config)
        else:
            # 停止功能
            main_window._stop_feature("Overlay", main_window.overlay)
    elif feature_key == "Bunnyhop":
        if state:
            # 如果功能正在运行则停止它
            if hasattr(main_window, 'bunnyhop') and getattr(main_window.bunnyhop, 'is_running', False):
                main_window._stop_feature("Bunnyhop", main_window.bunnyhop)
            # 启动功能
            main_window._start_feature("Bunnyhop", main_window.bunnyhop, main_window.config)
        else:
            # 停止功能
            main_window._stop_feature("Bunnyhop", main_window.bunnyhop)
    elif feature_key == "Trigger":
        if state:
            # 如果功能正在运行则停止它
            if hasattr(main_window, 'triggerbot') and getattr(main_window.triggerbot, 'is_running', False):
                main_window._stop_feature("TriggerBot", main_window.triggerbot)
            # 启动功能
            main_window._start_feature("TriggerBot", main_window.triggerbot, main_window.config)
        else:
            # 停止功能
            main_window._stop_feature("TriggerBot", main_window.triggerbot)
    elif feature_key == "Aimbot":
        if state:
            # 如果功能正在运行则停止它
            if hasattr(main_window, 'aimbot') and getattr(main_window.aimbot, 'is_running', False):
                main_window._stop_feature("Aimbot", main_window.aimbot)
            # 启动功能
            main_window._start_feature("Aimbot", main_window.aimbot, main_window.config)
        else:
            # 停止功能
            main_window._stop_feature("Aimbot", main_window.aimbot)
    elif feature_key == "Noflash":
        if state:
            # 如果功能正在运行则停止它
            if hasattr(main_window, 'noflash') and getattr(main_window.noflash, 'is_running', False):
                main_window._stop_feature("NoFlash", main_window.noflash)
            # 启动功能
            main_window._start_feature("NoFlash", main_window.noflash, main_window.config)
        else:
            # 停止功能
            main_window._stop_feature("NoFlash", main_window.noflash)
    elif feature_key == "Glow":
        # 更新Overlay配置中的enable_glow设置
        main_window.config["Overlay"]["enable_glow"] = state
        if hasattr(main_window, 'overlay_settings_frame'):
            # 更新视觉设置标签页中的UI控件
            if hasattr(main_window, 'enable_glow_var'):
                main_window.enable_glow_var.set(state)
        main_window.save_settings()


def create_setting_item(parent, label_text, description, widget_type, key, main_window, is_last=False):
    item_frame = ctk.CTkFrame(parent, fg_color="transparent")
    item_frame.pack(fill="x", padx=40, pady=(0, 30 if not is_last else 40))
    
    container = ctk.CTkFrame(
        item_frame,
        corner_radius=0,
        fg_color=("#f8fafc", "#252830"),
        border_width=1,
        border_color=("#e2e8f0", "#374151")
    )
    container.pack(fill="x")

    content_frame = ctk.CTkFrame(container, fg_color="transparent")
    content_frame.pack(fill="x", padx=15, pady=10)
    content_frame.grid_columnconfigure(0, weight=1)

    label = ctk.CTkLabel(
        content_frame,
        text=label_text,
        font=(MAIN_FONT, INPUT_BOLD_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff")
    )
    label.grid(row=0, column=0, sticky="w")

    if widget_type == "checkbox":
        var = ctk.BooleanVar(value=main_window.config.get("Trigger", {}).get(key, False))
        widget = ctk.CTkSwitch(
            content_frame,
            text="",
            variable=var,
            onvalue=True,
            offvalue=False,
            command=lambda: save_checkbox_setting(main_window, key, var.get()),
            fg_color=("#cbd5e1", "#475569"),
            progress_color=("#D5006D", "#E91E63"),
            width=35,
            height=18
        )
        widget.grid(row=0, column=1, padx=(10, 0))
        setattr(main_window, f"{key}_var", var)
    elif widget_type == "entry":
        entry = ctk.CTkEntry(
            content_frame,
            font=(MAIN_FONT, INPUT_FONT_SIZE),
            corner_radius=0,
            fg_color=("#f1f5f9", "#1e293b"),
            text_color=("#1f2937", "#e2e8f0"),
            border_width=2,
            border_color=("#cbd5e1", "#475569"),
            width=100,
            height=25
        )
        entry.grid(row=0, column=1, padx=(10, 0))
        current_value = main_window.config.get("Trigger", {}).get(key, "")
        entry.insert(0, str(current_value))
        entry.bind("<FocusOut>", lambda e: save_entry_setting(main_window, key, entry.get()))
        setattr(main_window, f"{key}_entry", entry)

    ctk.CTkLabel(
        content_frame,
        text=description,
        font=(SECONDARY_FONT, INPUT_FONT_SIZE),
        text_color=("#64748b", "#94a3b8")
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

def save_checkbox_setting(main_window, key, value):
    """将复选框设置保存到配置中"""
    main_window.config["Trigger"][key] = value
    main_window.save_settings()

def save_entry_setting(main_window, key, value):
    """将输入设置保存到配置中"""
    try:
        # 尝试将数值转换为浮点数
        if "." in value:
            value = float(value)
        else:
            value = int(value)
    except ValueError:
        # 如果转换失败则保持为字符串
        pass
    
    main_window.config["Trigger"][key] = value
    main_window.save_settings()

def create_reset_section(main_window, parent):
    """创建重置所有设置为默认值的部分"""
    section = ctk.CTkFrame(
        parent,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    section.pack(fill="x", pady=(0, 30))

    header = ctk.CTkFrame(section, fg_color="transparent")
    header.pack(fill="x", padx=40, pady=(40, 30))

    ctk.CTkLabel(
        header,
        text="配置管理",
        font=(MAIN_FONT, SECTION_SUBTITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).pack(side="left")

    ctk.CTkLabel(
        header,
        text="管理配置文件和设置",
        font=(SECONDARY_FONT, SETTING_DESCRIPTION_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).pack(side="right")

    button_frame = ctk.CTkFrame(section, fg_color="transparent")
    button_frame.pack(fill="x", padx=40, pady=(0, 40))

    # 创建水平排列的按钮框架
    buttons_container = ctk.CTkFrame(button_frame, fg_color="transparent")
    buttons_container.pack()

    # 添加"打开配置文件夹"按钮
    open_config_button = ctk.CTkButton(
        buttons_container,
        text="打开配置文件夹",
        command=main_window.open_config_directory,
        font=(MAIN_FONT, INPUT_BOLD_FONT_SIZE, "bold"),
        corner_radius=0,
        fg_color=("#22c55e", "#16a34a"),
        hover_color=("#16a34a", "#15803d"),
        height=35
    )
    open_config_button.pack(side="left", padx=(0, 10))

    def reset_to_defaults():
        """将所有设置重置为默认值"""
        result = messagebox.askyesno(
            "重置为默认值",
            "您确定要将所有设置重置为默认值吗？此操作无法撤销"
        )
        if result:
            ConfigManager.save_config(ConfigManager.DEFAULT_CONFIG)
            main_window.reload_config()
            messagebox.showinfo("默认值已恢复", "所有设置已重置为默认值")

    reset_button = ctk.CTkButton(
        buttons_container,
        text="重置为默认值",
        command=reset_to_defaults,
        font=(MAIN_FONT, INPUT_FONT_SIZE, "bold"),
        corner_radius=0,
        fg_color=("#ef4444", "#dc2626"),
        hover_color=("#dc2626", "#b91c1c"),
        height=35
    )
    reset_button.pack(side="left", padx=(10, 0))