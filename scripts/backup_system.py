#!/usr/bin/env python3
"""
SQLiteデータベース自動バックアップシステム

機能:
- 定期的なSQLiteファイルバックアップ
- GitHubへの自動コミット・プッシュ
- バックアップファイルのローテーション
- 復元機能
"""

import os
import shutil
import sqlite3
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import logging
import gzip

class DatabaseBackupSystem:
    def __init__(self, db_path=None, backup_dir=None):
        """バックアップシステムの初期化"""
        self.project_root = Path(__file__).parent.parent
        self.db_path = Path(db_path) if db_path else self.project_root / "src" / "data" / "database.db"
        self.backup_dir = Path(backup_dir) if backup_dir else self.project_root / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.project_root / "logs" / "backup.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def create_backup(self, compress=True):
        """データベースのバックアップを作成"""
        try:
            if not self.db_path.exists():
                self.logger.error(f"Database file not found: {self.db_path}")
                return None
                
            # タイムスタンプ付きファイル名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"database_backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename
            
            # SQLiteファイルをコピー
            shutil.copy2(self.db_path, backup_path)
            
            # 圧縮オプション
            if compress:
                compressed_path = backup_path.with_suffix('.db.gz')
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(backup_path)
                backup_path = compressed_path
                
            # バックアップメタデータを作成
            metadata = self._create_backup_metadata(backup_path)
            metadata_path = backup_path.with_suffix('.json')
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"Backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
            return None
            
    def _create_backup_metadata(self, backup_path):
        """バックアップメタデータを作成"""
        try:
            # 元データベースの情報を取得
            db_info = self._get_database_info()
            
            metadata = {
                'backup_time': datetime.now().isoformat(),
                'original_db_path': str(self.db_path),
                'backup_path': str(backup_path),
                'file_size': os.path.getsize(backup_path),
                'compressed': backup_path.suffix == '.gz',
                'database_info': db_info,
                'backup_type': 'automatic',
                'version': '1.0'
            }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Metadata creation failed: {e}")
            return {'error': str(e)}
            
    def _get_database_info(self):
        """データベース情報を取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # テーブル一覧
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            # 各テーブルの行数
            table_counts = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                table_counts[table] = cursor.fetchone()[0]
                
            # データベースサイズ
            db_size = os.path.getsize(self.db_path)
            
            conn.close()
            
            return {
                'tables': tables,
                'table_counts': table_counts,
                'total_tables': len(tables),
                'database_size': db_size,
                'last_modified': os.path.getmtime(self.db_path)
            }
            
        except Exception as e:
            self.logger.error(f"Database info retrieval failed: {e}")
            return {'error': str(e)}
            
    def cleanup_old_backups(self, keep_days=30, keep_minimum=5):
        """古いバックアップファイルを削除"""
        try:
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            backup_files = list(self.backup_dir.glob("database_backup_*.db*"))
            
            # 日付でソート（新しい順）
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 最小保持数を超える古いファイルを削除
            files_to_delete = []
            for i, backup_file in enumerate(backup_files[keep_minimum:], keep_minimum):
                if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff_date:
                    files_to_delete.append(backup_file)
                    
            for backup_file in files_to_delete:
                # メタデータファイルも削除
                metadata_file = backup_file.with_suffix('.json')
                if metadata_file.exists():
                    os.remove(metadata_file)
                os.remove(backup_file)
                self.logger.info(f"Removed old backup: {backup_file}")
                
            return len(files_to_delete)
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return 0
            
    def commit_to_git(self, backup_path):
        """バックアップをGitにコミット"""
        try:
            os.chdir(self.project_root)
            
            # Gitステータス確認
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True)
            
            # バックアップファイルをステージング
            subprocess.run(['git', 'add', str(backup_path)], check=True)
            
            # メタデータファイルもステージング
            metadata_file = backup_path.with_suffix('.json')
            if metadata_file.exists():
                subprocess.run(['git', 'add', str(metadata_file)], check=True)
                
            # コミット
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"Auto backup: Database backup created at {timestamp}"
            
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            
            # プッシュ（オプション）
            if os.environ.get('AUTO_PUSH_BACKUPS', 'false').lower() == 'true':
                subprocess.run(['git', 'push', 'origin', 'main'], check=True)
                self.logger.info("Backup pushed to remote repository")
            else:
                self.logger.info("Backup committed locally (push disabled)")
                
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git operation failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Git commit failed: {e}")
            return False
            
    def restore_backup(self, backup_path, target_path=None):
        """バックアップから復元"""
        try:
            backup_path = Path(backup_path)
            target_path = Path(target_path) if target_path else self.db_path
            
            if not backup_path.exists():
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
                
            # 現在のデータベースをバックアップ（念のため）
            if target_path.exists():
                emergency_backup = target_path.with_suffix(f'.emergency_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
                shutil.copy2(target_path, emergency_backup)
                self.logger.info(f"Emergency backup created: {emergency_backup}")
                
            # 復元実行
            if backup_path.suffix == '.gz':
                # 圧縮ファイルの場合
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(target_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # 通常のファイルコピー
                shutil.copy2(backup_path, target_path)
                
            self.logger.info(f"Database restored from: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            return False
            
    def run_full_backup(self):
        """完全バックアップの実行"""
        self.logger.info("Starting full backup process...")
        
        # バックアップ作成
        backup_path = self.create_backup(compress=True)
        if not backup_path:
            return False
            
        # 古いバックアップの削除
        deleted_count = self.cleanup_old_backups(keep_days=30, keep_minimum=5)
        self.logger.info(f"Cleaned up {deleted_count} old backup files")
        
        # Gitコミット
        if self.commit_to_git(backup_path):
            self.logger.info("Backup committed to Git successfully")
        else:
            self.logger.warning("Git commit failed, but backup file created")
            
        self.logger.info("Full backup process completed")
        return True
        
    def list_backups(self):
        """利用可能なバックアップ一覧"""
        backups = []
        for backup_file in sorted(self.backup_dir.glob("database_backup_*.db*")):
            metadata_file = backup_file.with_suffix('.json')
            metadata = {}
            
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                except:
                    pass
                    
            backup_info = {
                'file': str(backup_file),
                'size': os.path.getsize(backup_file),
                'created': datetime.fromtimestamp(backup_file.stat().st_mtime),
                'compressed': backup_file.suffix == '.gz',
                'metadata': metadata
            }
            backups.append(backup_info)
            
        return backups


def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Database Backup System')
    parser.add_argument('action', choices=['backup', 'restore', 'list', 'cleanup'],
                       help='Action to perform')
    parser.add_argument('--db-path', help='Database file path')
    parser.add_argument('--backup-dir', help='Backup directory path')
    parser.add_argument('--backup-file', help='Backup file for restore')
    parser.add_argument('--compress', action='store_true', help='Compress backup files')
    parser.add_argument('--keep-days', type=int, default=30, help='Days to keep backups')
    
    args = parser.parse_args()
    
    # バックアップシステム初期化
    backup_system = DatabaseBackupSystem(args.db_path, args.backup_dir)
    
    if args.action == 'backup':
        success = backup_system.run_full_backup()
        exit(0 if success else 1)
        
    elif args.action == 'restore':
        if not args.backup_file:
            print("--backup-file is required for restore")
            exit(1)
        success = backup_system.restore_backup(args.backup_file)
        exit(0 if success else 1)
        
    elif args.action == 'list':
        backups = backup_system.list_backups()
        print(f"Found {len(backups)} backup(s):")
        for backup in backups:
            size_mb = backup['size'] / (1024 * 1024)
            compressed = " (compressed)" if backup['compressed'] else ""
            print(f"  {backup['file']} - {size_mb:.1f}MB - {backup['created']}{compressed}")
            
    elif args.action == 'cleanup':
        deleted = backup_system.cleanup_old_backups(keep_days=args.keep_days)
        print(f"Deleted {deleted} old backup files")


if __name__ == '__main__':
    main()