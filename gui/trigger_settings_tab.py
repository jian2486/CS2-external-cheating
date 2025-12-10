import customtkinter as ctk
from classes.config_manager import ConfigManager
import threading
import time
from gui.font_manager import *
import keyboard

# 定义武器类型列表
WEAPON_TYPES = ["Pistols", "Rifles", "Snipers", "SMGs", "Heavy"]

def start_key_detection(main_window):
    """开始检测用户按键"""
    # 检查是否已经在进行按键检测
    if hasattr(main_window, 'trigger_key_detection_active') and main_window.trigger_key_detection_active:
        return
    
    # 标记按键检测正在进行
    main_window.trigger_key_detection_active = True
    main_window.trigger_key_entry.configure(state="normal")
    main_window.trigger_key_entry.delete(0, "end")
    main_window.trigger_key_entry.insert(0, "按下任意键...")
    main_window.trigger_key_entry.configure(state="disabled")
    
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
            
            main_window.root.after(0, lambda: finish_key_detection(main_window, key_name))
        except Exception as e:
            main_window.root.after(0, lambda: finish_key_detection(main_window, "space"))
        finally:
            main_window.trigger_key_detection_active = False
    
    threading.Thread(target=detect_key, daemon=True).start()

def finish_key_detection(main_window, key_name):
    """完成按键检测并更新UI"""
    main_window.trigger_key_entry.configure(state="normal")
    main_window.trigger_key_entry.delete(0, "end")
    main_window.trigger_key_entry.insert(0, key_name)
    main_window.trigger_key_entry.configure(state="disabled")
    
    # 更新配置
    main_window.triggerbot.config['Trigger']['TriggerKey'] = key_name
    main_window.save_settings()

def populate_trigger_settings(main_window, frame):
    """填充自动扳机设置标签页与配置选项。"""
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
        text="扳机设置",
        font=(MAIN_FONT, TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    )
    title_label.pack(side="left")

    # 提供上下文的副标题
    subtitle_label = ctk.CTkLabel(
        title_frame,
        text="配置您的自动扳机偏好",
        font=(SECONDARY_FONT, SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="w"
    )
    subtitle_label.pack(side="left", padx=(20, 0), pady=(10, 0))

    # 创建具有现代样式的触发键部分
    trigger_key_section = ctk.CTkFrame(
        settings,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    trigger_key_section.pack(fill="x", pady=(0, 30))

    # 创建具有现代样式的武器设置部分
    weapon_section = ctk.CTkFrame(
        settings,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    weapon_section.pack(fill="x", pady=(0, 30))

    # 创建具有现代样式的延迟设置部分
    delay_section = ctk.CTkFrame(
        settings,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    delay_section.pack(fill="x", pady=(0, 30))

    # 创建扳机键设置
    header_frame1 = ctk.CTkFrame(trigger_key_section, fg_color="transparent")
    header_frame1.pack(fill="x", padx=40, pady=(40, 30))
    header_frame1.grid_columnconfigure(0, weight=1)
    header_frame1.grid_columnconfigure(1, weight=1)
    
    ctk.CTkLabel(
        header_frame1,
        text="扳机键",
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).grid(row=0, column=0, sticky="w")

    ctk.CTkLabel(
        header_frame1,
        text="配置激活自动扳机的按键",
        font=(SECONDARY_FONT, SETTING_DESCRIPTION_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).grid(row=0, column=1, sticky="e")

    # 创建扳机键输入框架
    trigger_key_frame = ctk.CTkFrame(trigger_key_section, fg_color="transparent")
    trigger_key_frame.pack(fill="x", padx=40, pady=(0, 40))

    main_window.trigger_key_entry = ctk.CTkEntry(
        trigger_key_frame,
        width=180,
        height=35,
        corner_radius=0,
        border_width=2,
        border_color=("#d1d5db", "#374151"),
        fg_color=("#ffffff", "#1f2937"),
        text_color=("#1f2937", "#ffffff"),
        font=(MAIN_FONT, INPUT_FONT_SIZE),
        justify="center"
    )
    main_window.trigger_key_entry.insert(0, main_window.triggerbot.config['Trigger'].get('TriggerKey', ''))
    main_window.trigger_key_entry.pack(side="left", padx=(0, 5), pady=5)
    main_window.trigger_key_entry.configure(state="disabled")  # 禁用输入功能
    
    # 绑定点击事件开始按键检测
    main_window.trigger_key_entry.bind("<Button-1>", lambda e: start_key_detection(main_window))

    # 创建武器设置
    header_frame2 = ctk.CTkFrame(weapon_section, fg_color="transparent")
    header_frame2.pack(fill="x", padx=40, pady=(40, 30))
    header_frame2.grid_columnconfigure(0, weight=1)
    header_frame2.grid_columnconfigure(1, weight=1)
    
    ctk.CTkLabel(
        header_frame2,
        text="武器设置",
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).grid(row=0, column=0, sticky="w")

    ctk.CTkLabel(
        header_frame2,
        text="配置武器类型和模式",
        font=(SECONDARY_FONT, SETTING_DESCRIPTION_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).grid(row=0, column=1, sticky="e")

    # 创建武器设置网格（改为3个一排）
    weapon_settings_frame = ctk.CTkFrame(weapon_section, fg_color="transparent")
    weapon_settings_frame.pack(fill="x", padx=40, pady=(0, 40))

    # 创建居中框架，增加更多内边距避免遮挡大框
    center_frame = ctk.CTkFrame(weapon_settings_frame, fg_color="transparent")
    center_frame.pack(fill="x", pady=5)

    # 使用网格布局确保三个控件垂直对齐居中
    main_window.active_weapon_type = ctk.StringVar(
        value=main_window.triggerbot.config['Trigger'].get('active_weapon_type', 'Rifles'))
    
    # 武器类型选择
    ctk.CTkLabel(
        center_frame,
        text="武器类型:",
        font=(MAIN_FONT, SETTING_LABEL_FONT_SIZE),
        text_color=("#1f2937", "#ffffff")
    ).grid(row=0, column=0, padx=(0, 30), sticky="w")

    weapon_dropdown = ctk.CTkOptionMenu(
        center_frame,
        variable=main_window.active_weapon_type,
        values=WEAPON_TYPES,
        command=lambda e: main_window.update_weapon_settings_display(),
        font=(MAIN_FONT, INPUT_FONT_SIZE),
        dropdown_font=(MAIN_FONT, INPUT_FONT_SIZE),
        corner_radius=0,
        fg_color=("#D5006D", "#E91E63"),
        button_color=("#B8004A", "#C2185B"),
        button_hover_color=("#9F003D", "#A6144E"),
        width=150,
        height=30
    )
    weapon_dropdown.grid(row=0, column=1, padx=(0, 30), pady=(0, 0), sticky="w")

    main_window.toggle_mode_var = ctk.BooleanVar(
        value=main_window.triggerbot.config['Trigger'].get('ToggleMode', False))
    main_window.attack_teammates_var = ctk.BooleanVar(
        value=main_window.triggerbot.config['Trigger'].get('AttackOnTeammates', False))
    
    # 添加内存射击模式变量
    main_window.memory_shoot_var = ctk.BooleanVar(
        value=main_window.triggerbot.config['Trigger'].get('MemoryShoot', False))

    # 切换模式
    toggle_mode_checkbox = ctk.CTkCheckBox(
        center_frame,
        text="切换模式",
        variable=main_window.toggle_mode_var,
        width=25,
        height=25,
        corner_radius=0,
        border_width=2,
        fg_color=("#D5006D", "#E91E63"),
        hover_color=("#B8004A", "#C2185B"),
        checkmark_color="#ffffff",
        command=main_window.save_settings,
        font=(MAIN_FONT, INPUT_FONT_SIZE)
    )
    toggle_mode_checkbox.grid(row=0, column=2, padx=(0, 30), pady=(0, 0), sticky="w")

    # 攻击队友
    attack_teammates_checkbox = ctk.CTkCheckBox(
        center_frame,
        text="攻击队友",
        variable=main_window.attack_teammates_var,
        width=25,
        height=25,
        corner_radius=0,
        border_width=2,
        fg_color=("#D5006D", "#E91E63"),
        hover_color=("#B8004A", "#C2185B"),
        checkmark_color="#ffffff",
        command=main_window.save_settings,
        font=(MAIN_FONT, INPUT_FONT_SIZE)
    )
    attack_teammates_checkbox.grid(row=0, column=3, padx=(0, 30), pady=(0, 0), sticky="w")
    
    # 内存射击模式
    memory_shoot_checkbox = ctk.CTkCheckBox(
        center_frame,
        text="内存射击",
        variable=main_window.memory_shoot_var,
        width=25,
        height=25,
        corner_radius=0,
        border_width=2,
        fg_color=("#D5006D", "#E91E63"),
        hover_color=("#B8004A", "#C2185B"),
        checkmark_color="#ffffff",
        command=main_window.save_settings,
        font=(MAIN_FONT, INPUT_FONT_SIZE)
    )
    memory_shoot_checkbox.grid(row=0, column=4, padx=(0, 0), pady=(0, 0), sticky="w")

    # 创建延迟设置
    header_frame3 = ctk.CTkFrame(delay_section, fg_color="transparent")
    header_frame3.pack(fill="x", padx=40, pady=(40, 30))
    header_frame3.grid_columnconfigure(0, weight=1)
    header_frame3.grid_columnconfigure(1, weight=1)
    
    ctk.CTkLabel(
        header_frame3,
        text="延迟设置",
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).grid(row=0, column=0, sticky="w")

    ctk.CTkLabel(
        header_frame3,
        text="为每种武器类型配置射击延迟",
        font=(SECONDARY_FONT, SETTING_DESCRIPTION_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).grid(row=0, column=1, sticky="e")

    # 创建延迟设置网格（改为每行3个）
    delay_settings_frame = ctk.CTkFrame(delay_section, fg_color="transparent")
    delay_settings_frame.pack(fill="x", padx=40, pady=(0, 40))

    # 增加更多内边距避免遮挡大框
    delay_inputs_frame = ctk.CTkFrame(delay_settings_frame, fg_color="transparent")
    delay_inputs_frame.pack(fill="x", pady=5)

    # 最小延迟输入框
    ctk.CTkLabel(delay_inputs_frame, text="最小延迟", font=(MAIN_FONT, INPUT_FONT_SIZE)).grid(row=0, column=0, padx=(0, 15),
                                                                                 pady=(0, 5), sticky="w")
    main_window.min_delay_entry = ctk.CTkEntry(
        delay_inputs_frame,
        width=120,
        height=30,
        corner_radius=0,
        border_width=2,
        border_color=("#d1d5db", "#374151"),
        fg_color=("#ffffff", "#1f2937"),
        text_color=("#1f2937", "#ffffff"),
        font=(MAIN_FONT, INPUT_FONT_SIZE),
        justify="center"
    )
    main_window.min_delay_entry.bind("<FocusOut>", lambda e: main_window.save_settings())
    main_window.min_delay_entry.bind("<Return>", lambda e: main_window.save_settings())
    main_window.min_delay_entry.grid(row=1, column=0, padx=(0, 15), pady=(0, 15), sticky="w")

    # 最大延迟输入框
    ctk.CTkLabel(delay_inputs_frame, text="最大延迟", font=(MAIN_FONT, INPUT_FONT_SIZE)).grid(row=0, column=1, padx=(15, 15),
                                                                                 pady=(0, 5), sticky="w")
    main_window.max_delay_entry = ctk.CTkEntry(
        delay_inputs_frame,
        width=120,
        height=30,
        corner_radius=0,
        border_width=2,
        border_color=("#d1d5db", "#374151"),
        fg_color=("#ffffff", "#1f2937"),
        text_color=("#1f2937", "#ffffff"),
        font=(MAIN_FONT, INPUT_FONT_SIZE),
        justify="center"
    )
    main_window.max_delay_entry.bind("<FocusOut>", lambda e: main_window.save_settings())
    main_window.max_delay_entry.bind("<Return>", lambda e: main_window.save_settings())
    main_window.max_delay_entry.grid(row=1, column=1, padx=(15, 15), pady=(0, 15), sticky="w")

    # 射击后延迟输入框
    ctk.CTkLabel(delay_inputs_frame, text="射击后延迟", font=(MAIN_FONT, INPUT_FONT_SIZE)).grid(row=0, column=2, padx=(15, 0),
                                                                                   pady=(0, 5), sticky="w")
    main_window.post_shot_delay_entry = ctk.CTkEntry(
        delay_inputs_frame,
        width=120,
        height=30,
        corner_radius=0,
        border_width=2,
        border_color=("#d1d5db", "#374151"),
        fg_color=("#ffffff", "#1f2937"),
        text_color=("#1f2937", "#ffffff"),
        font=(MAIN_FONT, INPUT_FONT_SIZE),
        justify="center"
    )
    main_window.post_shot_delay_entry.bind("<FocusOut>", lambda e: main_window.save_settings())
    main_window.post_shot_delay_entry.bind("<Return>", lambda e: main_window.save_settings())
    main_window.post_shot_delay_entry.grid(row=1, column=2, padx=(15, 0), pady=(0, 15), sticky="w")

    delay_inputs_frame.grid_columnconfigure(0, weight=1)
    delay_inputs_frame.grid_columnconfigure(1, weight=1)
    delay_inputs_frame.grid_columnconfigure(2, weight=1)

    main_window.update_weapon_settings_display()