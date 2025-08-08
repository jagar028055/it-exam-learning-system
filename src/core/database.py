"""
情報技術者試験学習システム - データベース管理モジュール
"""

import sqlite3
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from contextlib import contextmanager

from .config import config
from .cache_manager import cached_service, cache_manager
from ..utils.utils import Logger, FileUtils, ValidationUtils, DataError

class DatabaseManager:
    """SQLiteデータベース管理クラス"""
    
    def __init__(self, db_path: Path = None):
        """
        初期化
        
        Args:
            db_path: データベースファイルパス
        """
        # 環境変数からデータベースパスを取得
        env_db_path = os.environ.get('DATABASE_PATH')
        if env_db_path:
            self.db_path = Path(env_db_path)
        else:
            self.db_path = db_path or config.DATABASE_PATH
            
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # ログ設定
        self.logger = Logger.setup_logger(
            "DatabaseManager",
            config.LOG_FILE,
            config.LOG_LEVEL
        )
        
        # データベース初期化
        self.init_database()
    
    def init_database(self):
        """データベースを初期化"""
        self.logger.info("データベースを初期化中...")
        
        with self.get_connection() as conn:
            # テーブル作成
            self._create_tables(conn)
            
            # 初期データ投入
            self._insert_initial_data(conn)
            
            # インデックス作成
            self._create_indexes(conn)
            
        self.logger.info("データベース初期化完了")
    
    @contextmanager
    def get_connection(self):
        """データベース接続のコンテキストマネージャー"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,  # タイムアウト設定
            check_same_thread=False  # 本番環境対応
        )
        conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能
        
        # 本番環境用最適化設定
        if os.environ.get('FLASK_ENV') == 'production':
            conn.execute('PRAGMA journal_mode=WAL')  # WALモード
            conn.execute('PRAGMA synchronous=NORMAL')  # 同期設定
            conn.execute('PRAGMA cache_size=10000')  # キャッシュサイズ
            conn.execute('PRAGMA temp_store=MEMORY')  # 一時ストレージ
        
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            self.logger.error(f"データベースエラー: {e}")
            raise
        finally:
            conn.close()
    
    def _create_tables(self, conn: sqlite3.Connection):
        """テーブルを作成"""
        # 試験区分テーブル
        conn.execute("""
            CREATE TABLE IF NOT EXISTS exam_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                code VARCHAR(10) NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 問題テーブル
        conn.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_category_id INTEGER,
                year INTEGER NOT NULL,
                question_number INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                choices TEXT NOT NULL,  -- JSON形式で保存
                correct_answer INTEGER,
                explanation TEXT,
                category VARCHAR(100),
                subcategory VARCHAR(100),
                difficulty_level INTEGER DEFAULT 2,
                source_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exam_category_id) REFERENCES exam_categories(id),
                UNIQUE(exam_category_id, year, question_number)
            )
        """)
        
        # 学習記録テーブル
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER,
                user_answer INTEGER,
                is_correct BOOLEAN NOT NULL,
                attempt_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_time INTEGER,  -- 秒単位
                study_mode VARCHAR(50),  -- 'practice', 'mock_exam', 'review'
                notes TEXT,
                FOREIGN KEY (question_id) REFERENCES questions(id)
            )
        """)
        
        # 学習セッションテーブル
        conn.execute("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name VARCHAR(200),
                exam_category_id INTEGER,
                study_mode VARCHAR(50),
                total_questions INTEGER,
                correct_answers INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration INTEGER,  -- 秒単位
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exam_category_id) REFERENCES exam_categories(id)
            )
        """)
        
        # 学習統計テーブル
        conn.execute("""
            CREATE TABLE IF NOT EXISTS study_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_category_id INTEGER,
                category VARCHAR(100),
                total_questions INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                incorrect_answers INTEGER DEFAULT 0,
                average_response_time REAL DEFAULT 0,
                last_study_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exam_category_id) REFERENCES exam_categories(id)
            )
        """)
        
        # 設定テーブル
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key VARCHAR(100) NOT NULL UNIQUE,
                setting_value TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
    
    def _create_indexes(self, conn: sqlite3.Connection):
        """インデックスを作成"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_questions_exam_year ON questions(exam_category_id, year)",
            "CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category)",
            "CREATE INDEX IF NOT EXISTS idx_learning_records_question ON learning_records(question_id)",
            "CREATE INDEX IF NOT EXISTS idx_learning_records_date ON learning_records(attempt_date)",
            "CREATE INDEX IF NOT EXISTS idx_study_sessions_exam ON study_sessions(exam_category_id)",
            "CREATE INDEX IF NOT EXISTS idx_study_statistics_exam ON study_statistics(exam_category_id)"
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
        
        conn.commit()
    
    def _insert_initial_data(self, conn: sqlite3.Connection):
        """初期データを投入"""
        # 試験区分の初期データ
        exam_categories = [
            ("基本情報技術者試験", "FE", "ITエンジニアの登竜門"),
            ("応用情報技術者試験", "AP", "ワンランク上のITエンジニア"),
            ("ITパスポート試験", "IP", "ITを利活用するすべての社会人・学生"),
            ("情報セキュリティマネジメント試験", "SG", "情報セキュリティの基本")
        ]
        
        for name, code, description in exam_categories:
            conn.execute("""
                INSERT OR IGNORE INTO exam_categories (name, code, description)
                VALUES (?, ?, ?)
            """, (name, code, description))
        
        # システム設定の初期データ
        settings = [
            ("last_update", "", "最終更新日時"),
            ("data_version", "1.0", "データバージョン"),
            ("backup_interval", "7", "バックアップ間隔（日）")
        ]
        
        for key, value, description in settings:
            conn.execute("""
                INSERT OR IGNORE INTO system_settings (setting_key, setting_value, description)
                VALUES (?, ?, ?)
            """, (key, value, description))
        
        conn.commit()
    
    # 問題関連のCRUD操作
    def insert_question(self, question_data: Dict) -> int:
        """問題を追加"""
        # バリデーション
        is_valid, errors = ValidationUtils.validate_question_data(question_data)
        if not is_valid:
            raise DataError(f"問題データが無効: {errors}")
        
        with self.get_connection() as conn:
            # 試験区分IDを取得
            exam_category_id = self._get_exam_category_id(conn, question_data.get('exam_type', 'FE'))
            
            # 選択肢をJSON形式に変換
            choices_json = json.dumps(question_data['choices'], ensure_ascii=False)
            
            cursor = conn.execute("""
                INSERT INTO questions (
                    exam_category_id, year, question_number, question_text,
                    choices, correct_answer, explanation, category, subcategory,
                    difficulty_level, source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exam_category_id,
                question_data.get('year'),
                question_data.get('question_number'),
                question_data['question_text'],
                choices_json,
                question_data.get('correct_answer'),
                question_data.get('explanation'),
                question_data.get('category'),
                question_data.get('subcategory'),
                question_data.get('difficulty_level', 2),
                question_data.get('source_url')
            ))
            
            question_id = cursor.lastrowid
            conn.commit()
            
            self.logger.info(f"問題を追加: ID={question_id}")
            return question_id
    
    def get_question(self, question_id: int) -> Optional[Dict]:
        """問題を取得"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT q.*, ec.name as exam_name, ec.code as exam_code
                FROM questions q
                JOIN exam_categories ec ON q.exam_category_id = ec.id
                WHERE q.id = ?
            """, (question_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            question = dict(row)
            question['choices'] = json.loads(question['choices'])
            return question
    
    def update_question(self, question_id: int, question_data: Dict):
        """問題を更新"""
        with self.get_connection() as conn:
            # 更新可能なフィールドを指定
            update_fields = [
                'question_text', 'choices', 'correct_answer', 'explanation',
                'category', 'subcategory', 'difficulty_level'
            ]
            
            set_clause = []
            values = []
            
            for field in update_fields:
                if field in question_data:
                    if field == 'choices':
                        set_clause.append(f"{field} = ?")
                        values.append(json.dumps(question_data[field], ensure_ascii=False))
                    else:
                        set_clause.append(f"{field} = ?")
                        values.append(question_data[field])
            
            if set_clause:
                set_clause.append("updated_at = CURRENT_TIMESTAMP")
                values.append(question_id)
                
                sql = f"UPDATE questions SET {', '.join(set_clause)} WHERE id = ?"
                conn.execute(sql, values)
                conn.commit()
                
                self.logger.info(f"問題を更新: ID={question_id}")
    
    def delete_question(self, question_id: int):
        """問題を削除"""
        with self.get_connection() as conn:
            # 関連する学習記録も削除
            conn.execute("DELETE FROM learning_records WHERE question_id = ?", (question_id,))
            conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            conn.commit()
            
            self.logger.info(f"問題を削除: ID={question_id}")
    
    def get_questions(self, exam_type: str = None, year: int = None, 
                     category: str = None, limit: int = None) -> List[Dict]:
        """問題リストを取得"""
        with self.get_connection() as conn:
            sql = """
                SELECT q.*, ec.name as exam_name, ec.code as exam_code
                FROM questions q
                JOIN exam_categories ec ON q.exam_category_id = ec.id
                WHERE 1=1
            """
            params = []
            
            if exam_type:
                sql += " AND ec.code = ?"
                params.append(exam_type)
            
            if year:
                sql += " AND q.year = ?"
                params.append(year)
            
            if category:
                sql += " AND q.category = ?"
                params.append(category)
            
            sql += " ORDER BY q.year DESC, q.question_number ASC"
            
            if limit:
                sql += " LIMIT ?"
                params.append(limit)
            
            cursor = conn.execute(sql, params)
            questions = []
            
            for row in cursor.fetchall():
                question = dict(row)
                question['choices'] = json.loads(question['choices'])
                questions.append(question)
            
            return questions
    
    def get_random_questions(self, exam_type: str = None, category: str = None,
                           count: int = 20) -> List[Dict]:
        """ランダムな問題を取得"""
        with self.get_connection() as conn:
            sql = """
                SELECT q.*, ec.name as exam_name, ec.code as exam_code
                FROM questions q
                JOIN exam_categories ec ON q.exam_category_id = ec.id
                WHERE q.correct_answer IS NOT NULL
            """
            params = []
            
            if exam_type:
                sql += " AND ec.code = ?"
                params.append(exam_type)
            
            if category:
                sql += " AND q.category = ?"
                params.append(category)
            
            sql += " ORDER BY RANDOM() LIMIT ?"
            params.append(count)
            
            cursor = conn.execute(sql, params)
            questions = []
            
            for row in cursor.fetchall():
                question = dict(row)
                question['choices'] = json.loads(question['choices'])
                questions.append(question)
            
            return questions
    
    # 学習記録関連の操作
    def record_answer(self, question_id: int, user_answer: int, is_correct: bool,
                     response_time: int = None, study_mode: str = 'practice',
                     notes: str = None) -> int:
        """回答を記録"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO learning_records (
                    question_id, user_answer, is_correct, response_time, 
                    study_mode, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (question_id, user_answer, is_correct, response_time, study_mode, notes))
            
            record_id = cursor.lastrowid
            conn.commit()
            
            # 統計を更新
            self._update_statistics(conn, question_id, is_correct, response_time)
            
            # 関連キャッシュを無効化
            self._invalidate_related_cache()
            
            return record_id
    
    def get_learning_records(self, question_id: int = None, 
                           start_date: datetime = None, end_date: datetime = None,
                           limit: int = None) -> List[Dict]:
        """学習記録を取得"""
        with self.get_connection() as conn:
            sql = """
                SELECT lr.*, q.question_text, q.category, ec.name as exam_name
                FROM learning_records lr
                JOIN questions q ON lr.question_id = q.id
                JOIN exam_categories ec ON q.exam_category_id = ec.id
                WHERE 1=1
            """
            params = []
            
            if question_id:
                sql += " AND lr.question_id = ?"
                params.append(question_id)
            
            if start_date:
                sql += " AND lr.attempt_date >= ?"
                params.append(start_date)
            
            if end_date:
                sql += " AND lr.attempt_date <= ?"
                params.append(end_date)
            
            sql += " ORDER BY lr.attempt_date DESC"
            
            if limit:
                sql += " LIMIT ?"
                params.append(limit)
            
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def _update_statistics(self, conn: sqlite3.Connection, question_id: int,
                          is_correct: bool, response_time: int = None):
        """統計情報を更新"""
        # 問題の情報を取得
        cursor = conn.execute("""
            SELECT q.category, q.exam_category_id
            FROM questions q
            WHERE q.id = ?
        """, (question_id,))
        
        row = cursor.fetchone()
        if not row:
            return
        
        category = row['category']
        exam_category_id = row['exam_category_id']
        
        # 統計レコードを取得または作成
        cursor = conn.execute("""
            SELECT id, total_questions, correct_answers, incorrect_answers, average_response_time
            FROM study_statistics
            WHERE exam_category_id = ? AND category = ?
        """, (exam_category_id, category))
        
        stat_row = cursor.fetchone()
        
        if stat_row:
            # 既存の統計を更新
            stats_id = stat_row['id']
            total_questions = stat_row['total_questions'] + 1
            correct_answers = stat_row['correct_answers'] + (1 if is_correct else 0)
            incorrect_answers = stat_row['incorrect_answers'] + (0 if is_correct else 1)
            
            # 平均応答時間を計算
            if response_time and stat_row['average_response_time']:
                avg_time = (stat_row['average_response_time'] * stat_row['total_questions'] + response_time) / total_questions
            else:
                avg_time = response_time or stat_row['average_response_time']
            
            conn.execute("""
                UPDATE study_statistics
                SET total_questions = ?, correct_answers = ?, incorrect_answers = ?,
                    average_response_time = ?, last_study_date = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (total_questions, correct_answers, incorrect_answers, avg_time, stats_id))
        else:
            # 新しい統計レコードを作成
            conn.execute("""
                INSERT INTO study_statistics (
                    exam_category_id, category, total_questions, correct_answers,
                    incorrect_answers, average_response_time, last_study_date
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (exam_category_id, category, 1, 1 if is_correct else 0,
                  0 if is_correct else 1, response_time))
        
        conn.commit()
    
    # 学習セッション管理
    def create_study_session(self, session_name: str, exam_type: str,
                           study_mode: str, total_questions: int) -> int:
        """学習セッションを作成"""
        with self.get_connection() as conn:
            exam_category_id = self._get_exam_category_id(conn, exam_type)
            
            cursor = conn.execute("""
                INSERT INTO study_sessions (
                    session_name, exam_category_id, study_mode, total_questions,
                    start_time
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (session_name, exam_category_id, study_mode, total_questions))
            
            session_id = cursor.lastrowid
            conn.commit()
            
            return session_id
    
    def end_study_session(self, session_id: int, correct_answers: int):
        """学習セッションを終了"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE study_sessions
                SET end_time = CURRENT_TIMESTAMP,
                    correct_answers = ?,
                    duration = (strftime('%s', CURRENT_TIMESTAMP) - strftime('%s', start_time))
                WHERE id = ?
            """, (correct_answers, session_id))
            
            conn.commit()
    
    # 統計・分析関連
    @cached_service.cached_method(ttl=300, key_prefix="stats")  # 5分キャッシュ
    def get_statistics(self, exam_type: str = None) -> Dict:
        """統計情報を取得（キャッシュ機能付き）"""
        with self.get_connection() as conn:
            sql = """
                SELECT 
                    ec.name as exam_name,
                    ss.category,
                    ss.total_questions,
                    ss.correct_answers,
                    ss.incorrect_answers,
                    ss.average_response_time,
                    ss.last_study_date,
                    CASE 
                        WHEN ss.total_questions > 0 
                        THEN ROUND(ss.correct_answers * 100.0 / ss.total_questions, 1)
                        ELSE 0
                    END as correct_rate
                FROM study_statistics ss
                JOIN exam_categories ec ON ss.exam_category_id = ec.id
            """
            params = []
            
            if exam_type:
                sql += " WHERE ec.code = ?"
                params.append(exam_type)
            
            sql += " ORDER BY ec.name, ss.category"
            
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    @cached_service.cached_method(ttl=600, key_prefix="weak")  # 10分キャッシュ
    def get_weak_areas(self, exam_type: str = None, limit: int = 5) -> List[Dict]:
        """弱点分野を取得（キャッシュ機能付き）"""
        with self.get_connection() as conn:
            sql = """
                SELECT 
                    ec.name as exam_name,
                    ss.category,
                    ss.total_questions,
                    ss.correct_answers,
                    ss.incorrect_answers,
                    ROUND(ss.correct_answers * 100.0 / ss.total_questions, 1) as correct_rate
                FROM study_statistics ss
                JOIN exam_categories ec ON ss.exam_category_id = ec.id
                WHERE ss.total_questions >= 3
            """
            params = []
            
            if exam_type:
                sql += " AND ec.code = ?"
                params.append(exam_type)
            
            sql += " ORDER BY correct_rate ASC, ss.total_questions DESC"
            
            if limit:
                sql += " LIMIT ?"
                params.append(limit)
            
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    @cached_service.cached_method(ttl=1800, key_prefix="progress")  # 30分キャッシュ
    def get_progress_over_time(self, exam_type: str = None, days: int = 30) -> List[Dict]:
        """時系列での進捗を取得（キャッシュ機能付き）"""
        with self.get_connection() as conn:
            sql = """
                SELECT 
                    DATE(lr.attempt_date) as study_date,
                    COUNT(*) as total_questions,
                    SUM(lr.is_correct) as correct_answers,
                    ROUND(SUM(lr.is_correct) * 100.0 / COUNT(*), 1) as correct_rate
                FROM learning_records lr
                JOIN questions q ON lr.question_id = q.id
                JOIN exam_categories ec ON q.exam_category_id = ec.id
                WHERE lr.attempt_date >= datetime('now', '-{} days')
            """.format(days)
            params = []
            
            if exam_type:
                sql += " AND ec.code = ?"
                params.append(exam_type)
            
            sql += " GROUP BY DATE(lr.attempt_date) ORDER BY study_date"
            
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def _invalidate_related_cache(self):
        """関連キャッシュを無効化"""
        try:
            cached_service.invalidate_cache("stats:*")
            cached_service.invalidate_cache("weak:*") 
            cached_service.invalidate_cache("progress:*")
            self.logger.debug("関連キャッシュを無効化しました")
        except Exception as e:
            self.logger.warning(f"キャッシュ無効化に失敗: {e}")
    
    def clear_all_cache(self):
        """すべてのキャッシュをクリア"""
        try:
            cache_manager.clear()
            self.logger.info("全キャッシュをクリアしました")
        except Exception as e:
            self.logger.error(f"キャッシュクリアに失敗: {e}")
    
    def get_cache_stats(self) -> Dict:
        """キャッシュ統計を取得"""
        return cache_manager.get_stats()
    
    # ユーティリティメソッド
    def _get_exam_category_id(self, conn: sqlite3.Connection, exam_code: str) -> int:
        """試験区分IDを取得"""
        cursor = conn.execute(
            "SELECT id FROM exam_categories WHERE code = ?", (exam_code,)
        )
        row = cursor.fetchone()
        if not row:
            raise DataError(f"試験区分が見つかりません: {exam_code}")
        return row['id']
    
    def backup_database(self, backup_path: Path = None) -> Path:
        """データベースをバックアップ"""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.db_path.parent / f"backup_{timestamp}.db"
        
        import shutil
        shutil.copy2(self.db_path, backup_path)
        
        self.logger.info(f"データベースをバックアップ: {backup_path}")
        return backup_path
    
    def restore_database(self, backup_path: Path):
        """データベースを復元"""
        if not backup_path.exists():
            raise DataError(f"バックアップファイルが見つかりません: {backup_path}")
        
        import shutil
        shutil.copy2(backup_path, self.db_path)
        
        self.logger.info(f"データベースを復元: {backup_path}")
    
    def get_database_info(self) -> Dict:
        """データベース情報を取得"""
        with self.get_connection() as conn:
            info = {}
            
            # 各テーブルの件数
            tables = ['exam_categories', 'questions', 'learning_records', 'study_sessions']
            for table in tables:
                cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                info[f"{table}_count"] = cursor.fetchone()['count']
            
            # ファイルサイズ
            info['file_size'] = self.db_path.stat().st_size
            
            # 最終更新日時
            info['last_modified'] = datetime.fromtimestamp(self.db_path.stat().st_mtime)
            
            return info
    
    def vacuum_database(self):
        """データベースを最適化"""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
            conn.commit()
        
        self.logger.info("データベースを最適化しました")
    
    def cleanup_old_records(self, days: int = 90):
        """古いレコードを削除"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self.get_connection() as conn:
            # 古い学習記録を削除
            cursor = conn.execute("""
                DELETE FROM learning_records 
                WHERE attempt_date < ?
            """, (cutoff_date,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            self.logger.info(f"古いレコードを削除: {deleted_count} 件")
            
            return deleted_count
    
    def optimize_database(self):
        """データベースパフォーマンス最適化"""
        with self.get_connection() as conn:
            # インデックスの再構築
            conn.execute("REINDEX")
            
            # プラグマ設定でパフォーマンス向上
            conn.execute("PRAGMA optimize")
            conn.execute("PRAGMA cache_size = 10000")
            conn.execute("PRAGMA temp_store = MEMORY")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            
            conn.commit()
        
        self.logger.info("データベースパフォーマンス最適化完了")
    
    def get_cache_stats(self) -> Dict:
        """キャッシュ統計を取得"""
        with self.get_connection() as conn:
            cursor = conn.execute("PRAGMA cache_size")
            cache_size = cursor.fetchone()[0]
            
            cursor = conn.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            cursor = conn.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            return {
                'cache_size': cache_size,
                'page_size': page_size,
                'page_count': page_count,
                'total_size': page_size * page_count
            }
    
    def get_performance_metrics(self) -> Dict:
        """パフォーマンスメトリクスを取得"""
        with self.get_connection() as conn:
            # データベースサイズ
            cursor = conn.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            cursor = conn.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            # インデックス情報
            cursor = conn.execute("""
                SELECT name, sql FROM sqlite_master 
                WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
            """)
            indexes = [dict(row) for row in cursor.fetchall()]
            
            # テーブル統計
            table_stats = []
            for table in ['questions', 'learning_records', 'study_sessions']:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                table_stats.append({'table': table, 'count': count})
            
            return {
                'database_size': page_count * page_size,
                'page_count': page_count,
                'page_size': page_size,
                'indexes': indexes,
                'table_stats': table_stats
            }
    
    # N+1クエリ問題解消のための最適化メソッド
    def get_questions_with_stats(self, exam_type: str = None, category: str = None, 
                                limit: int = None) -> List[Dict]:
        """問題を統計情報と一緒に効率的に取得（N+1問題解消）"""
        with self.get_connection() as conn:
            sql = """
                SELECT 
                    q.id, q.question_text, q.choices, q.correct_answer, q.explanation,
                    q.category, q.subcategory, q.difficulty_level, q.year, q.question_number,
                    ec.name as exam_name, ec.code as exam_code,
                    COALESCE(lr_stats.total_attempts, 0) as total_attempts,
                    COALESCE(lr_stats.correct_attempts, 0) as correct_attempts,
                    COALESCE(lr_stats.avg_response_time, 0) as avg_response_time,
                    CASE 
                        WHEN lr_stats.total_attempts > 0 
                        THEN ROUND(lr_stats.correct_attempts * 100.0 / lr_stats.total_attempts, 1)
                        ELSE 0 
                    END as success_rate
                FROM questions q
                JOIN exam_categories ec ON q.exam_category_id = ec.id
                LEFT JOIN (
                    SELECT 
                        question_id,
                        COUNT(*) as total_attempts,
                        SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_attempts,
                        AVG(response_time) as avg_response_time
                    FROM learning_records 
                    GROUP BY question_id
                ) lr_stats ON q.id = lr_stats.question_id
                WHERE 1=1
            """
            params = []
            
            if exam_type:
                sql += " AND ec.code = ?"
                params.append(exam_type)
            
            if category:
                sql += " AND q.category = ?"
                params.append(category)
            
            sql += " ORDER BY q.year DESC, q.question_number ASC"
            
            if limit:
                sql += " LIMIT ?"
                params.append(limit)
            
            cursor = conn.execute(sql, params)
            questions = []
            
            for row in cursor.fetchall():
                question = dict(row)
                # JSONの選択肢を配列に変換
                if question['choices']:
                    try:
                        question['choices'] = json.loads(question['choices'])
                    except json.JSONDecodeError:
                        question['choices'] = []
                questions.append(question)
            
            return questions
    
    def bulk_record_answers(self, answer_records: List[Dict]) -> List[int]:
        """回答を一括で記録（N+1問題解消）"""
        if not answer_records:
            return []
        
        with self.get_connection() as conn:
            try:
                conn.execute("BEGIN TRANSACTION")
                
                # 回答記録を一括挿入
                record_ids = []
                for record in answer_records:
                    cursor = conn.execute("""
                        INSERT INTO learning_records (
                            question_id, user_answer, is_correct, response_time, 
                            study_mode, notes
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        record['question_id'],
                        record['user_answer'], 
                        record['is_correct'],
                        record.get('response_time'),
                        record.get('study_mode', 'practice'),
                        record.get('notes')
                    ))
                    record_ids.append(cursor.lastrowid)
                
                # 統計を一括更新
                self._batch_update_statistics(conn, answer_records)
                
                conn.execute("COMMIT")
                return record_ids
                
            except Exception as e:
                conn.execute("ROLLBACK")
                self.logger.error(f"一括回答記録エラー: {e}")
                raise
    
    def _batch_update_statistics(self, conn: sqlite3.Connection, answer_records: List[Dict]):
        """統計情報を一括更新"""
        # 問題情報を一度に取得
        question_ids = [r['question_id'] for r in answer_records]
        if not question_ids:
            return
            
        placeholders = ','.join(['?'] * len(question_ids))
        
        cursor = conn.execute(f"""
            SELECT id, category, exam_category_id
            FROM questions 
            WHERE id IN ({placeholders})
        """, question_ids)
        
        question_info = {row['id']: row for row in cursor.fetchall()}
        
        # カテゴリ別統計更新データを集計
        stats_updates = {}
        for record in answer_records:
            question_id = record['question_id']
            if question_id not in question_info:
                continue
            
            q_info = question_info[question_id]
            key = (q_info['exam_category_id'], q_info['category'])
            
            if key not in stats_updates:
                stats_updates[key] = {
                    'total_questions': 0,
                    'correct_answers': 0,
                    'incorrect_answers': 0,
                    'total_response_time': 0,
                    'count': 0
                }
            
            stats = stats_updates[key]
            stats['total_questions'] += 1
            stats['correct_answers'] += 1 if record['is_correct'] else 0
            stats['incorrect_answers'] += 0 if record['is_correct'] else 1
            
            if record.get('response_time'):
                stats['total_response_time'] += record['response_time']
                stats['count'] += 1
        
        # 統計テーブルを更新
        for (exam_category_id, category), updates in stats_updates.items():
            avg_response_time = None
            if updates['count'] > 0:
                avg_response_time = updates['total_response_time'] / updates['count']
            
            # 既存レコードを更新または新規作成
            cursor = conn.execute("""
                SELECT id, total_questions, correct_answers, incorrect_answers, average_response_time
                FROM study_statistics
                WHERE exam_category_id = ? AND category = ?
            """, (exam_category_id, category))
            
            existing = cursor.fetchone()
            if existing:
                # 既存レコードを更新
                new_total = existing['total_questions'] + updates['total_questions']
                new_correct = existing['correct_answers'] + updates['correct_answers']
                new_incorrect = existing['incorrect_answers'] + updates['incorrect_answers']
                
                # 平均応答時間を再計算
                if avg_response_time and existing['average_response_time']:
                    weighted_avg = (
                        existing['average_response_time'] * existing['total_questions'] +
                        avg_response_time * updates['total_questions']
                    ) / new_total
                else:
                    weighted_avg = avg_response_time or existing['average_response_time']
                
                conn.execute("""
                    UPDATE study_statistics
                    SET total_questions = ?, correct_answers = ?, incorrect_answers = ?,
                        average_response_time = ?, last_study_date = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_total, new_correct, new_incorrect, weighted_avg, existing['id']))
            else:
                # 新規レコードを作成
                conn.execute("""
                    INSERT INTO study_statistics (
                        exam_category_id, category, total_questions, correct_answers,
                        incorrect_answers, average_response_time, last_study_date
                    ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (exam_category_id, category, updates['total_questions'],
                      updates['correct_answers'], updates['incorrect_answers'],
                      avg_response_time))
    
    # 学習セッション管理
    def create_study_session(self, session_name: str, exam_type: str, study_mode: str, total_questions: int) -> int:
        """学習セッションを作成"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO study_sessions (
                    session_name, exam_type, study_mode, total_questions, 
                    start_time, status
                ) VALUES (?, ?, ?, ?, ?, 'active')
            """, (session_name, exam_type, study_mode, total_questions, datetime.now()))
            
            session_id = cursor.lastrowid
            conn.commit()
            
            self.logger.info(f"学習セッションを作成: {session_name} (ID: {session_id})")
            return session_id
    
    def end_study_session(self, session_id: int, correct_count: int):
        """学習セッションを終了"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE study_sessions 
                SET end_time = ?, correct_count = ?, status = 'completed'
                WHERE id = ?
            """, (datetime.now(), correct_count, session_id))
            
            conn.commit()
            self.logger.info(f"学習セッションを終了: ID {session_id}")
    
    def get_random_questions(self, exam_type: str, category: str = None, count: int = 20) -> List[Dict]:
        """ランダムに問題を取得"""
        with self.get_connection() as conn:
            if category:
                cursor = conn.execute("""
                    SELECT id, exam_type, year, question_number, question_text, 
                           choices, correct_answer, explanation, category, subcategory, difficulty_level
                    FROM questions 
                    WHERE exam_type = ? AND category = ?
                    ORDER BY RANDOM() 
                    LIMIT ?
                """, (exam_type, category, count))
            else:
                cursor = conn.execute("""
                    SELECT id, exam_type, year, question_number, question_text, 
                           choices, correct_answer, explanation, category, subcategory, difficulty_level
                    FROM questions 
                    WHERE exam_type = ?
                    ORDER BY RANDOM() 
                    LIMIT ?
                """, (exam_type, count))
            
            questions = []
            for row in cursor.fetchall():
                question = dict(row)
                # JSONの選択肢を配列に変換
                if question['choices']:
                    try:
                        question['choices'] = json.loads(question['choices'])
                    except json.JSONDecodeError:
                        question['choices'] = []
                questions.append(question)
            
            return questions
    
    def record_answer(self, question_id: int, user_answer: int, is_correct: bool, study_mode: str):
        """回答を記録"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO learning_records (
                    question_id, user_answer, is_correct, study_mode, attempt_date
                ) VALUES (?, ?, ?, ?, ?)
            """, (question_id, user_answer, is_correct, study_mode, datetime.now()))
            
            conn.commit()