import json
import os
from typing import Dict, Optional

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
            "model": "gemini-2.5-flash-preview-04-17-nothink"
        }
        # 添加配置项说明
        self.config_comments = {
            "_comments": {
                "api_endpoint": "API 端点网址，例如：https://api.example.com/v1",
                "api_key": "API 密钥，用于身份验证",
                "temperature": "生成文本的随机性程度，范围 0-1，值越大随机性越强",
                "max_tokens": "生成文本的最大长度",
                "model": "使用的模型名称"
            }
        }

    def create_default_config(self) -> None:
        """创建默认配置文件"""
        print("\n=== 配置向导 ===")
        print("请输入必要的配置信息：")
        
        # 获取必要配置
        api_endpoint = input("请输入 API 端点网址: ").strip()
        api_key = input("请输入 API Key: ").strip()
        
        # 更新配置
        self.config = self.default_config.copy()
        self.config["api_endpoint"] = api_endpoint
        self.config["api_key"] = api_key
        
        # 询问是否自定义其他配置
        print("\n是否要自定义其他配置？(y/n)")
        if input().lower() == 'y':
            self._customize_config()
        
        # 合并配置和注释
        self.config.update(self.config_comments)
        
        # 保存配置
        self._save_config()
        print(f"\n配置已保存到 {self.config_file}")

    def _customize_config(self) -> None:
        """自定义其他配置项"""
        print("\n可自定义的配置项：")
        print("1. temperature (默认: 0.3) - 生成文本的随机性程度，范围 0-1")
        print("2. max_tokens (默认: 1000) - 生成文本的最大长度")
        print("3. model (默认: gemini-2.5-flash-preview-04-17-nothink) - 使用的模型名称")
        
        try:
            temp = input("\n请输入 temperature (0-1): ").strip()
            if temp:
                self.config["temperature"] = float(temp)
            
            tokens = input("请输入 max_tokens: ").strip()
            if tokens:
                self.config["max_tokens"] = int(tokens)
            
            model = input("请输入 model: ").strip()
            if model:
                self.config["model"] = model
        except ValueError:
            print("输入格式错误，将使用默认值")

    def _save_config(self) -> None:
        """保存配置到文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def load_config(self) -> Optional[Dict]:
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            print(f"配置文件 {self.config_file} 不存在")
            self.create_default_config()
            return self.config

        try:
            print(f"正在读取配置文件：{self.config_file}")
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            # 验证必要字段
            missing_fields = [field for field in self.required_fields 
                            if not self.config.get(field)]
            
            if missing_fields:
                print(f"错误：配置文件缺少必要字段：{', '.join(missing_fields)}")
                print("请修改配置文件后重试")
                return None
            
            # 验证字段值是否为空
            empty_fields = [field for field in self.required_fields 
                          if not self.config.get(field, '').strip()]
            
            if empty_fields:
                print(f"错误：以下字段的值为空：{', '.join(empty_fields)}")
                print("请修改配置文件后重试")
                return None
            
            print("配置文件验证通过")
            return self.config
            
        except json.JSONDecodeError:
            print(f"错误：配置文件 {self.config_file} 格式不正确")
            return None
        except Exception as e:
            print(f"读取配置文件时发生错误：{str(e)}")
            return None

    def get_config(self) -> Optional[Dict]:
        """获取配置信息"""
        return self.load_config() 