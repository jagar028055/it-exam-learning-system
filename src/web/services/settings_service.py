"""
設定関連サービス
"""

import logging
from typing import Dict

from ...core.database import DatabaseManager
from ...data.data_fetcher import IPADataFetcher, DataProcessor
from ...core.config import config

logger = logging.getLogger(__name__)

class SettingsService:
    """設定関連サービス"""
    
    def __init__(self, db_manager: DatabaseManager, data_fetcher: IPADataFetcher, data_processor: DataProcessor):
        self.db = db_manager
        self.fetcher = data_fetcher
        self.processor = data_processor
    
    def get_settings_data(self) -> Dict:
        """設定データを取得"""
        try:
            # データベース情報
            db_info = self.db.get_database_info()
            
            # パフォーマンスメトリクス
            perf_metrics = self.db.get_performance_metrics()
            
            # キャッシュ統計
            cache_stats = self.db.get_cache_stats()
            
            # 設定情報
            settings_info = {
                'project_root': str(config.PROJECT_ROOT),
                'database_path': str(config.DATABASE_PATH),
                'report_output_dir': str(config.REPORT_OUTPUT_DIR),
                'log_level': config.LOG_LEVEL
            }
            
            return {
                'db_info': db_info,
                'perf_metrics': perf_metrics,
                'cache_stats': cache_stats,
                'settings_info': settings_info
            }
        except Exception as e:
            logger.error(f"設定データ取得エラー: {e}")
            return {
                'db_info': {},
                'perf_metrics': {},
                'cache_stats': {},
                'settings_info': {}
            }
    
    def fetch_exam_data(self, exam_type: str, year: int = None) -> Dict:
        """試験データを取得"""
        try:
            if year:
                result = self.fetcher.process_exam_year(year, exam_type)
                if result['status'] == 'success':
                    self._save_questions_to_db(result['questions'], exam_type, year)
                    return {
                        'success': True,
                        'message': f'{year}年度のデータを取得しました。'
                    }
                else:
                    return {
                        'success': False,
                        'message': f'{year}年度のデータ取得に失敗しました。'
                    }
            else:
                # 全年度取得（最新3年度のみ）
                exam_list = self.fetcher.fetch_exam_list(exam_type)
                success_count = 0
                
                for exam in exam_list[:3]:
                    try:
                        result = self.fetcher.process_exam_year(exam['year'], exam_type)
                        if result['status'] == 'success':
                            self._save_questions_to_db(result['questions'], exam_type, exam['year'])
                            success_count += 1
                    except Exception as e:
                        logger.error(f"{exam['year']}年度処理エラー: {e}")
                        continue
                
                return {
                    'success': True,
                    'message': f'{success_count}年度のデータを取得しました。'
                }
                
        except Exception as e:
            logger.error(f"データ取得エラー: {e}")
            return {
                'success': False,
                'message': f'データ取得に失敗しました: {e}'
            }
    
    def optimize_database(self):
        """データベース最適化"""
        self.db.optimize_database()
    
    def _save_questions_to_db(self, questions: list, exam_type: str, year: int):
        """問題をデータベースに保存"""
        try:
            # 分野分類を実行
            questions = self.processor.categorize_questions(questions)
            
            # データ検証
            valid_questions, invalid_questions = self.processor.validate_question_data(questions)
            
            # データベースに保存
            for question in valid_questions:
                question['exam_type'] = exam_type
                question['year'] = year
                try:
                    self.db.insert_question(question)
                except Exception as e:
                    logger.error(f"問題保存エラー: {e}")
                    continue
            
            logger.info(f"データベース保存完了: {len(valid_questions)} 問題")
            
        except Exception as e:
            logger.error(f"データベース保存エラー: {e}")
            raise