"""
情報技術者試験学習システム - ユーティリティモジュール
"""

import os
import re
import json
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import requests
from bs4 import BeautifulSoup
import time

class Logger:
    """ログ管理クラス"""
    
    @staticmethod
    def setup_logger(name: str, log_file: Path = None, level: str = "INFO"):
        """ロガーをセットアップ"""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))
        
        # ハンドラーが既に存在する場合は削除
        if logger.handlers:
            logger.handlers.clear()
        
        # フォーマッター
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # ファイルハンドラー
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger

class FileUtils:
    """ファイル操作ユーティリティ"""
    
    @staticmethod
    def ensure_directory(path: Path):
        """ディレクトリが存在しない場合は作成"""
        path.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def safe_filename(filename: str) -> str:
        """ファイル名を安全な形式に変換"""
        # 危険な文字を除去
        safe = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 連続するアンダースコアを一つに
        safe = re.sub(r'_+', '_', safe)
        # 長さ制限
        if len(safe) > 100:
            safe = safe[:100]
        return safe.strip('_')
    
    @staticmethod
    def get_file_hash(file_path: Path) -> str:
        """ファイルのハッシュ値を取得"""
        if not file_path.exists():
            return ""
        
        hash_md5 = hashlib.md5(usedforsecurity=False)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    @staticmethod
    def backup_file(file_path: Path, backup_dir: Path = None):
        """ファイルをバックアップ"""
        if not file_path.exists():
            return None
        
        if backup_dir is None:
            backup_dir = file_path.parent / "backups"
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = backup_dir / backup_name
        
        import shutil
        shutil.copy2(file_path, backup_path)
        return backup_path

class WebUtils:
    """Web関連ユーティリティ"""
    
    @staticmethod
    def safe_request(url: str, delay: float = 1.0, timeout: int = 30, 
                    max_retries: int = 3) -> Optional[requests.Response]:
        """安全なHTTPリクエスト"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        for attempt in range(max_retries):
            try:
                if delay > 0:
                    time.sleep(delay)
                
                response = requests.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    logging.error(f"Request failed after {max_retries} attempts: {e}")
                    return None
                else:
                    logging.warning(f"Request attempt {attempt + 1} failed: {e}")
                    time.sleep(delay * (attempt + 1))
        
        return None
    
    @staticmethod
    def extract_links(html: str, base_url: str = "") -> List[str]:
        """HTMLからリンクを抽出"""
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('http'):
                links.append(href)
            elif href.startswith('/'):
                links.append(base_url + href)
            else:
                links.append(base_url + '/' + href)
        
        return links
    
    @staticmethod
    def clean_text(text: str) -> str:
        """テキストをクリーンアップ"""
        if not text:
            return ""
        
        # 改行・タブを正規化
        text = re.sub(r'\s+', ' ', text)
        # 前後の空白を削除
        text = text.strip()
        return text

class DataUtils:
    """データ処理ユーティリティ"""
    
    @staticmethod
    def normalize_question_text(text: str) -> str:
        """問題文を正規化"""
        if not text:
            return ""
        
        # HTMLタグを除去
        text = re.sub(r'<[^>]+>', '', text)
        # 余分な空白を削除
        text = re.sub(r'\s+', ' ', text)
        # 特殊文字を正規化
        text = text.replace('　', ' ')  # 全角空白を半角に
        text = text.replace('"', '"').replace('"', '"')  # 引用符を統一
        text = text.replace(''', "'").replace(''', "'")  # アポストロフィを統一
        
        return text.strip()
    
    @staticmethod
    def parse_choices(choices_text: str) -> List[str]:
        """選択肢テキストを解析"""
        if not choices_text:
            return []
        
        # 選択肢の区切り文字を統一
        choices_text = re.sub(r'[ａ-ｚＡ-Ｚ][\.\)]\s*', '\n', choices_text)
        choices_text = re.sub(r'[a-zA-Z][\.\)]\s*', '\n', choices_text)
        
        # 改行で分割
        choices = []
        for choice in choices_text.split('\n'):
            choice = choice.strip()
            if choice:
                choices.append(choice)
        
        return choices
    
    @staticmethod
    def calculate_difficulty(correct_rate: float) -> int:
        """正答率から難易度を計算"""
        if correct_rate >= 0.8:
            return 1  # 基礎
        elif correct_rate >= 0.6:
            return 2  # 標準
        elif correct_rate >= 0.4:
            return 3  # 応用
        else:
            return 4  # 高度
    
    @staticmethod
    def format_percentage(value: float, decimal_places: int = 1) -> str:
        """パーセンテージを書式設定"""
        return f"{value * 100:.{decimal_places}f}%"
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """秒を時間形式に変換"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            return f"{minutes}分{remaining_seconds}秒"
        else:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            return f"{hours}時間{remaining_minutes}分"

class ValidationUtils:
    """バリデーションユーティリティ"""
    
    @staticmethod
    def validate_year(year: int) -> bool:
        """年度の妥当性をチェック"""
        current_year = datetime.now().year
        return 2020 <= year <= current_year
    
    @staticmethod
    def validate_exam_code(exam_code: str) -> bool:
        """試験コードの妥当性をチェック"""
        valid_codes = ["FE", "AP", "IP", "SG", "DB", "NW", "SC", "AU", "ES", "FL", "PM", "ST", "SA", "SM"]
        return exam_code.upper() in valid_codes
    
    @staticmethod
    def validate_question_data(question_data: Dict) -> Tuple[bool, List[str]]:
        """問題データの妥当性をチェック"""
        errors = []
        
        # 必須フィールドチェック
        required_fields = ["question_text", "choices", "correct_answer"]
        for field in required_fields:
            if field not in question_data or not question_data[field]:
                errors.append(f"必須フィールド '{field}' が不足しています")
        
        # 選択肢チェック
        if "choices" in question_data:
            choices = question_data["choices"]
            if not isinstance(choices, list) or len(choices) < 2:
                errors.append("選択肢は2つ以上必要です")
        
        # 正答チェック
        if "correct_answer" in question_data and "choices" in question_data:
            correct_answer = question_data["correct_answer"]
            choices_count = len(question_data["choices"])
            if not (1 <= correct_answer <= choices_count):
                errors.append(f"正答番号は1から{choices_count}の範囲で指定してください")
        
        return len(errors) == 0, errors

class CacheUtils:
    """キャッシュ管理ユーティリティ"""
    
    @staticmethod
    def get_cache_key(data: Any) -> str:
        """データからキャッシュキーを生成"""
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        
        return hashlib.md5(data_str.encode(), usedforsecurity=False).hexdigest()
    
    @staticmethod
    def is_cache_valid(cache_path: Path, max_age_hours: int = 24) -> bool:
        """キャッシュの有効性をチェック"""
        if not cache_path.exists():
            return False
        
        cache_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        max_age = timedelta(hours=max_age_hours)
        
        return datetime.now() - cache_time < max_age

class StatisticsUtils:
    """統計処理ユーティリティ"""
    
    @staticmethod
    def calculate_statistics(values: List[float]) -> Dict[str, float]:
        """基本統計量を計算"""
        if not values:
            return {}
        
        import numpy as np
        return {
            "count": len(values),
            "mean": np.mean(values),
            "median": np.median(values),
            "std": np.std(values),
            "min": np.min(values),
            "max": np.max(values)
        }
    
    @staticmethod
    def calculate_confidence_interval(values: List[float], confidence: float = 0.95) -> Tuple[float, float]:
        """信頼区間を計算"""
        if len(values) < 2:
            return (0, 0)
        
        import numpy as np
        from scipy import stats
        
        mean = np.mean(values)
        std_err = stats.sem(values)
        h = std_err * stats.t.ppf((1 + confidence) / 2, len(values) - 1)
        
        return (mean - h, mean + h)

# 共通エラークラス
class SystemError(Exception):
    """システム共通エラー"""
    pass

class DataError(SystemError):
    """データ関連エラー"""
    pass

class NetworkError(SystemError):
    """ネットワーク関連エラー"""
    pass

class ValidationError(SystemError):
    """バリデーション関連エラー"""
    pass