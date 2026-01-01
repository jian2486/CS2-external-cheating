import customtkinter as ctk
from classes.config_manager import COLOR_CHOICES, ConfigManager
from classes.utility import Utility
from gui.font_manager import *


def save_checkbox_setting(main_window, key, value):
    """保存复选框设置到叠加层配置。"""
    try:
        main_window.overlay.config["Overlay"][key] = value
        main_window.save_settings(show_message=False)
    except Exception as e:
        # 静默处理错误以防止UI问题
        pass

def populate_overlay_settings(main_window, frame):
    """填充叠加层设置标签页与配置选项。"""
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
        text="叠加层设置",
        font=(MAIN_FONT, TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    )
    title_label.pack(side="left")

    # 提供上下文的副标题
    subtitle_label = ctk.CTkLabel(
        title_frame,
        text="配置您的ESP叠加层偏好",
        font=(SECONDARY_FONT, SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="w"
    )
    subtitle_label.pack(side="left", padx=(20, 0), pady=(10, 0))

    # 为不同的叠加层设置创建部分
    create_bounding_box_section(main_window, settings)
    create_snaplines_section(main_window, settings)
    create_text_section(main_window, settings)
    create_player_info_section(main_window, settings)
    create_team_section(main_window, settings)
    create_minimap_section(main_window, settings)

def create_bounding_box_section(main_window, parent):
    """创建包含边框配置相关设置的部分。"""
    # 创建具有现代样式的边框设置部分
    box_section = ctk.CTkFrame(
        parent,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    box_section.pack(fill="x", pady=(0, 30))

    # 部分标题和描述的框架
    header = ctk.CTkFrame(box_section, fg_color="transparent")
    header.pack(fill="x", padx=40, pady=(40, 30))

    # 带图标的部分标题
    ctk.CTkLabel(
        header,
        text="边框配置",
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).pack(side="left")

    # 部分目的的描述
    ctk.CTkLabel(
        header,
        text="敌方边框设置",
        font=(SECONDARY_FONT, SECTION_SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).pack(side="right")

    # 边框配置的设置列表
    settings_list = [
        ("启用边框", "checkbox", "enable_box", "切换敌方边框可见性"),
        ("启用骨骼ESP", "checkbox", "enable_skeleton", "切换玩家骨骼可见性"),
        ("线条粗细", "slider", "box_line_thickness", "调整边框线条粗细 (0.5-5.0)"),
        ("边框颜色", "combo", "box_color_hex", "选择边框颜色"),
        ("目标FPS", "slider", "target_fps", "调整叠加层渲染目标FPS (60-420)")
    ]

    # 创建每个设置项
    create_settings_grid(
        box_section,
        settings_list,
        main_window
    )

def create_snaplines_section(main_window, parent):
    """创建包含连线配置相关设置的部分。"""
    # 创建具有现代样式的连线设置部分
    snapline_section = ctk.CTkFrame(
        parent,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    snapline_section.pack(fill="x", pady=(0, 30))

    # 部分标题和描述的框架
    header = ctk.CTkFrame(snapline_section, fg_color="transparent")
    header.pack(fill="x", padx=40, pady=(40, 30))

    # 带图标的部分标题
    ctk.CTkLabel(
        header,
        text="连线配置",
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).pack(side="left")

    # 部分目的的描述
    ctk.CTkLabel(
        header,
        text="敌方连线设置",
        font=(SECONDARY_FONT, SECTION_SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).pack(side="right")

    # 连线配置的设置列表
    settings_list = [
        ("绘制连线", "checkbox", "draw_snaplines", "切换敌方连线绘制"),
        ("连线颜色", "combo", "snaplines_color_hex", "选择连线颜色")
    ]

    # 创建每个设置项
    create_settings_grid(
        snapline_section,
        settings_list,
        main_window
    )

def create_text_section(main_window, parent):
    """创建包含文本配置相关设置的部分。"""
    # 创建具有现代样式的文本设置部分
    text_section = ctk.CTkFrame(
        parent,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    text_section.pack(fill="x", pady=(0, 30))

    # 部分标题和描述的框架
    header = ctk.CTkFrame(text_section, fg_color="transparent")
    header.pack(fill="x", padx=40, pady=(40, 30))

    # 带图标的部分标题
    ctk.CTkLabel(
        header,
        text="文本配置",
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).pack(side="left")

    # 部分目的的描述
    ctk.CTkLabel(
        header,
        text="文本显示设置",
        font=(SECONDARY_FONT, SECTION_SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).pack(side="right")

    # 文本配置的设置列表
    settings_list = [
        ("文本颜色", "combo", "text_color_hex", "选择文本颜色")
    ]

    # 创建每个设置项
    create_settings_grid(
        text_section,
        settings_list,
        main_window
    )

def create_player_info_section(main_window, parent):
    """创建包含玩家信息配置相关设置的部分。"""
    # 创建具有现代样式的玩家信息设置部分
    player_info_section = ctk.CTkFrame(
        parent,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    player_info_section.pack(fill="x", pady=(0, 30))

    # Frame for section title and description
    header = ctk.CTkFrame(player_info_section, fg_color="transparent")
    header.pack(fill="x", padx=40, pady=(40, 30))

    # Section title with icon
    ctk.CTkLabel(
        header,
        text="玩家信息配置",
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).pack(side="left")

    # Description of section purpose
    ctk.CTkLabel(
        header,
        text="玩家信息显示设置",
        font=(SECONDARY_FONT, SECTION_SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).pack(side="right")

    # 玩家信息配置的设置列表
    settings_list = [
        ("绘制生命值", "checkbox", "draw_health_numbers", "切换生命值数字显示"),
        ("绘制昵称", "checkbox", "draw_nicknames", "切换玩家昵称显示"),
        ("使用音译", "checkbox", "use_transliteration", "切换昵称音译模式")
    ]

    # Create each setting item
    create_settings_grid(
        player_info_section,
        settings_list,
        main_window
    )

def create_team_section(main_window, parent):
    """创建包含队友配置相关设置的部分。"""
    # 创建具有现代样式的队友设置部分
    team_section = ctk.CTkFrame(
        parent,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    team_section.pack(fill="x", pady=(0, 30))

    # Frame for section title and description
    header = ctk.CTkFrame(team_section, fg_color="transparent")
    header.pack(fill="x", padx=40, pady=(40, 30))

    # Section title with icon
    ctk.CTkLabel(
        header,
        text="队友配置",
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).pack(side="left")

    # 部分目的的描述
    ctk.CTkLabel(
        header,
        text="队友显示设置",
        font=(SECONDARY_FONT, SETTING_DESCRIPTION_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).pack(side="right")

    # 队友配置的设置列表
    settings_list = [
        ("绘制队友", "checkbox", "draw_teammates", "切换队友ESP可见性"),
        ("队友颜色", "combo", "teammate_color_hex", "选择队友高亮颜色")
    ]

    # 创建每个设置项
    create_settings_grid(
        team_section,
        settings_list,
        main_window
    )

def create_minimap_section(main_window, parent):
    """创建包含小地图配置相关设置的部分。"""
    # 创建具有现代样式的 minimap 设置部分
    minimap_section = ctk.CTkFrame(
        parent,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    minimap_section.pack(fill="x", pady=(0, 30))

    # Frame for section title and description
    header = ctk.CTkFrame(minimap_section, fg_color="transparent")
    header.pack(fill="x", padx=40, pady=(40, 30))

    # Section title with icon
    ctk.CTkLabel(
        header,
        text="小地图配置",
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).pack(side="left")

    # Description of section purpose
    ctk.CTkLabel(
        header,
        text="小地图显示设置",
        font=(SECONDARY_FONT, SECTION_SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).pack(side="right")

    # 小地图配置的设置列表
    settings_list = [
        ("启用小地图", "checkbox", "enable_minimap", "切换小地图可见性"),
        ("小地图大小", "slider", "minimap_size", "调整小地图尺寸 (100-500)")
    ]

    # Create each setting item
    create_settings_grid(
        minimap_section,
        settings_list,
        main_window
    )

def create_settings_grid(parent, settings_list, main_window):
    """创建每行包含2个设置项的网格。"""
    # 设置项网格的框架
    grid_frame = ctk.CTkFrame(parent, fg_color="transparent")
    grid_frame.pack(fill="x", padx=40, pady=(0, 20))
    
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
        # 带值显示的滑块框架
        slider_container = ctk.CTkFrame(widget_frame, fg_color="transparent")
        slider_container.pack()

        # 值显示的框架
        value_frame = ctk.CTkFrame(
            slider_container,
            corner_radius=0,
            fg_color=("#D5006D", "#E91E63"),
            width=35,
            height=20
        )
        value_frame.pack(side="right", padx=(8, 0))
        value_frame.pack_propagate(False)
        
        # 具有改进样式的值标签
        # 根据键格式化值
        initial_value = main_window.overlay.config['Overlay'][key]
        if key == "target_fps":
            value_text = f"{initial_value:.0f}"
        elif key == "minimap_size":
            value_text = f"{initial_value:.0f}"
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
            command=lambda e: update_slider_value(e, key, main_window)
        )
        widget.set(main_window.overlay.config["Overlay"][key])
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

def update_slider_value(event, key, main_window):
    """更新滑块值标签并保存设置。"""
    try:
        value = main_window.__getattribute__(f"{key}_slider").get()
        
        # 根据键格式化值
        if key == "target_fps":
            formatted_value = f"{value:.0f}"
        elif key == "minimap_size":
            formatted_value = f"{value:.0f}"
        else:
            formatted_value = f"{value:.1f}"
            
        main_window.__getattribute__(f"{key}_slider").value_label.configure(text=formatted_value)
        main_window.save_settings(show_message=False)
    except Exception as e:
        # 静默处理错误以防止UI问题
        pass
