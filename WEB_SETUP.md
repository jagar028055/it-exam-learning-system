# Webサービス版 - セットアップガイド

## 概要

情報技術者試験学習システムをWebサービスとして利用するためのセットアップガイドです。

## 必要な環境

- Python 3.8以上
- インターネット接続
- 2GB以上のメモリ
- 1GB以上のディスク容量

## セットアップ手順

### 1. 依存関係のインストール

```bash
# 仮想環境を作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Webサービス用の依存関係をインストール
pip install -r requirements.txt
```

### 2. データベースの初期化

```bash
# データベースを初期化
python main.py --init-db
```

### 3. 初期データの取得（オプション）

```bash
# 基本情報技術者試験の過去問題を取得
python main.py --fetch-data --exam-type FE --year 2023

# より多くのデータを取得したい場合
python main.py --fetch-data --exam-type FE  # 全年度
```

### 4. Webサーバーの起動

```bash
# 開発サーバーを起動
python app.py
```

サーバーが起動したら、ブラウザで `http://localhost:5000` にアクセスしてください。

## 主要機能

### 1. ダッシュボード (`/`)
- 学習統計の概要
- 最近の学習活動
- 学習推奨事項
- クイックアクション

### 2. 学習機能 (`/study`)
- 学習モードの選択
- 問題数・分野の設定
- インタラクティブな問題解答
- リアルタイムの結果表示

### 3. 進捗確認 (`/progress`)
- 学習進捗の可視化
- 分野別パフォーマンス
- 弱点分析

### 4. レポート (`/reports`)
- 詳細なHTML レポート生成
- 学習状況の包括的な分析
- グラフとチャートによる可視化

### 5. 設定 (`/settings`)
- データベース情報
- データ取得機能
- システム設定

## API エンドポイント

### 統計情報API
```
GET /api/stats?exam_type=FE
```

### 問題取得API
```
GET /api/questions?exam_type=FE&category=テクノロジ系&count=20
```

## 本番環境での運用

### 1. 環境設定

```bash
# 本番環境の設定
export ENVIRONMENT=production
export FLASK_ENV=production
```

### 2. WSGIサーバーの使用

```bash
# gunicornを使用した本番運用
pip install gunicorn

# サーバー起動
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 3. Nginxとの連携

```nginx
# /etc/nginx/sites-available/it-exam-study
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /path/to/your/app/static/;
    }
}
```

### 4. SSL証明書の設定

```bash
# Let's Encryptを使用
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Docker を使用した運用

### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python main.py --init-db

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
      - ./reports:/app/reports
      - ./logs:/app/logs
    environment:
      - ENVIRONMENT=production
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./static:/app/static
    depends_on:
      - web
    restart: unless-stopped
```

## セキュリティ設定

### 1. 基本的なセキュリティ設定

```python
# app.py に追加
from flask_talisman import Talisman

# CSP設定
Talisman(app, {
    'default-src': "'self'",
    'script-src': "'self' 'unsafe-inline' cdn.jsdelivr.net cdn.plot.ly cdnjs.cloudflare.com",
    'style-src': "'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com",
    'img-src': "'self' data:",
    'connect-src': "'self'"
})
```

### 2. レート制限

```python
# Flask-Limiterを使用
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/questions')
@limiter.limit("10 per minute")
def api_questions():
    # ...
```

## 監視とログ

### 1. アプリケーションログ

```python
# ログ設定の改善
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
```

### 2. システム監視

```bash
# systemdサービスファイル
# /etc/systemd/system/it-exam-study.service
[Unit]
Description=IT Exam Study System
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/app
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## バックアップとメンテナンス

### 1. データベースバックアップ

```bash
# 定期バックアップスクリプト
#!/bin/bash
cd /path/to/app
source venv/bin/activate
python main.py --backup
```

### 2. ログローテーション

```bash
# /etc/logrotate.d/it-exam-study
/path/to/app/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 www-data www-data
}
```

## トラブルシューティング

### よくある問題と解決方法

1. **ポート5000が既に使用されている**
   ```bash
   # 別のポートで起動
   python app.py  # app.py内でポート番号を変更
   ```

2. **データベースエラー**
   ```bash
   # データベースを再初期化
   rm data/database.db
   python main.py --init-db
   ```

3. **メモリ不足**
   ```bash
   # ワーカープロセス数を調整
   gunicorn -w 2 -b 0.0.0.0:5000 app:app
   ```

4. **セッションエラー**
   ```bash
   # セッションディレクトリをクリア
   rm -rf flask_session/*
   ```

## パフォーマンス最適化

### 1. データベース最適化

```python
# 定期的なデータベースメンテナンス
@app.cli.command()
def optimize_db():
    """データベースを最適化"""
    db.vacuum_database()
    db.cleanup_old_records(90)
```

### 2. キャッシュの活用

```python
# Flask-Cachingを使用
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/api/stats')
@cache.cached(timeout=300)  # 5分間キャッシュ
def api_stats():
    # ...
```

## 開発時の注意事項

### 1. デバッグモード

```bash
# 開発時のみデバッグモードを有効
export FLASK_ENV=development
python app.py
```

### 2. ホットリロード

```bash
# ファイル変更時に自動リロード
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py
```

## まとめ

この設定により、情報技術者試験学習システムを本格的なWebサービスとして運用できます。

- **開発環境**: `python app.py`
- **本番環境**: `gunicorn` + `nginx`
- **コンテナ環境**: Docker + docker-compose

セキュリティ、パフォーマンス、監視の各側面を考慮して運用してください。