"""
データベースマイグレーション管理
IMPROVEMENT_ROADMAP.md Phase 1.2.3の実装
"""

import sqlite3
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable
from contextlib import contextmanager

from .config import config


class DatabaseMigration:
    """データベースマイグレーション管理クラス"""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.DATABASE_PATH
        self.migrations_dir = Path(__file__).parent.parent.parent / "migrations"
        self.migrations_dir.mkdir(exist_ok=True)
        
        # ログ設定
        self.logger = logging.getLogger("DatabaseMigration")
        
        # マイグレーションテーブルを初期化
        self._ensure_migration_table()
    
    @contextmanager
    def get_connection(self):
        """データベース接続のコンテキストマネージャー"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            self.logger.error(f"マイグレーションエラー: {e}")
            raise
        finally:
            conn.close()
    
    def _ensure_migration_table(self):
        """マイグレーション管理テーブルを作成"""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    execution_time_ms INTEGER,
                    checksum TEXT
                )
            """)
            conn.commit()
    
    def get_current_version(self) -> int:
        """現在のスキーマバージョンを取得"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT COALESCE(MAX(version), 0) as version 
                FROM schema_migrations
            """)
            return cursor.fetchone()['version']
    
    def get_applied_migrations(self) -> List[Dict]:
        """適用済みマイグレーション一覧を取得"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT version, name, applied_at, execution_time_ms, checksum
                FROM schema_migrations
                ORDER BY version
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def register_migration(self, version: int, name: str, up_func: Callable, 
                          down_func: Callable = None, description: str = ""):
        """マイグレーションを登録"""
        migration_file = self.migrations_dir / f"{version:03d}_{name}.py"
        
        # マイグレーションファイルを生成
        migration_code = f'''"""
{description}
"""

def up(conn):
    """マイグレーション適用"""
    {up_func.__doc__ or "# マイグレーション処理"}
    # TODO: マイグレーション処理を実装

def down(conn):
    """マイグレーション取り消し"""
    {down_func.__doc__ if down_func else "# 取り消し処理"}
    # TODO: 取り消し処理を実装
'''
        
        migration_file.write_text(migration_code, encoding='utf-8')
        self.logger.info(f"マイグレーションファイルを生成: {migration_file}")
    
    def apply_migration(self, version: int) -> bool:
        """指定されたバージョンのマイグレーションを適用"""
        try:
            migration_file = self._find_migration_file(version)
            if not migration_file:
                self.logger.error(f"マイグレーションファイルが見つかりません: version {version}")
                return False
            
            start_time = datetime.now()
            
            with self.get_connection() as conn:
                # マイグレーション実行
                migration_module = self._load_migration_module(migration_file)
                
                if hasattr(migration_module, 'up'):
                    conn.execute("BEGIN TRANSACTION")
                    try:
                        migration_module.up(conn)
                        
                        # マイグレーション記録を追加
                        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                        checksum = self._calculate_checksum(migration_file)
                        
                        conn.execute("""
                            INSERT INTO schema_migrations (version, name, execution_time_ms, checksum)
                            VALUES (?, ?, ?, ?)
                        """, (version, migration_file.stem, execution_time, checksum))
                        
                        conn.execute("COMMIT")
                        self.logger.info(f"マイグレーション適用完了: {migration_file.stem}")
                        return True
                        
                    except Exception as e:
                        conn.execute("ROLLBACK")
                        self.logger.error(f"マイグレーション適用エラー: {e}")
                        raise
                else:
                    self.logger.error(f"up関数が見つかりません: {migration_file}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"マイグレーション適用エラー: {e}")
            return False
    
    def rollback_migration(self, version: int) -> bool:
        """指定されたバージョンのマイグレーションを取り消し"""
        try:
            migration_file = self._find_migration_file(version)
            if not migration_file:
                return False
            
            with self.get_connection() as conn:
                # 適用済みチェック
                cursor = conn.execute("""
                    SELECT 1 FROM schema_migrations WHERE version = ?
                """, (version,))
                
                if not cursor.fetchone():
                    self.logger.warning(f"マイグレーションが適用されていません: version {version}")
                    return False
                
                migration_module = self._load_migration_module(migration_file)
                
                if hasattr(migration_module, 'down'):
                    conn.execute("BEGIN TRANSACTION")
                    try:
                        migration_module.down(conn)
                        
                        # マイグレーション記録を削除
                        conn.execute("""
                            DELETE FROM schema_migrations WHERE version = ?
                        """, (version,))
                        
                        conn.execute("COMMIT")
                        self.logger.info(f"マイグレーション取り消し完了: {migration_file.stem}")
                        return True
                        
                    except Exception as e:
                        conn.execute("ROLLBACK")
                        self.logger.error(f"マイグレーション取り消しエラー: {e}")
                        raise
                else:
                    self.logger.warning(f"down関数が見つかりません: {migration_file}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"マイグレーション取り消しエラー: {e}")
            return False
    
    def migrate_to_latest(self) -> bool:
        """最新バージョンまでマイグレーションを適用"""
        current_version = self.get_current_version()
        migration_files = self._get_available_migrations()
        
        if not migration_files:
            self.logger.info("適用可能なマイグレーションがありません")
            return True
        
        latest_version = max(migration_files.keys())
        
        if current_version >= latest_version:
            self.logger.info(f"データベースは最新です (version {current_version})")
            return True
        
        # 未適用のマイグレーションを適用
        success_count = 0
        for version in sorted(migration_files.keys()):
            if version > current_version:
                self.logger.info(f"マイグレーション適用中: version {version}")
                if self.apply_migration(version):
                    success_count += 1
                else:
                    self.logger.error(f"マイグレーション適用失敗: version {version}")
                    break
        
        self.logger.info(f"マイグレーション完了: {success_count}件適用")
        return success_count > 0
    
    def _find_migration_file(self, version: int) -> Optional[Path]:
        """バージョンに対応するマイグレーションファイルを検索"""
        pattern = f"{version:03d}_*.py"
        matches = list(self.migrations_dir.glob(pattern))
        return matches[0] if matches else None
    
    def _get_available_migrations(self) -> Dict[int, Path]:
        """利用可能なマイグレーションファイル一覧を取得"""
        migrations = {}
        for migration_file in self.migrations_dir.glob("*.py"):
            if migration_file.name.startswith("__"):
                continue
            
            try:
                version_str = migration_file.name.split("_")[0]
                version = int(version_str)
                migrations[version] = migration_file
            except (ValueError, IndexError):
                self.logger.warning(f"無効なマイグレーションファイル名: {migration_file.name}")
        
        return migrations
    
    def _load_migration_module(self, migration_file: Path):
        """マイグレーションモジュールを動的にロード"""
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("migration", migration_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    def _calculate_checksum(self, migration_file: Path) -> str:
        """マイグレーションファイルのチェックサムを計算"""
        import hashlib
        
        content = migration_file.read_bytes()
        return hashlib.sha256(content).hexdigest()
    
    def create_backup(self) -> Path:
        """マイグレーション前にデータベースをバックアップ"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.db_path.parent / f"backup_before_migration_{timestamp}.db"
        
        import shutil
        shutil.copy2(self.db_path, backup_path)
        
        self.logger.info(f"データベースをバックアップ: {backup_path}")
        return backup_path


# 定義済みマイグレーション
class PredefinedMigrations:
    """事前定義されたマイグレーション"""
    
    @staticmethod
    def create_performance_indexes_migration():
        """パフォーマンス最適化インデックス追加のマイグレーション"""
        def up(conn):
            """パフォーマンス最適化インデックスを追加"""
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_learning_records_user_category ON learning_records(question_id, attempt_date)",
                "CREATE INDEX IF NOT EXISTS idx_questions_category_difficulty ON questions(exam_category_id, category, difficulty_level)",
                "CREATE INDEX IF NOT EXISTS idx_study_sessions_date ON study_sessions(exam_category_id, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_study_statistics_category ON study_statistics(exam_category_id, category, last_study_date)",
                "CREATE INDEX IF NOT EXISTS idx_questions_year_exam ON questions(year, exam_category_id)",
                "CREATE INDEX IF NOT EXISTS idx_learning_records_correct ON learning_records(is_correct, study_mode, attempt_date)"
            ]
            
            for index_sql in indexes:
                conn.execute(index_sql)
            
            # インデックス統計を更新
            conn.execute("ANALYZE")
        
        def down(conn):
            """パフォーマンス最適化インデックスを削除"""
            indexes = [
                "DROP INDEX IF EXISTS idx_learning_records_user_category",
                "DROP INDEX IF EXISTS idx_questions_category_difficulty", 
                "DROP INDEX IF EXISTS idx_study_sessions_date",
                "DROP INDEX IF EXISTS idx_study_statistics_category",
                "DROP INDEX IF EXISTS idx_questions_year_exam",
                "DROP INDEX IF EXISTS idx_learning_records_correct"
            ]
            
            for index_sql in indexes:
                conn.execute(index_sql)
        
        return up, down


def run_migration_cli():
    """CLI形式でマイグレーションを実行"""
    import sys
    
    migration = DatabaseMigration()
    
    if len(sys.argv) < 2:
        print("使用法: python -m src.core.migration <command> [args]")
        print("コマンド:")
        print("  status    - 現在のマイグレーション状態を表示")
        print("  migrate   - 最新バージョンまでマイグレーション")
        print("  rollback <version> - 指定バージョンを取り消し")
        print("  create_performance_migration - パフォーマンス最適化マイグレーションを作成")
        return
    
    command = sys.argv[1]
    
    if command == "status":
        current_version = migration.get_current_version()
        applied_migrations = migration.get_applied_migrations()
        
        print(f"現在のバージョン: {current_version}")
        print(f"適用済みマイグレーション: {len(applied_migrations)}件")
        
        for m in applied_migrations:
            print(f"  {m['version']:03d} - {m['name']} ({m['applied_at']})")
    
    elif command == "migrate":
        print("マイグレーション開始...")
        backup_path = migration.create_backup()
        
        if migration.migrate_to_latest():
            print("✅ マイグレーション完了")
        else:
            print("❌ マイグレーション失敗")
            print(f"バックアップファイル: {backup_path}")
    
    elif command == "rollback" and len(sys.argv) > 2:
        version = int(sys.argv[2])
        print(f"マイグレーション取り消し: version {version}")
        
        if migration.rollback_migration(version):
            print("✅ 取り消し完了")
        else:
            print("❌ 取り消し失敗")
    
    elif command == "create_performance_migration":
        up_func, down_func = PredefinedMigrations.create_performance_indexes_migration()
        migration.register_migration(
            version=1,
            name="add_performance_indexes",
            up_func=up_func,
            down_func=down_func,
            description="パフォーマンス最適化のためのインデックス追加"
        )
        print("✅ パフォーマンス最適化マイグレーションを作成しました")
    
    else:
        print(f"不明なコマンド: {command}")


if __name__ == "__main__":
    run_migration_cli()