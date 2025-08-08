"""
学習セッション管理サービス
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from flask import session

from ...core.database import DatabaseManager
from ...core.progress_tracker import StudyMode
from ...core.config import config

logger = logging.getLogger(__name__)

class SessionService:
    """学習セッション管理サービス"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def start_study_session(self, exam_type: str, mode: str, count: int, category: Optional[str] = None) -> int:
        """学習セッション開始"""
        # 学習モードの設定
        study_mode = StudyMode.PRACTICE
        if mode == "mock_exam":
            study_mode = StudyMode.MOCK_EXAM
            count = 80
        elif mode == "review":
            study_mode = StudyMode.REVIEW
        elif mode == "weak_area":
            study_mode = StudyMode.WEAK_AREA
        
        # セッション名を生成
        session_name = f"{exam_type}_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # セッション開始
        session_id = self.db.create_study_session(
            session_name=session_name,
            exam_type=exam_type,
            study_mode=mode,
            total_questions=count
        )
        
        # 問題を取得
        if mode == "weak_area":
            questions = self._get_weak_area_questions(exam_type, count)
        else:
            questions = self.db.get_random_questions(exam_type, category, count)
        
        if not questions:
            # デモ用問題を生成
            questions = self._generate_demo_questions(exam_type, count)
        
        # セッション情報を保存
        session['session_id'] = session_id
        session['questions'] = questions
        session['current_question'] = 0
        session['answers'] = []
        session['start_time'] = datetime.now().isoformat()
        
        logger.info(f"学習セッション開始: {session_name}")
        return session_id
    
    def process_answer(self, user_answer: int) -> Dict:
        """回答処理"""
        questions = session['questions']
        current_idx = session['current_question']
        current_question = questions[current_idx]
        
        # 回答を記録
        correct_answer = current_question.get('correct_answer', 1)
        is_correct = user_answer == correct_answer
        
        # データベースに記録（問題IDがない場合は0を使用）
        question_id = current_question.get('id', 0)
        if question_id > 0:
            self.db.record_answer(
                question_id=question_id,
                user_answer=user_answer,
                is_correct=is_correct,
                study_mode='practice'
            )
        
        # セッション情報を更新
        session['answers'].append({
            'question_id': question_id,
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct
        })
        
        session['current_question'] = current_idx + 1
        
        # 結果を返す
        return {
            'is_correct': is_correct,
            'correct_answer': correct_answer,
            'explanation': current_question.get('explanation', ''),
            'is_last_question': current_idx + 1 >= len(questions)
        }
    
    def calculate_session_result(self) -> Dict:
        """セッション結果を計算"""
        answers = session['answers']
        total_questions = len(answers)
        correct_count = sum(1 for ans in answers if ans['is_correct'])
        
        duration = self._calculate_session_duration()
        
        summary = {
            'total_questions': total_questions,
            'correct_answers': correct_count,
            'incorrect_answers': total_questions - correct_count,
            'correct_rate': (correct_count / total_questions) if total_questions > 0 else 0,
            'session_name': f"学習セッション_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'total_time': duration,
            'average_response_time': duration / total_questions if total_questions > 0 else 0
        }
        
        # セッション終了をデータベースに記録
        session_id = session.get('session_id')
        if session_id:
            self.db.end_study_session(session_id, correct_count)
        
        return summary
    
    def clear_session(self):
        """セッション情報をクリア"""
        session.pop('session_id', None)
        session.pop('questions', None)
        session.pop('current_question', None)
        session.pop('answers', None)
        session.pop('start_time', None)
    
    def _calculate_session_duration(self) -> int:
        """セッション時間を計算"""
        start_time_str = session.get('start_time')
        if not start_time_str:
            return 0
        
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds())
        return duration
    
    def _get_weak_area_questions(self, exam_type: str, count: int) -> List[Dict]:
        """弱点分野の問題を取得"""
        weak_areas = self.db.get_weak_areas(exam_type, limit=3)
        if not weak_areas:
            return self.db.get_random_questions(exam_type, None, count)
        
        questions = []
        questions_per_area = count // len(weak_areas)
        
        for area in weak_areas:
            area_questions = self.db.get_random_questions(
                exam_type, area['category'], questions_per_area
            )
            questions.extend(area_questions)
        
        # 不足分を補う
        remaining = count - len(questions)
        if remaining > 0:
            additional = self.db.get_random_questions(exam_type, None, remaining)
            questions.extend(additional)
        
        return questions[:count]
    
    def _generate_demo_questions(self, exam_type: str, count: int) -> List[Dict]:
        """デモ用問題を生成"""
        demo_questions = []
        
        for i in range(count):
            question = {
                'id': i + 1,
                'exam_type': exam_type,
                'year': 2024,
                'question_number': i + 1,
                'question_text': f"問題{i + 1}: {exam_type}に関する基本的な問題です。",
                'choices': [
                    f"選択肢{i + 1}-1",
                    f"選択肢{i + 1}-2", 
                    f"選択肢{i + 1}-3",
                    f"選択肢{i + 1}-4"
                ],
                'correct_answer': (i % 4) + 1,
                'explanation': f"問題{i + 1}の解説です。",
                'category': 'テクノロジ系',
                'subcategory': 'システム構成要素',
                'difficulty_level': 2
            }
            demo_questions.append(question)
        
        return demo_questions