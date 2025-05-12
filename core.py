import pandas as pd
import re
import requests
import json
import time
from typing import List, Dict, Optional, Callable
from config_manager import ConfigManager
import csv
from langdetect import detect, LangDetectException

class CoreProcessor:
    def __init__(self, config: Dict):
        """初始化处理器"""
        self.config = config
        self.stop_processing = False
        self.progress_callback: Optional[Callable[[str], None]] = None
        
        # 从配置中获取API相关设置
        self.API_KEY = config["api_key"]
        self.API_ENDPOINT = config["api_endpoint"]
        self.TEMPERATURE = config.get("temperature", 0.3)
        self.MAX_TOKENS = config.get("max_tokens", 1000)
        self.MODEL = config.get("model", "gemini-2.5-flash-preview-04-17-nothink")
        
        # 设置批处理大小
        self.BATCH_SIZE = 100
        
        # 设置句子长度限制
        self.MIN_SENTENCE_LENGTH = config.get("min_sentence_length", 10)
        self.MAX_SENTENCE_LENGTH = config.get("max_sentence_length", 500)

    def set_progress_callback(self, callback: Callable[[str], None]):
        """设置进度回调函数"""
        self.progress_callback = callback

    def log(self, message: str):
        """记录日志"""
        if self.progress_callback:
            self.progress_callback(message)
        else:
            print(message)

    def is_valid_language(self, text: str, expected_lang: str) -> bool:
        """
        检查文本是否符合预期的语言
        
        Args:
            text: 要检查的文本
            expected_lang: 期望的语言代码 ('en' 或 'zh-cn')
            
        Returns:
            bool: 是否符合预期语言
        """
        try:
            # 如果文本太短，可能无法准确检测
            if len(text.strip()) < 10:
                return False
                
            detected_lang = detect(text)
            
            # 处理中文的特殊情况
            if expected_lang == 'zh-cn':
                return detected_lang in ['zh-cn', 'zh-tw', 'zh']
            else:
                return detected_lang == expected_lang
                
        except LangDetectException:
            return False

    def construct_prompt(self, english_sentence: str, chinese_sentence: str) -> str:
        """构造提示词"""
        # 定义名词化结构    
        nominalization_structure_definitions = """
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

    def analyze_sentence_with_ai(self, english_sentence: str, chinese_sentence: str) -> List[Dict]:
        """使用AI分析句子"""
        prompt = self.construct_prompt(english_sentence, chinese_sentence)
        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.TEMPERATURE,
            "max_tokens": self.MAX_TOKENS
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.API_ENDPOINT}/chat/completions", 
                    headers=headers, 
                    json=payload, 
                    timeout=60
                )
                response.raise_for_status()
                
                response_json = response.json()
                ai_response_content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if not ai_response_content:
                    self.log("警告：AI返回了空内容。")
                    return []

                try:
                    json_match = re.search(r'\[.*\]', ai_response_content, re.DOTALL)
                    if json_match:
                        parsed_json = json.loads(json_match.group(0))
                        return parsed_json
                    else:
                        self.log(f"警告：无法从AI回复中提取有效的JSON列表。\nAI回复：\n{ai_response_content}")
                        return []
                except json.JSONDecodeError as e:
                    self.log(f"错误：解析AI返回的JSON失败。错误信息：{e}\nAI回复：\n{ai_response_content}")
                    return []

            except requests.exceptions.RequestException as e:
                self.log(f"API请求错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))
                else:
                    self.log("已达到最大重试次数，跳过此句对。")
                    return []
            except Exception as e:
                self.log(f"处理API响应时发生未知错误: {e}")
                return []
        return []

    def process_file(self, input_file: str, output_file: str) -> bool:
        """处理文件"""
        try:
            # 读取Excel文件
            self.log("正在读取Excel文件...")
            df = pd.read_excel(input_file, skiprows=6, header=None, 
                             names=['index', 'doc_id', 'english', 'type', 'chinese'])
            
            # 清理空行
            df.dropna(how='all', inplace=True)
            df.reset_index(drop=True, inplace=True)
            
            # 提取句对
            sentence_pairs = []
            invalid_pairs = []  # 记录无效的句对
            
            for i in range(0, len(df)):
                if i + 1 < len(df):
                    eng_text_raw = str(df.iloc[i, 1])
                    chi_text_raw = str(df.iloc[i, 3])
                    doc_id = str(df.iloc[i, 0])

                    # 清理句子
                    eng_sentence = re.sub(r'<s>|</s>|doc#\w+\s*', '', eng_text_raw).strip()
                    chi_sentence = re.sub(r'<s>|</s>|doc#\w+\s*', '', chi_text_raw).strip()
                    chi_sentence = re.sub(r'^\d+\s*\.\s*', '', chi_sentence).strip()
                    chi_sentence = re.sub(r'\s+', '', chi_sentence)
                    
                    # 检查是否完整句子（以标点符号结尾）
                    if not re.search(r'[.!?;,]$', eng_sentence):
                        invalid_pairs.append({
                            'doc_id': doc_id,
                            'reason': '英文句子不以标点符号结尾',
                            'english': eng_sentence,
                            'chinese': chi_sentence
                        })
                        continue

                    # 检查句子长度
                    eng_len = len(eng_sentence)
                    chi_len = len(chi_sentence)
                    
                    if eng_len < self.MIN_SENTENCE_LENGTH or chi_len < self.MIN_SENTENCE_LENGTH:
                        invalid_pairs.append({
                            'doc_id': doc_id,
                            'reason': f'句子长度小于最小限制（英文：{eng_len}，中文：{chi_len}）',
                            'english': eng_sentence,
                            'chinese': chi_sentence
                        })
                        continue
                        
                    if eng_len > self.MAX_SENTENCE_LENGTH or chi_len > self.MAX_SENTENCE_LENGTH:
                        invalid_pairs.append({
                            'doc_id': doc_id,
                            'reason': f'句子长度超过最大限制（英文：{eng_len}，中文：{chi_len}）',
                            'english': eng_sentence,
                            'chinese': chi_sentence
                        })
                        continue

                    # 检查语言
                    if not self.is_valid_language(eng_sentence, 'en'):
                        invalid_pairs.append({
                            'doc_id': doc_id,
                            'reason': '英文句子语言检测失败',
                            'english': eng_sentence,
                            'chinese': chi_sentence
                        })
                        continue
                        
                    if not self.is_valid_language(chi_sentence, 'zh-cn'):
                        invalid_pairs.append({
                            'doc_id': doc_id,
                            'reason': '中文句子语言检测失败',
                            'english': eng_sentence,
                            'chinese': chi_sentence
                        })
                        continue

                    if eng_sentence and chi_sentence:
                        sentence_pairs.append({
                            'doc_id': doc_id,
                            'english_sentence': eng_sentence,
                            'chinese_sentence': chi_sentence
                        })
            
            # 记录无效句对
            if invalid_pairs:
                invalid_file = output_file.replace('.csv', '_invalid.csv')
                with open(invalid_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=['doc_id', 'reason', 'english', 'chinese'])
                    writer.writeheader()
                    writer.writerows(invalid_pairs)
                self.log(f"发现 {len(invalid_pairs)} 个无效句对，已保存到: {invalid_file}")
            
            self.log(f"成功提取 {len(sentence_pairs)} 个有效句对。")
            
            # 创建CSV文件并写入表头
            fieldnames = ['doc_id', 'english_sentence', 'chinese_sentence', 
                         'identified_nominalization_en', 'nominalization_type', 
                         'translation_technique']
            
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                # 处理句对
                batch_results = []
                for index, pair in enumerate(sentence_pairs):
                    if self.stop_processing:
                        self.log("处理已停止")
                        break
                        
                    self.log(f"正在处理句对 {index + 1}/{len(sentence_pairs)}: {pair['doc_id']}")
                    
                    if index > 0 and index % 5 == 0:
                        self.log("暂停1秒以避免API速率限制...")
                        time.sleep(1)

                    analysis_results = self.analyze_sentence_with_ai(
                        pair['english_sentence'],
                        pair['chinese_sentence']
                    )

                    if analysis_results:
                        for result_item in analysis_results:
                            result = {
                                'doc_id': pair['doc_id'],
                                'english_sentence': pair['english_sentence'],
                                'chinese_sentence': pair['chinese_sentence'],
                                'identified_nominalization_en': result_item.get('Identified_Nominalization_EN', 'N/A'),
                                'nominalization_type': result_item.get('Nominalization_Type', 'N/A'),
                                'translation_technique': result_item.get('Translation_Technique', 'N/A')
                            }
                            batch_results.append(result)
                    else:
                        result = {
                            'doc_id': pair['doc_id'],
                            'english_sentence': pair['english_sentence'],
                            'chinese_sentence': pair['chinese_sentence'],
                            'identified_nominalization_en': 'AI_NO_RESULT_OR_ERROR',
                            'nominalization_type': 'N/A',
                            'translation_technique': 'N/A'
                        }
                        batch_results.append(result)
                    
                    # 当达到批处理大小时，写入文件并清空缓存
                    if len(batch_results) >= self.BATCH_SIZE:
                        writer.writerows(batch_results)
                        batch_results = []
                        self.log(f"已处理并保存 {index + 1} 个句对")
                
                # 写入剩余的结果
                if batch_results:
                    writer.writerows(batch_results)
                    self.log(f"已处理并保存所有剩余句对")
            
            self.log(f"结果已保存到: {output_file}")
            return True
            
        except Exception as e:
            self.log(f"处理文件时发生错误: {str(e)}")
            return False

    def stop(self):
        """停止处理"""
        self.stop_processing = True 