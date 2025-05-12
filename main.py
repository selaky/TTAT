import pandas as pd
import re
import requests
import json
import time
import os
import signal
from dotenv import load_dotenv # 如果使用.env文件
import tkinter as tk
from tkinter import filedialog
from typing import List, Dict
from config_manager import ConfigManager

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_ENDPOINT = os.getenv("API_ENDPOINT")

# 添加全局停止标志
stop_processing = False

def set_stop_flag():
    """设置停止标志"""
    global stop_processing
    stop_processing = True
    print("正在停止处理...")

def signal_handler(signum, frame):
    """处理键盘中断信号"""
    print("\n检测到键盘中断，正在停止处理...")
    set_stop_flag()

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)

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

# 跳过前6行元数据，并指定列名
try:
    df = pd.read_excel(excel_file_path, skiprows=6, header=None, 
                      names=['index', 'doc_id', 'english', 'type', 'chinese'])
except FileNotFoundError:
    print(f"错误：找不到文件 {excel_file_path}")
    exit()

# 清理空行 (如果有的话)
df.dropna(how='all', inplace=True)
df.reset_index(drop=True, inplace=True)

# 将成对的中英文句子提取出来
sentence_pairs = []
for i in range(0, len(df)):
    if i + 1 < len(df):
        eng_text_raw = str(df.iloc[i, 1]) # 英文在第二列
        chi_text_raw = str(df.iloc[i, 3]) # 中文在第四列
        doc_id = str(df.iloc[i, 0])  # 使用第一列的编号作为doc_id

        # 清理句子，去除<s>, </s>标签和doc#信息
        eng_sentence = re.sub(r'<s>|</s>|doc#\w+\s*', '', eng_text_raw).strip()
        chi_sentence = re.sub(r'<s>|</s>|doc#\w+\s*', '', chi_text_raw).strip()

        # 移除中文句子开头的数字和点 (如 "41 . ", "64 . ")
        chi_sentence = re.sub(r'^\d+\s*\.\s*', '', chi_sentence).strip()
        
        # 删除中文句子中的所有空格
        chi_sentence = re.sub(r'\s+', '', chi_sentence)
        
        # 检查英文句子是否是句子
        if not re.search(r'[.!?;,]$', eng_sentence):
            continue  # 说明是标题，跳过该句对

        if eng_sentence and chi_sentence: # 确保句子不为空
            sentence_pairs.append({
                'doc_id': doc_id,
                'english_sentence': eng_sentence,
                'chinese_sentence': chi_sentence
            })
print(f"成功提取 {len(sentence_pairs)} 个句对。")

def construct_prompt(english_sentence, chinese_sentence):
    # 定义名词化结构    
    nominalization_structure_definitions = """
Definition of Nominalization Structure:
Nominalization is the conversion of actions, states, qualities, or other non-nominal concepts into noun forms or noun phrases.
Types of Nominalization:
1. Derivational Nominalization: Formed by adding nominalizing affixes to a verb/adjective (e.g., -ment, -tion, -sion, -cy, -ty, -ance).
   Example words: 'development', 'protection'.
2. Conversional Nominalization (Zero Derivation): A verb or adjective used directly as a noun without form change.
   Example: 'a request' (from 'to request'), 'use' (from 'to use').
3. Phrasal Nominalization: Specifically the 'V-ing of NP' construction (gerund + 'of' + noun phrase).
   Example: 'the killing of members', 'the setting up of a committee'.
"""
    # 定义翻译技巧
    translation_technique_definitions = """
    Translation techniques:
1. Maintain_Noun: The nominalization is translated as a noun in Chinese.
2. Shift_Word_Class: The nominalization is translated as a verb, adjective, etc.
3. Omit_Structure: The nominalization is omitted in translation.
4. Reconstruct_Sentence: The overall sentence structure is changed.
5. Difficult_To_Determine: Difficult to categorize or no clear correspondence.
    """ 
    # 整体prompt
    prompt = f"""
    Please analyze the following English sentence from United Nations documents and its Chinese translation.
English original:
{english_sentence}
Chinese translation:
{chinese_sentence}
Tasks:
1. Identify all core nominalization structures in the English sentence. The definition of nominalization structure is as follows:
   {nominalization_structure_definitions}
2. For each identified nominalization structure, provide:
   a. The identified English nominalization structure (Identified_Nominalization_EN)
   b. Type of nominalization (Nominalization_Type): Derivational, Conversional, or Phrasal
   c. Translation technique used (Translation_Technique). The definition of translation technique is as follows:
      {translation_technique_definitions}

Please return your analysis as a JSON list, where each element is a dictionary representing an identified nominalization structure:
[
  {{
    "Identified_Nominalization_EN": "the killing of members",
    "Nominalization_Type": "Phrasal",
    "Translation_Technique": "Maintain_Noun"
  }},
  {{
    "Identified_Nominalization_EN": "development",
    "Nominalization_Type": "Derivational",
    "Translation_Technique": "Shift_Word_Class"
  }}
]
If no nominalization structures are found, please return an empty list: []

    """
    return prompt

def analyze_sentence_with_ai(english_sentence, chinese_sentence, api_key, api_endpoint):
    prompt = construct_prompt(english_sentence, chinese_sentence)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 修改API调用格式以符合AIHubMix的要求
    payload = {
        "model": "gemini-2.5-flash-preview-04-17-nothink",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1000
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 修改API端点，添加/chat/completions
            response = requests.post(f"{api_endpoint}/chat/completions", 
                                  headers=headers, 
                                  json=payload, 
                                  timeout=60)
            response.raise_for_status()
            
            response_json = response.json()
            
            # 修改响应解析逻辑以匹配AIHubMix的返回格式
            ai_response_content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if not ai_response_content:
                print("警告：AI返回了空内容。")
                return []

            try:
                # AI可能在JSON外包裹了其他文本，尝试提取JSON部分
                # 例如，如果AI说 "Here is the JSON list: \n[...]\n"
                json_match = re.search(r'\[.*\]', ai_response_content, re.DOTALL)
                if json_match:
                    parsed_json = json.loads(json_match.group(0))
                    return parsed_json
                else:
                    print(f"警告：无法从AI回复中提取有效的JSON列表。\nAI回复：\n{ai_response_content}")
                    return []
            except json.JSONDecodeError as e:
                print(f"错误：解析AI返回的JSON失败。错误信息：{e}\nAI回复：\n{ai_response_content}")
                return [] # 返回空列表表示解析失败

        except requests.exceptions.RequestException as e:
            print(f"API请求错误 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1)) # 指数退避等待
            else:
                print("已达到最大重试次数，跳过此句对。")
                return [] # 表示API调用失败
        except Exception as e:
            print(f"处理API响应时发生未知错误: {e}")
            return []
    return [] # 如果所有重试都失败

all_results = []
for index, pair in enumerate(sentence_pairs):
    # 检查是否收到停止信号
    if stop_processing:
        print("处理已停止")
        break
        
    print(f"正在处理句对 {index + 1}/{len(sentence_pairs)}: {pair['doc_id']}")
    
    # 控制API请求频率，避免触发速率限制 (根据你的API提供商调整)
    if index > 0 and index % 5 == 0: # 例如每5个请求暂停1秒
        print("暂停1秒以避免API速率限制...")
        time.sleep(1)

    analysis_results = analyze_sentence_with_ai(
        pair['english_sentence'],
        pair['chinese_sentence'],
        API_KEY,
        API_ENDPOINT
    )

    if analysis_results: # 如果AI返回了有效的分析结果（一个列表）
        for result_item in analysis_results: # analysis_results 是一个列表，每个元素是一个字典
            # 将原始句对信息和AI分析结果合并
            combined_result = {
                'doc_id': pair['doc_id'],
                'english_sentence': pair['english_sentence'],
                'chinese_sentence': pair['chinese_sentence'],
                'identified_nominalization_en': result_item.get('Identified_Nominalization_EN', 'N/A'),
                'nominalization_type': result_item.get('Nominalization_Type', 'N/A'),
                'translation_technique': result_item.get('Translation_Technique', 'N/A')
            }
            all_results.append(combined_result)
    else:
        # 即使AI没有找到名词化结构或API调用失败，也记录原始句对信息，方便后续检查
        all_results.append({
            'doc_id': pair['doc_id'],
            'english_sentence': pair['english_sentence'],
            'chinese_sentence': pair['chinese_sentence'],
            'identified_nominalization_en': 'AI_NO_RESULT_OR_ERROR',
            'nominalization_type': 'N/A',
            'translation_technique': 'N/A'
        })
    
    if index >= 9: # 测试前10条
        break

# 根据是否停止来显示不同的完成信息
if stop_processing:
    print(f"处理中断。已处理 {len(all_results)} 条结果记录。")
else:
    print(f"所有句对处理完毕。共收集到 {len(all_results)} 条结果记录。")

# 将收集到的所有结果转换为DataFrame并保存
output_df = pd.DataFrame(all_results)
try:
    output_df.to_csv(output_csv_path, index=False, encoding='utf-8-sig') # utf-8-sig 确保Excel正确显示中文
    print(f"结果已保存到: {output_csv_path}")
except Exception as e:
    print(f"保存结果到CSV时出错: {e}")
