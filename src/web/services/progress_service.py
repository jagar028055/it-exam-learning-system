"""
進捗・レポート関連サービス
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from ...core.database import DatabaseManager
from ...core.report_generator import ReportGenerator
from ...core.config import config

logger = logging.getLogger(__name__)

class ProgressService:
    """進捗・レポート関連サービス"""
    
    def __init__(self, db_manager: DatabaseManager, report_generator: ReportGenerator):
        self.db = db_manager
        self.report_generator = report_generator
    
    def get_progress_data(self, exam_type: str, days: int) -> Dict:
        """進捗データを取得"""
        try:
            # 統計情報を取得
            stats = self.db.get_statistics(exam_type)
            
            # 弱点分野を取得
            weak_areas = self.db.get_weak_areas(exam_type, limit=5)
            
            # 時系列進捗を取得
            progress_over_time = self.db.get_progress_over_time(exam_type, days)
            
            # 統計データが空またはリストの場合のデフォルト値
            if not stats or isinstance(stats, list):
                stats = {
                    'total_questions': 0,
                    'total_correct': 0,
                    'overall_correct_rate': 0.0,
                    'categories_studied': 0
                }
            
            # テンプレートが期待する構造に合わせる
            return {
                'overall_statistics': stats,
                'statistics': stats,
                'weak_areas': weak_areas if weak_areas else [],
                'progress_over_time': progress_over_time if progress_over_time else []
            }
        except Exception as e:
            logger.error(f"進捗データ取得エラー: {e}")
            return {
                'overall_statistics': {
                    'total_questions': 0,
                    'total_correct': 0,
                    'overall_correct_rate': 0.0,
                    'categories_studied': 0
                },
                'statistics': {
                    'total_questions': 0,
                    'total_correct': 0,
                    'overall_correct_rate': 0.0,
                    'categories_studied': 0
                },
                'weak_areas': [],
                'progress_over_time': []
            }
    
    def get_report_files(self) -> List[Dict]:
        """レポートファイル一覧を取得"""
        try:
            report_files = []
            if config.REPORT_OUTPUT_DIR.exists():
                for file in config.REPORT_OUTPUT_DIR.glob('*.html'):
                    report_files.append({
                        'name': file.name,
                        'path': str(file.relative_to(config.PROJECT_ROOT)),
                        'created': datetime.fromtimestamp(file.stat().st_mtime)
                    })
            
            # 作成日時順にソート
            report_files.sort(key=lambda x: x['created'], reverse=True)
            
            return report_files
        except Exception as e:
            logger.error(f"レポートファイル取得エラー: {e}")
            return []
    
    def generate_comprehensive_report(self, exam_type: str, days: int) -> Path:
        """包括的なレポートを生成"""
        return self.report_generator.generate_comprehensive_report(
            exam_type=exam_type,
            days=days
        )