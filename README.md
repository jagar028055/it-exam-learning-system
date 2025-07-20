# 情報技術者試験学習システム

## 概要
情報技術者試験（基本情報技術者試験、応用情報技術者試験など）の学習を支援するWebベースの学習管理システムです。

## 主な機能
- 📚 **問題解答システム**: インタラクティブな問題演習
- 📊 **進捗管理**: 分野別の学習進捗と正答率の可視化
- 📈 **弱点分析**: 苦手分野の特定と集中学習
- 📄 **レポート生成**: 詳細な学習結果レポート
- 🔐 **セキュリティ**: CSRF保護、セッション管理、入力値検証

## システム構成

```
情報技術者試験/
├── src/
│   ├── core/           # コアモジュール
│   │   ├── config.py   # 設定管理
│   │   ├── database.py # データベース管理
│   │   ├── progress_tracker.py # 進捗追跡
│   │   └── report_generator.py # レポート生成
│   ├── web/            # Webアプリケーション
│   │   └── app.py      # Flask アプリケーション
│   ├── data/           # データ処理
│   │   └── data_fetcher.py # データ取得
│   └── utils/          # ユーティリティ
│       └── utils.py    # 共通機能
├── web/               # Web関連アセット
│   ├── templates/     # HTMLテンプレート
│   └── static/        # 静的ファイル（CSS, JS）
├── tools/             # ユーティリティツール
│   ├── pdf_analyzer.py      # PDF解析
│   ├── pdf_question_extractor.py # 問題抽出
│   └── data_migration.py    # データ移行
├── legacy/            # 旧ファイル
├── data/              # データベース・ダウンロード
├── logs/              # ログファイル
├── reports/           # 生成レポート
└── docs/              # ドキュメント
```

## 技術スタック
- **Backend**: Python 3.13, Flask 3.1.1
- **Database**: SQLite3
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5.1.3
- **Charts**: Chart.js 3.9.1
- **Security**: Flask-WTF (CSRF保護)

## セットアップ

### 1. 仮想環境の作成
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 3. システム起動

#### Webアプリケーション（推奨）
```bash
python app.py
```

#### CLIインターフェース
```bash
python app.py --mode cli
```

または
```bash
python main.py --help
```

### 4. アクセス
ブラウザで `http://localhost:5001` にアクセスしてください。

## 🚀 Render無料デプロイ

このアプリケーションはRender無料プランでデプロイ可能です。

### クイックデプロイ手順

1. **GitHubリポジトリ作成**
   ```bash
   # このプロジェクトをGitHubにプッシュ
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Render設定**
   - [Render](https://render.com)でアカウント作成
   - 「New Web Service」を選択
   - GitHubリポジトリを接続
   - 設定は自動検出（render.yamlベース）

3. **環境変数設定**（Renderダッシュボードで設定）
   ```
   FLASK_ENV=production
   PYTHONPATH=/opt/render/project/src
   ```

4. **デプロイ完了**
   - 約5-10分で自動デプロイ完了
   - `https://your-app-name.onrender.com` でアクセス可能

### 無料プランの制限
- 15分間非アクティブでスリープ
- 512MB RAM制限
- 月750時間（実質無制限）

詳細は [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) を参照してください。

## 使用方法

### 1. 学習セッションの開始
- 「学習」ページで試験種別・学習モード・問題数を選択
- 「練習問題」「模擬試験」「弱点分野」から選択可能

### 2. 進捗確認
- 「進捗」ページで分野別の学習状況を確認
- グラフで可視化された統計情報を表示

### 3. レポート生成
- 「レポート」ページで詳細な学習結果レポートを生成
- HTML形式で保存・表示

### 4. システム管理
- 「設定」ページでデータベース管理・最適化

## データベース構造

### 主要テーブル
- `exam_categories`: 試験区分
- `questions`: 問題データ
- `learning_records`: 学習記録
- `study_sessions`: 学習セッション
- `study_statistics`: 学習統計

## セキュリティ機能
- CSRF保護
- セッション管理
- 入力値検証
- エラーハンドリング
- ログ機能

## パフォーマンス最適化
- データベースインデックス
- キャッシュ機能
- SQLite最適化
- 効率的なクエリ

## 開発者情報
- 開発者: Claude Code
- バージョン: 1.0.0
- 更新日: 2025年7月17日

## ライセンス
このプロジェクトは学習目的で作成されています。