import json
import os
from typing import Dict, Optional, Tuple
from datetime import datetime

class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config: Dict = {}
        self.required_fields = ["api_endpoint", "api_key"]
        self.default_config = {
            "api_endpoint": "",
            "api_key": "",
            "temperature": 0.3,
            "max_tokens": 1000,
            "model": "gemini-2.5-flash-preview-04-17-nothink",
            "min_sentence_length": 10,  # 默认最小句子长度
            "max_sentence_length": 500,   # 默认最大句子长度
            "filter_incomplete_sentences": True,  # 是否过滤非完整句子
            "mock_mode": False  # 是否启用模拟模式
        }
        # 配置元数据
        self.metadata = {
            "_metadata": {
                "version": "1.0",
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "documentation": {
                    "api_endpoint": "API 端点网址，例如：https://api.example.com/v1",
                    "api_key": "API 密钥，用于身份验证",
                    "temperature": "生成文本的随机性程度，范围 0-1，值越大随机性越强",
                    "max_tokens": "生成文本的最大长度",
                    "model": "使用的模型名称",
                    "min_sentence_length": "最小句子长度限制（字符数）。\n推荐值：10-20\n风险提示：设置过小可能导致语言识别不准确",
                    "max_sentence_length": "最大句子长度限制（字符数）。\n推荐值：300-500",
                    "filter_incomplete_sentences": "是否过滤不以标点符号结尾的非句子。\n- 开启：只处理以标点符号结尾的完整句子\n- 关闭：处理所有句子，不判断完整性",
                    "mock_mode": "是否启用模拟模式。\n- 开启：不实际调用API，返回模拟数据\n- 关闭：正常调用API"
                }
            }
        }

    def create_default_config(self) -> None:
        """创建默认配置文件"""
        # 创建默认配置
        self.config = self.default_config.copy()
        
        # 合并配置和元数据
        self.config.update(self.metadata)
        
        # 保存配置
        self._save_config()
        print(f"\n默认配置文件已创建：{self.config_file}")

    def validate_config(self) -> Tuple[bool, str]:
        """
        验证配置文件内容
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not self.config:
            return False, "配置文件为空"
            
        # 检查必要字段是否存在（排除元数据字段）
        missing_fields = [field for field in self.required_fields 
                         if field not in self.config or field.startswith('_')]
        if missing_fields:
            return False, f"配置文件缺少必要字段：{', '.join(missing_fields)}"
            
        # 检查字段值是否为空（排除元数据字段）
        empty_fields = [field for field in self.required_fields 
                       if not self.config.get(field, '').strip() and not field.startswith('_')]
        if empty_fields:
            return False, f"以下字段的值为空：{', '.join(empty_fields)}"
            
        # 验证数值字段
        try:
            temp = float(self.config.get("temperature", 0))
            if not 0 <= temp <= 1:
                return False, "temperature 必须在 0 到 1 之间"
                
            tokens = int(self.config.get("max_tokens", 0))
            if tokens <= 0:
                return False, "max_tokens 必须大于 0"
                
            min_len = int(self.config.get("min_sentence_length", 0))
            max_len = int(self.config.get("max_sentence_length", 0))
            if min_len <= 0:
                return False, "min_sentence_length 必须大于 0"
            if max_len <= min_len:
                return False, "max_sentence_length 必须大于 min_sentence_length"
                
        except (ValueError, TypeError):
            return False, "配置中的数值字段格式不正确"
            
        return True, ""

    def _save_config(self) -> None:
        """保存配置到文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def load_config(self) -> Tuple[Optional[Dict], Optional[str]]:
        """
        加载配置文件
        
        Returns:
            Tuple[Optional[Dict], Optional[str]]: (配置字典, 错误信息)
        """
        if not os.path.exists(self.config_file):
            self.create_default_config()
            # 创建完默认配置后，不要直接返回，而是继续验证
            # 这样会触发验证失败，提示用户配置API信息
            return None, f"配置文件 {self.config_file} 不存在，已创建默认配置"

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            # 验证配置
            is_valid, error_msg = self.validate_config()
            if not is_valid:
                return None, f"配置验证失败：{error_msg}"
            
            return self.config, None
            
        except json.JSONDecodeError:
            return None, f"配置文件 {self.config_file} 格式不正确"
        except Exception as e:
            return None, f"读取配置文件时发生错误：{str(e)}"
