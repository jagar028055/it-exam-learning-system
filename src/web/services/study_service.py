"""
学習関連サービス
"""

import logging
from typing import Dict, List, Optional

from ...core.database import DatabaseManager
from ...core.config import config

logger = logging.getLogger(__name__)

class StudyService:
    """学習関連サービス"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_exam_types(self) -> Dict:
        """利用可能な試験種別を取得"""
        return config.EXAM_CATEGORIES
    
    def get_categories(self) -> List[str]:
        """分野情報を取得"""
        return list(config.SUBJECT_CATEGORIES.keys())
    
    def get_statistics(self, exam_type: str) -> Dict:
        """統計情報を取得"""
        return self.db.get_statistics(exam_type)
    
    def get_recent_activity(self, limit: int = 5) -> List[Dict]:
        """最近の活動を取得"""
        return self.db.get_learning_records(limit=limit)
    
    def get_recommendations(self) -> List[Dict]:
        """推奨事項を取得"""
        return [
            {
                'title': '弱点分野の集中学習',
                'description': 'ネットワーク分野での正答率が低めです。',
                'priority': 'high'
            },
            {
                'title': '模擬試験の実施',
                'description': '全分野バランスよく出題される模擬試験を実施しましょう。',
                'priority': 'medium'
            },
            {
                'title': '継続的な学習',
                'description': '毎日少しずつでも学習を続けることが重要です。',
                'priority': 'low'
            }
        ]