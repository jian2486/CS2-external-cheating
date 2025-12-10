import os, orjson, copy
from pathlib import Path
from pyMeow import get_color, fade_color

from classes.logger import Logger

# 初始化日志记录器，以实现一致的日志记录
logger = Logger.get_logger()

class ConfigManager:
    # 应用程序版本
    VERSION = "v1.0"
    # 存储配置文件的目录
    CONFIG_DIRECTORY = Path("CS2-external-cheating").resolve()
    # 完整路径到配置文件
    CONFIG_FILE = CONFIG_DIRECTORY / 'config.json'

    # 默认配置字典
    DEFAULT_CONFIG = {
        "General": {
            "Trigger": False,
            "Aimbot": False,
            "Overlay": False,
            "OverlayVulkan": False,
            "Bunnyhop": False,
            "Noflash": False,
            "Glow": False,
            "RenderMode": "默认(pyMeow)"  # 添加渲染模式选项
        },
        "Trigger": {
            "TriggerKey": "x",
            "ToggleMode": False,
            "AttackOnTeammates": False,
            "MemoryShoot": False,  # 添加内存射击模式选项
            "active_weapon_type": "Rifles",
            "WeaponSettings": {
                "Pistols": {"ShotDelayMin": 0.02, "ShotDelayMax": 0.04, "PostShotDelay": 0.02},
                "Rifles": {"ShotDelayMin": 0.01, "ShotDelayMax": 0.03, "PostShotDelay": 0.02},
                "Snipers": {"ShotDelayMin": 0.05, "ShotDelayMax": 0.1, "PostShotDelay": 0.5},
                "SMGs": {"ShotDelayMin": 0.01, "ShotDelayMax": 0.02, "PostShotDelay": 0.05},
                "Heavy": {"ShotDelayMin": 0.03, "ShotDelayMax": 0.05, "PostShotDelay": 0.2}
            }
        },
        "Aimbot": {
            "AimKey": "v",
            "ToggleMode": False,
            "AttackOnTeammates": False,
            "FOV": 50,
            "Smooth": 2.0,
            "active_weapon_type": "Rifles",
            "WeaponSettings": {
                "Pistols": {"FOV": 30, "Smooth": 3.0},
                "Rifles": {"FOV": 50, "Smooth": 2.0},
                "Snipers": {"FOV": 100, "Smooth": 1.0},
                "SMGs": {"FOV": 40, "Smooth": 2.5},
                "Heavy": {"FOV": 60, "Smooth": 1.5}
            }
        },
        "Overlay": {
            "target_fps": 60,
            "enable_box": True,
            "enable_skeleton": False,
            "draw_snaplines": True,
            "snaplines_color_hex": "#FFFFFF",
            "box_line_thickness": 1.0,
            "box_color_hex": "#FFA500",
            "text_color_hex": "#FFFFFF",
            "draw_health_numbers": True,
            "use_transliteration": False,
            "draw_nicknames": True,
            "draw_teammates": False,
            "teammate_color_hex": "#00FFFF",
            "enable_minimap": True,
            "minimap_size": 200,
            "enable_glow": False,
            "glow_exclude_dead": True,
            "glow_teammates": False,
            "glow_thickness": 1.0,
            "glow_color_hex": "#FF00FF",
            "glow_teammate_color_hex": "#00FFFF"
        },
        "Bunnyhop": {
            "JumpKey": "space",
            "JumpDelay": 0.01
        },
        "NoFlash": {
            "FlashSuppressionStrength": 1.0
        },
    }

    # 缓存用于存储已加载的配置信息
    _config_cache = None

    @classmethod
    def load_config(cls):
        """
        从配置文件中加载配置。
        -如果配置目录和文件不存在，则创建它们并设置默认值。
        -为避免重复读取文件，对配置进行缓存。
        """
        # 返回缓存的配置副本（如果可用）。
        if cls._config_cache is not None:
            return copy.deepcopy(cls._config_cache)

        # 确保配置目录存在。
        Path(cls.CONFIG_DIRECTORY).mkdir(parents=True, exist_ok=True)

        # 确保偏移量目录存在。
        offsets_dir = cls.CONFIG_DIRECTORY / "Offsets"
        offsets_dir.mkdir(parents=True, exist_ok=True)

        if not Path(cls.CONFIG_FILE).exists():
            logger.info("在 %s 未找到 config.json，正在创建默认配置", cls.CONFIG_FILE)
            default_copy = copy.deepcopy(cls.DEFAULT_CONFIG)
            cls.save_config(default_copy, log_info=False)
            cls._config_cache = default_copy
        else:
            try:
                # 使用 orjson 读取并解析配置文件
                file_bytes = Path(cls.CONFIG_FILE).read_bytes()
                cls._config_cache = orjson.loads(file_bytes)
                logger.info("已加载配置")
            except (orjson.JSONDecodeError, IOError) as e:
                logger.exception("加载配置失败: %s", e)
                default_copy = copy.deepcopy(cls.DEFAULT_CONFIG)
                cls.save_config(default_copy, log_info=False)
                cls._config_cache = default_copy

            # 如果存在任何缺失的键，则请更新配置。
            if cls._update_config(cls.DEFAULT_CONFIG, cls._config_cache):
                cls.save_config(cls._config_cache, log_info=False)
        
        return copy.deepcopy(cls._config_cache)

    @classmethod
    def _update_config(cls, default: dict, current: dict) -> bool:
        """
        递归地将 `current` 对象中的缺失键更新为 `default` 对象中的相应键值。
        如果添加了任何键，则返回 True。
        """
        updated = False
        for key, value in default.items():
            if key not in current:
                current[key] = value
                updated = True
            elif isinstance(value, dict) and isinstance(current.get(key), dict):
                if cls._update_config(value, current[key]):
                    updated = True
        return updated

    @classmethod
    def save_config(cls, config: dict, log_info: bool = True):
        """
        将配置保存至配置文件中。
        使用新的配置更新缓存。
        """
        cls._config_cache = copy.deepcopy(config)
        try:
            # 确保配置目录存在。
            Path(cls.CONFIG_DIRECTORY).mkdir(parents=True, exist_ok=True)
            # 使用 orjson 将配置序列化为 JSON 格式并写入文件，同时进行美化格式化。
            config_bytes = orjson.dumps(config, option=orjson.OPT_INDENT_2)
            Path(cls.CONFIG_FILE).write_bytes(config_bytes)
            if log_info:
                logger.info("配置已保存至 %s", cls.CONFIG_FILE)
        except IOError as e:
            logger.exception("保存配置失败: %s", e)

COLOR_CHOICES = {
    "橙色": "#FFA500",
    "红色": "#FF0000",
    "绿色": "#00FF00",
    "蓝色": "#0000FF",
    "白色": "#FFFFFF",
    "黑色": "#000000",
    "青色": "#00FFFF",
    "黄色": "#FFFF00",
    "洋红色": "#FF00FF"
}

class Colors:
    orange = get_color("orange")
    black = get_color("black")
    cyan = get_color("cyan")
    white = get_color("white")
    grey = fade_color(get_color("#242625"), 0.7)
    red = get_color("red")
    green = get_color("green")
    blue = get_color("blue")
    yellow = get_color("yellow")