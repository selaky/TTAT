import json
import os
from typing import Dict, Any

class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            # 如果配置文件不存在，创建默认配置
            default_config = {
                "api": {
                    "key": "",
                    "endpoint": ""
                },
                "model": {
                    "name": "gemini-2.5-flash-preview-04-17-nothink",
                    "temperature": 0.3,
                    "max_tokens": 1000
                },
                "processing": {
                    "batch_size": 5,
                    "delay_between_batches": 1
                }
            }
            self.save_config(default_config)
            return default_config

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件时出错: {e}")
            return {}

    def save_config(self, config: Dict[str, Any] = None) -> bool:
        """保存配置到文件"""
        if config is None:
            config = self.config

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置文件时出错: {e}")
            return False

    def get_api_key(self) -> str:
        """获取API密钥"""
        return self.config.get("api", {}).get("key", "")

    def get_api_endpoint(self) -> str:
        """获取API端点"""
        return self.config.get("api", {}).get("endpoint", "")

    def get_model_name(self) -> str:
        """获取模型名称"""
        return self.config.get("model", {}).get("name", "")

    def get_temperature(self) -> float:
        """获取温度参数"""
        return self.config.get("model", {}).get("temperature", 0.3)

    def get_max_tokens(self) -> int:
        """获取最大token数"""
        return self.config.get("model", {}).get("max_tokens", 1000)

    def get_batch_size(self) -> int:
        """获取批处理大小"""
        return self.config.get("processing", {}).get("batch_size", 5)

    def get_delay_between_batches(self) -> int:
        """获取批处理间隔时间"""
        return self.config.get("processing", {}).get("delay_between_batches", 1)

    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """更新配置"""
        self.config.update(new_config)
        return self.save_config()

    def validate_config(self) -> bool:
        """验证配置是否有效"""
        required_fields = {
            "api": ["key", "endpoint"],
            "model": ["name", "temperature", "max_tokens"],
            "processing": ["batch_size", "delay_between_batches"]
        }

        for section, fields in required_fields.items():
            if section not in self.config:
                print(f"缺少配置节: {section}")
                return False
            for field in fields:
                if field not in self.config[section]:
                    print(f"缺少配置项: {section}.{field}")
                    return False

        return True 