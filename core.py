import pandas as pd
import re
import requests
import json
import time
from typing import List, Dict, Optional, Callable
from config_manager import ConfigManager
import csv
from data_processor import DataProcessor
from logger import logger

class CoreProcessor:
    def __init__(self, config: Dict):
        """初始化处理器"""
        self.config = config
        self.stop_processing = False
        
        # 从配置中获取API相关设置
        self.API_KEY = config["api_key"]
        self.API_ENDPOINT = config["api_endpoint"]
        self.TEMPERATURE = config.get("temperature", 0.3)
        self.MAX_TOKENS = config.get("max_tokens", 1000)
        self.MODEL = config.get("model", "gemini-2.5-flash-preview-04-17-nothink")
        
        # 设置句子长度限制
        self.MIN_SENTENCE_LENGTH = config.get("min_sentence_length", 10)
        self.MAX_SENTENCE_LENGTH = config.get("max_sentence_length", 500)
        self.FILTER_INCOMPLETE_SENTENCES = config.get("filter_incomplete_sentences", True)
        
        # 模拟模式设置
        self.MOCK_MODE = config.get("mock_mode", False)

        # 初始化数据处理器
        self.data_processor = DataProcessor(config)

    def set_progress_callback(self, callback: Callable[[str], None]):
        """设置进度回调函数"""
        logger.set_callback(callback)

    def log(self, message: str):
        """记录日志（保持向后兼容）"""
        logger.info(message)

    def construct_prompt(self, english_sentence: str, chinese_sentence: str) -> str:
        """构造提示词 (精简版)"""
        # 转义句子中的引号，避免影响JSON解析
        english_sentence = english_sentence.replace('"', '\\"').replace("'", "\\'")
        chinese_sentence = chinese_sentence.replace('"', '\\"').replace("'", "\\'")
        
        # 定义名词化结构 (核心)
        nominalization_structure_definitions = """
Nominalization: Conversion of non-nominal concepts (actions, states, qualities) into noun forms/phrases. Identified noun/phrase could alternatively be a verb/adjective.
Types:
1. Derivational: Adding nominalizing affixes (e.g., -ment, -tion, -sion, -ness, -ity, -cy, -ance, -age, -al, -ure) to a VERB or ADJECTIVE base. Focus on clear verb/adjective origin representing an action, process, or state.
   Examples: 'development' (from 'develop'), 'awareness' (from 'aware').
   AVOID: Common nouns like 'situation', 'nation' unless context clearly shows nominalized action.
2. Conversional (Zero Derivation): VERB or ADJECTIVE used as a noun without form change, representing its action/state.
   Examples: 'a request' (from 'to request'), 'a visit' (from 'to visit').
   AVOID: Common nouns like 'report', 'plan' unless context shows nominalized action.
3. Phrasal: Strictly 'V-ing *of* NP' (gerund + 'of' + noun phrase) representing an action/process.
   Examples: 'the killing of members', 'the setting up of a committee'.
   AVOID: Other V-ing phrases (e.g., 'implementing resolutions' without 'of NP').
"""
        # 定义翻译技巧 (核心)
        translation_technique_definitions = """
1. Maintain_Noun: English nominalization translated as a Chinese noun/noun phrase, retaining nominal character within a largely similar clausal structure.
2. Shift_Word_Class: English nominalization translated as a different word class (e.g., verb, adjective) in Chinese, but the surrounding clausal structure is relatively similar.
3. Omit_Structure: English nominalization (or its core abstract meaning) not explicitly translated; meaning implied, absorbed, or redundant.
   Example: EN: 'a process of reorganization' -> CN: '开始改组' ('process' is omitted).
   Example: EN: 'after the completion of a visit' -> CN: '访问之后' ('completion' is omitted as '之后' implies it).
4. Reconstruct_Sentence: Chinese translation significantly rearranges the syntactic structure of the clause (or larger part of the sentence) where the English nominalization's meaning is expressed. This involves more than local changes to the nominalization (e.g., unpacking into a new clause, voice change, major reordering). If unsure but see significant structural changes, consider this. This may still render the nominalization as a noun/verb within the new structure.
   Example: EN: 'Questions were also asked on the nature of the NGO...' -> CN: '人们还问到该组织的性质...' (original passive structure related to the nominalized concept 'questions' is changed to an active one, altering the clausal structure).
   Example: EN: 'the ageing of unpaid assessments with varying uncertainty of collectability remains a concern' -> CN: '未缴摊款久拖不付, 而且在能否收到这些款项方面, 各笔欠款的情况又各不相同, 因此, 这仍然是委员会关切的一个问题' (the complex English nominal phrase is broken down and rephrased into multiple coordinated Chinese clauses, a major structural change).
5. Difficult_To_Determine: Only if truly ambiguous after considering other categories, especially Reconstruct_Sentence.
"""
        # 整体prompt
        prompt = f"""
Analyze the English sentence and its Chinese translation for nominalization.

English:
{english_sentence}
Chinese:
{chinese_sentence}

Tasks:
1. Identify ONLY core nominalization structures in English strictly fitting these definitions:
   {nominalization_structure_definitions}
   CRITICAL: Do NOT identify common nouns or phrases not clearly derived from verbs/adjectives representing actions/states. No infinitives.

2. For each identified nominalization:
   a. Identified_Nominalization_EN (minimal nominalized phrase)
   b. Nominalization_Type (Derivational, Conversional, Phrasal)
   c. Translation_Technique (using these definitions):
      {translation_technique_definitions}

Return JSON list (empty [] if none found):
[
  {{"Identified_Nominalization_EN": "nominalization", "Nominalization_Type": "Type", "Translation_Technique": "Technique"}},
  ...
]
Ensure valid JSON.
"""
        return prompt

    def normalize_nominalization_type(self, result_item: Dict) -> Dict:
        """标准化Nominalization_Type字段"""
        nt = result_item.get("Nominalization_Type", "")
        if "Phrasal" in nt:
            result_item["Nominalization_Type"] = "Phrasal"
        elif "Derivational" in nt:
            result_item["Nominalization_Type"] = "Derivational"
        elif "Conversional" in nt:
            result_item["Nominalization_Type"] = "Conversional"
        # 可根据需要添加更多规则
        return result_item

    def analyze_sentence_with_ai(self, english_sentence: str, chinese_sentence: str) -> List[Dict]:
        """使用AI分析句子"""
        # 如果启用模拟模式，返回模拟数据
        if self.MOCK_MODE:
            logger.info("模拟模式：返回模拟数据")
            # 模拟API调用延时
            time.sleep(1)
            # 模拟一些常见的名词化结构，且ai有部分不标准输出
            mock_results = [
                {
                    "Identified_Nominalization_EN": "development",
                    "Nominalization_Type": "Derivational",
                    "Translation_Technique": "Maintain_Noun"
                },
                {
                    "Identified_Nominalization_EN": "the implementation of policies",
                    "Nominalization_Type": "Phrasal Nominalization (Gerund Phrase)",
                    "Translation_Technique": "Shift_Word_Class"
                }
            ]
            # 对模拟数据也做标准化
            return [self.normalize_nominalization_type(item) for item in mock_results]

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
                    logger.warning("AI返回了空内容。")
                    return []

                try:
                    # 使用更健壮的JSON提取方法
                    json_match = re.search(r'\[[\s\S]*\]', ai_response_content)
                    if json_match:
                        parsed_json = json.loads(json_match.group(0))
                        # 对AI返回的每个结果项做标准化
                        return [self.normalize_nominalization_type(item) for item in parsed_json]
                    else:
                        logger.warning(f"无法从AI回复中提取有效的JSON列表。\nAI回复：\n{ai_response_content}")
                        return []
                except json.JSONDecodeError as e:
                    logger.error(f"解析AI返回的JSON失败。错误信息：{e}\nAI回复：\n{ai_response_content}")
                    return []

            except requests.exceptions.RequestException as e:
                logger.warning(f"API请求错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))
                else:
                    logger.error("已达到最大重试次数，跳过此句对。")
                    return []
            except Exception as e:
                logger.error(f"处理API响应时发生未知错误: {e}")
                return []
        return []

    def process_file(self, input_file: str, output_file: str) -> bool:
        """处理文件"""
        try:
            logger.info(f"开始处理文件: {input_file}")
            logger.info(f"输出文件: {output_file}")
            
            # 创建CSV文件并写入表头
            fieldnames = ['source_doc_id', 'source_sentence', 'target_doc_id', 'target_sentence', 
                         'identified_nominalization_en', 'nominalization_type', 
                         'translation_technique']
            
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                writer.writeheader()
            
            # 分批处理句对
            total_processed = 0
            total_analyzed = 0
            total_valid = 0
            total_invalid = 0
            batch_count = 0
            
            for batch_sentence_pairs, batch_invalid_pairs in self.data_processor.process_sentence_pairs_batch(input_file):
                if self.stop_processing:
                    logger.info("处理已停止")
                    break
                
                batch_count += 1
                logger.info(f"开始处理第 {batch_count} 批，包含 {len(batch_sentence_pairs)} 个有效句对")
                
                # 保存无效句对
                if batch_invalid_pairs:
                    self.data_processor.save_invalid_pairs(batch_invalid_pairs, output_file)
                    total_invalid += len(batch_invalid_pairs)
                
                # 处理当前批次的句对
                for pair in batch_sentence_pairs:
                    if self.stop_processing:
                        break
                        
                    total_processed += 1
                    total_valid += 1
                    logger.info(f"正在处理第 {total_processed} 个句对")
                    
                    if total_processed > 1 and total_processed % 5 == 0:
                        logger.info("暂停1秒以避免API速率限制...")
                        time.sleep(1)

                    analysis_results = self.analyze_sentence_with_ai(
                        pair['source_sentence'],
                        pair['target_sentence']
                    )

                    # 追加写入结果
                    with open(output_file, 'a', newline='', encoding='utf-8-sig') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                        
                        if analysis_results:
                            total_analyzed += 1
                            for result_item in analysis_results:
                                result = {
                                    'source_doc_id': pair['source_doc_id'],
                                    'source_sentence': pair['source_sentence'],
                                    'target_doc_id': pair.get('target_doc_id', ''),
                                    'target_sentence': pair['target_sentence'],
                                    'identified_nominalization_en': result_item.get('Identified_Nominalization_EN', 'N/A'),
                                    'nominalization_type': result_item.get('Nominalization_Type', 'N/A'),
                                    'translation_technique': result_item.get('Translation_Technique', 'N/A')
                                }
                                writer.writerow(result)
                        else:
                            result = {
                                'source_doc_id': pair['source_doc_id'],
                                'source_sentence': pair['source_sentence'],
                                'target_doc_id': pair.get('target_doc_id', ''),
                                'target_sentence': pair['target_sentence'],
                                'identified_nominalization_en': 'AI_NO_RESULT_OR_ERROR',
                                'nominalization_type': 'N/A',
                                'translation_technique': 'N/A'
                            }
                            writer.writerow(result)
                
                logger.info(f"第 {batch_count} 批处理完成")
            
            logger.info(f"处理完成，总计：\n- 总处理句对：{total_processed}\n- 有效句对：{total_valid}\n- 无效句对：{total_invalid}\n- 成功分析句对：{total_analyzed}\n- 处理批次数：{batch_count}")
            logger.info(f"结果已保存到: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"处理文件时发生错误: {str(e)}")
            return False

    def stop(self):
        """停止处理"""
        self.stop_processing = True 