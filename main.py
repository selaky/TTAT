import pandas as pd
import re
import requests
import json
import time
import os
from dotenv import load_dotenv # 如果使用.env文件
import tkinter as tk
from tkinter import filedialog

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_ENDPOINT = os.getenv("API_ENDPOINT")

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

# 跳过第一行元数据，并指定列名，如果Excel没有明确的列头给pandas用
# 或者，如果你的数据从第二行开始，且没有header，可以设置 header=None
# 然后再根据需要选取列
try:
    df = pd.read_excel(excel_file_path, skiprows=1, header=None, 
                      names=['index', 'doc_id', 'english', 'type', 'chinese'])
except FileNotFoundError:
    print(f"错误：找不到文件 {excel_file_path}")
    exit()

# 清理空行 (如果有的话)
df.dropna(how='all', inplace=True)
df.reset_index(drop=True, inplace=True)

# 将成对的中英文句子提取出来
sentence_pairs = []
for i in range(0, len(df), 2):
    if i + 1 < len(df):
        eng_text_raw = str(df.iloc[i, 1]) # 英文在第二列
        chi_text_raw = str(df.iloc[i, 3]) # 中文在第四列
        doc_id = str(df.iloc[i, 1]) # 使用Excel中的doc_id列

        # 清理句子，去除<s>, </s>标签和doc#信息
        eng_sentence = re.sub(r'<s>|</s>|doc#\w+\s*', '', eng_text_raw).strip()
        chi_sentence = re.sub(r'<s>|</s>|doc#\w+\s*', '', chi_text_raw).strip()

        # 移除中文句子开头的数字和点 (如 "41 . ", "64 . ")
        chi_sentence = re.sub(r'^\d+\s*\.\s*', '', chi_sentence).strip()

        if eng_sentence and chi_sentence: # 确保句子不为空
            sentence_pairs.append({
                'doc_id': doc_id,
                'english_sentence': eng_sentence,
                'chinese_sentence': chi_sentence
            })
print(f"成功提取 {len(sentence_pairs)} 个句对。")

def construct_prompt(english_sentence, chinese_sentence):
    # 需要根据名词化结构定义来完善这部分
    # 例如，研究的是 "V-ing of" 结构，或者 "-tion", "-ment" 派生词等
    nominalization_definition_example = """
    名词化结构定义：
    1. 派生型名词化：由动词或形容词通过添加后缀（如-tion, -ment, -ness, -ity, -ing等）转换而来的名词，表达动作、过程、状态或性质。例如：development, management, happiness, ability, building (作为名词)。
    2. 转换型名词化（零派生）：动词或形容词直接用作名词，形式不变但词性改变。例如：a run, a hope, the good, a find.
    3. 短语型名词化：通常指动名词短语（如 "the V-ing of N" 结构）或不定式短语在句中充当名词成分。例如： "the killing of members", "to achieve success".

    请重点关注英文句子中符合上述定义的、充当核心名词成分的名词化结构。
    """

    prompt = f"""
    请分析以下英文句子及其对应的中文译文。

    英文原句：
    {english_sentence}

    中文译文：
    {chinese_sentence}

    任务：
    1.  请识别英文原句中的所有核心名词化结构。{nominalization_definition_example}
    2.  对于每一个识别出的名词化结构，请提供以下信息：
        a.  识别出的英文名词化结构本身 (Identified_Nominalization_EN)。
        b.  该名词化结构的类型 (Nominalization_Type)，从以下选项中选择：派生型 (Derivational), 转换型 (Conversional), 短语型 (Phrasal)。
        c.  该名词化结构在中文译文中的翻译技巧 (Translation_Technique)，从以下选项中选择：保持名词结构 (Maintain_Noun), 词类转换 (Shift_Word_Class), 省略不必要结构 (Omit_Structure), 句子重构 (Reconstruct_Sentence)。如果一个名词化结构在译文中没有直接对应或者难以判断，请标记为“难以判断 (Difficult_To_Determine)”。

    请以JSON列表的格式返回结果，每个元素是一个字典，代表一个识别出的名词化结构及其分析。
    例如：
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
    如果英文句子中没有找到符合要求的名词化结构，请返回一个空列表：[]
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

print(f"所有句对处理完毕。共收集到 {len(all_results)} 条结果记录。")

# 将收集到的所有结果转换为DataFrame并保存
output_df = pd.DataFrame(all_results)
output_csv_path = 'ai_analysis_results.csv'
try:
    output_df.to_csv(output_csv_path, index=False, encoding='utf-8-sig') # utf-8-sig 确保Excel正确显示中文
    print(f"结果已保存到: {output_csv_path}")
except Exception as e:
    print(f"保存结果到CSV时出错: {e}")
