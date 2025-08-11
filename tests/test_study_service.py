"""
StudyService の単体テスト
"""
import pytest
from unittest.mock import MagicMock, patch

from src.web.services.study_service import StudyService
from src.core.database import DatabaseManager


class TestStudyService:
    """StudyServiceのテストクラス"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """モックDBマネージャーを提供"""
        return MagicMock(spec=DatabaseManager)
    
    @pytest.fixture
    def study_service(self, mock_db_manager):
        """テスト用StudyServiceインスタンスを提供"""
        return StudyService(mock_db_manager)
    
    def test_get_exam_types(self, study_service):
        """試験種別取得のテスト"""
        with patch('src.web.services.study_service.config.EXAM_CATEGORIES', {'FE': '基本情報技術者試験'}):
            exam_types = study_service.get_exam_types()
            assert exam_types == {'FE': '基本情報技術者試験'}
    
    def test_get_categories(self, study_service):
        """分野取得のテスト"""
        with patch('src.web.services.study_service.config.SUBJECT_CATEGORIES', {
            'テクノロジ系': ['基礎理論', 'システム構成要素'],
            'マネジメント系': ['プロジェクトマネジメント']
        }):
            categories = study_service.get_categories()
            assert 'テクノロジ系' in categories
            assert 'マネジメント系' in categories
    
    def test_get_statistics(self, study_service, mock_db_manager):
        """統計情報取得のテスト"""
        # モックの戻り値を設定
        mock_db_manager.get_statistics.return_value = {
            'total_questions': 100,
            'correct_answers': 80,
            'correct_rate': 0.8
        }
        
        stats = study_service.get_statistics('FE')
        
        # DBマネージャーのメソッドが正しく呼ばれたかチェック
        mock_db_manager.get_statistics.assert_called_once_with('FE')
        
        # 返り値の検証
        assert stats['total_questions'] == 100
        assert stats['correct_answers'] == 80
        assert stats['correct_rate'] == 0.8
    
    def test_get_recent_activity(self, study_service, mock_db_manager):
        """最近の活動取得のテスト"""
        # モックの戻り値を設定
        mock_db_manager.get_learning_records.return_value = [
            {'question_id': 1, 'is_correct': True, 'date': '2025-08-08'},
            {'question_id': 2, 'is_correct': False, 'date': '2025-08-08'}
        ]
        
        activity = study_service.get_recent_activity(limit=2)
        
        # DBマネージャーのメソッドが正しく呼ばれたかチェック
        mock_db_manager.get_learning_records.assert_called_once_with(limit=2)
        
        # 返り値の検証
        assert len(activity) == 2
        assert activity[0]['question_id'] == 1
        assert activity[1]['is_correct'] is False
    
    def test_get_recommendations(self, study_service):
        """推奨事項取得のテスト"""
        recommendations = study_service.get_recommendations()
        
        # 推奨事項が返されることを確認
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # 各推奨事項に必要なフィールドがあることを確認
        for rec in recommendations:
            assert 'title' in rec
            assert 'description' in rec
            assert 'priority' in rec
            assert rec['priority'] in ['high', 'medium', 'low']
    
    def test_get_recommendations_structure(self, study_service):
        """推奨事項の構造テスト"""
        recommendations = study_service.get_recommendations()
        
        # 具体的な推奨事項の内容を確認
        assert len(recommendations) == 3
        
        # 弱点分野の集中学習
        weak_area_rec = next(r for r in recommendations if r['title'] == '弱点分野の集中学習')
        assert weak_area_rec['priority'] == 'high'
        
        # 模擬試験の実施
        mock_exam_rec = next(r for r in recommendations if r['title'] == '模擬試験の実施')
        assert mock_exam_rec['priority'] == 'medium'
        
        # 継続的な学習
        continuous_rec = next(r for r in recommendations if r['title'] == '継続的な学習')
        assert continuous_rec['priority'] == 'low'