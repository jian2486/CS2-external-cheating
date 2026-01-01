import sys
import signal
import ctypes
import os
import psutil
from classes.logger import Logger
from classes.config_manager import ConfigManager
from classes.utility import Utility

from gui.main_window import MainWindow

def is_admin():
    """检查当前是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """以管理员权限重新运行程序"""
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, 
            "runas", 
            sys.executable, 
            " ".join(sys.argv), 
            None, 
            1
        )
        return True
    except:
        return False

def setup_signal_handlers(logger):
    """设置信号处理器以实现关闭。"""
    def signal_handler(signum, frame):
        logger.info(f"收到信号 {signum}，正在关闭...")
        cleanup_and_exit()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def cleanup_and_exit():
    """清理资源并退出程序"""
    # 获取当前进程PID并强制终止
    try:
        current_process = psutil.Process(os.getpid())
        current_process.terminate()
        current_process.wait(timeout=5)  # 等待最多5秒
    except psutil.TimeoutExpired:
        # 如果进程没有及时终止，则强制杀死
        current_process.kill()
    except Exception as e:
        # 如果有任何异常，直接使用sys.exit
        pass
    finally:
        sys.exit(0)

def main():
    """应用程序主入口点。"""
    # 检查是否以管理员权限运行，如果不是则尝试以管理员权限重启
    if not is_admin():
        print("请求管理员权限...")
        if run_as_admin():
            sys.exit(0)
        else:
            print("无法获取管理员权限，程序将以普通权限运行")
    
    # 为应用程序设置日志记录。
    try:
        Logger.setup_logging()
        logger = Logger.get_logger()
    except Exception as e:
        print(f"设置日志记录失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 设置信号处理器以实现优雅关闭
    setup_signal_handlers(logger)

    # 记录加载的版本。
    try:
        version = ConfigManager.VERSION
    except Exception as e:
        logger.warning("无法加载版本信息: %s", e)

    # 记录应用程序启动
    logger.info("正在启动应用程序...")

    exit_code = 0
    window = None

    try:
        # 创建并运行主应用程序窗口。
        window = MainWindow()
        logger.debug("主窗口创建成功")
        window.run()
        logger.debug("应用程序正常完成")
    except KeyboardInterrupt:
        logger.info("应用程序被用户中断")
        exit_code = 0  # Ctrl+C时干净退出
    except ImportError as e:
        logger.error("导入所需模块失败: %s", e)
        logger.error("请确保所有依赖项都已安装")
        exit_code = 2
    except Exception as e:
        logger.error("意外错误: %s", e, exc_info=True)
        exit_code = 1
    finally:
        # 确保正确清理
        if window and hasattr(window, 'cleanup'):
            try:
                logger.debug("正在清理窗口资源...")
                window.cleanup()
            except Exception as cleanup_error:
                logger.warning("清理过程中出现错误: %s", cleanup_error)
        
        logger.debug("应用程序正在关闭")
        
        # 确保日志被正确刷新
        try:
            Logger.shutdown()
        except Exception:
            pass  # 不要让日志错误阻止关闭

    # 获取当前进程PID并结束进程
    cleanup_and_exit()

if __name__ == "__main__":
    main()