import json
import os
from typing import Dict, Optional, Tuple
from datetime import datetime

class ConfigManager:
    # 当前软件版本号
    CURRENT_VERSION = "1.0.0"
    
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
            },
            "batch_size": {
                "default": 500,
                "required": False,
                "type": "integer",
                "min": 50,
                "max": 2000,
                "description": "每批处理的句子数量。\n推荐值：200-1000\n- 值过小会增加I/O开销\n- 值过大会增加内存占用"
            },
            "file_structure": {
                "default": {
                    "skip_rows": 6,
                    "columns": {
                        "source_doc_id": {
                            "enabled": True,
                            "index": 0,
                            "description": "源语言文档编号列（可选）"
                        },
                        "source_text": {
                            "enabled": True,
                            "index": 1,
                            "description": "源语言文本列（必选）"
                        },
                        "target_doc_id": {
                            "enabled": True,
                            "index": 2,
                            "description": "目标语言文档编号列（可选）"
                        },
                        "target_text": {
                            "enabled": True,
                            "index": 3,
                            "description": "目标语言文本列（必选）"
                        }
                    },
                    "language": {
                        "source": "en",
                        "target": "zh-cn",
                        "description": "源语言和目标语言代码"
                    }
                },
                "required": False,
                "type": "object",
                "description": "Excel文件结构配置\n" +
                             "- skip_rows: 跳过的行数\n" +
                             "- columns: 各列的配置\n" +
                             "  - enabled: 是否启用该列\n" +
                             "  - index: 列索引位置\n" +
                             "  - description: 列说明\n" +
                             "- language: 语言设置\n" +
                             "  - source: 源语言代码\n" +
                             "  - target: 目标语言代码"
            }
        }
        
        # 从schema生成默认配置
        self.default_config = {}
        for key, value in self.config_schema.items():
            if isinstance(value.get("default"), dict):
                # 对于嵌套的字典，进行深拷贝
                self.default_config[key] = value["default"].copy()
            else:
                self.default_config[key] = value["default"]
        
        # 配置元数据
        self.metadata = {
            "_metadata": {
                "version": self.CURRENT_VERSION,
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

    def update_config(self) -> Tuple[bool, str]:
        """
        更新配置文件到最新版本
        
        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """
        try:
            # 获取当前配置文件的版本
            current_version = self.config.get("_metadata", {}).get("version", "0.0.0")
            
            # 如果版本相同，无需更新
            if current_version == self.CURRENT_VERSION:
                return True, "配置文件已是最新版本"
            
            # 保存用户当前的配置值
            user_config = {k: v for k, v in self.config.items() if not k.startswith('_')}
            
            # 创建新的配置，合并默认值和用户配置
            new_config = self.default_config.copy()
            new_config.update(user_config)
            
            # 更新元数据
            new_config.update(self.metadata)
            
            # 保存更新后的配置
            self.config = new_config
            self._save_config()
            
            return True, f"配置文件已从 {current_version} 更新到 {self.CURRENT_VERSION}"
            
        except Exception as e:
            return False, f"更新配置文件时发生错误：{str(e)}"

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
            
            # 检查并更新配置
            success, update_msg = self.update_config()
            if not success:
                return None, update_msg
            
            # 验证配置
            is_valid, error_msg = self.validate_config(require_all_fields)
            if not is_valid:
                return None, f"配置验证失败：{error_msg}"
            
            return self.config, None
            
        except json.JSONDecodeError:
            return None, f"配置文件 {self.config_file} 格式不正确"
        except Exception as e:
            return None, f"读取配置文件时发生错误：{str(e)}"
