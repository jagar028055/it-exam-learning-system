"""
進捗・レポート関連のルート定義
"""

import logging
from pathlib import Path
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file

from ..services.progress_service import ProgressService
from ...core.config import config

logger = logging.getLogger(__name__)

# Blueprint作成
progress_bp = Blueprint('progress', __name__)

# サービス初期化は後でDIで行う
progress_service = None

def init_services(progress_svc):
    """サービスの初期化"""
    global progress_service
    progress_service = progress_svc

@progress_bp.route('/progress')
def progress():
    """進捗ページ"""
    try:
        exam_type = request.args.get('exam_type', 'FE')
        days = int(request.args.get('days', 30))
        
        progress_data = progress_service.get_progress_data(exam_type, days)
        
        return render_template('progress.html',
                             progress_data=progress_data,
                             exam_type=exam_type,
                             days=days)
        
    except Exception as e:
        logger.error(f"進捗ページエラー: {e}")
        flash(f"進捗表示に失敗しました: {e}", 'error')
        return render_template('progress.html', progress_data={})

@progress_bp.route('/reports')
def reports():
    """レポート一覧ページ"""
    try:
        report_files = progress_service.get_report_files()
        
        return render_template('reports.html',
                             report_files=report_files)
        
    except Exception as e:
        logger.error(f"レポートページエラー: {e}")
        flash(f"レポート表示に失敗しました: {e}", 'error')
        return render_template('reports.html', report_files=[])

@progress_bp.route('/generate_report', methods=['POST'])
def generate_report():
    """レポート生成"""
    try:
        exam_type = request.form.get('exam_type', 'FE')
        days = int(request.form.get('days', 30))
        
        # 入力値検証
        if exam_type not in config.EXAM_CATEGORIES:
            flash('無効な試験種別です。', 'error')
            return redirect(url_for('progress.reports'))
        
        if not (1 <= days <= 365):
            flash('日数は1〜365の範囲で指定してください。', 'error')
            return redirect(url_for('progress.reports'))
        
        # レポート生成
        report_path = progress_service.generate_comprehensive_report(
            exam_type=exam_type,
            days=days
        )
        
        flash(f'レポートを生成しました: {report_path.name}', 'success')
        return redirect(url_for('progress.reports'))
        
    except Exception as e:
        logger.error(f"レポート生成エラー: {e}")
        flash(f"レポート生成に失敗しました: {e}", 'error')
        return redirect(url_for('progress.reports'))

@progress_bp.route('/report/<path:filename>')
def view_report(filename):
    """レポート表示"""
    try:
        report_path = config.REPORT_OUTPUT_DIR / filename
        if not report_path.exists():
            flash('レポートファイルが見つかりません。', 'error')
            return redirect(url_for('progress.reports'))
        
        return send_file(report_path)
        
    except Exception as e:
        logger.error(f"レポート表示エラー: {e}")
        flash(f"レポート表示に失敗しました: {e}", 'error')
        return redirect(url_for('progress.reports'))