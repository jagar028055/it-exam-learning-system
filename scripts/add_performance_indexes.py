#!/usr/bin/env python3
"""
データベースパフォーマンス最適化インデックス追加スクリプト
IMPROVEMENT_ROADMAP.md Phase 1.2.1の実装
"""

import sqlite3
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import config

def add_performance_indexes():
    """パフォーマンス最適化インデックスを追加"""
    
    # 環境変数からデータベースパスを取得
    db_path = os.environ.get('DATABASE_PATH', config.DATABASE_PATH)
    
    print(f"データベースパス: {db_path}")
    
    if not Path(db_path).exists():
        print(f"データベースファイルが見つかりません: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # IMPROVEMENT_ROADMAP.mdで指定された必須インデックス
        performance_indexes = [
            # 学習記録の user_id + category_id のインデックス
            """CREATE INDEX IF NOT EXISTS idx_learning_records_user_category 
               ON learning_records(question_id, attempt_date)""",
            
            # 問題の category_id + difficulty_level のインデックス  
            """CREATE INDEX IF NOT EXISTS idx_questions_category_difficulty 
               ON questions(exam_category_id, category, difficulty_level)""",
            
            # 学習セッションの user_id + date のインデックス
            """CREATE INDEX IF NOT EXISTS idx_study_sessions_date 
               ON study_sessions(exam_category_id, created_at)""",
            
            # 学習統計の category 検索用
            """CREATE INDEX IF NOT EXISTS idx_study_statistics_category 
               ON study_statistics(exam_category_id, category, last_study_date)""",
            
            # 問題の年度検索用（頻繁に使用される）
            """CREATE INDEX IF NOT EXISTS idx_questions_year_exam 
               ON questions(year, exam_category_id)""",
            
            # 学習記録の正答率分析用
            """CREATE INDEX IF NOT EXISTS idx_learning_records_correct 
               ON learning_records(is_correct, study_mode, attempt_date)"""
        ]
        
        print("パフォーマンス最適化インデックスを追加中...")
        
        for i, index_sql in enumerate(performance_indexes, 1):
            print(f"インデックス {i}/{len(performance_indexes)} を作成中...")
            cursor.execute(index_sql)
            print(f"✓ 完了")
        
        # インデックス統計を更新
        print("インデックス統計を更新中...")
        cursor.execute("ANALYZE")
        
        conn.commit()
        print(f"✅ {len(performance_indexes)}個のパフォーマンス最適化インデックスを追加しました")
        
        # 追加されたインデックスを確認
        cursor.execute("""
            SELECT name, sql FROM sqlite_master 
            WHERE type = 'index' AND name LIKE 'idx_%' 
            ORDER BY name
        """)
        
        indexes = cursor.fetchall()
        print(f"\n現在のインデックス一覧 ({len(indexes)}個):")
        for name, sql in indexes:
            print(f"  - {name}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ インデックス追加エラー: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

def check_index_effectiveness():
    """インデックスの効果をチェック"""
    
    db_path = os.environ.get('DATABASE_PATH', config.DATABASE_PATH)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\n📊 インデックス効果のチェック:")
        
        # よく使われるクエリの実行計画をチェック
        test_queries = [
            ("問題カテゴリ検索", """
                EXPLAIN QUERY PLAN 
                SELECT * FROM questions 
                WHERE exam_category_id = 1 AND category = 'ネットワーク'
            """),
            ("学習記録の統計", """
                EXPLAIN QUERY PLAN
                SELECT COUNT(*), AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END)
                FROM learning_records 
                WHERE question_id IN (
                    SELECT id FROM questions WHERE exam_category_id = 1
                )
            """),
            ("年度別問題検索", """
                EXPLAIN QUERY PLAN
                SELECT * FROM questions 
                WHERE year = 2023 AND exam_category_id = 1
                ORDER BY question_number
            """)
        ]
        
        for query_name, query in test_queries:
            print(f"\n{query_name}:")
            cursor.execute(query)
            plan = cursor.fetchall()
            for row in plan:
                detail = ' | '.join(str(x) for x in row)
                if 'USING INDEX' in detail:
                    print(f"  ✅ {detail}")
                else:
                    print(f"  ⚠️ {detail}")
        
    except sqlite3.Error as e:
        print(f"❌ チェックエラー: {e}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 データベースパフォーマンス最適化を開始...")
    
    success = add_performance_indexes()
    if success:
        check_index_effectiveness()
        print("\n✅ パフォーマンス最適化が完了しました!")
    else:
        print("\n❌ パフォーマンス最適化に失敗しました")
        sys.exit(1)