"""
情報技術者試験学習システム - レポート生成モジュール
"""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from jinja2 import Environment, FileSystemLoader

from .config import config
from .database import DatabaseManager
from .progress_tracker import ProgressTracker
from ..utils.utils import Logger, FileUtils, DataUtils

class ChartGenerator:
    """チャート生成クラス"""
    
    def __init__(self):
        self.colors = config.CHART_COLORS
        self.logger = Logger.setup_logger(
            "ChartGenerator",
            config.LOG_FILE,
            config.LOG_LEVEL
        )
    
    def create_progress_chart(self, progress_data: List[Dict]) -> go.Figure:
        """進捗チャートを作成"""
        if not progress_data:
            return self._create_empty_chart("進捗データがありません")
        
        dates = [data['study_date'] for data in progress_data]
        correct_rates = [data['correct_rate'] for data in progress_data]
        total_questions = [data['total_questions'] for data in progress_data]
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('正答率の推移', '学習量の推移'),
            specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
        )
        
        # 正答率の推移
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=correct_rates,
                mode='lines+markers',
                name='正答率',
                line=dict(color=self.colors[0], width=3),
                marker=dict(size=8)
            ),
            row=1, col=1
        )
        
        # 目標ライン（60%）
        fig.add_hline(
            y=60, line_dash="dash", line_color="red",
            annotation_text="合格ライン（60%）",
            row=1, col=1
        )
        
        # 学習量の推移
        fig.add_trace(
            go.Bar(
                x=dates,
                y=total_questions,
                name='学習問題数',
                marker_color=self.colors[1]
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            title="学習進捗レポート",
            height=600,
            showlegend=True
        )
        
        fig.update_yaxes(title_text="正答率 (%)", row=1, col=1)
        fig.update_yaxes(title_text="問題数", row=2, col=1)
        fig.update_xaxes(title_text="日付", row=2, col=1)
        
        return fig
    
    def create_category_performance_chart(self, category_stats: List[Dict]) -> go.Figure:
        """分野別パフォーマンスチャートを作成"""
        if not category_stats:
            return self._create_empty_chart("分野別データがありません")
        
        categories = [stat['category'] for stat in category_stats]
        correct_rates = [stat['correct_rate'] for stat in category_stats]
        total_questions = [stat['total_questions'] for stat in category_stats]
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('分野別正答率', '分野別学習量'),
            specs=[[{"type": "bar"}, {"type": "bar"}]]
        )
        
        # 分野別正答率
        colors = [self.colors[0] if rate >= 60 else self.colors[1] for rate in correct_rates]
        
        fig.add_trace(
            go.Bar(
                x=categories,
                y=correct_rates,
                name='正答率',
                marker_color=colors,
                text=[f"{rate:.1f}%" for rate in correct_rates],
                textposition='auto'
            ),
            row=1, col=1
        )
        
        # 分野別学習量
        fig.add_trace(
            go.Bar(
                x=categories,
                y=total_questions,
                name='学習量',
                marker_color=self.colors[2],
                text=total_questions,
                textposition='auto'
            ),
            row=1, col=2
        )
        
        fig.update_layout(
            title="分野別パフォーマンス",
            height=500,
            showlegend=False
        )
        
        fig.update_yaxes(title_text="正答率 (%)", row=1, col=1)
        fig.update_yaxes(title_text="問題数", row=1, col=2)
        fig.update_xaxes(tickangle=45)
        
        return fig
    
    def create_weak_areas_chart(self, weak_areas: List[Dict]) -> go.Figure:
        """弱点分野チャートを作成"""
        if not weak_areas:
            return self._create_empty_chart("弱点分野がありません（素晴らしい！）")
        
        categories = [area['category'] for area in weak_areas]
        correct_rates = [area['correct_rate'] for area in weak_areas]
        total_questions = [area['total_questions'] for area in weak_areas]
        
        fig = go.Figure()
        
        fig.add_trace(
            go.Bar(
                x=categories,
                y=correct_rates,
                name='正答率',
                marker_color=self.colors[1],  # 赤系
                text=[f"{rate:.1f}%" for rate in correct_rates],
                textposition='auto',
                customdata=total_questions,
                hovertemplate='<b>%{x}</b><br>' +
                             '正答率: %{y:.1f}%<br>' +
                             '問題数: %{customdata}<br>' +
                             '<extra></extra>'
            )
        )
        
        fig.add_hline(
            y=60, line_dash="dash", line_color="green",
            annotation_text="目標ライン（60%）"
        )
        
        fig.update_layout(
            title="弱点分野（優先改善対象）",
            xaxis_title="分野",
            yaxis_title="正答率 (%)",
            height=400,
            showlegend=False
        )
        
        fig.update_xaxes(tickangle=45)
        
        return fig
    
    def create_study_pattern_chart(self, learning_patterns: Dict) -> go.Figure:
        """学習パターンチャートを作成"""
        if not learning_patterns.get('hourly_performance'):
            return self._create_empty_chart("学習パターンデータがありません")
        
        hourly_data = learning_patterns['hourly_performance']
        
        hours = list(hourly_data.keys())
        correct_rates = [stats['correct'] / stats['total'] * 100 
                        for stats in hourly_data.values()]
        question_counts = [stats['total'] for stats in hourly_data.values()]
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('時間帯別正答率', '時間帯別学習量'),
            specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
        )
        
        # 時間帯別正答率
        fig.add_trace(
            go.Scatter(
                x=hours,
                y=correct_rates,
                mode='lines+markers',
                name='正答率',
                line=dict(color=self.colors[0], width=3),
                marker=dict(size=8)
            ),
            row=1, col=1
        )
        
        # 時間帯別学習量
        fig.add_trace(
            go.Bar(
                x=hours,
                y=question_counts,
                name='学習量',
                marker_color=self.colors[2]
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            title="学習パターン分析",
            height=600,
            showlegend=False
        )
        
        fig.update_yaxes(title_text="正答率 (%)", row=1, col=1)
        fig.update_yaxes(title_text="問題数", row=2, col=1)
        fig.update_xaxes(title_text="時間", row=2, col=1)
        
        return fig
    
    def create_difficulty_distribution_chart(self, difficulty_stats: Dict) -> go.Figure:
        """難易度分布チャートを作成"""
        if not difficulty_stats:
            return self._create_empty_chart("難易度データがありません")
        
        difficulties = list(difficulty_stats.keys())
        correct_rates = [stats['correct_rate'] * 100 for stats in difficulty_stats.values()]
        totals = [stats['total'] for stats in difficulty_stats.values()]
        
        difficulty_names = {
            1: "基礎",
            2: "標準", 
            3: "応用",
            4: "高度"
        }
        
        labels = [difficulty_names.get(d, f"難易度{d}") for d in difficulties]
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('難易度別正答率', '難易度別問題数'),
            specs=[[{"type": "bar"}, {"type": "pie"}]]
        )
        
        # 難易度別正答率
        fig.add_trace(
            go.Bar(
                x=labels,
                y=correct_rates,
                name='正答率',
                marker_color=self.colors[:len(labels)],
                text=[f"{rate:.1f}%" for rate in correct_rates],
                textposition='auto'
            ),
            row=1, col=1
        )
        
        # 難易度別問題数（パイチャート）
        fig.add_trace(
            go.Pie(
                labels=labels,
                values=totals,
                name='問題数',
                textinfo='label+percent',
                marker_colors=self.colors[:len(labels)]
            ),
            row=1, col=2
        )
        
        fig.update_layout(
            title="難易度別分析",
            height=400,
            showlegend=False
        )
        
        fig.update_yaxes(title_text="正答率 (%)", row=1, col=1)
        
        return fig
    
    def create_achievement_chart(self, achievements: List[str]) -> go.Figure:
        """達成状況チャートを作成"""
        if not achievements:
            return self._create_empty_chart("まだ達成項目がありません")
        
        # 達成項目を分類
        achievement_types = {
            '正答率': 0,
            '連続正解': 0,
            '難問': 0,
            '速答': 0,
            'その他': 0
        }
        
        for achievement in achievements:
            if '成績' in achievement:
                achievement_types['正答率'] += 1
            elif '連続正解' in achievement:
                achievement_types['連続正解'] += 1
            elif '難問' in achievement:
                achievement_types['難問'] += 1
            elif '速答' in achievement:
                achievement_types['速答'] += 1
            else:
                achievement_types['その他'] += 1
        
        # 0の項目を除外
        achievement_types = {k: v for k, v in achievement_types.items() if v > 0}
        
        fig = go.Figure()
        
        fig.add_trace(
            go.Bar(
                x=list(achievement_types.keys()),
                y=list(achievement_types.values()),
                name='達成数',
                marker_color=self.colors[4],  # 紫系
                text=list(achievement_types.values()),
                textposition='auto'
            )
        )
        
        fig.update_layout(
            title="達成状況",
            xaxis_title="達成項目",
            yaxis_title="達成数",
            height=400,
            showlegend=False
        )
        
        return fig
    
    def _create_empty_chart(self, message: str) -> go.Figure:
        """空のチャートを作成"""
        fig = go.Figure()
        
        fig.add_annotation(
            x=0.5,
            y=0.5,
            text=message,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        
        fig.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            height=300
        )
        
        return fig

class ReportGenerator:
    """レポート生成クラス"""
    
    def __init__(self, db_manager: DatabaseManager = None, 
                 progress_tracker: ProgressTracker = None):
        """
        初期化
        
        Args:
            db_manager: データベースマネージャー
            progress_tracker: 進捗追跡器
        """
        self.db = db_manager or DatabaseManager()
        self.tracker = progress_tracker or ProgressTracker(self.db)
        self.chart_generator = ChartGenerator()
        
        # ログ設定
        self.logger = Logger.setup_logger(
            "ReportGenerator",
            config.LOG_FILE,
            config.LOG_LEVEL
        )
        
        # Jinja2環境設定
        self.jinja_env = Environment(
            loader=FileSystemLoader(config.TEMPLATE_DIR),
            autoescape=True
        )
        
        # 出力ディレクトリ作成
        config.REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    def generate_comprehensive_report(self, exam_type: str = "FE", 
                                    days: int = 30) -> Path:
        """
        包括的なレポートを生成
        
        Args:
            exam_type: 試験種別
            days: 対象日数
            
        Returns:
            Path: レポートファイルパス
        """
        self.logger.info(f"包括的レポート生成開始: {exam_type}")
        
        # データ取得
        progress_data = self.tracker.get_overall_progress(exam_type, days)
        detailed_analysis = self.tracker.get_detailed_analysis(exam_type)
        recommendations = self.tracker.get_study_recommendations(exam_type)
        
        # チャート生成
        charts = self._generate_all_charts(progress_data, detailed_analysis)
        
        # レポートデータ準備
        report_data = {
            'title': f'{exam_type} 学習進捗レポート',
            'generated_at': datetime.now().strftime('%Y年%m月%d日 %H:%M'),
            'exam_type': exam_type,
            'period_days': days,
            'progress_data': progress_data,
            'detailed_analysis': detailed_analysis,
            'recommendations': recommendations,
            'charts': charts,
            'summary': self._generate_summary(progress_data)
        }
        
        # HTMLレポート生成
        html_content = self._render_html_report(report_data)
        
        # ファイル保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = config.REPORT_OUTPUT_DIR / f'comprehensive_report_{exam_type}_{timestamp}.html'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"レポート生成完了: {report_path}")
        return report_path
    
    def generate_session_report(self, session_summary: Dict) -> Path:
        """
        セッションレポートを生成
        
        Args:
            session_summary: セッション概要
            
        Returns:
            Path: レポートファイルパス
        """
        self.logger.info("セッションレポート生成開始")
        
        # セッション用チャート生成
        charts = self._generate_session_charts(session_summary)
        
        # レポートデータ準備
        report_data = {
            'title': 'セッション結果レポート',
            'generated_at': datetime.now().strftime('%Y年%m月%d日 %H:%M'),
            'session_summary': session_summary,
            'charts': charts,
            'performance_grade': self._calculate_performance_grade(session_summary.correct_rate),
            'time_efficiency': self._calculate_time_efficiency(session_summary.average_response_time)
        }
        
        # HTMLレポート生成
        html_content = self._render_session_report(report_data)
        
        # ファイル保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = config.REPORT_OUTPUT_DIR / f'session_report_{timestamp}.html'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"セッションレポート生成完了: {report_path}")
        return report_path
    
    def _generate_all_charts(self, progress_data: Dict, 
                           detailed_analysis: Dict) -> Dict[str, str]:
        """すべてのチャートを生成"""
        charts = {}
        
        # 進捗チャート
        if progress_data.get('progress_over_time'):
            fig = self.chart_generator.create_progress_chart(
                progress_data['progress_over_time']
            )
            charts['progress'] = fig.to_html(include_plotlyjs='cdn')
        
        # 分野別パフォーマンス
        if progress_data.get('category_statistics'):
            fig = self.chart_generator.create_category_performance_chart(
                progress_data['category_statistics']
            )
            charts['category_performance'] = fig.to_html(include_plotlyjs='cdn')
        
        # 弱点分野
        if progress_data.get('weak_areas'):
            fig = self.chart_generator.create_weak_areas_chart(
                progress_data['weak_areas']
            )
            charts['weak_areas'] = fig.to_html(include_plotlyjs='cdn')
        
        # 学習パターン
        if detailed_analysis.get('learning_patterns'):
            fig = self.chart_generator.create_study_pattern_chart(
                detailed_analysis['learning_patterns']
            )
            charts['study_patterns'] = fig.to_html(include_plotlyjs='cdn')
        
        # 難易度分布
        if detailed_analysis.get('difficulty_statistics'):
            fig = self.chart_generator.create_difficulty_distribution_chart(
                detailed_analysis['difficulty_statistics']
            )
            charts['difficulty_distribution'] = fig.to_html(include_plotlyjs='cdn')
        
        return charts
    
    def _generate_session_charts(self, session_summary: Dict) -> Dict[str, str]:
        """セッション用チャートを生成"""
        charts = {}
        
        # 正答率円グラフ
        fig = go.Figure(data=[
            go.Pie(
                labels=['正解', '不正解'],
                values=[session_summary.correct_answers, session_summary.incorrect_answers],
                marker_colors=[self.chart_generator.colors[0], self.chart_generator.colors[1]],
                textinfo='label+percent',
                hole=0.3
            )
        ])
        
        fig.update_layout(
            title="セッション結果",
            height=400,
            showlegend=True
        )
        
        charts['session_result'] = fig.to_html(include_plotlyjs='cdn')
        
        # 分野別結果（データがあれば）
        if session_summary.categories_studied:
            categories = session_summary.categories_studied
            fig = go.Figure(data=[
                go.Bar(
                    x=categories,
                    y=[1] * len(categories),  # 簡略化
                    name='学習分野',
                    marker_color=self.chart_generator.colors[2]
                )
            ])
            
            fig.update_layout(
                title="学習分野",
                height=300,
                showlegend=False
            )
            
            charts['categories'] = fig.to_html(include_plotlyjs='cdn')
        
        return charts
    
    def _generate_summary(self, progress_data: Dict) -> Dict:
        """サマリーを生成"""
        stats = progress_data.get('overall_statistics', {})
        
        return {
            'total_questions': stats.get('total_questions', 0),
            'overall_rate': stats.get('overall_correct_rate', 0),
            'grade': self._calculate_performance_grade(stats.get('overall_correct_rate', 0)),
            'categories_count': stats.get('categories_studied', 0),
            'weak_areas_count': len(progress_data.get('weak_areas', [])),
            'status': self._determine_study_status(stats.get('overall_correct_rate', 0))
        }
    
    def _calculate_performance_grade(self, correct_rate: float) -> str:
        """パフォーマンスグレードを計算"""
        if correct_rate >= 0.9:
            return "A+"
        elif correct_rate >= 0.8:
            return "A"
        elif correct_rate >= 0.7:
            return "B"
        elif correct_rate >= 0.6:
            return "C"
        elif correct_rate >= 0.5:
            return "D"
        else:
            return "F"
    
    def _calculate_time_efficiency(self, avg_response_time: float) -> str:
        """時間効率を計算"""
        if avg_response_time <= 30:
            return "優秀"
        elif avg_response_time <= 60:
            return "良好"
        elif avg_response_time <= 90:
            return "標準"
        else:
            return "要改善"
    
    def _determine_study_status(self, correct_rate: float) -> str:
        """学習状況を判定"""
        if correct_rate >= 0.8:
            return "合格圏内"
        elif correct_rate >= 0.6:
            return "合格ライン"
        elif correct_rate >= 0.4:
            return "要努力"
        else:
            return "基礎固め必要"
    
    def _render_html_report(self, report_data: Dict) -> str:
        """HTMLレポートをレンダリング"""
        try:
            template = self.jinja_env.get_template('comprehensive_report.html')
            return template.render(**report_data)
        except Exception as e:
            self.logger.error(f"HTMLレンダリングエラー: {e}")
            return self._generate_fallback_html(report_data)
    
    def _render_session_report(self, report_data: Dict) -> str:
        """セッションレポートをレンダリング"""
        try:
            template = self.jinja_env.get_template('session_report.html')
            return template.render(**report_data)
        except Exception as e:
            self.logger.error(f"セッションレポートHTMLレンダリングエラー: {e}")
            return self._generate_fallback_session_html(report_data)
    
    def _generate_fallback_html(self, report_data: Dict) -> str:
        """フォールバック用HTMLを生成"""
        html = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{report_data['title']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; text-align: center; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
                .chart {{ margin: 20px 0; }}
                .stats {{ display: flex; justify-content: space-around; }}
                .stat-item {{ text-align: center; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{report_data['title']}</h1>
                <p>生成日時: {report_data['generated_at']}</p>
            </div>
            
            <div class="section">
                <h2>概要</h2>
                <div class="stats">
                    <div class="stat-item">
                        <h3>総問題数</h3>
                        <p>{report_data['summary']['total_questions']}</p>
                    </div>
                    <div class="stat-item">
                        <h3>全体正答率</h3>
                        <p>{report_data['summary']['overall_rate']:.1f}%</p>
                    </div>
                    <div class="stat-item">
                        <h3>成績</h3>
                        <p>{report_data['summary']['grade']}</p>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>推奨事項</h2>
                <ul>
        """
        
        for rec in report_data.get('recommendations', []):
            html += f"<li>{rec.get('description', '')}</li>"
        
        html += """
                </ul>
            </div>
            
            <div class="section">
                <h2>チャート</h2>
        """
        
        for chart_name, chart_html in report_data.get('charts', {}).items():
            html += f'<div class="chart">{chart_html}</div>'
        
        html += """
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_fallback_session_html(self, report_data: Dict) -> str:
        """フォールバック用セッションHTMLを生成"""
        session = report_data['session_summary']
        
        html = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{report_data['title']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; text-align: center; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
                .stats {{ display: flex; justify-content: space-around; }}
                .stat-item {{ text-align: center; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{report_data['title']}</h1>
                <p>生成日時: {report_data['generated_at']}</p>
            </div>
            
            <div class="section">
                <h2>セッション結果</h2>
                <div class="stats">
                    <div class="stat-item">
                        <h3>総問題数</h3>
                        <p>{session.total_questions}</p>
                    </div>
                    <div class="stat-item">
                        <h3>正解数</h3>
                        <p>{session.correct_answers}</p>
                    </div>
                    <div class="stat-item">
                        <h3>正答率</h3>
                        <p>{session.correct_rate:.1f}%</p>
                    </div>
                    <div class="stat-item">
                        <h3>成績</h3>
                        <p>{report_data['performance_grade']}</p>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>達成事項</h2>
                <ul>
        """
        
        for achievement in session.achievements:
            html += f"<li>{achievement}</li>"
        
        html += """
                </ul>
            </div>
            
            <div class="section">
                <h2>チャート</h2>
        """
        
        for chart_name, chart_html in report_data.get('charts', {}).items():
            html += f'<div class="chart">{chart_html}</div>'
        
        html += """
            </div>
        </body>
        </html>
        """
        
        return html
    
    def export_data(self, data: Dict, format: str = 'json') -> str:
        """データをエクスポート"""
        if format == 'json':
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 簡単なCSV出力（実際のデータ構造に応じて調整が必要）
            writer.writerow(['項目', '値'])
            for key, value in data.items():
                if isinstance(value, (str, int, float)):
                    writer.writerow([key, value])
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def cleanup_old_reports(self, days: int = 30):
        """古いレポートを削除"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        deleted_count = 0
        for report_file in config.REPORT_OUTPUT_DIR.glob('*.html'):
            if datetime.fromtimestamp(report_file.stat().st_mtime) < cutoff_date:
                report_file.unlink()
                deleted_count += 1
        
        self.logger.info(f"古いレポートを削除: {deleted_count} 件")
        return deleted_count