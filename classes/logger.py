import os
import logging
import traceback
import sys
import inspect
from pathlib import Path

class SuppressErrorFilter(logging.Filter):
    def __init__(self, pattern):
        super().__init__()
        self.pattern = pattern

    def filter(self, record):
        if self.pattern in record.getMessage():
            return False
        return True

class Logger:
    """
    用于处理应用程序日志的类。
    它设置日志记录到文件、详细日志文件和控制台，并提供增强的错误详情。
    """
    # 定义存储日志的目录。
    LOG_DIRECTORY = Path("CS2-external-cheating/crashes").resolve()
    # 定义LOG_DIRECTORY中日志文件的完整路径。
    LOG_FILE = LOG_DIRECTORY / 'vw_logs.log'
    # 定义LOG_DIRECTORY中详细日志文件的完整路径。
    DETAILED_LOG_FILE = LOG_DIRECTORY / 'vw_detailed_logs.log'
    
    # 日志记录器实例的缓存。
    _logger = None
    
    # 防止多次设置日志记录的标志
    _logger_configured = False

    @staticmethod
    def setup_logging():
        """
        为应用程序配置日志记录。
        - 确保日志目录存在。
        - 初始化日志文件（清除以前的日志）。
        - 设置日志记录，将消息写入简要日志文件、详细日志文件和控制台。
        """
        if Logger._logger_configured:
            return
        Logger._logger_configured = True
        
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.DEBUG)

        # 确保日志目录存在
        try:
            os.makedirs(Logger.LOG_DIRECTORY, exist_ok=True)
        except Exception as e:
            print(f"创建日志目录 {Logger.LOG_DIRECTORY} 时出错: {e}")
            return  # 如果目录创建失败则退出设置

        # 简要日志和控制台的标准格式化器
        standard_formatter = logging.Formatter(
            fmt='[%(asctime)s %(levelname)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 带错误处理的vw_logs.log文件处理器
        try:
            file_handler = logging.FileHandler(Logger.LOG_FILE, mode='w', encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(standard_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"为 {Logger.LOG_FILE} 设置文件处理器时出错: {e}")

        # 控制台的流处理器
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(standard_formatter)
        # 移除对"Error drawing entity: 'NoneType' object is not subscriptable"错误的过滤
        # suppress_filter = SuppressErrorFilter("Error drawing entity: 'NoneType' object is not subscriptable")
        # stream_handler.addFilter(suppress_filter)
        root_logger.addHandler(stream_handler)

        # 带增强错误上下文的详细格式化器
        detailed_formatter = logging.Formatter(
            fmt='[%(asctime)s.%(msecs)03d %(levelname)-8s] {%(name)s:%(module)s:%(funcName)s:%(lineno)d} [PID:%(process)d TID:%(thread)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        try:
            detailed_handler = logging.FileHandler(Logger.DETAILED_LOG_FILE, mode='w', encoding='utf-8')
            detailed_handler.setLevel(logging.DEBUG)
            detailed_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(detailed_handler)
        except Exception as e:
            print(f"为 {Logger.DETAILED_LOG_FILE} 设置详细处理器时出错: {e}")

        # 测试日志以验证设置
        logger = Logger.get_logger()
        logger.info("日志系统初始化成功")

    @staticmethod
    def get_logger():
        """返回缓存的日志记录器实例，如有必要则创建它。"""
        if Logger._logger is None:
            Logger._logger = logging.getLogger(__name__)
        return Logger._logger

    @staticmethod
    def _get_caller_info():
        """获取调用者的详细信息，包括文件、函数和行号。"""
        frame = inspect.currentframe()
        try:
            # 向上遍历调用栈以找到实际的调用者（跳过_get_caller_info和log_exception）
            caller_frame = frame.f_back.f_back
            if caller_frame:
                filename = caller_frame.f_code.co_filename
                function_name = caller_frame.f_code.co_name
                line_number = caller_frame.f_lineno
                return {
                    'filename': os.path.basename(filename),
                    'full_path': filename,
                    'function': function_name,
                    'line': line_number
                }
        except:
            pass
        finally:
            del frame
        return None

    @staticmethod
    def _format_traceback_with_context(exc: Exception, context_lines: int = 3):
        """格式化回溯信息，包含每个帧周围的源代码上下文。"""
        tb_lines = []
        tb = exc.__traceback__
        
        while tb is not None:
            frame = tb.tb_frame
            filename = frame.f_code.co_filename
            line_number = tb.tb_lineno
            function_name = frame.f_code.co_name
            
            tb_lines.append(f"  File \"{filename}\", line {line_number}, in {function_name}")
            
            # 尝试获取源代码上下文
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    source_lines = f.readlines()
                    
                start_line = max(0, line_number - context_lines - 1)
                end_line = min(len(source_lines), line_number + context_lines)
                
                for i in range(start_line, end_line):
                    line_content = source_lines[i].rstrip()
                    line_num = i + 1
                    if line_num == line_number:
                        tb_lines.append(f"    {line_num:4d} >>> {line_content}")
                    else:
                        tb_lines.append(f"    {line_num:4d}     {line_content}")
            except:
                # 如果我们无法读取源代码，只显示行号
                tb_lines.append(f"    <source unavailable>")
            
            tb_lines.append("")  # Empty line for readability
            tb = tb.tb_next
        
        return "\n".join(tb_lines)

    @staticmethod
    def log_exception(exc: Exception, context: str = None):
        """记录异常，包含详细信息，包括堆栈跟踪和可选上下文。"""
        logger_instance = Logger.get_logger()
        
        # 获取调用者信息
        caller_info = Logger._get_caller_info()
        
        # 如果未提供，则获取当前异常信息
        if exc is None:
            exc_type, exc_value, exc_tb = sys.exc_info()
            if exc_value:
                exc = exc_value
            else:
                logger_instance.error("调用了log_exception但未提供异常且当前无异常")
                return
        
        # 使用源代码上下文格式化增强的回溯信息
        enhanced_traceback = Logger._format_traceback_with_context(exc)
        
        # 构建详细的错误消息
        error_parts = []
        
        if context:
            error_parts.append(f"上下文: {context}")
        
        if caller_info:
            error_parts.append(f"调用位置: {caller_info['filename']}:{caller_info['line']} in {caller_info['function']}()")
        
        error_parts.extend([
            f"异常类型: {type(exc).__name__}",
            f"异常消息: {str(exc)}",
            f"带源代码上下文的详细回溯:",
            enhanced_traceback
        ])
        
        # 使用换行符连接所有部分
        exc_details = "\n".join(error_parts)
        
        # 记录详细错误
        logger_instance.error(f"发生异常:\n{exc_details}")
        
        # 同时为控制台/标准日志记录简要版本
        brief_message = f"{type(exc).__name__}: {str(exc)}"
        if caller_info:
            brief_message += f" (at {caller_info['filename']}:{caller_info['line']})"
        
        logger_instance.info(f"异常: {brief_message}")

    @staticmethod
    def log_error_with_line(message: str, include_stack: bool = True):
        """记录带有自动行号检测的错误消息。"""
        logger_instance = Logger.get_logger()
        caller_info = Logger._get_caller_info()
        
        if caller_info:
            enhanced_message = f"{message} (at {caller_info['filename']}:{caller_info['line']} in {caller_info['function']}())"
        else:
            enhanced_message = message
        
        if include_stack:
            # 获取当前堆栈跟踪
            stack_trace = ''.join(traceback.format_stack()[:-1])  # 排除当前帧
            enhanced_message += f"\n堆栈跟踪:\n{stack_trace}"
        
        logger_instance.error(enhanced_message)

    @staticmethod
    def log_warning_with_line(message: str):
        """记录带有自动行号检测的警告消息。"""
        logger_instance = Logger.get_logger()
        caller_info = Logger._get_caller_info()
        
        if caller_info:
            enhanced_message = f"{message} (at {caller_info['filename']}:{caller_info['line']} in {caller_info['function']}())"
        else:
            enhanced_message = message
        
        logger_instance.warning(enhanced_message)