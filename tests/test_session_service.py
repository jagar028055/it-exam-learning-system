"""
SessionService の単体テスト
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.web.services.session_service import SessionService
from src.core.database import DatabaseManager
from src.core.progress_tracker import StudyMode


class TestSessionService:
    """SessionServiceのテストクラス"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """モックDBマネージャーを提供"""
        return MagicMock(spec=DatabaseManager)
    
    @pytest.fixture
    def session_service(self, mock_db_manager):
        """テスト用SessionServiceインスタンスを提供"""
        return SessionService(mock_db_manager)
    
    @pytest.fixture
    def sample_questions(self):
        """サンプル問題データ"""
        return [
            {
                'id': 1,
                'question_text': 'サンプル問題1',
                'choices': ['選択肢1', '選択肢2', '選択肢3', '選択肢4'],
                'correct_answer': 1,
                'explanation': 'サンプル解説1'
            },
            {
                'id': 2,
                'question_text': 'サンプル問題2',
                'choices': ['選択肢1', '選択肢2', '選択肢3', '選択肢4'],
                'correct_answer': 2,
                'explanation': 'サンプル解説2'
            }
        ]
    
    @patch('src.web.services.session_service.session', {})
    def test_start_study_session_practice_mode(self, session_service, mock_db_manager, sample_questions):
        """学習セッション開始（練習モード）のテスト"""
        # モックの設定
        mock_db_manager.create_study_session.return_value = 1
        mock_db_manager.get_random_questions.return_value = sample_questions
        
        with patch('src.web.services.session_service.session', {}) as mock_session:
            session_id = session_service.start_study_session('FE', 'practice', 10)
            
            # セッションIDが返されることを確認
            assert session_id == 1
            
            # DBマネージャーのメソッドが正しく呼ばれたかチェック
            mock_db_manager.create_study_session.assert_called_once()
            mock_db_manager.get_random_questions.assert_called_once_with('FE', None, 10)
            
            # セッション情報が正しく設定されているかチェック
            assert mock_session['session_id'] == 1
            assert len(mock_session['questions']) == 2
            assert mock_session['current_question'] == 0
            assert mock_session['answers'] == []
    
    @patch('src.web.services.session_service.session', {})
    def test_start_study_session_mock_exam_mode(self, session_service, mock_db_manager, sample_questions):
        """学習セッション開始（模擬試験モード）のテスト"""
        # モックの設定
        mock_db_manager.create_study_session.return_value = 2
        mock_db_manager.get_random_questions.return_value = sample_questions
        
        with patch('src.web.services.session_service.session', {}) as mock_session:
            session_id = session_service.start_study_session('FE', 'mock_exam', 10)
            
            # 模擬試験では問題数が80に強制されることを確認
            create_call = mock_db_manager.create_study_session.call_args
            assert create_call[1]['total_questions'] == 80
            
            # ランダム問題取得では80問分が要求されることを確認
            mock_db_manager.get_random_questions.assert_called_once_with('FE', None, 80)
    
    @patch('src.web.services.session_service.session', {})
    def test_start_study_session_no_questions_generates_demo(self, session_service, mock_db_manager):
        """問題が取得できない場合のデモ問題生成テスト"""
        # モックの設定：問題が見つからない
        mock_db_manager.create_study_session.return_value = 3
        mock_db_manager.get_random_questions.return_value = []
        
        with patch('src.web.services.session_service.session', {}) as mock_session:
            session_id = session_service.start_study_session('FE', 'practice', 5)
            
            # デモ問題が生成されることを確認
            questions = mock_session['questions']
            assert len(questions) == 5
            
            # デモ問題の構造を確認
            for i, question in enumerate(questions):
                assert question['id'] == i + 1
                assert question['exam_type'] == 'FE'
                assert len(question['choices']) == 4
                assert 1 <= question['correct_answer'] <= 4
    
    def test_process_answer_correct(self, session_service, mock_db_manager):
        """正解処理のテスト"""
        # セッション状態をモック
        test_questions = [
            {
                'id': 1,
                'correct_answer': 2,
                'explanation': 'テスト解説'
            }
        ]
        
        with patch('src.web.services.session_service.session', {
            'questions': test_questions,
            'current_question': 0,
            'answers': []
        }) as mock_session:
            result = session_service.process_answer(2)  # 正解を入力
            
            # 結果の確認
            assert result['is_correct'] is True
            assert result['correct_answer'] == 2
            assert result['explanation'] == 'テスト解説'
            assert result['is_last_question'] is True
            
            # 回答記録の確認
            mock_db_manager.record_answer.assert_called_once_with(
                question_id=1,
                user_answer=2,
                is_correct=True,
                study_mode='practice'
            )
            
            # セッション更新の確認
            assert len(mock_session['answers']) == 1
            assert mock_session['current_question'] == 1
            assert mock_session['answers'][0]['is_correct'] is True
    
    def test_process_answer_incorrect(self, session_service, mock_db_manager):
        """不正解処理のテスト"""
        test_questions = [
            {
                'id': 1,
                'correct_answer': 2,
                'explanation': 'テスト解説'
            }
        ]
        
        with patch('src.web.services.session_service.session', {
            'questions': test_questions,
            'current_question': 0,
            'answers': []
        }) as mock_session:
            result = session_service.process_answer(1)  # 不正解を入力
            
            # 結果の確認
            assert result['is_correct'] is False
            assert result['correct_answer'] == 2
            
            # 回答記録の確認
            mock_db_manager.record_answer.assert_called_once_with(
                question_id=1,
                user_answer=1,
                is_correct=False,
                study_mode='practice'
            )
    
    def test_calculate_session_result(self, session_service, mock_db_manager):
        """セッション結果計算のテスト"""
        # セッション状態をモック
        test_answers = [
            {'is_correct': True},
            {'is_correct': False},
            {'is_correct': True},
            {'is_correct': True}
        ]
        
        start_time = datetime.now().isoformat()
        
        with patch('src.web.services.session_service.session', {
            'session_id': 1,
            'answers': test_answers,
            'start_time': start_time
        }):
            result = session_service.calculate_session_result()
            
            # 結果の確認
            assert result['total_questions'] == 4
            assert result['correct_answers'] == 3
            assert result['incorrect_answers'] == 1
            assert result['correct_rate'] == 0.75
            assert 'session_name' in result
            assert 'total_time' in result
            
            # セッション終了記録の確認
            mock_db_manager.end_study_session.assert_called_once_with(1, 3)
    
    def test_clear_session(self, session_service):
        """セッション情報クリアのテスト"""
        with patch('src.web.services.session_service.session', {
            'session_id': 1,
            'questions': [],
            'current_question': 0,
            'answers': [],
            'start_time': datetime.now().isoformat()
        }) as mock_session:
            session_service.clear_session()
            
            # すべてのセッション情報がクリアされることを確認
            expected_keys = ['session_id', 'questions', 'current_question', 'answers', 'start_time']
            for key in expected_keys:
                assert key not in mock_session
    
    def test_get_weak_area_questions(self, session_service, mock_db_manager):
        """弱点分野問題取得のテスト"""
        # 弱点分野データをモック
        mock_db_manager.get_weak_areas.return_value = [
            {'category': 'ネットワーク'},
            {'category': 'データベース'}
        ]
        
        # 各分野からの問題をモック
        mock_db_manager.get_random_questions.side_effect = [
            [{'id': 1, 'category': 'ネットワーク'}],
            [{'id': 2, 'category': 'データベース'}]
        ]
        
        questions = session_service._get_weak_area_questions('FE', 4)
        
        # 弱点分野取得の確認
        mock_db_manager.get_weak_areas.assert_called_once_with('FE', limit=3)
        
        # 問題取得呼び出しの確認
        assert mock_db_manager.get_random_questions.call_count == 2
        
        # 結果の確認
        assert len(questions) == 2