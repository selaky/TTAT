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

def signal_handler(signum, frame):
    """处理终止信号"""
    print("\n正在终止程序...")
    if 'processor' in globals():
        processor.stop()
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# 初始化配置管理器
print("正在初始化配置...")
config_manager = ConfigManager()
config = config_manager.get_config()

# 如果配置无效，退出程序
if not config:
    print("程序因配置错误而退出")
    print("请检查配置文件是否正确，然后重新运行程序")
    exit()

print("配置加载成功，正在启动程序...")

# 创建文件选择对话框
root = tk.Tk()
root.withdraw()  # 隐藏主窗口
excel_file_path = filedialog.askopenfilename(
    title="选择Excel文件",
    filetypes=[("Excel files", "*.xlsx *.xls")]
)

if not excel_file_path:
    print("未选择文件，程序退出。")
    exit()

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
    print(f"未选择保存位置，将使用默认路径：{output_csv_path}")

try:
    # 创建处理器并处理文件
    processor = CoreProcessor(config)
    success = processor.process_file(excel_file_path, output_csv_path)

    if not success:
        print("处理过程中发生错误，请检查日志。")
        exit(1)

    print("处理完成！")
except KeyboardInterrupt:
    print("\n用户中断，正在停止处理...")
    if 'processor' in locals():
        processor.stop()
    sys.exit(0)
except Exception as e:
    print(f"发生未预期的错误：{str(e)}")
    sys.exit(1) 