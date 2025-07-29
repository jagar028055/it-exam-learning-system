#!/usr/bin/env python3
"""
情報技術者試験学習システム - Webアプリケーション
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
import secrets
import os
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

# プロジェクトルートをパスに追加
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import config
from src.core.database import DatabaseManager
from src.data.data_fetcher import IPADataFetcher, DataProcessor
from src.core.progress_tracker import ProgressTracker, StudyMode
from src.core.report_generator import ReportGenerator
from src.utils.utils import Logger, SystemError, ValidationError

# Flaskアプリケーションの初期化
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# 静的ファイルキャッシュ設定（本番環境のみ）
if os.environ.get('FLASK_ENV') == 'production':
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1年

@app.after_request
def after_request(response):
    """レスポンスヘッダーの設定"""
    # 静的ファイルのキャッシュ設定
    if request.endpoint == 'static':
        response.cache_control.max_age = 31536000  # 1年
        response.cache_control.public = True
    return response
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_DIR'] = os.environ.get('SESSION_FILE_DIR', str(config.PROJECT_ROOT / 'flask_session'))

# セッション設定
Session(app)

# CSRF保護
csrf = CSRFProtect(app)

# セキュリティヘッダー設定（本番環境のみ）
if os.environ.get('FLASK_ENV') == 'production':
    csp = {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline'",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data:",
        'font-src': "'self'",
        'connect-src': "'self'",
        'frame-src': "'none'"
    }
    Talisman(app, 
             force_https=True,
             strict_transport_security=True,
             content_security_policy=csp)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# システムコンポーネント
try:
    db = DatabaseManager()
    fetcher = IPADataFetcher()
    processor = DataProcessor()
    tracker = ProgressTracker(db)
    report_generator = ReportGenerator(db, tracker)
    logger.info("システムコンポーネント初期化完了")
except Exception as e:
    logger.error(f"システム初期化エラー: {e}")
    raise

# テンプレートフィルター
@app.template_filter('percentage')
def percentage_filter(value):
    """パーセンテージ表示フィルター"""
    if value is None:
        return "0.0%"
    return f"{value:.1f}%"

@app.template_filter('grade_class')
def grade_class_filter(rate):
    """成績に応じたCSSクラス"""
    if rate >= 80:
        return "success"
    elif rate >= 60:
        return "info"
    elif rate >= 40:
        return "warning"
    else:
        return "danger"

# ルート定義
@app.route('/')
def index():
    """トップページ"""
    try:
        # 統計情報を取得
        stats = db.get_statistics('FE')
        
        # 最近の活動
        recent_activity = db.get_learning_records(limit=5)
        
        # 推奨事項（デモ用）
        recommendations = _get_demo_recommendations()
        
        return render_template('index.html', 
                             stats=stats,
                             recent_activity=recent_activity,
                             recommendations=recommendations)
    except Exception as e:
        logger.error(f"トップページエラー: {e}")
        flash(f"エラーが発生しました: {e}", 'error')
        return render_template('index.html', stats={})

@app.route('/study')
def study():
    """学習ページ"""
    try:
        # 利用可能な試験種別を取得
        exam_types = list(config.EXAM_CATEGORIES.keys())
        
        # 分野情報を取得
        categories = list(config.SUBJECT_CATEGORIES.keys())
        
        return render_template('study.html',
                             exam_types=exam_types,
                             categories=categories)
    except Exception as e:
        logger.error(f"学習ページエラー: {e}")
        flash(f"エラーが発生しました: {e}", 'error')
        return render_template('study.html', exam_types=[], categories=[])

@app.route('/start_session', methods=['POST'])
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
            return redirect(url_for('study'))
        
        if not (1 <= count <= 100):
            flash('問題数は1〜100の範囲で指定してください。', 'error')
            return redirect(url_for('study'))
        
        if mode not in ['practice', 'mock_exam', 'review', 'weak_area']:
            flash('無効な学習モードです。', 'error')
            return redirect(url_for('study'))
        
        # 学習モードの設定
        study_mode = StudyMode.PRACTICE
        if mode == "mock_exam":
            study_mode = StudyMode.MOCK_EXAM
            count = 80
        elif mode == "review":
            study_mode = StudyMode.REVIEW
        elif mode == "weak_area":
            study_mode = StudyMode.WEAK_AREA
        
        # セッション名を生成
        session_name = f"{exam_type}_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # セッション開始
        session_id = db.create_study_session(
            session_name=session_name,
            exam_type=exam_type,
            study_mode=mode,
            total_questions=count
        )
        
        # 問題を取得
        if mode == "weak_area":
            questions = _get_weak_area_questions(exam_type, count)
        else:
            questions = db.get_random_questions(exam_type, category, count)
        
        if not questions:
            # デモ用問題を生成
            questions = _generate_demo_questions(exam_type, count)
        
        # セッション情報を保存
        session['session_id'] = session_id
        session['questions'] = questions
        session['current_question'] = 0
        session['answers'] = []
        session['start_time'] = datetime.now().isoformat()
        
        return redirect(url_for('question'))
        
    except Exception as e:
        logger.error(f"セッション開始エラー: {e}")
        flash(f"セッション開始に失敗しました: {e}", 'error')
        return redirect(url_for('study'))

@app.route('/question')
def question():
    """問題表示"""
    try:
        if 'session_id' not in session or 'questions' not in session:
            flash('セッションが見つかりません。', 'error')
            return redirect(url_for('study'))
        
        questions = session['questions']
        current_idx = session['current_question']
        
        if current_idx >= len(questions):
            return redirect(url_for('session_result'))
        
        current_question = questions[current_idx]
        
        return render_template('question.html',
                             question=current_question,
                             question_number=current_idx + 1,
                             total_questions=len(questions))
        
    except Exception as e:
        logger.error(f"問題表示エラー: {e}")
        flash(f"問題表示に失敗しました: {e}", 'error')
        return redirect(url_for('study'))

@app.route('/answer', methods=['POST'])
def answer():
    """回答処理"""
    try:
        if 'session_id' not in session or 'questions' not in session:
            flash('セッションが見つかりません。', 'error')
            return redirect(url_for('study'))
        
        user_answer = int(request.form.get('answer'))
        
        # 入力値検証
        if not (1 <= user_answer <= 4):
            return jsonify({'error': '無効な回答です'}), 400
        questions = session['questions']
        current_idx = session['current_question']
        current_question = questions[current_idx]
        
        # 回答を記録
        correct_answer = current_question.get('correct_answer', 1)
        is_correct = user_answer == correct_answer
        
        # データベースに記録（問題IDがない場合は0を使用）
        question_id = current_question.get('id', 0)
        if question_id > 0:
            db.record_answer(
                question_id=question_id,
                user_answer=user_answer,
                is_correct=is_correct,
                study_mode='practice'
            )
        
        # セッション情報を更新
        session['answers'].append({
            'question_id': question_id,
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct
        })
        
        session['current_question'] = current_idx + 1
        
        # 結果を返す
        return jsonify({
            'is_correct': is_correct,
            'correct_answer': correct_answer,
            'explanation': current_question.get('explanation', ''),
            'is_last_question': current_idx + 1 >= len(questions)
        })
        
    except Exception as e:
        logger.error(f"回答処理エラー: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/session_result')
def session_result():
    """セッション結果表示"""
    try:
        if 'session_id' not in session or 'answers' not in session:
            flash('セッションが見つかりません。', 'error')
            return redirect(url_for('study'))
        
        # セッション結果を計算
        answers = session['answers']
        total_questions = len(answers)
        correct_count = sum(1 for ans in answers if ans['is_correct'])
        
        summary = {
            'total_questions': total_questions,
            'correct_answers': correct_count,
            'incorrect_answers': total_questions - correct_count,
            'correct_rate': (correct_count / total_questions * 100) if total_questions > 0 else 0,
            'session_name': f"学習セッション_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'duration': _calculate_session_duration()
        }
        
        # セッション終了をデータベースに記録
        session_id = session.get('session_id')
        if session_id:
            db.end_study_session(session_id, correct_count)
        
        # セッション情報をクリア
        session.pop('session_id', None)
        session.pop('questions', None)
        session.pop('current_question', None)
        session.pop('answers', None)
        session.pop('start_time', None)
        
        return render_template('session_result.html',
                             summary=summary)
        
    except Exception as e:
        logger.error(f"セッション結果エラー: {e}")
        flash(f"結果表示に失敗しました: {e}", 'error')
        return redirect(url_for('study'))

@app.route('/progress')
def progress():
    """進捗ページ"""
    try:
        exam_type = request.args.get('exam_type', 'FE')
        days = int(request.args.get('days', 30))
        
        # 統計情報を取得
        stats = db.get_statistics(exam_type)
        
        # 弱点分野を取得
        weak_areas = db.get_weak_areas(exam_type, limit=5)
        
        # 時系列進捗を取得
        progress_over_time = db.get_progress_over_time(exam_type, days)
        
        progress_data = {
            'statistics': stats,
            'weak_areas': weak_areas,
            'progress_over_time': progress_over_time
        }
        
        return render_template('progress.html',
                             progress_data=progress_data,
                             exam_type=exam_type,
                             days=days)
        
    except Exception as e:
        logger.error(f"進捗ページエラー: {e}")
        flash(f"進捗表示に失敗しました: {e}", 'error')
        return render_template('progress.html', progress_data={})

@app.route('/reports')
def reports():
    """レポート一覧ページ"""
    try:
        # 既存のレポートファイルを取得
        report_files = []
        if config.REPORT_OUTPUT_DIR.exists():
            for file in config.REPORT_OUTPUT_DIR.glob('*.html'):
                report_files.append({
                    'name': file.name,
                    'path': str(file.relative_to(config.PROJECT_ROOT)),
                    'created': datetime.fromtimestamp(file.stat().st_mtime)
                })
        
        # 作成日時順にソート
        report_files.sort(key=lambda x: x['created'], reverse=True)
        
        return render_template('reports.html',
                             report_files=report_files)
        
    except Exception as e:
        logger.error(f"レポートページエラー: {e}")
        flash(f"レポート表示に失敗しました: {e}", 'error')
        return render_template('reports.html', report_files=[])

@app.route('/generate_report', methods=['POST'])
def generate_report():
    """レポート生成"""
    try:
        exam_type = request.form.get('exam_type', 'FE')
        days = int(request.form.get('days', 30))
        
        # 入力値検証
        if exam_type not in config.EXAM_CATEGORIES:
            flash('無効な試験種別です。', 'error')
            return redirect(url_for('reports'))
        
        if not (1 <= days <= 365):
            flash('日数は1〜365の範囲で指定してください。', 'error')
            return redirect(url_for('reports'))
        
        # レポート生成
        report_path = report_generator.generate_comprehensive_report(
            exam_type=exam_type,
            days=days
        )
        
        flash(f'レポートを生成しました: {report_path.name}', 'success')
        return redirect(url_for('reports'))
        
    except Exception as e:
        logger.error(f"レポート生成エラー: {e}")
        flash(f"レポート生成に失敗しました: {e}", 'error')
        return redirect(url_for('reports'))

@app.route('/report/<path:filename>')
def view_report(filename):
    """レポート表示"""
    try:
        report_path = config.REPORT_OUTPUT_DIR / filename
        if not report_path.exists():
            flash('レポートファイルが見つかりません。', 'error')
            return redirect(url_for('reports'))
        
        return send_file(report_path)
        
    except Exception as e:
        logger.error(f"レポート表示エラー: {e}")
        flash(f"レポート表示に失敗しました: {e}", 'error')
        return redirect(url_for('reports'))

@app.route('/settings')
def settings():
    """設定ページ"""
    try:
        # データベース情報
        db_info = db.get_database_info()
        
        # パフォーマンスメトリクス
        perf_metrics = db.get_performance_metrics()
        
        # キャッシュ統計
        cache_stats = db.get_cache_stats()
        
        # 設定情報
        settings_info = {
            'project_root': str(config.PROJECT_ROOT),
            'database_path': str(config.DATABASE_PATH),
            'report_output_dir': str(config.REPORT_OUTPUT_DIR),
            'log_level': config.LOG_LEVEL
        }
        
        return render_template('settings.html',
                             db_info=db_info,
                             perf_metrics=perf_metrics,
                             cache_stats=cache_stats,
                             settings_info=settings_info)
        
    except Exception as e:
        logger.error(f"設定ページエラー: {e}")
        flash(f"設定表示に失敗しました: {e}", 'error')
        return render_template('settings.html', db_info={}, settings_info={})

@app.route('/fetch_data', methods=['POST'])
def fetch_data():
    """データ取得"""
    try:
        exam_type = request.form.get('exam_type', 'FE')
        year = request.form.get('year', None)
        
        # 入力値検証
        if exam_type not in config.EXAM_CATEGORIES:
            flash('無効な試験種別です。', 'error')
            return redirect(url_for('settings'))
        
        if year:
            year = int(year)
            if not (2015 <= year <= 2025):
                flash('年度は2015〜2025の範囲で指定してください。', 'error')
                return redirect(url_for('settings'))
        
        # データ取得処理（非同期で実行すべきだが、簡単のため同期実行）
        if year:
            result = fetcher.process_exam_year(year, exam_type)
            if result['status'] == 'success':
                _save_questions_to_db(result['questions'], exam_type, year)
                flash(f'{year}年度のデータを取得しました。', 'success')
            else:
                flash(f'{year}年度のデータ取得に失敗しました。', 'error')
        else:
            # 全年度取得（時間がかかるため、実際の運用では非同期処理が必要）
            flash('全年度のデータ取得を開始しました。時間がかかる場合があります。', 'info')
            exam_list = fetcher.fetch_exam_list(exam_type)
            success_count = 0
            
            for exam in exam_list[:3]:  # 最新3年度のみ
                try:
                    result = fetcher.process_exam_year(exam['year'], exam_type)
                    if result['status'] == 'success':
                        _save_questions_to_db(result['questions'], exam_type, exam['year'])
                        success_count += 1
                except Exception as e:
                    logger.error(f"{exam['year']}年度処理エラー: {e}")
                    continue
            
            flash(f'{success_count}年度のデータを取得しました。', 'success')
        
        return redirect(url_for('settings'))
        
    except Exception as e:
        logger.error(f"データ取得エラー: {e}")
        flash(f"データ取得に失敗しました: {e}", 'error')
        return redirect(url_for('settings'))

@app.route('/optimize_db', methods=['POST'])
def optimize_db():
    """データベース最適化"""
    try:
        db.optimize_database()
        flash('データベースを最適化しました。', 'success')
        return redirect(url_for('settings'))
    except Exception as e:
        logger.error(f"データベース最適化エラー: {e}")
        flash(f"データベース最適化に失敗しました: {e}", 'error')
        return redirect(url_for('settings'))

@app.route('/api/stats')
def api_stats():
    """統計情報API"""
    try:
        exam_type = request.args.get('exam_type', 'FE')
        stats = db.get_statistics(exam_type)
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/questions')
def api_questions():
    """問題取得API"""
    try:
        exam_type = request.args.get('exam_type', 'FE')
        category = request.args.get('category', None)
        count = int(request.args.get('count', 20))
        
        questions = db.get_random_questions(exam_type, category, count)
        return jsonify(questions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """ヘルスチェックエンドポイント (Render用)"""
    try:
        # データベース接続確認
        db_info = db.get_database_info()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'tables': db_info.get('table_count', 0)
        })
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        return jsonify({
            'status': 'unhealthy', 
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/ping')
def ping():
    """UptimeRobot用軽量ピングエンドポイント"""
    return 'pong'

# ヘルパー関数
def _get_weak_area_questions(exam_type: str, count: int) -> List[Dict]:
    """弱点分野の問題を取得"""
    weak_areas = db.get_weak_areas(exam_type, limit=3)
    if not weak_areas:
        return db.get_random_questions(exam_type, None, count)
    
    questions = []
    questions_per_area = count // len(weak_areas)
    
    for area in weak_areas:
        area_questions = db.get_random_questions(
            exam_type, area['category'], questions_per_area
        )
        questions.extend(area_questions)
    
    # 不足分を補う
    remaining = count - len(questions)
    if remaining > 0:
        additional = db.get_random_questions(exam_type, None, remaining)
        questions.extend(additional)
    
    return questions[:count]

def _generate_demo_questions(exam_type: str, count: int) -> List[Dict]:
    """デモ用問題を生成"""
    demo_questions = []
    
    for i in range(count):
        question = {
            'id': i + 1,
            'exam_type': exam_type,
            'year': 2024,
            'question_number': i + 1,
            'question_text': f"問題{i + 1}: {exam_type}に関する基本的な問題です。",
            'choices': [
                f"選択肢{i + 1}-1",
                f"選択肢{i + 1}-2", 
                f"選択肢{i + 1}-3",
                f"選択肢{i + 1}-4"
            ],
            'correct_answer': (i % 4) + 1,
            'explanation': f"問題{i + 1}の解説です。",
            'category': 'テクノロジ系',
            'subcategory': 'システム構成要素',
            'difficulty_level': 2
        }
        demo_questions.append(question)
    
    return demo_questions

def _get_demo_recommendations() -> List[Dict]:
    """デモ用推奨事項を取得"""
    return [
        {
            'title': '弱点分野の集中学習',
            'description': 'ネットワーク分野での正答率が低めです。',
            'priority': 'high'
        },
        {
            'title': '模擬試験の実施',
            'description': '全分野バランスよく出題される模擬試験を実施しましょう。',
            'priority': 'medium'
        },
        {
            'title': '継続的な学習',
            'description': '毎日少しずつでも学習を続けることが重要です。',
            'priority': 'low'
        }
    ]

def _calculate_session_duration() -> int:
    """セッション時間を計算"""
    start_time_str = session.get('start_time')
    if not start_time_str:
        return 0
    
    start_time = datetime.fromisoformat(start_time_str)
    end_time = datetime.now()
    duration = int((end_time - start_time).total_seconds())
    return duration

def _save_questions_to_db(questions: List[Dict], exam_type: str, year: int):
    """問題をデータベースに保存"""
    try:
        # 分野分類を実行
        questions = processor.categorize_questions(questions)
        
        # データ検証
        valid_questions, invalid_questions = processor.validate_question_data(questions)
        
        # データベースに保存
        for question in valid_questions:
            question['exam_type'] = exam_type
            question['year'] = year
            try:
                db.insert_question(question)
            except Exception as e:
                logger.error(f"問題保存エラー: {e}")
                continue
        
        logger.info(f"データベース保存完了: {len(valid_questions)} 問題")
        
    except Exception as e:
        logger.error(f"データベース保存エラー: {e}")
        raise

# エラーハンドリング
@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404エラー: {request.url}")
    return render_template('error.html', 
                         error_code=404, 
                         error_message="ページが見つかりません"), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500エラー: {error}")
    return render_template('error.html', 
                         error_code=500, 
                         error_message="内部サーバーエラーが発生しました"), 500

@app.errorhandler(400)
def bad_request(error):
    logger.warning(f"400エラー: {error}")
    return render_template('error.html',
                         error_code=400,
                         error_message="不正なリクエストです"), 400

@app.errorhandler(403)
def forbidden(error):
    logger.warning(f"403エラー: {error}")
    return render_template('error.html',
                         error_code=403,
                         error_message="アクセスが拒否されました"), 403

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"予期しないエラー: {e}")
    return render_template('error.html',
                         error_code=500,
                         error_message="予期しないエラーが発生しました"), 500

if __name__ == '__main__':
    # 必要なディレクトリを作成
    config.create_directories()
    
    # セッション用ディレクトリを作成
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    
    # 開発サーバーを起動
    app.run(debug=True, host='0.0.0.0', port=5001)