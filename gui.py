import customtkinter as ctk
import tkinter as tk
from typing import Optional, Dict
import sys
import threading
from config_manager import ConfigManager
from core import CoreProcessor

class LogRedirector:
    """将print输出重定向到GUI文本框的类"""
    def __init__(self, text_widget: ctk.CTkTextbox):
        self.text_widget = text_widget
        self.original_stdout = sys.stdout

    def write(self, text):
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", text)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")
        self.original_stdout.write(text)

    def flush(self):
        self.original_stdout.flush()

class ConfigDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        # 设置窗口
        self.title("配置设置")
        self.geometry("500x400")
        self.resizable(False, False)
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config() or {}
        
        # 创建变量存储配置值
        self.api_endpoint_var = tk.StringVar(value=self.config.get("api_endpoint", ""))
        self.api_key_var = tk.StringVar(value=self.config.get("api_key", ""))
        self.temperature_var = tk.StringVar(value=str(self.config.get("temperature", 0.3)))
        self.max_tokens_var = tk.StringVar(value=str(self.config.get("max_tokens", 1000)))
        self.model_var = tk.StringVar(value=self.config.get("model", "gemini-2.5-flash-preview-04-17-nothink"))
        
        self.setup_ui()
        
        # 使窗口模态
        self.grab_set()
        
    def setup_ui(self):
        """设置UI布局"""
        # 主框架
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # API设置区域
        api_frame = ctk.CTkFrame(main_frame)
        api_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(api_frame, text="API设置", font=("Arial", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        
        # API端点
        endpoint_frame = ctk.CTkFrame(api_frame)
        endpoint_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(endpoint_frame, text="API端点：").pack(side="left", padx=5)
        ctk.CTkEntry(endpoint_frame, textvariable=self.api_endpoint_var, width=300).pack(side="left", padx=5)
        
        # API密钥
        key_frame = ctk.CTkFrame(api_frame)
        key_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(key_frame, text="API密钥：").pack(side="left", padx=5)
        key_entry = ctk.CTkEntry(key_frame, textvariable=self.api_key_var, width=300, show="*")
        key_entry.pack(side="left", padx=5)
        
        # 高级设置区域
        advanced_frame = ctk.CTkFrame(main_frame)
        advanced_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(advanced_frame, text="高级设置", font=("Arial", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        
        # Temperature
        temp_frame = ctk.CTkFrame(advanced_frame)
        temp_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(temp_frame, text="Temperature：").pack(side="left", padx=5)
        temp_entry = ctk.CTkEntry(temp_frame, textvariable=self.temperature_var, width=100)
        temp_entry.pack(side="left", padx=5)
        ctk.CTkLabel(temp_frame, text="(0-1之间的值)").pack(side="left", padx=5)
        
        # Max Tokens
        tokens_frame = ctk.CTkFrame(advanced_frame)
        tokens_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(tokens_frame, text="Max Tokens：").pack(side="left", padx=5)
        tokens_entry = ctk.CTkEntry(tokens_frame, textvariable=self.max_tokens_var, width=100)
        tokens_entry.pack(side="left", padx=5)
        
        # Model
        model_frame = ctk.CTkFrame(advanced_frame)
        model_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(model_frame, text="模型：").pack(side="left", padx=5)
        model_entry = ctk.CTkEntry(model_frame, textvariable=self.model_var, width=300)
        model_entry.pack(side="left", padx=5)
        
        # 按钮区域
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            button_frame,
            text="保存",
            command=self.save_config,
            width=100
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="取消",
            command=self.destroy,
            width=100
        ).pack(side="right", padx=5)
        
    def save_config(self):
        """保存配置"""
        try:
            # 验证temperature值
            temp = float(self.temperature_var.get())
            if not 0 <= temp <= 1:
                raise ValueError("Temperature必须在0到1之间")
                
            # 验证max_tokens值
            tokens = int(self.max_tokens_var.get())
            if tokens <= 0:
                raise ValueError("Max Tokens必须大于0")
                
            # 更新配置
            new_config = {
                "api_endpoint": self.api_endpoint_var.get().strip(),
                "api_key": self.api_key_var.get().strip(),
                "temperature": temp,
                "max_tokens": tokens,
                "model": self.model_var.get().strip()
            }
            
            # 验证必要字段
            if not new_config["api_endpoint"] or not new_config["api_key"]:
                raise ValueError("API端点和API密钥不能为空")
            
            # 保存配置
            self.config_manager.config = new_config
            self.config_manager._save_config()
            
            print("配置已保存")
            self.destroy()
            
        except ValueError as e:
            print(f"错误：{str(e)}")
        except Exception as e:
            print(f"保存配置时发生错误：{str(e)}")

class MainGUI:
    def __init__(self):
        # 设置主题
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # 创建主窗口
        self.root = ctk.CTk()
        self.root.title("名词化分析工具")
        self.root.geometry("800x600")

        # 初始化变量
        self.input_file_path: Optional[str] = None
        self.output_file_path: Optional[str] = None
        self.is_processing = False
        self.processor: Optional[CoreProcessor] = None
        self.processing_thread: Optional[threading.Thread] = None

        # 创建UI
        self.setup_ui()

    def setup_ui(self):
        """设置UI布局"""
        # 文件选择区域
        self.file_frame = ctk.CTkFrame(self.root)
        self.file_frame.pack(fill="x", padx=10, pady=(10, 5))

        # 输入文件选择
        self.input_label = ctk.CTkLabel(self.file_frame, text="输入文件：")
        self.input_label.pack(side="left", padx=5)
        
        self.input_path_label = ctk.CTkLabel(self.file_frame, text="未选择", width=400)
        self.input_path_label.pack(side="left", padx=5)
        
        self.select_input_btn = ctk.CTkButton(
            self.file_frame, 
            text="选择输入文件", 
            command=self.select_input_file,
            width=120
        )
        self.select_input_btn.pack(side="left", padx=5)

        # 输出文件选择区域
        self.output_frame = ctk.CTkFrame(self.root)
        self.output_frame.pack(fill="x", padx=10, pady=5)

        self.output_label = ctk.CTkLabel(self.output_frame, text="输出文件：")
        self.output_label.pack(side="left", padx=5)
        
        self.output_path_label = ctk.CTkLabel(self.output_frame, text="未选择", width=400)
        self.output_path_label.pack(side="left", padx=5)
        
        self.select_output_btn = ctk.CTkButton(
            self.output_frame, 
            text="选择输出位置", 
            command=self.select_output_file,
            width=120
        )
        self.select_output_btn.pack(side="left", padx=5)

        # 控制按钮区域
        self.control_frame = ctk.CTkFrame(self.root)
        self.control_frame.pack(fill="x", padx=10, pady=5)

        self.start_btn = ctk.CTkButton(
            self.control_frame, 
            text="开始处理", 
            command=self.start_processing,
            width=120
        )
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(
            self.control_frame, 
            text="停止处理", 
            command=self.stop_processing,
            width=120,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)

        self.settings_btn = ctk.CTkButton(
            self.control_frame, 
            text="设置", 
            command=self.open_settings,
            width=120
        )
        self.settings_btn.pack(side="right", padx=5)

        # 状态/日志显示区域
        self.log_frame = ctk.CTkFrame(self.root)
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_label = ctk.CTkLabel(self.log_frame, text="处理日志：")
        self.log_label.pack(anchor="w", padx=5, pady=2)

        self.log_text = ctk.CTkTextbox(self.log_frame, wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=2)

        # 设置日志重定向
        self.log_redirector = LogRedirector(self.log_text)
        sys.stdout = self.log_redirector

    def select_input_file(self):
        """选择输入文件"""
        file_path = tk.filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if file_path:
            self.input_file_path = file_path
            # 显示文件名而不是完整路径
            self.input_path_label.configure(text=file_path.split("/")[-1])

    def select_output_file(self):
        """选择输出文件保存位置"""
        file_path = tk.filedialog.asksaveasfilename(
            title="选择保存位置",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="ai_analysis_results.csv"
        )
        if file_path:
            self.output_file_path = file_path
            # 显示文件名而不是完整路径
            self.output_path_label.configure(text=file_path.split("/")[-1])

    def start_processing(self):
        """开始处理"""
        if not self.input_file_path or not self.output_file_path:
            print("请先选择输入和输出文件！")
            return

        # 获取配置
        config_manager = ConfigManager()
        config = config_manager.get_config()
        if not config:
            print("错误：无法加载配置，请先完成设置。")
            return

        # 创建处理器
        self.processor = CoreProcessor(config)
        self.processor.set_progress_callback(lambda msg: print(msg))

        # 更新UI状态
        self.is_processing = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.select_input_btn.configure(state="disabled")
        self.select_output_btn.configure(state="disabled")
        self.settings_btn.configure(state="disabled")

        # 在新线程中运行处理
        self.processing_thread = threading.Thread(
            target=self._run_processing,
            daemon=True
        )
        self.processing_thread.start()

    def _run_processing(self):
        """在新线程中运行处理逻辑"""
        try:
            success = self.processor.process_file(
                self.input_file_path,
                self.output_file_path
            )
            
            # 在主线程中更新UI
            self.root.after(0, self._processing_finished, success)
            
        except Exception as e:
            print(f"处理过程中发生错误: {str(e)}")
            self.root.after(0, self._processing_finished, False)

    def _processing_finished(self, success: bool):
        """处理完成后的回调"""
        self.is_processing = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.select_input_btn.configure(state="normal")
        self.select_output_btn.configure(state="normal")
        self.settings_btn.configure(state="normal")
        
        if success:
            print("处理完成！")
        else:
            print("处理失败！")

    def stop_processing(self):
        """停止处理"""
        if self.processor:
            self.processor.stop()
            print("正在停止处理...")

    def open_settings(self):
        """打开设置窗口"""
        config_dialog = ConfigDialog(self.root)
        self.root.wait_window(config_dialog)

    def run(self):
        """运行GUI程序"""
        self.root.mainloop()

if __name__ == "__main__":
    app = MainGUI()
    app.run() 