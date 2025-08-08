# IT試験学習システム - デプロイ環境整備プランニング

## 🔍 現在の状況分析

**プロジェクト構造：**
- ✅ Flask Webアプリケーション
- ✅ SQLiteデータベース 
- ✅ ヘルスチェックエンドポイント (`/health`, `/ping`) 実装済み
- ⚠️ 開発環境用設定のみ
- ❌ 本番用設定ファイルなし
- ❌ 環境変数管理なし

---

## 📋 デプロイ環境整備タスク一覧

### 🔥 **優先度: HIGH**

| タスクID | タスク内容 | 担当ファイル | 所要時間 | 状況 |
|----------|------------|--------------|----------|------|
| **ENV-01** | 環境設定ファイルとシークレット管理の実装 | `config/`, `.env` | 30分 | ✅ 完了 |
| **APP-02** | 本番用アプリケーションエントリーポイントの作成 | `app.py` | 15分 | 🔄 進行中 |
| **DEP-03** | 本番用依存関係の追加と最適化 | `requirements.txt` | 15分 | 待機中 |
| **REN-04** | Render用設定ファイルの調整 | `render.yaml` | 10分 | 待機中 |

### 🟡 **優先度: MEDIUM**

| タスクID | タスク内容 | 担当ファイル | 所要時間 | 状況 |
|----------|------------|--------------|----------|------|
| **HEL-05** | ヘルスチェックエンドポイントの最適化 | `src/web/main.py` | 10分 | 待機中 |
| **SEC-06** | 本番環境用セキュリティ設定の強化 | 各ファイル | 20分 | 待機中 |
| **STA-07** | 静的ファイル配信の最適化 | `static/` | 15分 | 待機中 |
| **DB-08** | 本番用データベース設定の調整 | `src/core/database.py` | 15分 | 待機中 |

### 🟢 **優先度: LOW**

| タスクID | タスク内容 | 担当ファイル | 所要時間 | 状況 |
|----------|------------|--------------|----------|------|
| **TEST-09** | デプロイテストと動作確認 | 全体 | 20分 | 待機中 |

---

## 🚀 **詳細実装プラン**

### **Phase 1: 基本設定 (1時間)**

#### ENV-01: 環境設定ファイル実装
- `.env.example`, `.env.production` 作成
- `SECRET_KEY`, `DATABASE_URL` 環境変数化
- 本番/開発環境分離

#### APP-02: 本番用エントリーポイント
- `app.py` 作成（Gunicorn用）
- PORT環境変数対応
- 本番用ログ設定

#### DEP-03: 依存関係最適化
- `Flask-Talisman` (セキュリティヘッダー)
- `python-dotenv` (環境変数)
- バージョン固定

#### REN-04: Render設定調整
- `buildCommand`, `startCommand` 修正
- 環境変数設定
- データベースパス調整

### **Phase 2: セキュリティ・最適化 (45分)**

#### HEL-05: ヘルスチェック最適化 ✨
- レスポンス時間測定
- データベース接続確認
- システム情報追加

#### SEC-06: セキュリティ強化
- CSRF トークン強化
- セキュリティヘッダー追加
- HTTPS リダイレクト

#### STA-07: 静的ファイル最適化
- ファイル圧縮
- キャッシュ設定
- CDN準備

#### DB-08: データベース設定
- 接続プール設定
- SQLite WALモード
- バックアップ設定

### **Phase 3: テスト・検証 (20分)**

#### TEST-09: デプロイテスト
- ローカルGunicornテスト
- Render手動デプロイ
- 動作確認チェックリスト

---

## ⏱️ **スケジュール**

| 時間 | フェーズ | 作業内容 |
|------|----------|----------|
| **0-30分** | Phase 1-1 | 環境設定ファイル実装 |
| **30-45分** | Phase 1-2 | 本番用エントリーポイント作成 |
| **45-60分** | Phase 1-3 | 依存関係・Render設定 |
| **60-85分** | Phase 2 | セキュリティ・最適化 |
| **85-105分** | Phase 3 | テスト・デプロイ |

**総所要時間: 約1時間45分**

---

## 🎯 **成功基準**

- [ ] ローカルでGunicornが正常起動
- [ ] `/health`エンドポイントが正常応答
- [ ] 環境変数でシークレット管理
- [ ] Renderで正常デプロイ
- [ ] 全機能が本番環境で動作

---

## 📝 **実装ログ**

### ✅ 完了したタスク
- ENV-01: 環境設定ファイル実装 (完了)

### 🔄 進行中のタスク
- APP-02: 本番用エントリーポイント作成

### 📋 待機中のタスク
- DEP-03: 本番用依存関係の追加と最適化
- REN-04: Render用設定ファイルの調整
- HEL-05: ヘルスチェックエンドポイントの最適化
- SEC-06: 本番環境用セキュリティ設定の強化
- STA-07: 静的ファイル配信の最適化
- DB-08: 本番用データベース設定の調整
- TEST-09: デプロイテストと動作確認

この計画で`from-oppo`ブランチを本番デプロイ可能な状態にします！

---

## 🚀 **Renderデプロイ手順**

### **Step 1: Renderアカウント作成** ✅
1. [https://render.com](https://render.com) にアクセス
2. **"Get Started for Free"** をクリック
3. **"Sign up with GitHub"** を選択（推奨）
4. GitHubアカウントで連携・認証

### **Step 2: Web Service作成**
1. Renderダッシュボードで **"New +"** → **"Web Service"**
2. **"Connect a repository"** で `jagar028055/it-exam-learning-system` を選択
3. **"Connect"** をクリック

### **Step 3: サービス設定**
以下の設定を入力：

| 項目 | 設定値 |
|------|--------|
| **Name** | `itexam-study-system` |
| **Branch** | `from-oppo` ⚠️ **重要: mainから変更** |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --access-logfile - --error-logfile - app:app` |
| **Plan** | `Free` ($0/月) |

### **Step 4: 環境変数確認**
`render.yaml`から自動読み込みされる環境変数：
- ✅ `FLASK_ENV=production`
- ✅ `SECRET_KEY` (自動生成)
- ✅ `PYTHONPATH=/opt/render/project/src`
- ✅ `DATABASE_PATH=/opt/render/project/src/data/database.db`
- ✅ `SESSION_FILE_DIR=/opt/render/project/src/flask_session`
- ✅ `LOG_LEVEL=INFO`

### **Step 5: デプロイ実行**
1. **"Create Web Service"** をクリック
2. 初回デプロイ開始（5-10分）
3. ログでビルド状況を確認

### **Step 6: 動作確認**
デプロイ完了後、以下のエンドポイントをテスト：
- ✅ `https://your-app.onrender.com/` (メインページ)
- ✅ `https://your-app.onrender.com/health` (ヘルスチェック)
- ✅ `https://your-app.onrender.com/ping` (軽量ピング)

---

## ⏰ **デプロイ所要時間**
- アカウント作成: **2-3分** ✅
- サービス設定: **3-5分**
- 初回デプロイ: **5-10分**
- **合計: 約10-18分**

## 🎯 **トラブルシューティング**

### よくある問題と対処法：

1. **ビルドエラー**
   - ログで `requirements.txt` のインストール状況を確認
   - Python バージョン互換性をチェック

2. **起動エラー**
   - `app.py` が正しく読み込まれているか確認
   - 環境変数が正しく設定されているか確認

3. **データベースエラー**
   - `/opt/render/project/src/data/` ディレクトリ作成を確認
   - SQLite ファイルの権限を確認

4. **静的ファイル404**
   - `src/web/static/` パスが正しいか確認
   - Flask 静的ファイル設定を確認

---

## 📞 **サポート情報**

**Render公式ドキュメント:**
- [Python デプロイガイド](https://render.com/docs/deploy-flask)
- [環境変数設定](https://render.com/docs/environment-variables)
- [トラブルシューティング](https://render.com/docs/troubleshooting-deploys)

**プロジェクト固有の設定:**
- ブランチ: `from-oppo`
- メインファイル: `app.py`
- ヘルスチェック: `/health`