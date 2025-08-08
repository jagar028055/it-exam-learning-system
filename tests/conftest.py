"""
pytest設定ファイル
"""
import pytest
import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# テスト環境設定
os.environ['TESTING'] = '1'
os.environ['DATABASE_PATH'] = ':memory:'


@pytest.fixture(scope="session")
def playwright_config():
    """Playwright設定"""
    return {
        "browser_name": "chromium",
        "headless": True,
        "slow_mo": 0,
        "timeout": 30000
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """各テストの前に実行される環境セットアップ"""
    # テスト固有の環境変数設定
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['WTF_CSRF_ENABLED'] = 'False'
    os.environ['DATABASE_PATH'] = ':memory:'
    
    yield
    
    # テスト後のクリーンアップ
    # 必要に応じてセッションクリアなど


@pytest.fixture
def test_database():
    """テスト用データベースセットアップ"""
    from src.core.database import DatabaseManager
    
    # インメモリデータベースを使用
    db = DatabaseManager(database_path=':memory:')
    
    # テストデータの投入（必要に応じて）
    # db.init_test_data()
    
    return db


@pytest.fixture
def sample_test_data():
    """テスト用サンプルデータ"""
    return {
        'questions': [
            {
                'id': 1,
                'exam_type': 'FE',
                'year': 2024,
                'question_number': 1,
                'question_text': 'テスト問題1',
                'choices': ['選択肢1', '選択肢2', '選択肢3', '選択肢4'],
                'correct_answer': 1,
                'explanation': 'テスト解説1',
                'category': 'テクノロジ系'
            },
            {
                'id': 2,
                'exam_type': 'FE',
                'year': 2024,
                'question_number': 2,
                'question_text': 'テスト問題2',
                'choices': ['選択肢1', '選択肢2', '選択肢3', '選択肢4'],
                'correct_answer': 2,
                'explanation': 'テスト解説2',
                'category': 'マネジメント系'
            }
        ],
        'study_sessions': [
            {
                'id': 1,
                'session_name': 'テストセッション1',
                'exam_type': 'FE',
                'total_questions': 10,
                'correct_answers': 8,
                'created_at': '2025-08-08 10:00:00'
            }
        ],
        'learning_records': [
            {
                'id': 1,
                'question_id': 1,
                'user_answer': 1,
                'is_correct': True,
                'attempt_date': '2025-08-08 10:00:00'
            },
            {
                'id': 2,
                'question_id': 2,
                'user_answer': 3,
                'is_correct': False,
                'attempt_date': '2025-08-08 10:01:00'
            }
        ]
    }


# Playwrightマーカー
def pytest_configure(config):
    """pytest設定"""
    config.addinivalue_line(
        "markers", "e2e: E2Eテスト（Playwright使用）"
    )
    config.addinivalue_line(
        "markers", "integration: 統合テスト"
    )
    config.addinivalue_line(
        "markers", "unit: 単体テスト"
    )
    config.addinivalue_line(
        "markers", "slow: 実行に時間がかかるテスト"
    )