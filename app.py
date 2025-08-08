#!/usr/bin/env python3
"""
情報技術者試験学習システム - 本番用エントリーポイント
Render デプロイメント用
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging

# 環境変数を読み込み
load_dotenv()

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 設定クラスをインポート
from src.core.config import Config

# 本番環境用設定
def setup_production_environment():
    """本番環境用の設定を適用"""
    
    # 必要なディレクトリを作成
    Config.create_directories()
    
    # ログ設定
    log_level = os.environ.get('LOG_LEVEL', Config.LOG_LEVEL)
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=Config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("本番環境設定完了")
    
    return logger

# 本番環境設定を実行
logger = setup_production_environment()

# Flaskアプリケーションをインポート
try:
    from src.web.main import app
    logger.info("Flaskアプリケーション読み込み完了")
    
    # 本番用設定を適用
    app.config.update({
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'fallback-secret-key-for-render'),
        'SESSION_FILE_DIR': os.environ.get('SESSION_FILE_DIR', str(Config.PROJECT_ROOT / 'flask_session')),
        'DATABASE_PATH': os.environ.get('DATABASE_PATH', str(Config.DATABASE_PATH)),
    })
    
    # Flask環境の設定
    if os.environ.get('FLASK_ENV') == 'production':
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        logger.info("本番モードで起動")
    
except Exception as e:
    logger.error(f"アプリケーション初期化エラー: {e}")
    raise

# Renderのヘルスチェック用
@app.route('/ready')
def ready():
    """Render用レディネスチェック"""
    return {'status': 'ready', 'app': 'it-exam-learning-system'}

# アプリケーション情報
@app.route('/info')
def app_info():
    """アプリケーション情報"""
    return {
        'name': 'IT試験学習システム',
        'version': '1.0.0',
        'environment': os.environ.get('FLASK_ENV', 'production'),
        'python_version': sys.version
    }

if __name__ == '__main__':
    # 開発用サーバー（本番ではGunicornが使用される）
    port = int(os.environ.get('PORT', 5001))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('FLASK_ENV') != 'production'
    )
