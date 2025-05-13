import pandas as pd
import re
import csv
from typing import List, Dict, Tuple, Optional, Callable
from langdetect import detect, LangDetectException
from logger import logger

class DataProcessor:
    def __init__(self, config: Dict):
        """初始化数据处理器"""
        self.config = config
        self.MIN_SENTENCE_LENGTH = config.get("min_sentence_length", 10)
        self.MAX_SENTENCE_LENGTH = config.get("max_sentence_length", 500)
        self.FILTER_INCOMPLETE_SENTENCES = config.get("filter_incomplete_sentences", True)

    def set_progress_callback(self, callback: Callable[[str], None]):
        """设置进度回调函数（保持向后兼容）"""
        logger.set_callback(callback)

    def log(self, message: str):
        """记录日志（保持向后兼容）"""
        logger.info(message)

    def read_excel_file(self, input_file: str) -> pd.DataFrame:
        """读取Excel文件"""
        try:
            return pd.read_excel(input_file, skiprows=6, header=None, 
                               names=['index', 'doc_id', 'english', 'type', 'chinese'])
        except Exception as e:
            logger.error(f"读取Excel文件失败: {str(e)}")
            raise

    def clean_sentence(self, text: str) -> str:
        """清理句子文本"""
        # 移除标记和文档ID
        cleaned = re.sub(r'<s>|</s>|doc#\w+\s*', '', text).strip()
        # 移除中文句子开头的数字和点
        cleaned = re.sub(r'^\d+\s*\.\s*', '', cleaned).strip()
        # 移除多余空格
        cleaned = re.sub(r'\s+', '', cleaned)
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

    def validate_sentence_pair(self, eng_sentence: str, chi_sentence: str, doc_id: str) -> Tuple[bool, str]:
        """验证句对是否有效"""
        # 检查是否完整句子
        if self.FILTER_INCOMPLETE_SENTENCES and not re.search(r'[.!?;,]$', eng_sentence):
            return False, '英文句子不以标点符号结尾'

        # 检查句子长度
        eng_len = len(eng_sentence)
        chi_len = len(chi_sentence)
        
        if eng_len < self.MIN_SENTENCE_LENGTH or chi_len < self.MIN_SENTENCE_LENGTH:
            return False, f'句子长度小于最小限制（英文：{eng_len}，中文：{chi_len}）'
            
        if eng_len > self.MAX_SENTENCE_LENGTH or chi_len > self.MAX_SENTENCE_LENGTH:
            return False, f'句子长度超过最大限制（英文：{eng_len}，中文：{chi_len}）'

        # 检查语言
        if not self.is_valid_language(eng_sentence, 'en'):
            return False, '英文句子语言检测失败'
            
        if not self.is_valid_language(chi_sentence, 'zh-cn'):
            return False, '中文句子语言检测失败'

        return True, ''

    def process_sentence_pairs(self, df: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
        """处理句对，返回有效和无效的句对列表"""
        sentence_pairs = []
        invalid_pairs = []
        
        for i in range(len(df)):
            eng_text_raw = str(df.iloc[i, 1])
            chi_text_raw = str(df.iloc[i, 3])
            doc_id = str(df.iloc[i, 0])

            # 清理句子
            eng_sentence = self.clean_sentence(eng_text_raw)
            chi_sentence = self.clean_sentence(chi_text_raw)

            # 验证句对
            is_valid, reason = self.validate_sentence_pair(eng_sentence, chi_sentence, doc_id)
            
            if is_valid:
                sentence_pairs.append({
                    'doc_id': doc_id,
                    'english_sentence': eng_sentence,
                    'chinese_sentence': chi_sentence
                })
            else:
                invalid_pairs.append({
                    'doc_id': doc_id,
                    'reason': reason,
                    'english': eng_sentence,
                    'chinese': chi_sentence
                })

        return sentence_pairs, invalid_pairs

    def save_invalid_pairs(self, invalid_pairs: List[Dict], output_file: str) -> None:
        """保存无效句对到文件"""
        if invalid_pairs:
            invalid_file = output_file.replace('.csv', '_invalid.csv')
            try:
                with open(invalid_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=['doc_id', 'reason', 'english', 'chinese'])
                    writer.writeheader()
                    writer.writerows(invalid_pairs)
                logger.info(f"已保存 {len(invalid_pairs)} 个无效句对到: {invalid_file}")
            except Exception as e:
                logger.error(f"保存无效句对时发生错误: {str(e)}")
                raise 