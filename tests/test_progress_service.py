"""
ProgressService の単体テスト
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from pathlib import Path

from src.web.services.progress_service import ProgressService
from src.core.database import DatabaseManager
from src.core.report_generator import ReportGenerator


class TestProgressService:
    """ProgressServiceのテストクラス"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """モックDBマネージャーを提供"""
        return MagicMock(spec=DatabaseManager)
    
    @pytest.fixture
    def mock_report_generator(self):
        """モックレポートジェネレーターを提供"""
        return MagicMock(spec=ReportGenerator)
    
    @pytest.fixture
    def progress_service(self, mock_db_manager, mock_report_generator):
        """テスト用ProgressServiceインスタンスを提供"""
        return ProgressService(mock_db_manager, mock_report_generator)
    
    def test_get_progress_data_success(self, progress_service, mock_db_manager):
        """進捗データ取得成功のテスト"""
        # モックの戻り値を設定
        mock_stats = {
            'total_questions': 100,
            'correct_answers': 80,
            'correct_rate': 0.8
        }
        mock_weak_areas = [
            {'category': 'ネットワーク', 'correct_rate': 0.6},
            {'category': 'データベース', 'correct_rate': 0.7}
        ]
        mock_progress = [
            {'date': '2025-08-01', 'correct_rate': 0.75},
            {'date': '2025-08-02', 'correct_rate': 0.80}
        ]
        
        mock_db_manager.get_statistics.return_value = mock_stats
        mock_db_manager.get_weak_areas.return_value = mock_weak_areas
        mock_db_manager.get_progress_over_time.return_value = mock_progress
        
        result = progress_service.get_progress_data('FE', 30)
        
        # メソッド呼び出しの確認
        mock_db_manager.get_statistics.assert_called_once_with('FE')
        mock_db_manager.get_weak_areas.assert_called_once_with('FE', limit=5)
        mock_db_manager.get_progress_over_time.assert_called_once_with('FE', 30)
        
        # 返り値の確認
        assert 'statistics' in result
        assert 'weak_areas' in result
        assert 'progress_over_time' in result
        assert result['statistics'] == mock_stats
        assert result['weak_areas'] == mock_weak_areas
        assert result['progress_over_time'] == mock_progress
    
    def test_get_progress_data_exception(self, progress_service, mock_db_manager):
        """進捗データ取得でエラー発生時のテスト"""
        # データベースエラーをモック
        mock_db_manager.get_statistics.side_effect = Exception("Database error")
        
        with patch('src.web.services.progress_service.logger') as mock_logger:
            result = progress_service.get_progress_data('FE', 30)
            
            # エラーログが出力されることを確認
            mock_logger.error.assert_called_once()
            
            # 空の辞書が返されることを確認
            assert result == {}
    
    @patch('src.web.services.progress_service.config.REPORT_OUTPUT_DIR')
    @patch('src.web.services.progress_service.config.PROJECT_ROOT')
    def test_get_report_files_success(self, mock_project_root, mock_report_dir, progress_service):
        """レポートファイル一覧取得成功のテスト"""
        # モックディレクトリの設定
        mock_report_dir.exists.return_value = True
        
        # モックファイルの設定
        mock_file1 = MagicMock()
        mock_file1.name = 'report_20250808.html'
        mock_file1.relative_to.return_value = Path('reports/report_20250808.html')
        mock_file1.stat.return_value.st_mtime = 1691472000  # 2023-08-08のタイムスタンプ
        
        mock_file2 = MagicMock()
        mock_file2.name = 'report_20250807.html'
        mock_file2.relative_to.return_value = Path('reports/report_20250807.html')
        mock_file2.stat.return_value.st_mtime = 1691385600  # 2023-08-07のタイムスタンプ
        
        mock_report_dir.glob.return_value = [mock_file1, mock_file2]
        mock_project_root.return_value = Path('/test')
        
        result = progress_service.get_report_files()
        
        # 結果の確認
        assert len(result) == 2
        
        # 新しいファイルが先頭にくることを確認（作成日時順）
        assert result[0]['name'] == 'report_20250808.html'
        assert result[1]['name'] == 'report_20250807.html'
        
        # ファイル情報の確認
        for file_info in result:
            assert 'name' in file_info
            assert 'path' in file_info
            assert 'created' in file_info
            assert isinstance(file_info['created'], datetime)
    
    @patch('src.web.services.progress_service.config.REPORT_OUTPUT_DIR')
    def test_get_report_files_directory_not_exists(self, mock_report_dir, progress_service):
        """レポートディレクトリが存在しない場合のテスト"""
        mock_report_dir.exists.return_value = False
        
        result = progress_service.get_report_files()
        
        # 空のリストが返されることを確認
        assert result == []
    
    @patch('src.web.services.progress_service.config.REPORT_OUTPUT_DIR')
    def test_get_report_files_exception(self, mock_report_dir, progress_service):
        """レポートファイル取得でエラー発生時のテスト"""
        mock_report_dir.exists.side_effect = Exception("File system error")
        
        with patch('src.web.services.progress_service.logger') as mock_logger:
            result = progress_service.get_report_files()
            
            # エラーログが出力されることを確認
            mock_logger.error.assert_called_once()
            
            # 空のリストが返されることを確認
            assert result == []
    
    def test_generate_comprehensive_report(self, progress_service, mock_report_generator):
        """包括的レポート生成のテスト"""
        mock_path = Path('/test/reports/comprehensive_report.html')
        mock_report_generator.generate_comprehensive_report.return_value = mock_path
        
        result = progress_service.generate_comprehensive_report('FE', 30)
        
        # レポートジェネレーターのメソッドが正しく呼ばれたかチェック
        mock_report_generator.generate_comprehensive_report.assert_called_once_with(
            exam_type='FE',
            days=30
        )
        
        # パスが返されることを確認
        assert result == mock_path
    
    def test_get_progress_data_empty_weak_areas(self, progress_service, mock_db_manager):
        """弱点分野が存在しない場合のテスト"""
        mock_db_manager.get_statistics.return_value = {'total_questions': 0}
        mock_db_manager.get_weak_areas.return_value = []
        mock_db_manager.get_progress_over_time.return_value = []
        
        result = progress_service.get_progress_data('FE', 30)
        
        # 空のデータでも正常に処理されることを確認
        assert result['statistics']['total_questions'] == 0
        assert result['weak_areas'] == []
        assert result['progress_over_time'] == []
    
    def test_get_progress_data_different_exam_types(self, progress_service, mock_db_manager):
        """異なる試験種別での進捗データ取得テスト"""
        mock_db_manager.get_statistics.return_value = {}
        mock_db_manager.get_weak_areas.return_value = []
        mock_db_manager.get_progress_over_time.return_value = []
        
        # FE試験
        progress_service.get_progress_data('FE', 30)
        mock_db_manager.get_statistics.assert_called_with('FE')
        
        # AP試験
        progress_service.get_progress_data('AP', 60)
        mock_db_manager.get_statistics.assert_called_with('AP')
        mock_db_manager.get_progress_over_time.assert_called_with('AP', 60)