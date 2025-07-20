"""
情報技術者試験学習システム - 学習進捗管理モジュール
"""

import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .config import config
from .database import DatabaseManager
from ..utils.utils import Logger, DataUtils, StatisticsUtils

class StudyMode(Enum):
    """学習モード"""
    PRACTICE = "practice"
    MOCK_EXAM = "mock_exam"
    REVIEW = "review"
    WEAK_AREA = "weak_area"

@dataclass
class StudyResult:
    """学習結果データクラス"""
    question_id: int
    user_answer: int
    correct_answer: int
    is_correct: bool
    response_time: int
    category: str
    difficulty_level: int

@dataclass
class SessionSummary:
    """セッション概要データクラス"""
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    correct_rate: float
    average_response_time: float
    total_time: int
    categories_studied: List[str]
    weak_areas: List[str]
    achievements: List[str]

class ProgressTracker:
    """学習進捗追跡クラス"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        """
        初期化
        
        Args:
            db_manager: データベースマネージャー
        """
        self.db = db_manager or DatabaseManager()
        
        # ログ設定
        self.logger = Logger.setup_logger(
            "ProgressTracker",
            config.LOG_FILE,
            config.LOG_LEVEL
        )
        
        # 現在のセッション情報
        self.current_session_id = None
        self.current_session_results = []
        self.session_start_time = None
    
    def start_study_session(self, session_name: str, exam_type: str = "FE",
                           study_mode: StudyMode = StudyMode.PRACTICE,
                           target_questions: int = 20) -> int:
        """
        学習セッションを開始
        
        Args:
            session_name: セッション名
            exam_type: 試験種別
            study_mode: 学習モード
            target_questions: 目標問題数
            
        Returns:
            int: セッションID
        """
        self.logger.info(f"学習セッション開始: {session_name}")
        
        # 前のセッションが残っている場合は終了
        if self.current_session_id:
            self.end_study_session()
        
        # 新しいセッションを作成
        self.current_session_id = self.db.create_study_session(
            session_name=session_name,
            exam_type=exam_type,
            study_mode=study_mode.value,
            total_questions=target_questions
        )
        
        self.current_session_results = []
        self.session_start_time = datetime.now()
        
        self.logger.info(f"セッションID: {self.current_session_id}")
        return self.current_session_id
    
    def record_answer(self, question_id: int, user_answer: int, correct_answer: int,
                     response_time: int = None, notes: str = None) -> StudyResult:
        """
        回答を記録
        
        Args:
            question_id: 問題ID
            user_answer: ユーザーの回答
            correct_answer: 正解
            response_time: 回答時間（秒）
            notes: メモ
            
        Returns:
            StudyResult: 学習結果
        """
        is_correct = user_answer == correct_answer
        
        # データベースに記録
        self.db.record_answer(
            question_id=question_id,
            user_answer=user_answer,
            is_correct=is_correct,
            response_time=response_time,
            study_mode=self._get_current_study_mode(),
            notes=notes
        )
        
        # 問題情報を取得
        question = self.db.get_question(question_id)
        if not question:
            raise ValueError(f"問題が見つかりません: {question_id}")
        
        # 学習結果を作成
        result = StudyResult(
            question_id=question_id,
            user_answer=user_answer,
            correct_answer=correct_answer,
            is_correct=is_correct,
            response_time=response_time or 0,
            category=question.get('category', ''),
            difficulty_level=question.get('difficulty_level', 2)
        )
        
        # セッション結果に追加
        if self.current_session_id:
            self.current_session_results.append(result)
        
        self.logger.info(f"回答記録: Q{question_id} - {'正解' if is_correct else '不正解'}")
        
        return result
    
    def end_study_session(self) -> SessionSummary:
        """
        学習セッションを終了
        
        Returns:
            SessionSummary: セッション概要
        """
        if not self.current_session_id:
            raise ValueError("アクティブなセッションがありません")
        
        self.logger.info(f"学習セッション終了: {self.current_session_id}")
        
        # セッション統計を計算
        summary = self._calculate_session_summary()
        
        # データベースを更新
        self.db.end_study_session(
            session_id=self.current_session_id,
            correct_answers=summary.correct_answers
        )
        
        # セッション情報をクリア
        self.current_session_id = None
        self.current_session_results = []
        self.session_start_time = None
        
        return summary
    
    def _calculate_session_summary(self) -> SessionSummary:
        """セッション概要を計算"""
        results = self.current_session_results
        
        if not results:
            return SessionSummary(
                total_questions=0,
                correct_answers=0,
                incorrect_answers=0,
                correct_rate=0.0,
                average_response_time=0.0,
                total_time=0,
                categories_studied=[],
                weak_areas=[],
                achievements=[]
            )
        
        # 基本統計
        total_questions = len(results)
        correct_answers = sum(1 for r in results if r.is_correct)
        incorrect_answers = total_questions - correct_answers
        correct_rate = correct_answers / total_questions if total_questions > 0 else 0
        
        # 時間統計
        response_times = [r.response_time for r in results if r.response_time > 0]
        average_response_time = statistics.mean(response_times) if response_times else 0
        
        total_time = int((datetime.now() - self.session_start_time).total_seconds()) if self.session_start_time else 0
        
        # 分野統計
        categories_studied = list(set(r.category for r in results if r.category))
        
        # 弱点分野の特定
        weak_areas = self._identify_weak_areas_in_session(results)
        
        # 達成事項の特定
        achievements = self._identify_achievements(results, correct_rate)
        
        return SessionSummary(
            total_questions=total_questions,
            correct_answers=correct_answers,
            incorrect_answers=incorrect_answers,
            correct_rate=correct_rate,
            average_response_time=average_response_time,
            total_time=total_time,
            categories_studied=categories_studied,
            weak_areas=weak_areas,
            achievements=achievements
        )
    
    def _identify_weak_areas_in_session(self, results: List[StudyResult]) -> List[str]:
        """セッション内の弱点分野を特定"""
        category_stats = {}
        
        for result in results:
            category = result.category
            if category not in category_stats:
                category_stats[category] = {'correct': 0, 'total': 0}
            
            category_stats[category]['total'] += 1
            if result.is_correct:
                category_stats[category]['correct'] += 1
        
        # 正答率が低い分野を特定（60%未満）
        weak_areas = []
        for category, stats in category_stats.items():
            if stats['total'] >= 3:  # 最低3問以上
                correct_rate = stats['correct'] / stats['total']
                if correct_rate < 0.6:
                    weak_areas.append(category)
        
        return weak_areas
    
    def _identify_achievements(self, results: List[StudyResult], 
                             correct_rate: float) -> List[str]:
        """達成事項を特定"""
        achievements = []
        
        if not results:
            return achievements
        
        # 正答率による達成事項
        if correct_rate >= 0.9:
            achievements.append("🏆 優秀な成績")
        elif correct_rate >= 0.8:
            achievements.append("🥇 良好な成績")
        elif correct_rate >= 0.7:
            achievements.append("🥈 標準的な成績")
        
        # 連続正解による達成事項
        max_streak = self._calculate_max_streak(results)
        if max_streak >= 10:
            achievements.append(f"🔥 {max_streak}問連続正解")
        elif max_streak >= 5:
            achievements.append(f"✨ {max_streak}問連続正解")
        
        # 難易度別達成事項
        high_difficulty_correct = sum(1 for r in results 
                                    if r.difficulty_level >= 3 and r.is_correct)
        if high_difficulty_correct >= 3:
            achievements.append("💎 難問チャレンジ達成")
        
        # 時間効率による達成事項
        response_times = [r.response_time for r in results if r.response_time > 0]
        if response_times:
            avg_time = statistics.mean(response_times)
            if avg_time <= 30:  # 30秒以内
                achievements.append("⚡ 速答マスター")
        
        return achievements
    
    def _calculate_max_streak(self, results: List[StudyResult]) -> int:
        """最大連続正解数を計算"""
        if not results:
            return 0
        
        max_streak = 0
        current_streak = 0
        
        for result in results:
            if result.is_correct:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak
    
    def get_overall_progress(self, exam_type: str = None, 
                           days: int = 30) -> Dict[str, Any]:
        """
        全体的な学習進捗を取得
        
        Args:
            exam_type: 試験種別
            days: 対象日数
            
        Returns:
            Dict: 進捗情報
        """
        self.logger.info(f"進捗情報取得: {exam_type or 'all'}, {days}日間")
        
        # 基本統計
        statistics = self.db.get_statistics(exam_type)
        
        # 時系列進捗
        progress_data = self.db.get_progress_over_time(exam_type, days)
        
        # 弱点分野
        weak_areas = self.db.get_weak_areas(exam_type)
        
        # 全体サマリー
        total_questions = sum(stat['total_questions'] for stat in statistics)
        total_correct = sum(stat['correct_answers'] for stat in statistics)
        overall_rate = total_correct / total_questions if total_questions > 0 else 0
        
        # 学習記録
        recent_records = self.db.get_learning_records(
            start_date=datetime.now() - timedelta(days=days),
            limit=100
        )
        
        return {
            'overall_statistics': {
                'total_questions': total_questions,
                'total_correct': total_correct,
                'overall_correct_rate': overall_rate,
                'categories_studied': len(statistics)
            },
            'category_statistics': statistics,
            'progress_over_time': progress_data,
            'weak_areas': weak_areas,
            'recent_activity': recent_records[:10],  # 最新10件
            'recommendations': self._generate_recommendations(statistics, weak_areas)
        }
    
    def _generate_recommendations(self, statistics: List[Dict], 
                                weak_areas: List[Dict]) -> List[str]:
        """学習推奨事項を生成"""
        recommendations = []
        
        # 弱点分野の推奨
        if weak_areas:
            top_weak = weak_areas[0]
            recommendations.append(
                f"「{top_weak['category']}」の正答率が{top_weak['correct_rate']}%です。集中学習をお勧めします。"
            )
        
        # 学習量の推奨
        total_questions = sum(stat['total_questions'] for stat in statistics)
        if total_questions < 50:
            recommendations.append("まずは50問以上の学習を目標にしましょう。")
        elif total_questions < 100:
            recommendations.append("100問到達まであと少しです。継続学習を頑張りましょう。")
        
        # 正答率による推奨
        if statistics:
            avg_rate = sum(stat['correct_answers'] / stat['total_questions'] 
                         for stat in statistics if stat['total_questions'] > 0) / len(statistics)
            
            if avg_rate < 0.6:
                recommendations.append("基礎を固める学習に重点を置きましょう。")
            elif avg_rate < 0.8:
                recommendations.append("応用問題にもチャレンジしてみましょう。")
            else:
                recommendations.append("素晴らしい成績です！模擬試験に挑戦してみませんか？")
        
        # 学習継続の推奨
        recommendations.append("毎日少しずつでも継続学習を心がけましょう。")
        
        return recommendations
    
    def get_detailed_analysis(self, exam_type: str = None, 
                            category: str = None) -> Dict[str, Any]:
        """
        詳細分析結果を取得
        
        Args:
            exam_type: 試験種別
            category: 分野
            
        Returns:
            Dict: 詳細分析結果
        """
        self.logger.info(f"詳細分析: {exam_type}, {category}")
        
        # 学習記録を取得
        records = self.db.get_learning_records()
        
        if exam_type or category:
            # フィルタリング
            filtered_records = []
            for record in records:
                if exam_type and record['exam_name'] != exam_type:
                    continue
                if category and record['category'] != category:
                    continue
                filtered_records.append(record)
            records = filtered_records
        
        if not records:
            return {'error': 'データが見つかりません'}
        
        # 統計計算
        correct_count = sum(1 for r in records if r['is_correct'])
        total_count = len(records)
        correct_rate = correct_count / total_count
        
        # 時間統計
        response_times = [r['response_time'] for r in records if r['response_time']]
        time_stats = StatisticsUtils.calculate_statistics(response_times) if response_times else {}
        
        # 難易度別統計
        difficulty_stats = self._calculate_difficulty_stats(records)
        
        # 学習パターン分析
        learning_patterns = self._analyze_learning_patterns(records)
        
        # 成長傾向
        growth_trend = self._calculate_growth_trend(records)
        
        return {
            'basic_stats': {
                'total_questions': total_count,
                'correct_answers': correct_count,
                'correct_rate': correct_rate,
                'study_days': len(set(r['attempt_date'][:10] for r in records))
            },
            'time_statistics': time_stats,
            'difficulty_statistics': difficulty_stats,
            'learning_patterns': learning_patterns,
            'growth_trend': growth_trend,
            'performance_prediction': self._predict_performance(records)
        }
    
    def _calculate_difficulty_stats(self, records: List[Dict]) -> Dict[str, Any]:
        """難易度別統計を計算"""
        difficulty_stats = {}
        
        for record in records:
            # 問題情報を取得（簡略化のため、ここでは仮の難易度を使用）
            difficulty = 2  # デフォルト難易度
            
            if difficulty not in difficulty_stats:
                difficulty_stats[difficulty] = {'correct': 0, 'total': 0}
            
            difficulty_stats[difficulty]['total'] += 1
            if record['is_correct']:
                difficulty_stats[difficulty]['correct'] += 1
        
        # 正答率を計算
        for difficulty, stats in difficulty_stats.items():
            stats['correct_rate'] = stats['correct'] / stats['total']
        
        return difficulty_stats
    
    def _analyze_learning_patterns(self, records: List[Dict]) -> Dict[str, Any]:
        """学習パターンを分析"""
        # 曜日別学習パターン
        weekday_stats = {}
        # 時間帯別学習パターン
        hour_stats = {}
        
        for record in records:
            attempt_date = datetime.fromisoformat(record['attempt_date'])
            
            # 曜日
            weekday = attempt_date.strftime('%A')
            if weekday not in weekday_stats:
                weekday_stats[weekday] = {'correct': 0, 'total': 0}
            weekday_stats[weekday]['total'] += 1
            if record['is_correct']:
                weekday_stats[weekday]['correct'] += 1
            
            # 時間帯
            hour = attempt_date.hour
            if hour not in hour_stats:
                hour_stats[hour] = {'correct': 0, 'total': 0}
            hour_stats[hour]['total'] += 1
            if record['is_correct']:
                hour_stats[hour]['correct'] += 1
        
        # 最適な学習時間帯を特定
        best_hours = []
        for hour, stats in hour_stats.items():
            if stats['total'] >= 3:  # 最低3問以上
                rate = stats['correct'] / stats['total']
                if rate >= 0.8:
                    best_hours.append(hour)
        
        return {
            'weekday_performance': weekday_stats,
            'hourly_performance': hour_stats,
            'best_study_hours': best_hours
        }
    
    def _calculate_growth_trend(self, records: List[Dict]) -> Dict[str, Any]:
        """成長傾向を計算"""
        if len(records) < 10:
            return {'trend': 'insufficient_data'}
        
        # 日付順にソート
        sorted_records = sorted(records, key=lambda r: r['attempt_date'])
        
        # 週別正答率を計算
        weekly_rates = []
        current_week = []
        current_week_start = None
        
        for record in sorted_records:
            attempt_date = datetime.fromisoformat(record['attempt_date'])
            
            if current_week_start is None:
                current_week_start = attempt_date
            
            # 週が変わった場合
            if (attempt_date - current_week_start).days >= 7:
                if current_week:
                    week_rate = sum(1 for r in current_week if r['is_correct']) / len(current_week)
                    weekly_rates.append(week_rate)
                
                current_week = [record]
                current_week_start = attempt_date
            else:
                current_week.append(record)
        
        # 最後の週を追加
        if current_week:
            week_rate = sum(1 for r in current_week if r['is_correct']) / len(current_week)
            weekly_rates.append(week_rate)
        
        # 傾向を計算
        if len(weekly_rates) >= 2:
            # 線形回帰による傾向計算（簡略化）
            x = list(range(len(weekly_rates)))
            y = weekly_rates
            
            # 傾きを計算
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(xi * xi for xi in x)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            
            if slope > 0.02:
                trend = 'improving'
            elif slope < -0.02:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'
        
        return {
            'trend': trend,
            'weekly_rates': weekly_rates,
            'slope': slope if 'slope' in locals() else 0
        }
    
    def _predict_performance(self, records: List[Dict]) -> Dict[str, Any]:
        """パフォーマンス予測"""
        if len(records) < 20:
            return {'prediction': 'insufficient_data'}
        
        # 最近のパフォーマンス（直近20問）
        recent_records = records[-20:]
        recent_rate = sum(1 for r in recent_records if r['is_correct']) / len(recent_records)
        
        # 全体パフォーマンス
        overall_rate = sum(1 for r in records if r['is_correct']) / len(records)
        
        # 予測スコア（合格可能性）
        if recent_rate >= 0.6:
            if overall_rate >= 0.6:
                prediction = 'high_pass_probability'
            else:
                prediction = 'improving_trend'
        else:
            prediction = 'needs_improvement'
        
        return {
            'prediction': prediction,
            'recent_performance': recent_rate,
            'overall_performance': overall_rate,
            'estimated_pass_rate': min(recent_rate * 1.2, 1.0)  # 楽観的予測
        }
    
    def _get_current_study_mode(self) -> str:
        """現在の学習モードを取得"""
        # 簡略化のため、デフォルトを返す
        return StudyMode.PRACTICE.value
    
    def export_progress_data(self, format: str = 'json') -> str:
        """
        進捗データをエクスポート
        
        Args:
            format: エクスポート形式 ('json', 'csv')
            
        Returns:
            str: エクスポートされたデータ
        """
        progress_data = self.get_overall_progress()
        
        if format == 'json':
            import json
            return json.dumps(progress_data, ensure_ascii=False, indent=2)
        elif format == 'csv':
            # CSV形式での出力（簡略化）
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # ヘッダー
            writer.writerow(['Category', 'Total Questions', 'Correct Rate'])
            
            # データ
            for stat in progress_data['category_statistics']:
                writer.writerow([
                    stat['category'],
                    stat['total_questions'],
                    f"{stat['correct_rate']:.1f}%"
                ])
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def get_study_recommendations(self, exam_type: str = "FE") -> List[Dict]:
        """
        学習推奨事項を取得
        
        Args:
            exam_type: 試験種別
            
        Returns:
            List[Dict]: 推奨事項リスト
        """
        recommendations = []
        
        # 弱点分野の推奨
        weak_areas = self.db.get_weak_areas(exam_type, limit=3)
        
        for area in weak_areas:
            recommendations.append({
                'type': 'weak_area',
                'priority': 'high',
                'title': f"「{area['category']}」の強化学習",
                'description': f"正答率{area['correct_rate']}%の分野です。重点的に学習しましょう。",
                'action': f"category:{area['category']}"
            })
        
        # 学習量の推奨
        statistics = self.db.get_statistics(exam_type)
        total_questions = sum(stat['total_questions'] for stat in statistics)
        
        if total_questions < 100:
            recommendations.append({
                'type': 'volume',
                'priority': 'medium',
                'title': '学習量の増加',
                'description': f'現在{total_questions}問を学習済み。100問を目標にしましょう。',
                'action': 'increase_volume'
            })
        
        # 難易度の推奨
        avg_rate = sum(stat['correct_answers'] / stat['total_questions'] 
                      for stat in statistics if stat['total_questions'] > 0) / len(statistics) if statistics else 0
        
        if avg_rate >= 0.8:
            recommendations.append({
                'type': 'difficulty',
                'priority': 'low',
                'title': '模擬試験への挑戦',
                'description': '高い正答率を維持しています。模擬試験に挑戦してみましょう。',
                'action': 'mock_exam'
            })
        
        return recommendations