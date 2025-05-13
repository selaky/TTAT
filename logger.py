import sys
from typing import Optional, Callable
from datetime import datetime
import customtkinter as ctk

class Logger:
    """统一的日志处理类"""
    
    # 日志级别
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    
    def __init__(self):
        """初始化日志处理器"""
        self.callback: Optional[Callable[[str], None]] = None
        self.text_widget: Optional[ctk.CTkTextbox] = None
        self.original_stdout = sys.stdout
    
    def set_callback(self, callback: Callable[[str], None]):
        """设置日志回调函数"""
        self.callback = callback
    
    def set_text_widget(self, text_widget: ctk.CTkTextbox):
        """设置GUI文本框组件"""
        self.text_widget = text_widget
    
    def _format_message(self, level: str, message: str) -> str:
        """格式化日志消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{level}] {message}"
    
    def _write_to_widget(self, message: str):
        """写入到GUI文本框"""
        if self.text_widget:
            self.text_widget.configure(state="normal")
            self.text_widget.insert("end", message + "\n")
            self.text_widget.see("end")
            self.text_widget.configure(state="disabled")
    
    def log(self, message: str, level: str = INFO):
        """记录日志"""
        formatted_message = self._format_message(level, message)
        
        # 使用回调函数
        if self.callback:
            self.callback(formatted_message)
        
        # 写入GUI文本框
        if self.text_widget:
            self._write_to_widget(formatted_message)
        
        # 写入标准输出
        self.original_stdout.write(formatted_message + "\n")
    
    def info(self, message: str):
        """记录信息级别日志"""
        self.log(message, self.INFO)
    
    def warning(self, message: str):
        """记录警告级别日志"""
        self.log(message, self.WARNING)
    
    def error(self, message: str):
        """记录错误级别日志"""
        self.log(message, self.ERROR)

# 创建全局日志实例
logger = Logger() 