"""
最適化されたデータベース操作
"""

import logging
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from .database import DatabaseManager
from ..web.utils.db_utils import DatabaseUtils, QueryBuilder, DatabaseCache
from ..web.utils.error_handler import DatabaseError

logger = logging.getLogger(__name__)

class OptimizedDatabaseManager(DatabaseManager):
    """最適化されたデータベース管理クラス"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = DatabaseCache(max_size=200)
        self.query_builder = QueryBuilder()
        
    @DatabaseUtils.with_error_handling
    def get_questions_optimized(self, exam_type: str = None, category: str = None, 
                               difficulty: str = None, limit: int = 50, 
                               page: int = 1) -> Dict[str, Any]:
        """最適化された問題取得"""
        cache_key = f"questions_{exam_type}_{category}_{difficulty}_{limit}_{page}"
        
        def query_func():
            builder = QueryBuilder()
            builder.select("""
                q.id, q.question_text, q.choices, q.correct_answer, 
                q.explanation, q.category, q.difficulty, q.tags,
                ec.name as exam_name, ec.code as exam_code
            """).from_table("questions q").from_table("""
                JOIN exam_categories ec ON q.exam_category_id = ec.id
            """)
            
            if exam_type:
                builder.where("ec.code = ?", exam_type)
            if category:
                builder.and_where("q.category = ?", category)
            if difficulty:
                builder.and_where("q.difficulty = ?", difficulty)
            
            builder.order_by("q.id", "ASC")
            
            # ページネーション計算
            offset = (page - 1) * limit
            builder.limit(limit)
            if offset > 0:
                # SQLiteではOFFSETはLIMITと組み合わせて使用
                query, params = builder.build()
                query += f" OFFSET {offset}"
            else:
                query, params = builder.build()
            
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                questions = [dict(row) for row in cursor.fetchall()]
                
                # choicesをJSONから変換
                for question in questions:
                    if question.get('choices'):
                        import json
                        question['choices'] = json.loads(question['choices'])
                
                return DatabaseUtils.paginate_results(questions, page, limit)
        
        return self.cache.cached_query(cache_key, query_func)
    
    @DatabaseUtils.with_error_handling
    def get_random_questions_optimized(self, exam_type: str, count: int = 10, 
                                     categories: List[str] = None,
                                     exclude_ids: List[int] = None) -> List[Dict]:
        """最適化されたランダム問題取得"""
        cache_key = f"random_{exam_type}_{count}_{hash(str(categories))}_{hash(str(exclude_ids))}"
        
        def query_func():
            builder = QueryBuilder()
            builder.select("""
                q.id, q.question_text, q.choices, q.correct_answer,
                q.explanation, q.category, q.difficulty,
                ec.name as exam_name
            """).from_table("questions q").from_table("""
                JOIN exam_categories ec ON q.exam_category_id = ec.id
            """).where("ec.code = ?", exam_type)
            
            if categories:
                placeholders = ",".join("?" * len(categories))
                builder.and_where(f"q.category IN ({placeholders})", *categories)
            
            if exclude_ids:
                placeholders = ",".join("?" * len(exclude_ids))
                builder.and_where(f"q.id NOT IN ({placeholders})", *exclude_ids)
            
            builder.order_by("RANDOM()", "").limit(count)
            
            query, params = builder.build()
            
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                questions = [dict(row) for row in cursor.fetchall()]
                
                # choicesをJSONから変換
                for question in questions:
                    if question.get('choices'):
                        import json
                        question['choices'] = json.loads(question['choices'])
                
                return questions
        
        return self.cache.cached_query(cache_key, query_func)
    
    @DatabaseUtils.with_transaction(self)
    def batch_record_answers(self, conn, answers: List[Dict]) -> List[int]:
        """バッチで回答を記録"""
        record_ids = []
        
        for answer_data in answers:
            cursor = conn.execute("""
                INSERT INTO learning_records (
                    question_id, user_answer, is_correct, response_time,
                    study_mode, notes, session_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                answer_data['question_id'],
                answer_data['user_answer'],
                answer_data['is_correct'],
                answer_data.get('response_time'),
                answer_data.get('study_mode', 'practice'),
                answer_data.get('notes'),
                answer_data.get('session_id')
            ))
            
            record_ids.append(cursor.lastrowid)
        
        # 統計の一括更新
        self._batch_update_statistics(conn, answers)
        
        return record_ids
    
    def _batch_update_statistics(self, conn, answers: List[Dict]):
        """統計の一括更新"""
        # 問題IDごとにグループ化
        question_stats = {}
        
        for answer in answers:
            qid = answer['question_id']
            if qid not in question_stats:
                question_stats[qid] = {'correct': 0, 'total': 0, 'total_time': 0}
            
            question_stats[qid]['total'] += 1
            if answer['is_correct']:
                question_stats[qid]['correct'] += 1
            if answer.get('response_time'):
                question_stats[qid]['total_time'] += answer['response_time']
        
        # 統計テーブルを一括更新
        for question_id, stats in question_stats.items():
            accuracy = (stats['correct'] / stats['total']) * 100
            avg_time = stats['total_time'] / stats['total'] if stats['total'] > 0 else 0
            
            conn.execute("""
                INSERT OR REPLACE INTO question_statistics 
                (question_id, total_attempts, correct_attempts, accuracy_rate, average_response_time)
                VALUES (?, 
                    COALESCE((SELECT total_attempts FROM question_statistics WHERE question_id = ?), 0) + ?,
                    COALESCE((SELECT correct_attempts FROM question_statistics WHERE question_id = ?), 0) + ?,
                    ?,
                    ?
                )
            """, (question_id, question_id, stats['total'], question_id, stats['correct'], accuracy, avg_time))
    
    @DatabaseUtils.with_error_handling
    def get_learning_progress_optimized(self, exam_type: str = None, 
                                       days: int = 30) -> Dict[str, Any]:
        """最適化された学習進捗取得"""
        cache_key = f"progress_{exam_type}_{days}"
        
        def query_func():
            from datetime import datetime, timedelta
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            builder = QueryBuilder()
            builder.select("""
                DATE(lr.attempt_date) as date,
                COUNT(*) as total_questions,
                SUM(CASE WHEN lr.is_correct THEN 1 ELSE 0 END) as correct_answers,
                AVG(lr.response_time) as avg_response_time,
                ec.code as exam_type
            """).from_table("learning_records lr").from_table("""
                JOIN questions q ON lr.question_id = q.id
                JOIN exam_categories ec ON q.exam_category_id = ec.id
            """).where("lr.attempt_date >= ?", start_date).and_where("lr.attempt_date <= ?", end_date)
            
            if exam_type:
                builder.and_where("ec.code = ?", exam_type)
            
            query, params = builder.build()
            query += " GROUP BY DATE(lr.attempt_date), ec.code ORDER BY date DESC"
            
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                results = [dict(row) for row in cursor.fetchall()]
                
                # 日付ごとの集計データを生成
                daily_stats = {}
                for row in results:
                    date = row['date']
                    if date not in daily_stats:
                        daily_stats[date] = {
                            'total_questions': 0,
                            'correct_answers': 0,
                            'accuracy': 0,
                            'avg_response_time': 0
                        }
                    
                    daily_stats[date]['total_questions'] += row['total_questions']
                    daily_stats[date]['correct_answers'] += row['correct_answers']
                    
                    if daily_stats[date]['total_questions'] > 0:
                        daily_stats[date]['accuracy'] = (
                            daily_stats[date]['correct_answers'] / 
                            daily_stats[date]['total_questions']
                        ) * 100
                
                return {
                    'daily_stats': daily_stats,
                    'raw_data': results,
                    'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()}
                }
        
        return self.cache.cached_query(cache_key, query_func)
    
    def clear_cache(self, pattern: str = None):
        """キャッシュをクリア"""
        if pattern:
            # パターンマッチングは後で実装
            self.cache.clear()
        else:
            self.cache.clear()
        
        logger.info("データベースキャッシュをクリアしました")
    
    @DatabaseUtils.with_error_handling
    def get_weak_areas_optimized(self, exam_type: str, limit: int = 10) -> List[Dict]:
        """最適化された弱点分野取得"""
        cache_key = f"weak_areas_{exam_type}_{limit}"
        
        def query_func():
            builder = QueryBuilder()
            builder.select("""
                q.category,
                COUNT(*) as total_attempts,
                SUM(CASE WHEN lr.is_correct THEN 1 ELSE 0 END) as correct_attempts,
                (SUM(CASE WHEN lr.is_correct THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as accuracy_rate,
                AVG(lr.response_time) as avg_response_time
            """).from_table("learning_records lr").from_table("""
                JOIN questions q ON lr.question_id = q.id
                JOIN exam_categories ec ON q.exam_category_id = ec.id
            """).where("ec.code = ?", exam_type)
            
            query, params = builder.build()
            query += " GROUP BY q.category HAVING total_attempts >= 3 ORDER BY accuracy_rate ASC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        
        return self.cache.cached_query(cache_key, query_func)