"""
設定関連のルート定義
"""

import logging

from flask import Blueprint, render_template, request, redirect, url_for, flash

from ..services.settings_service import SettingsService
from ...core.config import config

logger = logging.getLogger(__name__)

# Blueprint作成
settings_bp = Blueprint('settings', __name__)

# サービス初期化は後でDIで行う
settings_service = None

def init_services(settings_svc):
    """サービスの初期化"""
    global settings_service
    settings_service = settings_svc

@settings_bp.route('/settings')
def settings():
    """設定ページ"""
    try:
        settings_data = settings_service.get_settings_data()
        
        return render_template('settings.html', **settings_data)
        
    except Exception as e:
        logger.error(f"設定ページエラー: {e}")
        flash(f"設定表示に失敗しました: {e}", 'error')
        return render_template('settings.html', db_info={}, settings_info={})

@settings_bp.route('/fetch_data', methods=['POST'])
def fetch_data():
    """データ取得"""
    try:
        exam_type = request.form.get('exam_type', 'FE')
        year = request.form.get('year', None)
        
        # 入力値検証
        if exam_type not in config.EXAM_CATEGORIES:
            flash('無効な試験種別です。', 'error')
            return redirect(url_for('settings.settings'))
        
        if year:
            year = int(year)
            if not (2015 <= year <= 2025):
                flash('年度は2015〜2025の範囲で指定してください。', 'error')
                return redirect(url_for('settings.settings'))
        
        # データ取得処理
        result = settings_service.fetch_exam_data(exam_type, year)
        
        if result['success']:
            flash(f'{result["message"]}', 'success')
        else:
            flash(f'{result["message"]}', 'error')
        
        return redirect(url_for('settings.settings'))
        
    except Exception as e:
        logger.error(f"データ取得エラー: {e}")
        flash(f"データ取得に失敗しました: {e}", 'error')
        return redirect(url_for('settings.settings'))

@settings_bp.route('/optimize_db', methods=['POST'])
def optimize_db():
    """データベース最適化"""
    try:
        settings_service.optimize_database()
        flash('データベースを最適化しました。', 'success')
        return redirect(url_for('settings.settings'))
    except Exception as e:
        logger.error(f"データベース最適化エラー: {e}")
        flash(f"データベース最適化に失敗しました: {e}", 'error')
        return redirect(url_for('settings.settings'))