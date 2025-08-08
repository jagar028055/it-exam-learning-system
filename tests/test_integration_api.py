"""
API統合テスト
"""
import pytest
import json
from datetime import datetime

from src.web.app import ApplicationFactory


@pytest.fixture
def app():
    """テスト用アプリケーション"""
    app = ApplicationFactory.create_app()
    app.config.update({
        'TESTING': True,
        'DATABASE_PATH': ':memory:',  # インメモリデータベース使用
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False  # テスト時はCSRF無効
    })
    return app


@pytest.fixture
def client(app):
    """テスト用クライアント"""
    return app.test_client()


@pytest.fixture 
def app_context(app):
    """アプリケーションコンテキスト"""
    with app.app_context():
        yield app


class TestHealthEndpoints:
    """ヘルスチェックエンドポイントの統合テスト"""
    
    @pytest.mark.integration
    def test_health_endpoint_integration(self, client):
        """ヘルスチェックエンドポイントの統合テスト"""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        
        # 必須フィールドの確認
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'database' in data
        
        # データベース接続確認
        assert data['database']['status'] == 'connected'
        
        # タイムスタンプが現在時刻に近いことを確認
        timestamp = datetime.fromisoformat(data['timestamp'])
        now = datetime.now()
        time_diff = abs((now - timestamp).total_seconds())
        assert time_diff < 60  # 1分以内
    
    @pytest.mark.integration
    def test_ping_endpoint_integration(self, client):
        """PINGエンドポイントの統合テスト"""
        response = client.get('/ping')
        
        assert response.status_code == 200
        assert response.data == b'pong'


class TestMainRoutes:
    """メインルートの統合テスト"""
    
    @pytest.mark.integration
    def test_index_page_integration(self, client):
        """トップページの統合テスト"""
        response = client.get('/')
        
        assert response.status_code == 200
        assert b'IT\xe8\xa9\xa6\xe9\xa8\x93\xe5\xad\xa6\xe7\xbf\x92\xe3\x82\xb7\xe3\x82\xb9\xe3\x83\x86\xe3\x83\xa0' in response.data  # 「IT試験学習システム」のUTF-8
    
    @pytest.mark.integration
    def test_study_page_integration(self, client):
        """学習ページの統合テスト"""
        response = client.get('/study')
        
        assert response.status_code == 200
        # 学習ページの要素確認
        assert b'exam_type' in response.data
        assert b'mode' in response.data
    
    @pytest.mark.integration
    def test_progress_page_integration(self, client):
        """進捗ページの統合テスト"""
        response = client.get('/progress')
        
        assert response.status_code == 200
        # 進捗ページの要素確認
        assert b'progress' in response.data or b'chart' in response.data


class TestStudyFlow:
    """学習フローの統合テスト"""
    
    @pytest.mark.integration
    def test_start_study_session_integration(self, client):
        """学習セッション開始の統合テスト"""
        # セッション開始
        response = client.post('/study/start', data={
            'exam_type': 'FE',
            'mode': 'practice', 
            'count': '5'
        })
        
        # リダイレクト確認
        assert response.status_code == 302
        assert '/question' in response.location
    
    @pytest.mark.integration
    def test_complete_study_flow_integration(self, client):
        """学習フロー完全実行の統合テスト"""
        # 1. セッション開始
        start_response = client.post('/study/start', data={
            'exam_type': 'FE',
            'mode': 'practice',
            'count': '3'
        })
        
        assert start_response.status_code == 302
        
        # 2. 最初の問題表示
        question_response = client.get('/question')
        assert question_response.status_code == 200
        assert b'question' in question_response.data
        
        # 3. 回答送信（3回分）
        for i in range(3):
            answer_response = client.post('/question', data={
                'answer': '1'  # 常に選択肢1を選択
            })
            
            # 最後の問題以外はリダイレクト（次の問題へ）
            if i < 2:
                assert answer_response.status_code == 302
                assert '/question' in answer_response.location
        
        # 4. 結果ページ確認
        result_response = client.get('/result')
        assert result_response.status_code == 200
        assert b'result' in result_response.data or b'\xe7\xb5\x90\xe6\x9e\x9c' in result_response.data  # 「結果」のUTF-8


class TestSettingsIntegration:
    """設定機能の統合テスト"""
    
    @pytest.mark.integration
    def test_settings_page_integration(self, client):
        """設定ページの統合テスト"""
        response = client.get('/settings')
        
        assert response.status_code == 200
        assert b'settings' in response.data or b'\xe8\xa8\xad\xe5\xae\x9a' in response.data  # 「設定」のUTF-8
    
    @pytest.mark.integration
    def test_settings_update_integration(self, client):
        """設定更新の統合テスト"""
        # 設定更新
        response = client.post('/settings', data={
            'theme': 'dark',
            'difficulty_level': '2',
            'notifications': 'on'
        })
        
        # リダイレクト確認（設定保存後）
        assert response.status_code == 302 or response.status_code == 200


class TestReportsIntegration:
    """レポート機能の統合テスト"""
    
    @pytest.mark.integration
    def test_reports_page_integration(self, client):
        """レポートページの統合テスト"""
        response = client.get('/reports')
        
        assert response.status_code == 200
        # レポートページの基本要素確認
        assert b'report' in response.data
    
    @pytest.mark.integration
    def test_generate_report_integration(self, client):
        """レポート生成の統合テスト"""
        response = client.post('/reports/generate', data={
            'exam_type': 'FE',
            'days': '30'
        })
        
        # レスポンスコードの確認（生成成功またはリダイレクト）
        assert response.status_code in [200, 302]


class TestErrorHandling:
    """エラーハンドリングの統合テスト"""
    
    @pytest.mark.integration
    def test_404_error_integration(self, client):
        """404エラーの統合テスト"""
        response = client.get('/nonexistent-page')
        
        assert response.status_code == 404
    
    @pytest.mark.integration
    def test_invalid_exam_type_integration(self, client):
        """無効な試験種別での統合テスト"""
        response = client.post('/study/start', data={
            'exam_type': 'INVALID',
            'mode': 'practice',
            'count': '5'
        })
        
        # バリデーションエラーまたはリダイレクト
        assert response.status_code in [400, 302]
    
    @pytest.mark.integration
    def test_empty_session_access_integration(self, client):
        """セッション未開始での問題アクセステスト"""
        response = client.get('/question')
        
        # 学習ページへのリダイレクトまたはエラーページ
        assert response.status_code in [302, 400]


class TestDatabaseIntegration:
    """データベース統合テスト"""
    
    @pytest.mark.integration
    def test_database_connection_integration(self, app_context):
        """データベース接続の統合テスト"""
        from src.core.database import DatabaseManager
        
        db = DatabaseManager()
        
        # 接続確認
        conn = db.get_connection()
        assert conn is not None
        
        # 基本クエリ実行確認
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1
    
    @pytest.mark.integration 
    def test_statistics_retrieval_integration(self, app_context):
        """統計情報取得の統合テスト"""
        from src.core.database import DatabaseManager
        
        db = DatabaseManager()
        stats = db.get_statistics('FE')
        
        # 統計情報の基本構造確認
        assert isinstance(stats, dict)
        expected_keys = ['total_questions', 'correct_answers', 'incorrect_answers', 'correct_rate']
        for key in expected_keys:
            assert key in stats