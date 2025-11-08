"""视觉设置标签页模块"""

import customtkinter as ctk
from classes.config_manager import COLOR_CHOICES, ConfigManager
from classes.utility import Utility
from gui.font_manager import *
from gui.overlay_settings_tab import save_checkbox_setting, update_slider_value
from gui.additional_settings_tab import update_slider_value as noflash_update_slider_value


def populate_visual_settings(main_window, frame):
    """填充视觉设置标签页与配置选项。"""
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
        text="视觉效果设置",
        font=(MAIN_FONT, TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    )
    title_label.pack(side="left")

    # 提供上下文的副标题
    subtitle_label = ctk.CTkLabel(
        title_frame,
        text="配置您的视觉效果偏好",
        font=(SECONDARY_FONT, SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="w"
    )
    subtitle_label.pack(side="left", padx=(20, 0), pady=(10, 0))

    # 为不同的视觉效果设置创建部分
    create_glow_section(main_window, settings)
    create_noflash_section(main_window, settings)

def create_glow_section(main_window, parent):
    """创建包含发光配置相关设置的部分。"""
    # 创建具有现代样式的发光设置部分
    glow_section = ctk.CTkFrame(
        parent,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    glow_section.pack(fill="x", pady=(0, 30))

    # 部分标题和描述的框架
    header = ctk.CTkFrame(glow_section, fg_color="transparent")
    header.pack(fill="x", padx=40, pady=(40, 30))

    # 带图标的部分标题
    ctk.CTkLabel(
        header,
        text="发光效果配置",
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).pack(side="left")

    # 部分目的的描述
    ctk.CTkLabel(
        header,
        text="发光效果设置",
        font=(SECONDARY_FONT, SECTION_SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).pack(side="right")

    # 发光配置的设置列表
    settings_list = [
        ("启用发光效果", "checkbox", "enable_glow", "切换发光效果可见性"),
        ("不对尸体发光", "checkbox", "glow_exclude_dead", "切换是否对尸体应用发光效果"),
        ("队友发光", "checkbox", "glow_teammates", "切换是否对队友应用发光效果"),
        ("发光粗细", "slider", "glow_thickness", "调整发光效果粗细 (0.5-5.0)"),
        ("敌人发光颜色", "combo", "glow_color_hex", "选择敌人发光效果颜色"),
        ("队友发光颜色", "combo", "glow_teammate_color_hex", "选择队友发光效果颜色")
    ]

    # 创建每个设置项
    create_settings_grid(
        glow_section,
        settings_list,
        main_window
    )

def create_noflash_section(main_window, parent):
    """创建包含无闪光配置相关设置的部分。"""
    # 创建具有现代样式的无闪光设置部分
    noflash_section = ctk.CTkFrame(
        parent,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    noflash_section.pack(fill="x", pady=(0, 30))

    # 部分标题和描述的框架
    header = ctk.CTkFrame(noflash_section, fg_color="transparent")
    header.pack(fill="x", padx=40, pady=(40, 30))

    # 带图标的部分标题
    ctk.CTkLabel(
        header,
        text="无闪光配置",
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).pack(side="left")

    # 部分目的的描述
    ctk.CTkLabel(
        header,
        text="控制闪光抑制行为",
        font=(SECONDARY_FONT, SECTION_SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).pack(side="right")

    # 无闪光配置的设置列表
    settings_list = [
        ("闪光抑制强度", "slider", "FlashSuppressionStrength", "闪光抑制的强度 (0.0-1.0)")
    ]

    # 创建每个设置项
    create_settings_grid(
        noflash_section,
        settings_list,
        main_window
    )

def create_settings_grid(parent, settings_list, main_window):
    """创建每行2个项目的设置网格。"""
    # 设置项目网格的框架
    grid_frame = ctk.CTkFrame(parent, fg_color="transparent")
    grid_frame.pack(fill="x", padx=40, pady=(0, 20))
    
    # 在网格中创建设置项目（每行2个）
    for i, (label_text, widget_type, key, description) in enumerate(settings_list):
        row = i // 2
        col = i % 2
        
        # 创建设置项目
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
    """创建具有改进样式的标准化设置项目。"""
    # 具有悬停效果的容器
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

    # 容器内的内容框架
    content_frame = ctk.CTkFrame(container, fg_color="transparent")
    content_frame.pack(fill="x", padx=15, pady=10)
    content_frame.grid_columnconfigure(0, weight=1)

    # 设置名称标签
    ctk.CTkLabel(
        content_frame,
        text=label_text,
        font=(MAIN_FONT, SETTING_LABEL_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).grid(row=0, column=0, sticky="w")

    # 设置描述
    ctk.CTkLabel(
        content_frame,
        text=description,
        font=(SECONDARY_FONT, SETTING_DESCRIPTION_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="w"
    ).grid(row=1, column=0, sticky="w", pady=(2, 0))

    # 输入控件框架
    widget_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    widget_frame.grid(row=0, column=1, rowspan=2, padx=(10, 0))

    # 根据类型创建控件
    if widget_type == "checkbox":
        var = ctk.BooleanVar(value=main_window.overlay.config["Overlay"][key])
        widget = ctk.CTkSwitch(
            widget_frame,
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
        widget.pack()
        main_window.__setattr__(f"{key}_var", var)
        
    elif widget_type == "slider":
        # 带数值显示的滑块容器
        slider_container = ctk.CTkFrame(widget_frame, fg_color="transparent")
        slider_container.pack()

        # 数值显示框架
        value_frame = ctk.CTkFrame(
            slider_container,
            corner_radius=0,
            fg_color=("#D5006D", "#E91E63"),
            width=35,
            height=20
        )
        value_frame.pack(side="right", padx=(8, 0))
        value_frame.pack_propagate(False)
        
        # 格式化数值标签
        # 根据键格式化数值
        if key == "FlashSuppressionStrength":
            initial_value = main_window.noflash.config['NoFlash'].get(key, 0.0)
        else:
            initial_value = main_window.overlay.config['Overlay'][key]
            
        if key == "target_fps":
            value_text = f"{initial_value:.0f}"
        elif key == "minimap_size":
            value_text = f"{initial_value:.0f}"
        elif key == "glow_thickness":
            value_text = f"{initial_value:.1f}"
        elif key == "FlashSuppressionStrength":
            value_text = f"{initial_value:.2f}"
        else:
            value_text = f"{initial_value:.1f}"
            
        value_label = ctk.CTkLabel(
            value_frame,
            text=value_text,
            font=(MAIN_FONT, INPUT_BOLD_FONT_SIZE, "bold"),
            text_color=("#1f2937", "#ffffff")
        )
        value_label.pack(expand=True)
        
        # 根据键设置滑块参数
        if key == "box_line_thickness":
            from_val, to_val, steps = 0.5, 5.0, 9
        elif key == "target_fps":
            from_val, to_val, steps = 60, 420, 3
        elif key == "minimap_size":
            from_val, to_val, steps = 100, 500, 40
        elif key == "glow_thickness":
            from_val, to_val, steps = 0.5, 5.0, 9
        elif key == "FlashSuppressionStrength":
            from_val, to_val, steps = 0.0, 1.0, 100
            initial_value = main_window.noflash.config['NoFlash'].get(key, 0.0)
            value_text = f"{initial_value:.2f}"
        else:
            from_val, to_val, steps = 0.0, 1.0, 100
            
        # 具有自定义样式的增强滑块
        widget = ctk.CTkSlider(
            slider_container,
            from_=from_val,
            to=to_val,
            number_of_steps=steps,
            width=120,
            height=14,
            corner_radius=0,
            button_corner_radius=0,
            border_width=0,
            fg_color=("#e2e8f0", "#374151"),
            progress_color=("#D5006D", "#E91E63"),
            button_color=("#ffffff", "#ffffff"),
            button_hover_color=("#f8fafc", "#f8fafc"),
            command=lambda e: update_slider_value(e, key, main_window) if key != "FlashSuppressionStrength" 
                              else noflash_update_slider_value(e, key, main_window)
        )
        widget.set(initial_value)
        widget.pack(side="left")
        
        # 存储引用以供后续使用
        widget.value_label = value_label
        main_window.__setattr__(f"{key}_slider", widget)
        main_window.__setattr__(f"{key}_value_label", value_label)

    elif widget_type == "combo":
        # 具有改进样式的增强组合框
        widget = ctk.CTkComboBox(
            widget_frame,
            values=list(COLOR_CHOICES.keys()),
            width=100,
            height=25,
            corner_radius=0,
            border_width=2,
            border_color=("#d1d5db", "#374151"),
            fg_color=("#ffffff", "#1f2937"),
            text_color=("#1f2937", "#ffffff"),
            font=(MAIN_FONT, INPUT_FONT_SIZE),
            dropdown_font=(MAIN_FONT, DROPDOWN_MENU_FONT_SIZE),
            button_color=("#D5006D", "#E91E63"),
            button_hover_color=("#B8004A", "#C2185B"),
            dropdown_fg_color=("#ffffff", "#1a1b23"),
            dropdown_hover_color=("#f8fafc", "#2d3748"),
            dropdown_text_color=("#1f2937", "#ffffff"),
            state="readonly",
            justify="center",
            command=lambda e: main_window.save_settings(show_message=False)
        )
        widget.set(Utility.get_color_name_from_hex(main_window.overlay.config["Overlay"][key]))
        widget.bind("<FocusOut>", lambda e: main_window.save_settings(show_message=False))
        widget.bind("<Return>", lambda e: main_window.save_settings(show_message=False))
        widget.pack()
        main_window.__setattr__(f"{key}_combo", widget)

    elif widget_type == "entry":
        widget = ctk.CTkEntry(
            widget_frame,
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
        widget.pack()
        main_window.__setattr__(f"{key}_entry", widget)