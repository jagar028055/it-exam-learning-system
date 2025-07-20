#!/usr/bin/env python3
"""
情報技術者試験学習システム - デモンストレーション用Webアプリケーション
"""

from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'demo-secret-key'

# デモ用のサンプルデータ
sample_stats = {
    'total_questions': 240,
    'total_correct': 180,
    'overall_correct_rate': 0.75,
    'categories_studied': 8
}

sample_recent_activity = [
    {
        'category': 'テクノロジ系',
        'attempt_date': '2025-01-15 14:30:00',
        'is_correct': True
    },
    {
        'category': 'マネジメント系',
        'attempt_date': '2025-01-15 14:25:00',
        'is_correct': False
    },
    {
        'category': 'ストラテジ系',
        'attempt_date': '2025-01-15 14:20:00',
        'is_correct': True
    }
]

sample_recommendations = [
    {
        'title': '「マネジメント系」の強化学習',
        'description': '正答率65%の分野です。重点的に学習しましょう。',
        'priority': 'high'
    },
    {
        'title': '学習量の増加',
        'description': '現在240問を学習済み。300問を目標にしましょう。',
        'priority': 'medium'
    },
    {
        'title': '継続的な学習',
        'description': '毎日少しずつでも継続学習を心がけましょう。',
        'priority': 'low'
    }
]

sample_questions = [
    {
        'id': 1,
        'question_text': 'コンピュータの基本的な構成要素として、演算処理を担当する部分は何か。',
        'choices': ['CPU', 'メモリ', 'ハードディスク', 'マザーボード'],
        'correct_answer': 1,
        'category': 'テクノロジ系',
        'difficulty_level': 1,
        'explanation': 'CPU（Central Processing Unit）は中央処理装置とも呼ばれ、コンピュータの演算処理を担当します。'
    },
    {
        'id': 2,
        'question_text': 'データベースの正規化の目的として、最も適切なものはどれか。',
        'choices': ['データの高速化', 'データの重複排除', 'データの暗号化', 'データの圧縮'],
        'correct_answer': 2,
        'category': 'テクノロジ系',
        'difficulty_level': 2,
        'explanation': 'データベースの正規化は、データの重複を排除し、データの整合性を保つことが主な目的です。'
    }
]

@app.route('/')
def index():
    """ダッシュボード"""
    return render_template('web/index.html', 
                         stats=sample_stats,
                         recent_activity=sample_recent_activity,
                         recommendations=sample_recommendations)

@app.route('/study')
def study():
    """学習ページ"""
    return render_template('web/study.html',
                         exam_types=['FE', 'AP', 'IP', 'SG'],
                         categories=['テクノロジ系', 'マネジメント系', 'ストラテジ系'])

@app.route('/start_session', methods=['POST'])
def start_session():
    """学習セッション開始（デモ用）"""
    # セッション設定を取得
    exam_type = request.form.get('exam_type', 'FE')
    mode = request.form.get('mode', 'practice')
    count = int(request.form.get('count', 20))
    
    # デモ用の問題を準備
    questions = sample_questions * (count // 2 + 1)
    questions = questions[:count]
    
    # セッション情報を簡単に管理（実際にはセッションまたはDBに保存）
    session_data = {
        'questions': questions,
        'current_question': 0,
        'answers': [],
        'start_time': datetime.now().isoformat()
    }
    
    # 最初の問題を表示
    return render_template('web/question.html',
                         question=questions[0],
                         question_number=1,
                         total_questions=len(questions),
                         session_data=json.dumps(session_data))

@app.route('/demo_question')
def demo_question():
    """デモ用問題ページ"""
    return render_template('web/question.html',
                         question=sample_questions[0],
                         question_number=1,
                         total_questions=2)

@app.route('/answer', methods=['POST'])
def answer():
    """回答処理（デモ用）"""
    user_answer = int(request.form.get('answer'))
    question_id = int(request.form.get('question_id', 1))
    
    # デモ用の固定応答
    correct_answer = sample_questions[0]['correct_answer']
    is_correct = user_answer == correct_answer
    
    return jsonify({
        'is_correct': is_correct,
        'correct_answer': correct_answer,
        'explanation': sample_questions[0]['explanation'],
        'is_last_question': question_id >= len(sample_questions)
    })

@app.route('/session_result')
def session_result():
    """セッション結果（デモ用）"""
    # デモ用の結果データ
    demo_summary = {
        'total_questions': 20,
        'correct_answers': 15,
        'incorrect_answers': 5,
        'correct_rate': 0.75,
        'average_response_time': 45.0,
        'total_time': 900,  # 15分
        'categories_studied': ['テクノロジ系', 'マネジメント系'],
        'weak_areas': ['マネジメント系'],
        'achievements': ['75%以上の正答率', '平均回答時間45秒以内']
    }
    
    return render_template('web/session_result.html', summary=demo_summary)

@app.route('/progress')
def progress():
    """進捗ページ（デモ用）"""
    demo_progress = {
        'overall_statistics': sample_stats,
        'category_statistics': [
            {'category': 'テクノロジ系', 'total_questions': 120, 'correct_answers': 96, 'correct_rate': 80.0},
            {'category': 'マネジメント系', 'total_questions': 80, 'correct_answers': 52, 'correct_rate': 65.0},
            {'category': 'ストラテジ系', 'total_questions': 40, 'correct_answers': 32, 'correct_rate': 80.0}
        ],
        'weak_areas': [
            {'category': 'マネジメント系', 'correct_rate': 65.0, 'total_questions': 80}
        ],
        'recent_activity': sample_recent_activity
    }
    
    demo_analysis = {
        'basic_stats': {
            'total_questions': 240,
            'correct_answers': 180,
            'correct_rate': 0.75,
            'study_days': 15
        },
        'growth_trend': {
            'trend': 'improving',
            'weekly_rates': [0.60, 0.65, 0.70, 0.75]
        },
        'performance_prediction': {
            'prediction': 'high_pass_probability',
            'recent_performance': 0.80,
            'overall_performance': 0.75
        }
    }
    
    return render_template('web/progress.html',
                         progress_data=demo_progress,
                         detailed_analysis=demo_analysis,
                         exam_type='FE',
                         days=30)

@app.route('/reports')
def reports():
    """レポート一覧（デモ用）"""
    demo_reports = [
        {
            'name': 'comprehensive_report_FE_20250717_143000.html',
            'path': 'reports/comprehensive_report_FE_20250717_143000.html',
            'created': datetime.now()
        },
        {
            'name': 'session_report_20250717_142500.html',
            'path': 'reports/session_report_20250717_142500.html',
            'created': datetime.now()
        },
        {
            'name': 'comprehensive_report_FE_20250716_101500.html',
            'path': 'reports/comprehensive_report_FE_20250716_101500.html',
            'created': datetime.now()
        }
    ]
    
    return render_template('web/reports.html', report_files=demo_reports)

@app.route('/generate_report', methods=['POST'])
def generate_report():
    """レポート生成（デモ用）"""
    exam_type = request.form.get('exam_type', 'FE')
    days = request.form.get('days', '30')
    
    # デモ用のレポート生成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_name = f'comprehensive_report_{exam_type}_{timestamp}.html'
    
    # 簡単なHTMLレポートを生成
    report_html = f'''
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>学習レポート - {exam_type}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <div class="container mt-5">
            <h1 class="text-center mb-4">📊 学習レポート</h1>
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5>学習概要</h5>
                        </div>
                        <div class="card-body">
                            <p><strong>試験種別:</strong> {exam_type}</p>
                            <p><strong>対象期間:</strong> 過去{days}日間</p>
                            <p><strong>生成日時:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5>統計情報</h5>
                        </div>
                        <div class="card-body">
                            <p><strong>学習問題数:</strong> 240問</p>
                            <p><strong>正答率:</strong> 75%</p>
                            <p><strong>学習日数:</strong> 15日</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="mt-4 text-center">
                <p class="text-muted">これはデモンストレーション用のレポートです。</p>
            </div>
        </div>
    </body>
    </html>
    '''
    
    # reportsディレクトリを作成
    os.makedirs('reports', exist_ok=True)
    
    # レポートファイルを保存
    with open(f'reports/{report_name}', 'w', encoding='utf-8') as f:
        f.write(report_html)
    
    return jsonify({
        'success': True,
        'report_name': report_name,
        'message': 'レポートが生成されました'
    })

@app.route('/view_report/<filename>')
def view_report(filename):
    """レポート表示"""
    try:
        with open(f'reports/{filename}', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return "レポートが見つかりません", 404

@app.route('/report/<filename>')
def download_report(filename):
    """レポートダウンロード"""
    try:
        with open(f'reports/{filename}', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return "レポートが見つかりません", 404

@app.route('/settings')
def settings():
    """設定ページ（デモ用）"""
    demo_db_info = {
        'questions_count': 1250,
        'learning_records_count': 240,
        'study_sessions_count': 15,
        'file_size': 2048000,  # 2MB
        'last_modified': datetime.now()
    }
    
    demo_settings = {
        'project_root': '/path/to/project',
        'database_path': '/path/to/database.db',
        'report_output_dir': '/path/to/reports',
        'log_level': 'INFO'
    }
    
    return render_template('web/settings.html',
                         db_info=demo_db_info,
                         settings_info=demo_settings)

@app.route('/settings/fetch_data', methods=['POST'])
def fetch_data():
    """データ取得（デモ用）"""
    exam_type = request.form.get('exam_type', 'FE')
    year = request.form.get('year', '2023')
    
    # デモ用のレスポンス
    return jsonify({
        'success': True,
        'message': f'{exam_type} {year}年度のデータ取得を開始しました（デモ機能）',
        'fetched_questions': 150,
        'new_questions': 45
    })

@app.route('/settings/backup', methods=['POST'])
def backup_database():
    """バックアップ（デモ用）"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'backup_{timestamp}.db'
    
    # デモ用のバックアップ処理
    return jsonify({
        'success': True,
        'message': f'バックアップが作成されました: {backup_name}',
        'backup_file': backup_name
    })

@app.route('/settings/optimize', methods=['POST'])
def optimize_database():
    """データベース最適化（デモ用）"""
    return jsonify({
        'success': True,
        'message': 'データベースの最適化が完了しました',
        'old_size': '2.1MB',
        'new_size': '1.8MB',
        'improvement': '14.3%'
    })

@app.route('/api/stats')
def api_stats():
    """統計情報API（デモ用）"""
    return jsonify({
        'overall_statistics': sample_stats,
        'category_statistics': [
            {'category': 'テクノロジ系', 'correct_rate': 80.0, 'total_questions': 120},
            {'category': 'マネジメント系', 'correct_rate': 65.0, 'total_questions': 80},
            {'category': 'ストラテジ系', 'correct_rate': 80.0, 'total_questions': 40}
        ]
    })

@app.route('/api/questions')
def api_questions():
    """問題取得API（デモ用）"""
    count = int(request.args.get('count', 20))
    questions = sample_questions * (count // 2 + 1)
    return jsonify(questions[:count])

# 追加のテンプレートページ
@app.route('/template_showcase')
def template_showcase():
    """テンプレートショーケース"""
    return '''
    <html>
    <head>
        <title>テンプレートショーケース</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .template-link { 
                display: block; 
                margin: 10px 0; 
                padding: 10px; 
                background: #f0f0f0; 
                text-decoration: none; 
                border-radius: 5px;
            }
            .template-link:hover { background: #e0e0e0; }
        </style>
    </head>
    <body>
        <h1>🎯 情報技術者試験学習システム - テンプレートショーケース</h1>
        
        <h2>主要ページ</h2>
        <a href="/" class="template-link">📊 ダッシュボード - 学習統計と概要</a>
        <a href="/study" class="template-link">📚 学習ページ - セッション設定</a>
        <a href="/demo_question" class="template-link">❓ 問題ページ - インタラクティブ問題</a>
        <a href="/session_result" class="template-link">🎉 結果ページ - セッション結果</a>
        <a href="/progress" class="template-link">📈 進捗ページ - 学習進捗分析</a>
        <a href="/reports" class="template-link">📄 レポート一覧 - 生成済みレポート</a>
        <a href="/settings" class="template-link">⚙️ 設定ページ - システム設定</a>
        
        <h2>API エンドポイント</h2>
        <a href="/api/stats" class="template-link">📊 統計API - JSON形式の統計データ</a>
        <a href="/api/questions" class="template-link">❓ 問題API - JSON形式の問題データ</a>
        
        <h2>特徴</h2>
        <ul>
            <li>✅ レスポンシブデザイン（PC・タブレット・スマホ対応）</li>
            <li>✅ Bootstrap 5.1.3 を使用</li>
            <li>✅ Font Awesome アイコン</li>
            <li>✅ Chart.js によるグラフ表示</li>
            <li>✅ インタラクティブな問題解答</li>
            <li>✅ リアルタイムの結果フィードバック</li>
            <li>✅ 美しいアニメーション効果</li>
        </ul>
        
        <p><strong>注意:</strong> これはデモンストレーション用のサンプルデータです。実際の運用には完全なセットアップが必要です。</p>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("🚀 情報技術者試験学習システム - デモサーバー起動")
    print("📱 アクセス URL: http://localhost:5001")
    print("🎯 テンプレート一覧: http://localhost:5001/template_showcase")
    print("⏹️  停止するには Ctrl+C を押してください")
    
    app.run(debug=True, host='0.0.0.0', port=5001)