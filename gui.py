import customtkinter as ctk
import tkinter as tk
from typing import Optional, Dict
import sys
import threading
from config_manager import ConfigManager
from core import CoreProcessor
from logger import logger

class ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, message: str, confirm_text: str = "确认", cancel_text: str = "取消"):
        super().__init__(parent)
        
        # 设置窗口
        self.title(title)
        self.geometry("320x150")
        self.resizable(False, False)
        
        # 使窗口模态
        self.grab_set()
        
        # 设置窗口位置为主窗口中心
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        
        # 存储结果
        self.result = False
        
        # 创建UI
        self.setup_ui(message, confirm_text, cancel_text)
        
    def setup_ui(self, message: str, confirm_text: str, cancel_text: str):
        """设置UI布局"""
        # 主容器
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 消息（只显示两句话，居中）
        message_label = ctk.CTkLabel(
            main_frame,
            text=message,
            wraplength=260,
            justify="center",
            font=("Arial", 13)
        )
        message_label.pack(pady=(0, 18))
        
        # 按钮容器
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x")
        
        # 取消按钮
        cancel_btn = ctk.CTkButton(
            button_frame,
            text=cancel_text,
            command=self.on_cancel,
            width=100,
            font=("Arial", 12, "bold")
        )
        cancel_btn.pack(side="left", padx=5)
        
        # 确认按钮
        confirm_btn = ctk.CTkButton(
            button_frame,
            text=confirm_text,
            command=self.on_confirm,
            width=100,
            fg_color="#E74C3C",
            hover_color="#C0392B",
            text_color="white",
            font=("Arial", 12, "bold")
        )
        confirm_btn.pack(side="right", padx=5)
        
    def on_confirm(self):
        """确认按钮回调"""
        self.result = True
        self.destroy()
        
    def on_cancel(self):
        """取消按钮回调"""
        self.result = False
        self.destroy()

class ConfigDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        # 设置窗口
        self.title("配置设置")
        self.geometry("425x500")
        self.resizable(False, False)
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        config, error = self.config_manager.load_config(require_all_fields=False)
        self.config = config or {}
        
        if error:
            logger.error(f"加载配置时发生错误：{error}")
        
        # 创建变量存储配置值
        self.api_endpoint_var = tk.StringVar(value=self.config.get("api_endpoint", ""))
        self.api_key_var = tk.StringVar(value=self.config.get("api_key", ""))
        self.temperature_var = tk.StringVar(value=str(self.config.get("temperature", 0.3)))
        self.max_tokens_var = tk.StringVar(value=str(self.config.get("max_tokens", 1000)))
        self.model_var = tk.StringVar(value=self.config.get("model", "gemini-2.5-flash-preview-04-17-nothink"))
        self.min_length_var = tk.StringVar(value=str(self.config.get("min_sentence_length", 10)))
        self.max_length_var = tk.StringVar(value=str(self.config.get("max_sentence_length", 500)))
        self.filter_incomplete_var = tk.BooleanVar(value=self.config.get("filter_incomplete_sentences", True))
        self.mock_mode_var = tk.BooleanVar(value=self.config.get("mock_mode", False))
        self.batch_size_var = tk.StringVar(value=str(self.config.get("batch_size", 500)))
        
        # 文件结构配置变量
        self.skip_rows_var = tk.StringVar(value=str(self.config.get("file_structure", {}).get("skip_rows", 6)))
        self.source_lang_var = tk.StringVar(value=self.config.get("file_structure", {}).get("language", {}).get("source", "en"))
        self.target_lang_var = tk.StringVar(value=self.config.get("file_structure", {}).get("language", {}).get("target", "zh-cn"))
        
        # 列配置变量
        self.column_vars = {}
        for col_name, col_config in self.config.get("file_structure", {}).get("columns", {}).items():
            self.column_vars[col_name] = {
                "enabled": tk.BooleanVar(value=col_config.get("enabled", True)),
                "index": tk.StringVar(value=str(col_config.get("index", 0)))
            }
        
        # 存储输入框引用
        self.entry_widgets = {}
        
        # 标记是否取消配置
        self.cancelled = False
        
        self.setup_ui()
        
        # 使窗口模态
        self.grab_set()
        
        # 设置关闭窗口的处理
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def on_closing(self):
        """处理窗口关闭事件"""
        if not self.config_manager.config:  # 如果是首次配置
            self.cancelled = True
        self.destroy()
        
    def validate_numeric_field(self, value: str, field_name: str, min_value: float = None, max_value: float = None) -> bool:
        """验证数值字段"""
        try:
            if not value.strip():
                return True  # 允许空值
                
            num_value = float(value)
            
            if min_value is not None and num_value < min_value:
                logger.error(f"{field_name} 必须大于等于 {min_value}")
                return False
                
            if max_value is not None and num_value > max_value:
                logger.error(f"{field_name} 必须小于等于 {max_value}")
                return False
                
            return True
        except ValueError:
            logger.error(f"{field_name} 必须是有效的数字")
            return False

    def highlight_error_field(self, field_name: str, is_error: bool):
        """高亮显示错误字段"""
        if field_name in self.entry_widgets:
            widget = self.entry_widgets[field_name]
            if is_error:
                widget.configure(border_color="red")
            else:
                widget.configure(border_color=["#3B8ED0", "#1F6AA5"])  # 恢复默认颜色

    def validate_all_fields(self) -> bool:
        """验证所有字段"""
        is_valid = True
        
        # 验证temperature
        temp_valid = self.validate_numeric_field(
            self.temperature_var.get(),
            "Temperature",
            min_value=0,
            max_value=1
        )
        self.highlight_error_field("temperature", not temp_valid)
        is_valid = is_valid and temp_valid
        
        # 验证max_tokens
        tokens_valid = self.validate_numeric_field(
            self.max_tokens_var.get(),
            "Max Tokens",
            min_value=1
        )
        self.highlight_error_field("max_tokens", not tokens_valid)
        is_valid = is_valid and tokens_valid
        
        # 验证min_sentence_length
        min_len_valid = self.validate_numeric_field(
            self.min_length_var.get(),
            "最小句子长度",
            min_value=1
        )
        self.highlight_error_field("min_sentence_length", not min_len_valid)
        is_valid = is_valid and min_len_valid
        
        # 验证max_sentence_length
        max_len_valid = self.validate_numeric_field(
            self.max_length_var.get(),
            "最大句子长度",
            min_value=1
        )
        self.highlight_error_field("max_sentence_length", not max_len_valid)
        is_valid = is_valid and max_len_valid
        
        # 验证batch_size
        batch_valid = self.validate_numeric_field(
            self.batch_size_var.get(),
            "每批处理数量",
            min_value=50,
            max_value=2000
        )
        self.highlight_error_field("batch_size", not batch_valid)
        is_valid = is_valid and batch_valid
        
        # 验证max_sentence_length > min_sentence_length
        if max_len_valid and min_len_valid:
            try:
                max_len = float(self.max_length_var.get())
                min_len = float(self.min_length_var.get())
                if max_len <= min_len:
                    logger.error("最大句子长度必须大于最小句子长度")
                    self.highlight_error_field("max_sentence_length", True)
                    self.highlight_error_field("min_sentence_length", True)
                    is_valid = False
            except ValueError:
                pass
        
        return is_valid

    def setup_ui(self):
        """设置UI布局，增加滚动条，按钮固定底部"""
        # 主容器，分为内容区和底部按钮区
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ========== 滚动内容区 ========== #
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=0, column=0, sticky="nsew")
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

        # 用Canvas+Frame实现滚动
        canvas = tk.Canvas(content_frame, borderwidth=0, highlightthickness=0, bg="#222")
        scrollable_frame = ctk.CTkFrame(canvas)
        vscrollbar = ctk.CTkScrollbar(content_frame, orientation="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscrollbar.set)

        vscrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # 自动调整滚动区域
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        scrollable_frame.bind("<Configure>", on_frame_configure)

        # 添加鼠标滚轮事件处理
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            
        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
            
        # 当鼠标进入canvas时绑定滚轮事件，离开时解绑
        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        # ========== 以下内容全部放到scrollable_frame里 ========== #
        # 创建标签页
        tabview = ctk.CTkTabview(scrollable_frame)
        tabview.pack(fill="both", expand=True, padx=10, pady=5)
        
        # API标签页
        api_tab = tabview.add("API")
        self.setup_api_tab(api_tab)
        
        # 文件标签页
        file_tab = tabview.add("文件")
        self.setup_file_tab(file_tab)

        # ========== 底部按钮区，固定在窗口底部 ========== #
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=1, column=0, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkButton(
            button_frame,
            text="保存",
            command=self.save_config,
            width=100
        ).pack(side="right", padx=5, pady=10)
        
        ctk.CTkButton(
            button_frame,
            text="取消",
            command=self.destroy,
            width=100
        ).pack(side="right", padx=5, pady=10)

        ctk.CTkButton(
            button_frame,
            text="还原默认配置",
            command=self.reset_to_default,
            width=120
        ).pack(side="left", padx=5, pady=10)

    def setup_api_tab(self, parent):
        """设置API标签页"""
        # 基础设置区域
        basic_frame = ctk.CTkFrame(parent)
        basic_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(basic_frame, text="基础设置", font=("Arial", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        
        endpoint_frame = ctk.CTkFrame(basic_frame)
        endpoint_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(endpoint_frame, text="API端点：").pack(side="left", padx=5)
        ctk.CTkEntry(endpoint_frame, textvariable=self.api_endpoint_var, width=300).pack(side="left", padx=5)
        
        key_frame = ctk.CTkFrame(basic_frame)
        key_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(key_frame, text="API密钥：").pack(side="left", padx=5)
        key_entry = ctk.CTkEntry(key_frame, textvariable=self.api_key_var, width=300, show="*")
        key_entry.pack(side="left", padx=5)

        # 模型参数区域
        model_frame = ctk.CTkFrame(parent)
        model_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(model_frame, text="模型参数", font=("Arial", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        
        model_select_frame = ctk.CTkFrame(model_frame)
        model_select_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(model_select_frame, text="模型：").pack(side="left", padx=5)
        model_entry = ctk.CTkEntry(model_select_frame, textvariable=self.model_var, width=300)
        model_entry.pack(side="left", padx=5)
        
        temp_frame = ctk.CTkFrame(model_frame)
        temp_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(temp_frame, text="Temperature：").pack(side="left", padx=5)
        temp_entry = ctk.CTkEntry(temp_frame, textvariable=self.temperature_var, width=100)
        temp_entry.pack(side="left", padx=5)
        self.entry_widgets["temperature"] = temp_entry
        ctk.CTkLabel(temp_frame, text="(0-1之间的值)").pack(side="left", padx=5)
        
        tokens_frame = ctk.CTkFrame(model_frame)
        tokens_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(tokens_frame, text="Max Tokens：").pack(side="left", padx=5)
        tokens_entry = ctk.CTkEntry(tokens_frame, textvariable=self.max_tokens_var, width=100)
        tokens_entry.pack(side="left", padx=5)
        self.entry_widgets["max_tokens"] = tokens_entry

        # 运行模式区域
        mode_frame = ctk.CTkFrame(parent)
        mode_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(mode_frame, text="运行模式", font=("Arial", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        
        mock_frame = ctk.CTkFrame(mode_frame)
        mock_frame.pack(fill="x", padx=5, pady=2)
        mock_checkbox = ctk.CTkCheckBox(
            mock_frame,
            text="启用模拟模式（不实际调用API）",
            variable=self.mock_mode_var
        )
        mock_checkbox.pack(side="left", padx=5)

    def setup_file_tab(self, parent):
        """设置文件标签页"""
        # 语言设置区域
        lang_frame = ctk.CTkFrame(parent)
        lang_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(lang_frame, text="语言设置", font=("Arial", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        
        source_lang_frame = ctk.CTkFrame(lang_frame)
        source_lang_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(source_lang_frame, text="源语言：").pack(side="left", padx=5)
        source_lang_entry = ctk.CTkEntry(source_lang_frame, textvariable=self.source_lang_var, width=100)
        source_lang_entry.pack(side="left", padx=5)
        ctk.CTkLabel(source_lang_frame, text="(例如: en)").pack(side="left", padx=5)
        
        target_lang_frame = ctk.CTkFrame(lang_frame)
        target_lang_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(target_lang_frame, text="目标语言：").pack(side="left", padx=5)
        target_lang_entry = ctk.CTkEntry(target_lang_frame, textvariable=self.target_lang_var, width=100)
        target_lang_entry.pack(side="left", padx=5)
        ctk.CTkLabel(target_lang_frame, text="(例如: zh-cn)").pack(side="left", padx=5)
        
        # 列设置区域
        columns_frame = ctk.CTkFrame(parent)
        columns_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(columns_frame, text="列设置", font=("Arial", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        
        # 列配置表格
        for col_name, col_config in self.column_vars.items():
            col_frame = ctk.CTkFrame(columns_frame)
            col_frame.pack(fill="x", padx=5, pady=2)
            
            # 列名
            col_label = ctk.CTkLabel(col_frame, text=self.get_column_display_name(col_name))
            col_label.pack(side="left", padx=5)
            
            # 启用复选框（仅对可选列显示）
            if col_name not in ['source_text', 'target_text']:
                enabled_checkbox = ctk.CTkCheckBox(
                    col_frame,
                    text="启用",
                    variable=col_config["enabled"]
                )
                enabled_checkbox.pack(side="left", padx=5)
            
            # 列索引
            ctk.CTkLabel(col_frame, text="列索引：").pack(side="right", padx=5)
            index_entry = ctk.CTkEntry(col_frame, textvariable=col_config["index"], width=50)
            index_entry.pack(side="right", padx=5)

        # 处理参数区域
        process_frame = ctk.CTkFrame(parent)
        process_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(process_frame, text="处理参数", font=("Arial", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        
        # 跳过行数设置
        skip_rows_frame = ctk.CTkFrame(process_frame)
        skip_rows_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(skip_rows_frame, text="跳过行数：").pack(side="left", padx=5)
        skip_rows_entry = ctk.CTkEntry(skip_rows_frame, textvariable=self.skip_rows_var, width=50)
        skip_rows_entry.pack(side="left", padx=5)
        ctk.CTkLabel(skip_rows_frame, text="(从第几行开始读取数据)").pack(side="left", padx=5)
        
        # 每批处理数量
        batch_frame = ctk.CTkFrame(process_frame)
        batch_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(batch_frame, text="每批处理数量：").pack(side="left", padx=5)
        batch_entry = ctk.CTkEntry(batch_frame, textvariable=self.batch_size_var, width=100)
        batch_entry.pack(side="left", padx=5)
        self.entry_widgets["batch_size"] = batch_entry
        ctk.CTkLabel(batch_frame, text="(推荐: 200-1000)").pack(side="left", padx=5)
        
        # 句子长度设置
        length_frame = ctk.CTkFrame(process_frame)
        length_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(length_frame, text="句子长度：").pack(side="left", padx=5)
        
        min_len_frame = ctk.CTkFrame(length_frame)
        min_len_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(min_len_frame, text="最小长度：").pack(side="left", padx=5)
        min_len_entry = ctk.CTkEntry(min_len_frame, textvariable=self.min_length_var, width=100)
        min_len_entry.pack(side="left", padx=5)
        self.entry_widgets["min_sentence_length"] = min_len_entry
        ctk.CTkLabel(min_len_frame, text="(推荐: 10-20)").pack(side="left", padx=5)
        
        max_len_frame = ctk.CTkFrame(length_frame)
        max_len_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(max_len_frame, text="最大长度：").pack(side="left", padx=5)
        max_len_entry = ctk.CTkEntry(max_len_frame, textvariable=self.max_length_var, width=100)
        max_len_entry.pack(side="left", padx=5)
        self.entry_widgets["max_sentence_length"] = max_len_entry
        ctk.CTkLabel(max_len_frame, text="(推荐: 300-500)").pack(side="left", padx=5)
        
        # 过滤选项
        filter_frame = ctk.CTkFrame(process_frame)
        filter_frame.pack(fill="x", padx=5, pady=2)
        filter_checkbox = ctk.CTkCheckBox(
            filter_frame,
            text="过滤非完整句子（不以标点符号结尾）",
            variable=self.filter_incomplete_var
        )
        filter_checkbox.pack(side="left", padx=5)
        
        # 风险提示
        risk_frame = ctk.CTkFrame(process_frame)
        risk_text = "提示：\n" + \
                   "- 长度设置过低可能导致语言识别不理想。"
        ctk.CTkLabel(risk_frame, text=risk_text, justify="left").pack(anchor="w", padx=5, pady=5)

    def get_column_display_name(self, col_name: str) -> str:
        """获取列的中文显示名称"""
        display_names = {
            "source_doc_id": "源语言文档编号",
            "source_text": "源语言文本",
            "target_doc_id": "目标语言文档编号",
            "target_text": "目标语言文本"
        }
        return display_names.get(col_name, col_name)

    def save_config(self):
        """保存配置"""
        try:
            # 验证所有字段
            if not self.validate_all_fields():
                return
                
            # 获取配置管理器的默认值
            default_config = self.config_manager.default_config
            
            # 构建新配置，对空值使用默认值
            new_config = {
                "api_endpoint": self.api_endpoint_var.get().strip(),
                "api_key": self.api_key_var.get().strip(),
                "temperature": float(self.temperature_var.get()) if self.temperature_var.get().strip() else default_config["temperature"],
                "max_tokens": int(self.max_tokens_var.get()) if self.max_tokens_var.get().strip() else default_config["max_tokens"],
                "model": self.model_var.get().strip() or default_config["model"],
                "min_sentence_length": int(self.min_length_var.get()) if self.min_length_var.get().strip() else default_config["min_sentence_length"],
                "max_sentence_length": int(self.max_length_var.get()) if self.max_length_var.get().strip() else default_config["max_sentence_length"],
                "filter_incomplete_sentences": self.filter_incomplete_var.get(),
                "mock_mode": self.mock_mode_var.get(),
                "batch_size": int(self.batch_size_var.get()) if self.batch_size_var.get().strip() else default_config["batch_size"],
                "file_structure": {
                    "skip_rows": int(self.skip_rows_var.get()) if self.skip_rows_var.get().strip() else 6,
                    "language": {
                        "source": self.source_lang_var.get().strip() or "en",
                        "target": self.target_lang_var.get().strip() or "zh-cn"
                    },
                    "columns": {
                        col_name: {
                            "enabled": col_config["enabled"].get(),
                            "index": int(col_config["index"].get()) if col_config["index"].get().strip() else 0
                        }
                        for col_name, col_config in self.column_vars.items()
                    }
                }
            }
            
            # 检查是否有字段被重置为默认值
            reset_fields = []
            for field, value in new_config.items():
                if field in ["api_endpoint", "api_key"]:  # 跳过必填字段
                    continue
                if str(value) != str(self.config.get(field, "")):
                    reset_fields.append(field)
            
            # 验证已填写的配置
            is_valid, error_msg = self.config_manager.validate_field_values(new_config)
            if not is_valid:
                logger.error(f"配置验证失败：{error_msg}")
                return
            
            # 更新配置管理器中的配置
            self.config_manager.config = new_config
            
            # 保存配置
            self.config_manager._save_config()
            
            # 如果有字段被重置为默认值，显示提示
            if reset_fields:
                reset_message = "以下字段未填写，已自动使用默认值：\n" + "\n".join(f"- {field}" for field in reset_fields)
                logger.info(reset_message)
            
            logger.info("配置已保存")
            self.destroy()
            
        except ValueError as e:
            logger.error(f"错误：{str(e)}")
        except Exception as e:
            logger.error(f"保存配置时发生错误：{str(e)}")

    def reset_to_default(self):
        """还原为默认配置"""
        # 创建确认弹窗
        dialog = ConfirmDialog(
            self,
            "确认还原",
            "确定要还原为默认配置吗？\n\n" +
            "此操作将重置所有设置项为默认值。",
            "还原",
            "取消"
        )
        
        # 等待用户响应
        self.wait_window(dialog)
        
        # 如果用户确认，执行还原操作
        if dialog.result:
            self.api_endpoint_var.set("")
            self.api_key_var.set("")
            self.temperature_var.set("0.3")
            self.max_tokens_var.set("1000")
            self.model_var.set("gemini-2.5-flash-preview-04-17-nothink")
            self.min_length_var.set("10")
            self.max_length_var.set("500")
            self.filter_incomplete_var.set(True)
            self.mock_mode_var.set(False)
            self.batch_size_var.set("500")
            
            # 重置文件结构配置
            self.skip_rows_var.set("6")
            self.source_lang_var.set("en")
            self.target_lang_var.set("zh-cn")
            for col_name, col_config in self.column_vars.items():
                col_config["enabled"].set(True)
                col_config["index"].set(str(self.config_manager.default_config["file_structure"]["columns"][col_name]["index"]))
            
            # 重置所有输入框的边框颜色
            for field in self.entry_widgets:
                self.highlight_error_field(field, False)
            
            logger.info("已还原为默认配置")

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

        # 设置日志文本框
        logger.set_text_widget(self.log_text)

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
        # 获取配置
        config_manager = ConfigManager()
        config, error = config_manager.load_config(require_all_fields=True)
        if not config:
            logger.error(f"配置不完整，请先完成必要设置。{error if error else ''}")
            return

        if not self.input_file_path or not self.output_file_path:
            logger.error("请先选择输入和输出文件！")
            return

        # 创建处理器
        self.processor = CoreProcessor(config)

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
            logger.error(f"处理过程中发生错误: {str(e)}")
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
            logger.info("处理完成！")
        else:
            logger.error("处理失败！")

    def stop_processing(self):
        """停止处理"""
        if self.processor:
            self.processor.stop()
            logger.info("正在停止处理...")

    def open_settings(self):
        """打开设置窗口"""
        config_dialog = ConfigDialog(self.root)
        self.root.wait_window(config_dialog)

    def run(self):
        """运行GUI程序"""
        self.root.mainloop()

if __name__ == "__main__":
    app = MainGUI()
    if app.root.winfo_exists():  # 检查窗口是否还存在
        app.run() 