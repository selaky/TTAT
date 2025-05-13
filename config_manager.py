import json
import os
from typing import Dict, Optional, Tuple
from datetime import datetime

class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config: Dict = {}
        
        # 配置定义
        self.config_schema = {
            "api_endpoint": {
                "default": "",
                "required": True,
                "type": "string",
                "description": "API 端点网址，例如：https://api.example.com/v1"
            },
            "api_key": {
                "default": "",
                "required": True,
                "type": "string",
                "description": "API 密钥，用于身份验证"
            },
            "temperature": {
                "default": 0.3,
                "required": False,
                "type": "float",
                "min": 0,
                "max": 1,
                "description": "生成文本的随机性程度，范围 0-1，值越大随机性越强"
            },
            "max_tokens": {
                "default": 1000,
                "required": False,
                "type": "integer",
                "min": 1,
                "description": "生成文本的最大长度"
            },
            "model": {
                "default": "gemini-2.5-flash-preview-04-17-nothink",
                "required": False,
                "type": "string",
                "description": "使用的模型名称"
            },
            "min_sentence_length": {
                "default": 10,
                "required": False,
                "type": "integer",
                "min": 1,
                "description": "最小句子长度限制（字符数）。\n推荐值：10-20\n风险提示：设置过小可能导致语言识别不准确"
            },
            "max_sentence_length": {
                "default": 500,
                "required": False,
                "type": "integer",
                "min": 1,
                "description": "最大句子长度限制（字符数）。\n推荐值：300-500"
            },
            "filter_incomplete_sentences": {
                "default": True,
                "required": False,
                "type": "boolean",
                "description": "是否过滤不以标点符号结尾的非句子。\n- 开启：只处理以标点符号结尾的完整句子\n- 关闭：处理所有句子，不判断完整性"
            },
            "mock_mode": {
                "default": False,
                "required": False,
                "type": "boolean",
                "description": "是否启用模拟模式。\n- 开启：不实际调用API，返回模拟数据\n- 关闭：正常调用API"
            }
        }
        
        # 从schema生成默认配置
        self.default_config = {
            key: value["default"] for key, value in self.config_schema.items()
        }
        
        # 配置元数据
        self.metadata = {
            "_metadata": {
                "version": "1.0",
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "documentation": {
                    key: value["description"] 
                    for key, value in self.config_schema.items()
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

    def validate_field_values(self, config: Dict) -> Tuple[bool, str]:
        """
        验证配置字段的值是否合法
        
        Args:
            config: 要验证的配置字典
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        try:
            for field, value in config.items():
                if field.startswith('_'):
                    continue
                    
                if field not in self.config_schema:
                    continue
                    
                schema = self.config_schema[field]
                
                # 类型检查
                if schema["type"] == "float":
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        return False, f"{field} 必须是浮点数"
                        
                elif schema["type"] == "integer":
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        return False, f"{field} 必须是整数"
                        
                elif schema["type"] == "boolean":
                    if not isinstance(value, bool):
                        return False, f"{field} 必须是布尔值"
                        
                # 范围检查
                if "min" in schema:
                    if value < schema["min"]:
                        return False, f"{field} 必须大于等于 {schema['min']}"
                        
                if "max" in schema:
                    if value > schema["max"]:
                        return False, f"{field} 必须小于等于 {schema['max']}"
                        
                # 特殊字段验证
                if field == "max_sentence_length" and "min_sentence_length" in config:
                    if value <= config["min_sentence_length"]:
                        return False, "max_sentence_length 必须大于 min_sentence_length"
                        
        except Exception as e:
            return False, f"配置验证时发生错误：{str(e)}"
            
        return True, ""

    def validate_config(self, require_all_fields: bool = True) -> Tuple[bool, str]:
        """
        验证配置文件内容
        
        Args:
            require_all_fields: 是否要求所有必要字段都必须填写
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not self.config:
            return False, "配置文件为空"
            
        # 检查必要字段
        if require_all_fields:
            missing_fields = []
            empty_fields = []
            
            for field, schema in self.config_schema.items():
                if schema["required"]:
                    if field not in self.config:
                        missing_fields.append(field)
                    elif not str(self.config[field]).strip():
                        empty_fields.append(field)
                        
            if missing_fields:
                return False, f"配置文件缺少必要字段：{', '.join(missing_fields)}"
                
            if empty_fields:
                return False, f"以下字段的值为空：{', '.join(empty_fields)}"
            
        # 验证字段值
        return self.validate_field_values(self.config)

    def _save_config(self) -> None:
        """保存配置到文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def load_config(self, require_all_fields: bool = True) -> Tuple[Optional[Dict], Optional[str]]:
        """
        加载配置文件
        
        Args:
            require_all_fields: 是否要求所有必要字段都必须填写
            
        Returns:
            Tuple[Optional[Dict], Optional[str]]: (配置字典, 错误信息)
        """
        if not os.path.exists(self.config_file):
            self.create_default_config()
            return None, f"配置文件 {self.config_file} 不存在，已创建默认配置"

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            # 验证配置
            is_valid, error_msg = self.validate_config(require_all_fields)
            if not is_valid:
                return None, f"配置验证失败：{error_msg}"
            
            return self.config, None
            
        except json.JSONDecodeError:
            return None, f"配置文件 {self.config_file} 格式不正确"
        except Exception as e:
            return None, f"读取配置文件时发生错误：{str(e)}"
