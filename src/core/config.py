"""
情報技術者試験学習システム - 設定管理モジュール
"""

import os
from pathlib import Path

class Config:
    """システム設定クラス"""
    
    # プロジェクトルートディレクトリ
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    
    # データベース設定
    DATABASE_PATH = PROJECT_ROOT / "data" / "database.db"
    
    # ログ設定
    LOG_FILE = PROJECT_ROOT / "logs" / "system.log"
    LOG_LEVEL = "INFO"
    
    # データ取得設定
    IPA_BASE_URL = "https://www.ipa.go.jp/shiken/mondai-kaiotu/"
    IPA_FE_URL = "https://www.ipa.go.jp/shiken/mondai-kaiotu/sg_fe/koukai/"
    IPA_AP_URL = "https://www.ipa.go.jp/shiken/mondai-kaiotu/ap/"
    
    # リクエスト設定
    REQUEST_DELAY = 1.0  # アクセス間隔（秒）
    REQUEST_TIMEOUT = 30  # タイムアウト（秒）
    MAX_RETRIES = 3  # 最大リトライ回数
    
    # ダウンロード設定
    DOWNLOAD_DIR = PROJECT_ROOT / "data" / "downloads"
    
    # レポート設定
    REPORT_OUTPUT_DIR = PROJECT_ROOT / "reports"
    TEMPLATE_DIR = PROJECT_ROOT / "templates"
    STATIC_DIR = PROJECT_ROOT / "static"
    
    # 学習設定
    DEFAULT_EXAM_TYPE = "FE"  # 基本情報技術者試験
    QUESTION_LIMIT = 20  # 1回の練習問題数
    MOCK_EXAM_QUESTIONS = 80  # 模擬試験問題数
    
    # 試験区分設定
    EXAM_CATEGORIES = {
        "FE": {
            "name": "基本情報技術者試験",
            "code": "FE",
            "description": "ITエンジニアの登竜門"
        },
        "AP": {
            "name": "応用情報技術者試験",
            "code": "AP", 
            "description": "ワンランク上のITエンジニア"
        },
        "IP": {
            "name": "ITパスポート試験",
            "code": "IP",
            "description": "ITを利活用するすべての社会人・学生"
        },
        "SG": {
            "name": "情報セキュリティマネジメント試験",
            "code": "SG",
            "description": "情報セキュリティの基本"
        }
    }
    
    # 分野設定
    SUBJECT_CATEGORIES = {
        "technology": {
            "name": "テクノロジ系",
            "weight": 0.5,
            "subcategories": [
                "基礎理論",
                "アルゴリズムとプログラミング",
                "コンピュータ構成要素",
                "システム構成要素",
                "ソフトウェア",
                "ハードウェア",
                "ヒューマンインターフェース",
                "マルチメディア",
                "データベース",
                "ネットワーク",
                "セキュリティ"
            ]
        },
        "management": {
            "name": "マネジメント系",
            "weight": 0.25,
            "subcategories": [
                "プロジェクトマネジメント",
                "サービスマネジメント",
                "システム監査"
            ]
        },
        "strategy": {
            "name": "ストラテジ系",
            "weight": 0.25,
            "subcategories": [
                "システム戦略",
                "システム企画",
                "経営戦略",
                "技術戦略",
                "ビジネスインダストリ"
            ]
        }
    }
    
    # ログ設定
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = PROJECT_ROOT / "logs" / "system.log"
    
    # パフォーマンス設定
    BATCH_SIZE = 100  # バッチ処理サイズ
    CACHE_SIZE = 1000  # キャッシュサイズ
    
    # UI設定
    CHART_COLORS = [
        "#3498db",  # Blue
        "#e74c3c",  # Red
        "#2ecc71",  # Green
        "#f39c12",  # Orange
        "#9b59b6",  # Purple
        "#1abc9c",  # Turquoise
        "#34495e",  # Dark Gray
        "#e67e22"   # Dark Orange
    ]
    
    # 難易度設定
    DIFFICULTY_LEVELS = {
        1: "基礎",
        2: "標準", 
        3: "応用",
        4: "高度"
    }
    
    @classmethod
    def create_directories(cls):
        """必要なディレクトリを作成"""
        directories = [
            cls.PROJECT_ROOT / "data",
            cls.DOWNLOAD_DIR,
            cls.REPORT_OUTPUT_DIR,
            cls.TEMPLATE_DIR,
            cls.STATIC_DIR,
            cls.PROJECT_ROOT / "logs"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_exam_info(cls, exam_code):
        """試験情報を取得"""
        return cls.EXAM_CATEGORIES.get(exam_code, None)
    
    @classmethod
    def get_subject_info(cls, subject_code):
        """分野情報を取得"""
        return cls.SUBJECT_CATEGORIES.get(subject_code, None)

# 開発環境設定
class DevelopmentConfig(Config):
    """開発環境用設定"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    REQUEST_DELAY = 2.0  # 開発時は間隔を長めに

# 本番環境設定
class ProductionConfig(Config):
    """本番環境用設定"""
    DEBUG = False
    LOG_LEVEL = "INFO"
    REQUEST_DELAY = 1.0

# 設定の選択
def get_config():
    """環境に応じた設定を返す"""
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        return ProductionConfig()
    else:
        return DevelopmentConfig()

# デフォルト設定
config = get_config()