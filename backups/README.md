# Database Backups

このディレクトリには、SQLiteデータベースの自動バックアップファイルが保存されます。

## バックアップスケジュール

- **日次バックアップ**: 毎日午前2時（JST 11時）
- **週次バックアップ**: 毎週日曜日午前3時
- **緊急バックアップ**: 手動実行可能

## ファイル形式

- `database_backup_YYYYMMDD_HHMMSS.db.gz`: 圧縮されたSQLiteデータベースファイル
- `database_backup_YYYYMMDD_HHMMSS.json`: バックアップメタデータ

## 保持ポリシー

- **保持期間**: 30日間
- **最小保持数**: 5ファイル
- **自動削除**: 古いバックアップファイルは自動削除

## 復元方法

### 手動復元
```bash
# バックアップファイル一覧表示
python scripts/backup_system.py list

# 指定したバックアップから復元
python scripts/backup_system.py restore --backup-file backups/database_backup_20250808_120000.db.gz
```

### GitHub Actionsでの復元
1. Actions タブで "Automatic Database Backup" を選択
2. "Run workflow" をクリック
3. backup_type を "emergency" に設定して実行

## バックアップの確認

最新のバックアップ状況は週次レポートIssueで確認できます。

## セキュリティ注意事項

- バックアップファイルには個人情報が含まれる可能性があります
- 本番環境では外部ストレージの使用を推奨します
- 定期的な復元テストを実施してください

---

🤖 Generated with [Claude Code](https://claude.ai/code)