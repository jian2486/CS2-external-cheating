import customtkinter as ctk
import threading
import time
import keyboard
from classes.config_manager import ConfigManager
from classes.logger import Logger
from gui.font_manager import *

def start_bunnyhop_key_detection(main_window):
    """开始检测连跳按键"""
    # 检查是否已经在进行按键检测
    if hasattr(main_window, 'bunnyhop_key_detection_active') and main_window.bunnyhop_key_detection_active:
        return
    
    # 标记按键检测正在进行
    main_window.bunnyhop_key_detection_active = True
    main_window.jump_key_entry.configure(state="normal")
    main_window.jump_key_entry.delete(0, "end")
    main_window.jump_key_entry.insert(0, "按下任意键...")
    main_window.jump_key_entry.configure(state="disabled")
    
    def detect_key():
        global key_detection_active
        try:
            # 等待按键释放，避免捕获到之前按下的键
            while keyboard.is_pressed('shift') or keyboard.is_pressed('ctrl') or keyboard.is_pressed('alt'):
                time.sleep(0.05)
            
            event = keyboard.read_event()
            while event.event_type != keyboard.KEY_DOWN:
                event = keyboard.read_event()
            
            key_name = event.name.lower()
            
            # 特殊键名映射
            special_keys = {
                'space': 'space',
                'enter': 'enter',
                'esc': 'esc',
                'backspace': 'backspace',
                'tab': 'tab',
                'caps lock': 'capslock',
                'windows': 'win',
                'right windows': 'rwin',
                'alt gr': 'altgr',
                'print screen': 'printscreen',
                'scroll lock': 'scrolllock',
                'pause': 'pause',
                'insert': 'insert',
                'home': 'home',
                'page up': 'pageup',
                'delete': 'delete',
                'end': 'end',
                'page down': 'pagedown',
                'right arrow': 'right',
                'left arrow': 'left',
                'down arrow': 'down',
                'up arrow': 'up'
            }
            
            if key_name in special_keys:
                key_name = special_keys[key_name]
            elif len(key_name) > 1:
                # 处理功能键
                if key_name.startswith('f') and key_name[1:].isdigit():
                    pass  # 保持原样，如 f1, f2 等
                else:
                    key_name = key_name.replace(' ', '')
            
            main_window.root.after(0, lambda: finish_bunnyhop_key_detection(main_window, key_name))
        except Exception as e:
            main_window.root.after(0, lambda: finish_bunnyhop_key_detection(main_window, "space"))
        finally:
            main_window.bunnyhop_key_detection_active = False
    
    threading.Thread(target=detect_key, daemon=True).start()

def finish_bunnyhop_key_detection(main_window, key_name):
    """完成连跳按键检测并更新UI"""
    main_window.jump_key_entry.configure(state="normal")
    main_window.jump_key_entry.delete(0, "end")
    main_window.jump_key_entry.insert(0, key_name)
    main_window.jump_key_entry.configure(state="disabled")
    
    # 更新配置
    main_window.bunnyhop.config['Bunnyhop']['JumpKey'] = key_name
    main_window.save_settings()

def populate_additional_settings(main_window, frame):
    """填充附加设置标签页"""
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
        text="附加设置",
        font=(MAIN_FONT, TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    )
    title_label.pack(side="left")

    # 提供上下文的副标题
    subtitle_label = ctk.CTkLabel(
        title_frame,
        text="配置其他偏好设置",
        font=(SECONDARY_FONT, SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="w"
    )
    subtitle_label.pack(side="left", padx=(20, 0), pady=(10, 0))

    # 创建具有现代样式的渲染模式设置部分
    render_mode_section = ctk.CTkFrame(
        settings,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    render_mode_section.pack(fill="x", pady=(0, 30))

    # 部分标题和描述的框架
    render_mode_header = ctk.CTkFrame(render_mode_section, fg_color="transparent")
    render_mode_header.pack(fill="x", padx=40, pady=(40, 30))

    # 带图标的部分标题
    ctk.CTkLabel(
        render_mode_header,
        text="渲染模式",
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).pack(side="left")

    # 部分目的的描述
    ctk.CTkLabel(
        render_mode_header,
        text="选择叠加层渲染后端",
        font=(SECONDARY_FONT, SECTION_SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).pack(side="right")

    # 渲染模式配置的设置列表
    render_mode_settings_list = [
        ("渲染后端", "combobox", "RenderMode", "选择渲染后端技术")
    ]

    # 创建每个设置项
    create_settings_grid(
        render_mode_section,
        render_mode_settings_list,
        main_window
    )

    # 创建具有现代样式的防截屏设置部分
    anti_screenshot_section = ctk.CTkFrame(
        settings,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    anti_screenshot_section.pack(fill="x", pady=(0, 30))

    # 部分标题和描述的框架
    anti_screenshot_header = ctk.CTkFrame(anti_screenshot_section, fg_color="transparent")
    anti_screenshot_header.pack(fill="x", padx=40, pady=(40, 30))

    # 带图标的部分标题
    ctk.CTkLabel(
        anti_screenshot_header,
        text="防截屏设置",
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).pack(side="left")

    # 部分目的的描述
    ctk.CTkLabel(
        anti_screenshot_header,
        text="防止窗口被截屏或录屏",
        font=(SECONDARY_FONT, SECTION_SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).pack(side="right")

    # 防截屏配置的设置列表
    anti_screenshot_settings_list = [
        ("启用防截屏", "checkbox", "AntiScreenshot", "防止窗口被截屏或录屏")
    ]

    # 创建每个设置项
    create_settings_grid(
        anti_screenshot_section,
        anti_screenshot_settings_list,
        main_window
    )

def create_settings_grid(parent, settings_list, main_window):
    """创建每行2项设置的网格"""
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
    """创建具有改进样式的标准化设置项"""
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
        if key == "JumpKey":
            main_window.jump_key_entry = widget
            widget.insert(0, main_window.bunnyhop.config.get('Bunnyhop', {}).get('JumpKey', 'space'))
            widget.bind("<FocusOut>", lambda e: main_window.save_settings())
            widget.bind("<Return>", lambda e: main_window.save_settings())
            # 绑定点击事件开始按键检测
            widget.bind("<Button-1>", lambda e: start_bunnyhop_key_detection(main_window))
        elif key == "JumpDelay":
            main_window.jump_delay_entry = widget
            widget.insert(0, str(main_window.bunnyhop.config.get('Bunnyhop', {}).get('JumpDelay', 0.01)))
            widget.bind("<FocusOut>", lambda e: main_window.save_settings())
            widget.bind("<Return>", lambda e: main_window.save_settings())
        widget.pack()

    elif widget_type == "slider":
        # Create container for slider and value display
        slider_container = ctk.CTkFrame(
            widget_frame,
            fg_color="transparent"
        )
        slider_container.pack()

        # Create frame for value label with background
        value_frame = ctk.CTkFrame(
            slider_container,
            corner_radius=0,
            fg_color=("#e2e8f0", "#374151"),
            width=40,
            height=20
        )
        value_frame.pack(side="right", padx=(8, 0))
        value_frame.pack_propagate(False)

        # Value label with improved styling
        value_label = ctk.CTkLabel(
            value_frame,
            text=f"{main_window.noflash.config['NoFlash'].get(key, 0.0):.2f}",
            font=(MAIN_FONT, INPUT_BOLD_FONT_SIZE, "bold"),
            text_color=("#1f2937", "#ffffff")
        )
        value_label.pack(expand=True)

        # Enhanced slider with custom styling
        widget = ctk.CTkSlider(
            slider_container,
            from_=0.0,
            to=1.0,
            number_of_steps=100,
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
        widget.set(main_window.noflash.config["NoFlash"].get(key, 0.0))
        widget.pack(side="left")

        # Store reference for later use
        widget.value_label = value_label
        main_window.__setattr__(f"{key}_slider", widget)
        main_window.__setattr__(f"{key}_value_label", value_label)
        
    elif widget_type == "combobox":
        # Create render mode combobox
        render_modes = ["默认(pyMeow)", "OpenGL", "Vulkan"]
        var = ctk.StringVar(value=main_window.config["General"].get(key, "默认(pyMeow)"))
        widget = ctk.CTkComboBox(
            widget_frame,
            values=render_modes,
            variable=var,
            width=150,
            height=30,
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
        widget.set(main_window.config["General"].get(key, "默认(pyMeow)"))
        widget.pack()
        main_window.__setattr__("render_mode_var", var)
        
    elif widget_type == "checkbox":
        # Create anti-screenshot checkbox
        var = ctk.BooleanVar()
        config = ConfigManager.load_config()
        var.set(config["General"].get(key, False))  # 默认设置为False（不开启）
        widget = ctk.CTkCheckBox(
            widget_frame,
            text="",
            variable=var,
            width=40,
            height=20,
            corner_radius=0,
            border_width=2,
            border_color=("#d1d5db", "#374151"),
            fg_color=("#D5006D", "#E91E63"),
            hover_color=("#B8004A", "#C2185B"),
            command=lambda: toggle_anti_screenshot(main_window, var.get())
        )
        widget.pack()
        main_window.__setattr__(f"{key}_var", var)

def toggle_anti_screenshot(main_window, enabled):
    """切换防截屏功能"""
    try:
        # 更新配置
        main_window.config["General"]["AntiScreenshot"] = enabled
        main_window.save_settings(show_message=False)
        
        # 通知affinity manager更新状态
        if hasattr(main_window, 'affinity_manager'):
            main_window.affinity_manager.set_anti_screenshot_enabled(enabled)
    except Exception as e:
        logger = Logger.get_logger()
        logger.error(f"切换防截屏功能时出错: {e}")

def update_slider_value(event, key, main_window):
    """更新滑块值标签并保存设置"""
    try:
        value = main_window.__getattribute__(f"{key}_slider").get()
        main_window.__getattribute__(f"{key}_slider").value_label.configure(text=f"{value:.2f}")
        main_window.save_settings(show_message=False)
    except Exception as e:
        # 静默处理错误以防止UI问题
        pass