import pandas as pd
import re
import csv
from typing import List, Dict, Tuple, Optional, Callable, Generator
from langdetect import detect, LangDetectException
from logger import logger
from openpyxl import load_workbook
import os

class DataProcessor:
    def __init__(self, config: Dict):
        """初始化数据处理器"""
        self.config = config
        self.MIN_SENTENCE_LENGTH = config.get("min_sentence_length", 10)
        self.MAX_SENTENCE_LENGTH = config.get("max_sentence_length", 500)
        self.FILTER_INCOMPLETE_SENTENCES = config.get("filter_incomplete_sentences", True)
        self.BATCH_SIZE = config.get("batch_size", 500)
        
        # 从配置中获取文件结构
        self.FILE_STRUCTURE = config.get("file_structure", {
            'skip_rows': 6,
            'columns': {
                'source_doc_id': {'enabled': True, 'index': 0},
                'source_text': {'enabled': True, 'index': 1},
                'target_doc_id': {'enabled': True, 'index': 2},
                'target_text': {'enabled': True, 'index': 3}
            },
            'language': {
                'source': 'en',
                'target': 'zh-cn'
            }
        })
        
        # 获取语言设置
        self.SOURCE_LANG = self.FILE_STRUCTURE['language']['source']
        self.TARGET_LANG = self.FILE_STRUCTURE['language']['target']

    def set_progress_callback(self, callback: Callable[[str], None]):
        """设置进度回调函数（保持向后兼容）"""
        logger.set_callback(callback)

    def log(self, message: str):
        """记录日志（保持向后兼容）"""
        logger.info(message)

    def read_excel_file(self, input_file: str) -> Generator[Dict, None, None]:
        """读取Excel文件，返回生成器"""
        try:
            logger.info(f"开始读取Excel文件: {input_file}")
            wb = load_workbook(input_file, read_only=True)
            ws = wb.active
            
            # 跳过指定行数
            logger.info(f"跳过前 {self.FILE_STRUCTURE['skip_rows']} 行...")
            for _ in range(self.FILE_STRUCTURE['skip_rows']):
                next(ws.rows)
            
            # 获取最大列索引
            max_column_index = max(
                col['index'] for col in self.FILE_STRUCTURE['columns'].values()
                if col['enabled']
            )
            
            # 逐行读取数据
            row_count = 0
            for row in ws.rows:
                # 确保行有足够的列
                if len(row) >= max_column_index + 1:
                    row_count += 1
                    if row_count % 1000 == 0:
                        logger.info(f"已读取 {row_count} 行...")
                    
                    # 读取数据
                    data = {}
                    for col_name, col_config in self.FILE_STRUCTURE['columns'].items():
                        if col_config['enabled']:
                            data[col_name] = str(row[col_config['index']].value or '')
                    
                    # 跳过空行
                    if all(not v.strip() for v in data.values()):
                        continue
                        
                    yield data
            
            logger.info(f"Excel文件读取完成，共读取 {row_count} 行")
            wb.close()
            
        except Exception as e:
            logger.error(f"读取Excel文件失败: {str(e)}")
            raise

    def clean_sentence(self, text: str) -> str:
        """清理句子文本"""
        # 移除标记和文档ID
        cleaned = re.sub(r'<s>|</s>|doc#\w+\s*', '', text).strip()
        # 移除中文句子开头的数字和点
        cleaned = re.sub(r'^\d+\s*\.\s*', '', cleaned).strip()
        
        # 检查是否为中文句子（通过检测是否包含中文字符）
        if re.search(r'[\u4e00-\u9fff]', cleaned):
            # 如果是中文句子，移除所有空格
            cleaned = re.sub(r'\s+', '', cleaned)
        else:
            # 如果是英文句子，只规范化空格（将多个空格替换为单个空格）
            cleaned = re.sub(r'\s+', ' ', cleaned)
            
        return cleaned

    def is_valid_language(self, text: str, expected_lang: str) -> bool:
        """检查文本是否符合预期的语言"""
        try:
            if len(text.strip()) < 10:
                return False
                
            detected_lang = detect(text)
            
            if expected_lang == 'zh-cn':
                return detected_lang in ['zh-cn', 'zh-tw', 'zh']
            else:
                return detected_lang == expected_lang
                
        except LangDetectException:
            return False

    def validate_sentence_pair(self, source_text: str, target_text: str, doc_id: str = '') -> Tuple[bool, str]:
        """验证句对是否有效"""
        # 检查源语言是否完整句子
        if self.FILTER_INCOMPLETE_SENTENCES:
            # 检查是否为空字符串
            if not source_text:
                return False, '源语言句子为空'

            # 跳过结尾的空格、引号、括号等可忽略字符，找到第一个非可忽略字符
            ignore_chars = [
                ' ', '\u3000',  # 空格、全角空格
                '\u2018', '\u2019', '\u201c', '\u201d',  # 英文弯引号
                '\u0022', '\u0027',  # 直引号
                '\u00ab', '\u00bb',  # 法式引号
                '"', "'", '“', '”', '‘', '’', '«', '»',
                '(', ')', '[', ']', '{', '}'
            ]
            i = len(source_text) - 1
            while i >= 0 and (source_text[i] in ignore_chars or re.match(r'[ \u2018\u2019\u201c\u201d\u0022\u0027\u00ab\u00bb"“”‘’«»()\[\]{}]', source_text[i])):
                i -= 1
            if i < 0:
                return False, '源语言句子为空或全为可忽略字符'
            # 使用Unicode范围来匹配所有可能的标点符号
            if not re.search(r'[.!?;:。！？；：…—]', source_text[i]):
                return False, '源语言句子不以标点符号结尾'

        # 检查句子长度
        source_len = len(source_text)
        target_len = len(target_text)
        
        if source_len < self.MIN_SENTENCE_LENGTH or target_len < self.MIN_SENTENCE_LENGTH:
            return False, f'句子长度小于最小限制（源语言：{source_len}，目标语言：{target_len}）'
            
        if source_len > self.MAX_SENTENCE_LENGTH or target_len > self.MAX_SENTENCE_LENGTH:
            return False, f'句子长度超过最大限制（源语言：{source_len}，目标语言：{target_len}）'

        # 检查语言
        if not self.is_valid_language(source_text, self.SOURCE_LANG):
            return False, '源语言句子语言检测失败'

        return True, ''

    def process_sentence_pairs_batch(self, input_file: str) -> Generator[Tuple[List[Dict], List[Dict]], None, None]:
        """分批处理句对，返回生成器"""
        sentence_pairs = []
        invalid_pairs = []
        total_processed = 0
        total_valid = 0
        total_invalid = 0
        
        logger.info("开始处理句对...")
        
        for row in self.read_excel_file(input_file):
            source_text = row['source_text']
            target_text = row['target_text']
            source_doc_id = row.get('source_doc_id', '')  # 如果未启用source_doc_id，则使用空字符串
            target_doc_id = row.get('target_doc_id', '')  # 如果未启用target_doc_id，则使用空字符串

            # 清理句子
            source_sentence = self.clean_sentence(source_text)
            target_sentence = self.clean_sentence(target_text)

            # 验证句对
            is_valid, reason = self.validate_sentence_pair(source_sentence, target_sentence, source_doc_id)
            
            if is_valid:
                sentence_pairs.append({
                    'source_doc_id': source_doc_id,
                    'target_doc_id': target_doc_id,
                    'source_sentence': source_sentence,
                    'target_sentence': target_sentence
                })
                total_valid += 1
            else:
                invalid_pairs.append({
                    'source_doc_id': source_doc_id,
                    'target_doc_id': target_doc_id,
                    'reason': reason,
                    'source': source_sentence,
                    'target': target_sentence
                })
                total_invalid += 1
            
            total_processed += 1
            
            # 当达到批处理大小时，返回当前批次
            if len(sentence_pairs) >= self.BATCH_SIZE:
                logger.info(f"已处理 {total_processed} 个句对，当前批次包含 {len(sentence_pairs)} 个有效句对")
                yield sentence_pairs, invalid_pairs
                sentence_pairs = []
                invalid_pairs = []
        
        # 返回最后一批
        if sentence_pairs or invalid_pairs:
            logger.info(f"已处理 {total_processed} 个句对，最后批次包含 {len(sentence_pairs)} 个有效句对")
            yield sentence_pairs, invalid_pairs
            
    def save_invalid_pairs(self, invalid_pairs: List[Dict], output_file: str) -> None:
        """保存无效句对到文件"""
        if invalid_pairs:
            invalid_file = output_file.replace('.csv', '_invalid.csv')
            try:
                # 检查文件是否存在，如果不存在则写入表头
                file_exists = os.path.exists(invalid_file)
                mode = 'a' if file_exists else 'w'
                
                with open(invalid_file, mode, newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=['source_doc_id', 'target_doc_id', 'reason', 'source', 'target'], quoting=csv.QUOTE_ALL)
                    if not file_exists:
                        writer.writeheader()
                    writer.writerows(invalid_pairs)
                logger.info(f"已保存 {len(invalid_pairs)} 个无效句对到: {invalid_file}")
            except Exception as e:
                logger.error(f"保存无效句对时发生错误: {str(e)}")
                raise 