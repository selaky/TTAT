import pandas as pd
import re
import requests
import json
import time
import os
import signal
import sys
import tkinter as tk
from tkinter import filedialog
from typing import List, Dict
from config_manager import ConfigManager
from core import CoreProcessor
import threading
import keyboard
from logger import logger

# 全局变量用于存储处理器实例
processor = None

def signal_handler(signum, frame):
    """处理终止信号"""
    logger.info("\n正在终止程序...")
    if processor:
        processor.stop()
    sys.exit(0)

def keyboard_listener():
    """键盘监听函数"""
    keyboard.add_hotkey('ctrl+q', lambda: signal_handler(signal.SIGINT, None))

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def check_and_setup_config() -> bool:
    """
    检查并设置配置文件
    
    Returns:
        bool: 配置是否有效
    """
    config_manager = ConfigManager()
    config, error = config_manager.load_config(require_all_fields=False)
    
    if config is None:
        # 配置文件不存在或无效
        if not os.path.exists(config_manager.config_file):
            logger.info("\n=== 首次运行配置 ===")
            logger.info("未检测到配置文件，正在创建默认配置文件...")
            config_manager.create_default_config()
            logger.info("\n请按以下步骤完成配置：")
            logger.info("1. 打开配置文件：" + config_manager.config_file)
            logger.info("2. 填写以下必要信息：")
            for field, schema in config_manager.config_schema.items():
                if schema["required"]:
                    logger.info(f"   - {field}: {schema['description']}")
            logger.info("3. 保存配置文件后重新运行程序")
        else:
            # 配置文件存在但无效
            logger.error("\n=== 配置错误 ===")
            logger.error("配置文件存在但内容无效，请检查并修改配置文件：" + config_manager.config_file)
            logger.error("确保填写了所有必要信息：")
            for field, schema in config_manager.config_schema.items():
                if schema["required"]:
                    logger.error(f"- {field}: {schema['description']}")
        
        return False
    
    # 检查必要字段是否已填写
    is_valid, error_msg = config_manager.validate_config(require_all_fields=True)
    if not is_valid:
        logger.warning("\n=== 配置不完整 ===")
        logger.warning("配置文件存在但缺少必要信息，请确保填写：")
        for field, schema in config_manager.config_schema.items():
            if schema["required"]:
                logger.warning(f"- {field}: {schema['description']}")
        return False
    
    return True

def main():
    """主函数"""
    # 检查配置
    if not check_and_setup_config():
        return
    
    logger.info("\n配置检查通过，正在启动程序...")
    logger.info("提示：按 Ctrl+Q 可以随时终止处理并退出程序")
    
    # 启动键盘监听
    keyboard_thread = threading.Thread(target=keyboard_listener, daemon=True)
    keyboard_thread.start()
    
    # 创建文件选择对话框
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    excel_file_path = filedialog.askopenfilename(
        title="选择Excel文件",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )

    if not excel_file_path:
        logger.error("未选择文件，程序退出。")
        return

    # 添加保存文件对话框
    output_csv_path = filedialog.asksaveasfilename(
        title="选择保存位置",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        initialfile="ai_analysis_results.csv"
    )

    # 如果用户没有选择保存位置，使用默认路径
    if not output_csv_path:
        output_csv_path = 'ai_analysis_results.csv'
        logger.warning(f"未选择保存位置，将使用默认路径：{output_csv_path}")

    try:
        # 获取配置
        config_manager = ConfigManager()
        config, error = config_manager.load_config()
        
        # 创建处理器并处理文件
        global processor
        processor = CoreProcessor(config)
        success = processor.process_file(excel_file_path, output_csv_path)

        if not success:
            logger.error("处理过程中发生错误，请检查日志。")
            return

        logger.info("处理完成！")
    except KeyboardInterrupt:
        logger.info("\n用户中断，正在停止处理...")
        if processor:
            processor.stop()
    except Exception as e:
        logger.error(f"发生未预期的错误：{str(e)}")

if __name__ == "__main__":
    main() 