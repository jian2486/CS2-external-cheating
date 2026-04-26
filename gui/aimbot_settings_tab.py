import threading
import time

import customtkinter as ctk
import keyboard

from gui.font_manager import *

# 定义武器类型列表 - 现在是具体的武器名称
WEAPON_TYPES = [
    "AK47", "M4A4", "Deagle", "AWP", "Glock", "P250", "FAMAS", "GalilAR", 
    "M4A1S", "USP", "P90", "MP7", "Nova", "FiveSeven", "AUG", "SCAR20", 
    "SG553", "SSG08", "CZ75", "DualBerettas", "Tec9", "MAC10", "UMP45", 
    "PPBizon", "MAG7", "XM1014", "Negev", "SawedOff", "M249", "R8"
]

def start_key_detection(main_window):
    """开始检测用户按键"""
    # 检查是否已经在进行按键检测
    if hasattr(main_window, 'aimbot_key_detection_active') and main_window.aimbot_key_detection_active:
        return
    
    # 标记按键检测正在进行
    main_window.aimbot_key_detection_active = True
    main_window.aim_key_entry.configure(state="normal")
    main_window.aim_key_entry.delete(0, "end")
    main_window.aim_key_entry.insert(0, "按下任意键...")
    main_window.aim_key_entry.configure(state="disabled")
    
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
            main_window.aimbot_key_detection_active = False
    
    threading.Thread(target=detect_key, daemon=True).start()

def finish_key_detection(main_window, key_name):
    """完成按键检测并更新UI"""
    main_window.aim_key_entry.configure(state="normal")
    main_window.aim_key_entry.delete(0, "end")
    main_window.aim_key_entry.insert(0, key_name)
    main_window.aim_key_entry.configure(state="disabled")
    
    # 更新配置
    main_window.aimbot.config['Aimbot']['AimKey'] = key_name
    # 确保主窗口配置也被更新
    main_window.triggerbot.config['Aimbot']['AimKey'] = key_name
    main_window.save_settings()

def populate_aimbot_settings(main_window, frame):
    """填充自瞄设置标签页与配置选项"""
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
        text="自瞄设置",
        font=(MAIN_FONT, TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    )
    title_label.pack(side="left")

    # 提供上下文的副标题
    subtitle_label = ctk.CTkLabel(
        title_frame,
        text="配置您的自瞄偏好",
        font=(SECONDARY_FONT, SUBTITLE_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="w"
    )
    subtitle_label.pack(side="left", padx=(20, 0), pady=(10, 0))

    # 创建具有现代样式的自瞄键部分
    aim_key_section = ctk.CTkFrame(
        settings,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    aim_key_section.pack(fill="x", pady=(0, 30))

    # 创建具有现代样式的FOV设置部分
    fov_section = ctk.CTkFrame(
        settings,
        corner_radius=0,
        fg_color=("#ffffff", "#1a1b23"),
        border_width=2,
        border_color=("#e2e8f0", "#2d3748")
    )
    fov_section.pack(fill="x", pady=(0, 30))

    # 创建自瞄键设置
    header_frame1 = ctk.CTkFrame(aim_key_section, fg_color="transparent")
    header_frame1.pack(fill="x", padx=40, pady=(40, 30))
    header_frame1.grid_columnconfigure(0, weight=1)
    header_frame1.grid_columnconfigure(1, weight=1)
    
    ctk.CTkLabel(
        header_frame1,
        text="自瞄键",
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).grid(row=0, column=0, sticky="w")

    ctk.CTkLabel(
        header_frame1,
        text="配置激活自瞄的按键",
        font=(SECONDARY_FONT, SETTING_DESCRIPTION_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).grid(row=0, column=1, sticky="e")

    # 创建自瞄键输入框架
    aim_key_frame = ctk.CTkFrame(aim_key_section, fg_color="transparent")
    aim_key_frame.pack(fill="x", padx=40, pady=(0, 40))

    main_window.aim_key_entry = ctk.CTkEntry(
        aim_key_frame,
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
    main_window.aim_key_entry.insert(0, main_window.aimbot.config['Aimbot'].get('AimKey', ''))
    main_window.aim_key_entry.pack(side="left", padx=(0, 5), pady=5)
    main_window.aim_key_entry.configure(state="disabled")  # 禁用输入功能
    
    # 绑定点击事件开始按键检测
    main_window.aim_key_entry.bind("<Button-1>", lambda e: start_key_detection(main_window))

    # 创建切换模式和攻击队友复选框
    toggle_attack_frame = ctk.CTkFrame(aim_key_section, fg_color="transparent")
    toggle_attack_frame.pack(fill="x", padx=40, pady=(0, 40))

    main_window.aimbot_toggle_mode_var = ctk.BooleanVar(
        value=main_window.aimbot.config['Aimbot'].get('ToggleMode', False))
    main_window.aimbot_attack_teammates_var = ctk.BooleanVar(
        value=main_window.aimbot.config['Aimbot'].get('AttackOnTeammates', False))

    # 切换模式
    toggle_mode_checkbox = ctk.CTkCheckBox(
        toggle_attack_frame,
        text="切换模式",
        variable=main_window.aimbot_toggle_mode_var,
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
    toggle_mode_checkbox.pack(side="left", padx=(0, 30))

    # 攻击队友
    attack_teammates_checkbox = ctk.CTkCheckBox(
        toggle_attack_frame,
        text="攻击队友",
        variable=main_window.aimbot_attack_teammates_var,
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
    attack_teammates_checkbox.pack(side="left")

    # 创建视野设置
    header_frame3 = ctk.CTkFrame(fov_section, fg_color="transparent")
    header_frame3.pack(fill="x", padx=40, pady=(40, 30))
    header_frame3.grid_columnconfigure(0, weight=1)
    header_frame3.grid_columnconfigure(1, weight=1)
    
    ctk.CTkLabel(
        header_frame3,
        text="视野和灵敏度设置",
        font=(MAIN_FONT, SECTION_TITLE_FONT_SIZE, "bold"),
        text_color=("#1f2937", "#ffffff"),
        anchor="w"
    ).grid(row=0, column=0, sticky="w")

    ctk.CTkLabel(
        header_frame3,
        text="配置视野范围和瞄准平滑度",
        font=(SECONDARY_FONT, SETTING_DESCRIPTION_FONT_SIZE),
        text_color=("#64748b", "#94a3b8"),
        anchor="e"
    ).grid(row=0, column=1, sticky="e")

    # 创建视野设置网格（改为每行2个）
    fov_settings_frame = ctk.CTkFrame(fov_section, fg_color="transparent")
    fov_settings_frame.pack(fill="x", padx=40, pady=(0, 40))

    # 增加更多内边距避免遮挡大框
    fov_inputs_frame = ctk.CTkFrame(fov_settings_frame, fg_color="transparent")
    fov_inputs_frame.pack(fill="x", pady=5)

    # 瞄准位置选择
    ctk.CTkLabel(fov_inputs_frame, text="瞄准位置", font=(MAIN_FONT, INPUT_FONT_SIZE)).grid(row=0, column=0, padx=(0, 15),
                                                                                 pady=(0, 5), sticky="w")
    main_window.aim_position_var = ctk.StringVar(
        value=main_window.aimbot.config['Aimbot'].get('AimPosition', 'head'))
    aim_position_menu = ctk.CTkComboBox(
        fov_inputs_frame,
        values=["头部", "脖子", "胸部", "根部"],
        variable=main_window.aim_position_var,
        width=120,
        height=30,
        corner_radius=0,
        border_width=2,
        border_color=("#d1d5db", "#374151"),
        fg_color=("#ffffff", "#1f2937"),
        text_color=("#1f2937", "#ffffff"),
        font=(MAIN_FONT, INPUT_FONT_SIZE),
        command=lambda e: main_window.save_settings()
    )
    aim_position_menu.grid(row=1, column=0, padx=(0, 15), pady=(0, 15), sticky="w")

    # 视野输入框
    ctk.CTkLabel(fov_inputs_frame, text="视野 (FOV)", font=(MAIN_FONT, INPUT_FONT_SIZE)).grid(row=0, column=1, padx=(15, 0),
                                                                                 pady=(0, 5), sticky="w")
    main_window.fov_entry = ctk.CTkEntry(
        fov_inputs_frame,
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
    main_window.fov_entry.bind("<FocusOut>", lambda e: main_window.save_settings())
    main_window.fov_entry.bind("<Return>", lambda e: main_window.save_settings())
    main_window.fov_entry.grid(row=1, column=1, padx=(15, 0), pady=(0, 15), sticky="w")

    # 平滑度输入框
    ctk.CTkLabel(fov_inputs_frame, text="平滑度", font=(MAIN_FONT, INPUT_FONT_SIZE)).grid(row=0, column=2, padx=(15, 0),
                                                                                   pady=(0, 5), sticky="w")
    main_window.smooth_entry = ctk.CTkEntry(
        fov_inputs_frame,
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
    main_window.smooth_entry.bind("<FocusOut>", lambda e: main_window.save_settings())
    main_window.smooth_entry.bind("<Return>", lambda e: main_window.save_settings())
    main_window.smooth_entry.grid(row=1, column=2, padx=(15, 0), pady=(0, 15), sticky="w")

    fov_inputs_frame.grid_columnconfigure(0, weight=1)
    fov_inputs_frame.grid_columnconfigure(1, weight=1)
    fov_inputs_frame.grid_columnconfigure(2, weight=1)

    # 初始化显示固定配置值
    main_window.update_aimbot_weapon_settings_display()