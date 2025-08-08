"""
学習関連のルート定義
"""

import logging
from datetime import datetime
from typing import Dict, List

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash

from ..services.study_service import StudyService
from ..services.session_service import SessionService
from ...core.config import config
from ...core.progress_tracker import StudyMode

logger = logging.getLogger(__name__)

# Blueprint作成
study_bp = Blueprint('study', __name__)

# サービス初期化は後でDIで行う
study_service = None
session_service = None

def init_services(study_svc, session_svc):
    """サービスの初期化"""
    global study_service, session_service
    study_service = study_svc
    session_service = session_svc

@study_bp.route('/study')
def study():
    """学習ページ"""
    try:
        # 利用可能な試験種別を取得
        exam_types = config.EXAM_CATEGORIES
        
        # 分野情報を取得
        categories = list(config.SUBJECT_CATEGORIES.keys())
        
        return render_template('study.html',
                             exam_types=exam_types,
                             categories=categories)
    except Exception as e:
        logger.error(f"学習ページエラー: {e}")
        flash(f"エラーが発生しました: {e}", 'error')
        return render_template('study.html', exam_types={}, categories=[])

@study_bp.route('/start_session', methods=['POST'])
def start_session():
    """学習セッション開始"""
    try:
        exam_type = request.form.get('exam_type', 'FE')
        mode = request.form.get('mode', 'practice')
        count = int(request.form.get('count', 20))
        category = request.form.get('category', None)
        
        # 入力値検証
        if exam_type not in config.EXAM_CATEGORIES:
            flash('無効な試験種別です。', 'error')
            return redirect(url_for('study.study'))
        
        if not (1 <= count <= 100):
            flash('問題数は1〜100の範囲で指定してください。', 'error')
            return redirect(url_for('study.study'))
        
        if mode not in ['practice', 'mock_exam', 'review', 'weak_area']:
            flash('無効な学習モードです。', 'error')
            return redirect(url_for('study.study'))
        
        # セッション開始処理をサービスに委譲
        session_id = session_service.start_study_session(
            exam_type=exam_type,
            mode=mode,
            count=count,
            category=category
        )
        
        return redirect(url_for('study.question'))
        
    except Exception as e:
        logger.error(f"セッション開始エラー: {e}")
        flash(f"セッション開始に失敗しました: {e}", 'error')
        return redirect(url_for('study.study'))

@study_bp.route('/question')
def question():
    """問題表示"""
    try:
        if 'session_id' not in session or 'questions' not in session:
            flash('セッションが見つかりません。', 'error')
            return redirect(url_for('study.study'))
        
        questions = session['questions']
        current_idx = session['current_question']
        
        if current_idx >= len(questions):
            return redirect(url_for('study.session_result'))
        
        current_question = questions[current_idx]
        
        return render_template('question.html',
                             question=current_question,
                             question_number=current_idx + 1,
                             total_questions=len(questions))
        
    except Exception as e:
        logger.error(f"問題表示エラー: {e}")
        flash(f"問題表示に失敗しました: {e}", 'error')
        return redirect(url_for('study.study'))

@study_bp.route('/answer', methods=['POST'])
def answer():
    """回答処理"""
    try:
        if 'session_id' not in session or 'questions' not in session:
            return jsonify({'error': 'セッションが見つかりません'}), 400
        
        user_answer = int(request.form.get('answer'))
        
        # 回答処理をサービスに委譲
        result = session_service.process_answer(user_answer)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"回答処理エラー: {e}")
        return jsonify({'error': str(e)}), 500

@study_bp.route('/session_result')
def session_result():
    """セッション結果表示"""
    try:
        if 'session_id' not in session or 'answers' not in session:
            flash('セッションが見つかりません。', 'error')
            return redirect(url_for('study.study'))
        
        # 結果計算をサービスに委譲
        summary = session_service.calculate_session_result()
        
        # セッション情報をクリア
        session_service.clear_session()
        
        return render_template('session_result.html', summary=summary)
        
    except Exception as e:
        logger.error(f"セッション結果エラー: {e}")
        flash(f"結果表示に失敗しました: {e}", 'error')
        return redirect(url_for('study.study'))