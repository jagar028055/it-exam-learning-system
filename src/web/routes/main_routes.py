"""
メインページ関連のルート定義
"""

import logging
from datetime import datetime

from flask import Blueprint, render_template, flash

from ..services.study_service import StudyService

logger = logging.getLogger(__name__)

# Blueprint作成
main_bp = Blueprint('main', __name__)

# サービス初期化は後でDIで行う
study_service = None

def init_services(study_svc):
    """サービスの初期化"""
    global study_service
    study_service = study_svc

@main_bp.route('/')
def index():
    """トップページ"""
    try:
        # 統計情報を取得
        stats = study_service.get_statistics('FE')
        
        # 最近の活動
        recent_activity = study_service.get_recent_activity(limit=5)
        
        # 推奨事項
        recommendations = study_service.get_recommendations()
        
        return render_template('index.html', 
                             stats=stats,
                             recent_activity=recent_activity,
                             recommendations=recommendations)
    except Exception as e:
        logger.error(f"トップページエラー: {e}")
        flash(f"エラーが発生しました: {e}", 'error')
        return render_template('index.html', stats={})

@main_bp.route('/health')
def health_check():
    """ヘルスチェックエンドポイント (Render用)"""
    try:
        # データベース接続確認
        db_info = study_service.db.get_database_info()
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'tables': db_info.get('table_count', 0)
        }
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        return {
            'status': 'unhealthy', 
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, 500

@main_bp.route('/ping')
def ping():
    """UptimeRobot用軽量ピングエンドポイント"""
    return 'pong'