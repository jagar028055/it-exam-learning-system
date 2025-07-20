"""
情報技術者試験学習システム - データ取得モジュール
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import PyPDF2
import pdfplumber
from tqdm import tqdm

from ..core.config import config
from ..utils.utils import (
    Logger, FileUtils, WebUtils, DataUtils, ValidationUtils,
    SystemError, NetworkError, DataError
)

class IPADataFetcher:
    """IPAサイトから過去問題データを取得するクラス"""
    
    def __init__(self, download_dir: Path = None):
        """
        初期化
        
        Args:
            download_dir: ダウンロード先ディレクトリ
        """
        self.download_dir = download_dir or config.DOWNLOAD_DIR
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # ログ設定
        self.logger = Logger.setup_logger(
            "IPADataFetcher",
            config.LOG_FILE,
            config.LOG_LEVEL
        )
        
        # セッション設定
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def fetch_exam_list(self, exam_type: str = "FE") -> List[Dict]:
        """
        指定された試験の過去問題リストを取得
        
        Args:
            exam_type: 試験種別 (FE, AP, IP等)
            
        Returns:
            List[Dict]: 過去問題情報のリスト
        """
        self.logger.info(f"試験種別 {exam_type} の過去問題リストを取得中...")
        
        if not ValidationUtils.validate_exam_code(exam_type):
            raise DataError(f"無効な試験種別: {exam_type}")
        
        # 試験種別に応じたURLを取得
        base_url = self._get_base_url(exam_type)
        
        try:
            # メインページを取得
            response = WebUtils.safe_request(
                base_url,
                delay=config.REQUEST_DELAY,
                timeout=config.REQUEST_TIMEOUT,
                max_retries=config.MAX_RETRIES
            )
            
            if not response:
                raise NetworkError(f"メインページの取得に失敗: {base_url}")
            
            # 年度別リンクを抽出
            exam_links = self._extract_exam_links(response.text, base_url)
            
            self.logger.info(f"{len(exam_links)} 件の過去問題を発見")
            
            return exam_links
            
        except Exception as e:
            self.logger.error(f"過去問題リストの取得に失敗: {e}")
            raise NetworkError(f"過去問題リストの取得に失敗: {e}")
    
    def _get_base_url(self, exam_type: str) -> str:
        """試験種別に応じたベースURLを取得"""
        url_mapping = {
            "FE": config.IPA_FE_URL,
            "AP": config.IPA_AP_URL,
            "IP": config.IPA_BASE_URL + "itpassport/",
            "SG": config.IPA_BASE_URL + "sg/",
        }
        
        return url_mapping.get(exam_type.upper(), config.IPA_BASE_URL)
    
    def _extract_exam_links(self, html: str, base_url: str) -> List[Dict]:
        """HTMLから過去問題リンクを抽出"""
        soup = BeautifulSoup(html, 'html.parser')
        exam_links = []
        
        # 年度別リンクを検索
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            
            # 年度パターンを検索
            year_match = re.search(r'(20\d{2})', text)
            if year_match:
                year = int(year_match.group(1))
                if ValidationUtils.validate_year(year):
                    full_url = urljoin(base_url, href)
                    exam_links.append({
                        'year': year,
                        'url': full_url,
                        'title': text,
                        'type': 'pdf' if href.endswith('.pdf') else 'html'
                    })
        
        # 重複を削除し、年度順でソート
        unique_links = {}
        for link in exam_links:
            key = (link['year'], link['type'])
            if key not in unique_links:
                unique_links[key] = link
        
        return sorted(unique_links.values(), key=lambda x: x['year'], reverse=True)
    
    def download_exam_data(self, exam_info: Dict) -> Optional[Path]:
        """
        過去問題ファイルをダウンロード
        
        Args:
            exam_info: 過去問題情報
            
        Returns:
            Optional[Path]: ダウンロードされたファイルパス
        """
        year = exam_info['year']
        url = exam_info['url']
        file_type = exam_info['type']
        
        # ファイル名を生成
        filename = f"exam_{year}.{file_type}"
        filepath = self.download_dir / filename
        
        # 既に存在する場合はスキップ
        if filepath.exists():
            self.logger.info(f"ファイルが既に存在: {filepath}")
            return filepath
        
        try:
            self.logger.info(f"ダウンロード開始: {url}")
            
            response = WebUtils.safe_request(
                url,
                delay=config.REQUEST_DELAY,
                timeout=config.REQUEST_TIMEOUT,
                max_retries=config.MAX_RETRIES
            )
            
            if not response:
                raise NetworkError(f"ダウンロードに失敗: {url}")
            
            # ファイルに保存
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            self.logger.info(f"ダウンロード完了: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"ダウンロードエラー: {e}")
            return None
    
    def extract_questions_from_pdf(self, pdf_path: Path) -> List[Dict]:
        """
        PDFファイルから問題を抽出
        
        Args:
            pdf_path: PDFファイルパス
            
        Returns:
            List[Dict]: 抽出された問題データ
        """
        self.logger.info(f"PDF解析開始: {pdf_path}")
        
        questions = []
        
        try:
            # pdfplumberを使用してPDFを解析
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
            
            # 問題を抽出
            extracted_questions = self._parse_questions_from_text(full_text)
            questions.extend(extracted_questions)
            
            self.logger.info(f"PDF解析完了: {len(questions)} 問題を抽出")
            
        except Exception as e:
            self.logger.error(f"PDF解析エラー: {e}")
            # フォールバック: PyPDF2を使用
            try:
                questions = self._extract_with_pypdf2(pdf_path)
            except Exception as e2:
                self.logger.error(f"PyPDF2でも解析に失敗: {e2}")
                raise DataError(f"PDF解析に失敗: {e}")
        
        return questions
    
    def _extract_with_pypdf2(self, pdf_path: Path) -> List[Dict]:
        """PyPDF2を使用してPDFから問題を抽出"""
        self.logger.info("PyPDF2による解析を実行中...")
        
        questions = []
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            full_text = ""
            
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        
        # 問題を抽出
        questions = self._parse_questions_from_text(full_text)
        
        return questions
    
    def _parse_questions_from_text(self, text: str) -> List[Dict]:
        """テキストから問題を解析"""
        questions = []
        
        # 問題番号パターン
        question_pattern = r'問\s*(\d+)\s*[．.]?\s*(.*?)(?=問\s*\d+|$)'
        
        # 問題を分割
        matches = re.finditer(question_pattern, text, re.DOTALL)
        
        for match in matches:
            question_num = int(match.group(1))
            question_content = match.group(2).strip()
            
            # 問題データを解析
            question_data = self._parse_single_question(question_num, question_content)
            if question_data:
                questions.append(question_data)
        
        return questions
    
    def _parse_single_question(self, question_num: int, content: str) -> Optional[Dict]:
        """個別の問題を解析"""
        try:
            # 問題文と選択肢を分離
            lines = content.split('\n')
            question_text = ""
            choices = []
            correct_answer = None
            
            current_section = "question"
            choice_pattern = r'^[ア-ン][\s\.\)]*(.+)'
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 選択肢の検出
                choice_match = re.match(choice_pattern, line)
                if choice_match:
                    current_section = "choices"
                    choices.append(choice_match.group(1).strip())
                elif current_section == "question":
                    question_text += line + " "
                elif current_section == "choices" and line:
                    choices[-1] += " " + line
            
            # 問題文を正規化
            question_text = DataUtils.normalize_question_text(question_text)
            
            # 選択肢を正規化
            if choices:
                choices = [DataUtils.normalize_question_text(choice) for choice in choices]
            
            # 最低限の検証
            if not question_text or len(choices) < 2:
                return None
            
            return {
                'question_number': question_num,
                'question_text': question_text,
                'choices': choices,
                'correct_answer': correct_answer,  # 別途解答を取得する必要がある
                'category': None,  # 分野分類は別途実装
                'difficulty_level': None,  # 難易度は統計から算出
                'explanation': None  # 解説は別途取得
            }
            
        except Exception as e:
            self.logger.error(f"問題{question_num}の解析に失敗: {e}")
            return None
    
    def fetch_answer_key(self, year: int, exam_type: str = "FE") -> Dict[int, int]:
        """
        解答を取得
        
        Args:
            year: 年度
            exam_type: 試験種別
            
        Returns:
            Dict[int, int]: 問題番号と正答番号のマッピング
        """
        self.logger.info(f"{year}年度の解答を取得中...")
        
        # 解答ページのURLを構築
        answer_url = self._get_answer_url(year, exam_type)
        
        try:
            response = WebUtils.safe_request(
                answer_url,
                delay=config.REQUEST_DELAY,
                timeout=config.REQUEST_TIMEOUT,
                max_retries=config.MAX_RETRIES
            )
            
            if not response:
                self.logger.warning(f"解答ページの取得に失敗: {answer_url}")
                return {}
            
            # 解答を抽出
            answers = self._extract_answers(response.text)
            
            self.logger.info(f"解答取得完了: {len(answers)} 問題")
            return answers
            
        except Exception as e:
            self.logger.error(f"解答取得エラー: {e}")
            return {}
    
    def _get_answer_url(self, year: int, exam_type: str) -> str:
        """解答ページのURLを取得"""
        # 年度とexam_typeに基づいてURLを構築
        # 実際のIPAサイトの構造に合わせて調整が必要
        base_url = self._get_base_url(exam_type)
        return f"{base_url}{year}/answer.html"
    
    def _extract_answers(self, html: str) -> Dict[int, int]:
        """HTMLから解答を抽出"""
        soup = BeautifulSoup(html, 'html.parser')
        answers = {}
        
        # 解答パターンを検索
        answer_patterns = [
            r'問\s*(\d+)\s*[：:]\s*([ア-ン])',
            r'(\d+)\s*[．.]\s*([ア-ン])',
            r'No\.\s*(\d+)\s*[：:]\s*([ア-ン])'
        ]
        
        for pattern in answer_patterns:
            matches = re.finditer(pattern, html)
            for match in matches:
                question_num = int(match.group(1))
                answer_char = match.group(2)
                # カタカナを番号に変換
                answer_num = ord(answer_char) - ord('ア') + 1
                answers[question_num] = answer_num
        
        return answers
    
    def save_questions_to_json(self, questions: List[Dict], output_path: Path):
        """問題データをJSONファイルに保存"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(questions, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"問題データを保存: {output_path}")
            
        except Exception as e:
            self.logger.error(f"JSONファイル保存エラー: {e}")
            raise DataError(f"JSONファイル保存に失敗: {e}")
    
    def process_exam_year(self, year: int, exam_type: str = "FE") -> Dict:
        """
        指定年度の試験データを処理
        
        Args:
            year: 年度
            exam_type: 試験種別
            
        Returns:
            Dict: 処理結果
        """
        self.logger.info(f"{year}年度 {exam_type} 試験データの処理を開始")
        
        result = {
            'year': year,
            'exam_type': exam_type,
            'questions': [],
            'answers': {},
            'status': 'failed'
        }
        
        try:
            # 過去問題リストを取得
            exam_list = self.fetch_exam_list(exam_type)
            
            # 指定年度の問題を検索
            target_exam = None
            for exam in exam_list:
                if exam['year'] == year:
                    target_exam = exam
                    break
            
            if not target_exam:
                raise DataError(f"{year}年度の試験データが見つかりません")
            
            # 問題ファイルをダウンロード
            pdf_path = self.download_exam_data(target_exam)
            if not pdf_path:
                raise DataError("問題ファイルのダウンロードに失敗")
            
            # 問題を抽出
            questions = self.extract_questions_from_pdf(pdf_path)
            
            # 解答を取得
            answers = self.fetch_answer_key(year, exam_type)
            
            # 解答を問題に統合
            for question in questions:
                question_num = question['question_number']
                if question_num in answers:
                    question['correct_answer'] = answers[question_num]
            
            result['questions'] = questions
            result['answers'] = answers
            result['status'] = 'success'
            
            self.logger.info(f"{year}年度の処理完了: {len(questions)} 問題を取得")
            
        except Exception as e:
            self.logger.error(f"{year}年度の処理に失敗: {e}")
            result['error'] = str(e)
        
        return result

class DataProcessor:
    """データ処理・正規化クラス"""
    
    def __init__(self):
        self.logger = Logger.setup_logger(
            "DataProcessor",
            config.LOG_FILE,
            config.LOG_LEVEL
        )
    
    def categorize_questions(self, questions: List[Dict]) -> List[Dict]:
        """問題を分野別に分類"""
        self.logger.info("問題の分野分類を開始")
        
        # 分野分類のキーワード辞書
        category_keywords = {
            'テクノロジ系': {
                'アルゴリズム': ['アルゴリズム', '計算量', 'ソート', '探索'],
                'データ構造': ['配列', 'リスト', 'スタック', 'キュー', 'ツリー'],
                'プログラミング': ['プログラム', 'コーディング', '変数', '関数'],
                'コンピュータ構成': ['CPU', 'メモリ', 'キャッシュ', 'アーキテクチャ'],
                'ネットワーク': ['TCP', 'IP', 'HTTP', 'LAN', 'WAN'],
                'データベース': ['SQL', 'テーブル', 'リレーション', 'データベース'],
                'セキュリティ': ['暗号', '認証', '脆弱性', 'セキュリティ']
            },
            'マネジメント系': {
                'プロジェクト管理': ['プロジェクト', 'WBS', 'PERT', 'CPM'],
                'サービス管理': ['ITIL', 'SLA', 'サービスレベル'],
                'システム監査': ['監査', 'コントロール', 'リスク']
            },
            'ストラテジ系': {
                'システム戦略': ['システム化', 'EA', 'SOA'],
                '経営戦略': ['経営', 'マーケティング', 'SCM'],
                '法務': ['知的財産', '個人情報', 'コンプライアンス']
            }
        }
        
        for question in questions:
            question['category'] = self._classify_question(
                question['question_text'], 
                category_keywords
            )
        
        self.logger.info("分野分類完了")
        return questions
    
    def _classify_question(self, question_text: str, category_keywords: Dict) -> str:
        """個別の問題を分野分類"""
        scores = {}
        
        for main_category, subcategories in category_keywords.items():
            scores[main_category] = 0
            
            for subcategory, keywords in subcategories.items():
                for keyword in keywords:
                    if keyword in question_text:
                        scores[main_category] += 1
        
        # 最も高いスコアの分野を返す
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        else:
            return "その他"
    
    def validate_question_data(self, questions: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """問題データの検証"""
        self.logger.info("問題データの検証を開始")
        
        valid_questions = []
        invalid_questions = []
        
        for question in questions:
            is_valid, errors = ValidationUtils.validate_question_data(question)
            
            if is_valid:
                valid_questions.append(question)
            else:
                question['validation_errors'] = errors
                invalid_questions.append(question)
        
        self.logger.info(f"検証完了: 有効{len(valid_questions)}問、無効{len(invalid_questions)}問")
        
        return valid_questions, invalid_questions