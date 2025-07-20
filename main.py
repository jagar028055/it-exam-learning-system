#!/usr/bin/env python3
"""
情報技術者試験学習システム - メインスクリプト
"""

import argparse
import sys
import os
import json
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from database import DatabaseManager
from data_fetcher import IPADataFetcher, DataProcessor
from progress_tracker import ProgressTracker, StudyMode
from report_generator import ReportGenerator
from utils import Logger, SystemError, ValidationError

class ITExamStudySystem:
    """情報技術者試験学習システム メインクラス"""
    
    def __init__(self):
        """初期化"""
        # ログ設定
        self.logger = Logger.setup_logger(
            "ITExamStudySystem",
            config.LOG_FILE,
            config.LOG_LEVEL
        )
        
        # モジュール初期化
        try:
            self.db = DatabaseManager()
            self.fetcher = IPADataFetcher()
            self.processor = DataProcessor()
            self.tracker = ProgressTracker(self.db)
            self.report_generator = ReportGenerator(self.db, self.tracker)
            
            self.logger.info("システム初期化完了")
            
        except Exception as e:
            self.logger.error(f"システム初期化エラー: {e}")
            raise SystemError(f"システム初期化に失敗しました: {e}")
    
    def fetch_data(self, exam_type: str = "FE", year: int = None, 
                   force_update: bool = False) -> bool:
        """
        過去問題データを取得
        
        Args:
            exam_type: 試験種別
            year: 年度（None の場合は全年度）
            force_update: 強制更新
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            self.logger.info(f"データ取得開始: {exam_type}, 年度: {year or '全年度'}")
            
            if year:
                # 特定年度のデータ取得
                result = self.fetcher.process_exam_year(year, exam_type)
                if result['status'] == 'success':
                    # データベースに保存
                    self._save_questions_to_db(result['questions'], exam_type, year)
                    self.logger.info(f"{year}年度データ取得完了: {len(result['questions'])} 問題")
                    return True
                else:
                    self.logger.error(f"{year}年度データ取得失敗: {result.get('error', '不明なエラー')}")
                    return False
            else:
                # 全年度のデータ取得
                exam_list = self.fetcher.fetch_exam_list(exam_type)
                success_count = 0
                
                for exam in exam_list:
                    try:
                        result = self.fetcher.process_exam_year(exam['year'], exam_type)
                        if result['status'] == 'success':
                            self._save_questions_to_db(result['questions'], exam_type, exam['year'])
                            success_count += 1
                            self.logger.info(f"{exam['year']}年度データ取得完了")
                        else:
                            self.logger.warning(f"{exam['year']}年度データ取得失敗")
                    except Exception as e:
                        self.logger.error(f"{exam['year']}年度処理エラー: {e}")
                        continue
                
                self.logger.info(f"データ取得完了: {success_count}/{len(exam_list)} 年度")
                return success_count > 0
                
        except Exception as e:
            self.logger.error(f"データ取得エラー: {e}")
            return False
    
    def _save_questions_to_db(self, questions: List[Dict], exam_type: str, year: int):
        """問題をデータベースに保存"""
        try:
            # 分野分類を実行
            questions = self.processor.categorize_questions(questions)
            
            # データ検証
            valid_questions, invalid_questions = self.processor.validate_question_data(questions)
            
            if invalid_questions:
                self.logger.warning(f"無効な問題データ: {len(invalid_questions)} 問")
            
            # データベースに保存
            for question in valid_questions:
                question['exam_type'] = exam_type
                question['year'] = year
                try:
                    self.db.insert_question(question)
                except Exception as e:
                    self.logger.error(f"問題保存エラー: {e}")
                    continue
            
            self.logger.info(f"データベース保存完了: {len(valid_questions)} 問題")
            
        except Exception as e:
            self.logger.error(f"データベース保存エラー: {e}")
            raise
    
    def start_study_session(self, exam_type: str = "FE", mode: str = "practice",
                           count: int = 20, category: str = None) -> bool:
        """
        学習セッションを開始
        
        Args:
            exam_type: 試験種別
            mode: 学習モード
            count: 問題数
            category: 分野（None の場合は全分野）
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            # 学習モードの設定
            study_mode = StudyMode.PRACTICE
            if mode == "mock_exam":
                study_mode = StudyMode.MOCK_EXAM
                count = 80  # 模擬試験は80問
            elif mode == "review":
                study_mode = StudyMode.REVIEW
            elif mode == "weak_area":
                study_mode = StudyMode.WEAK_AREA
            
            # セッション名を生成
            session_name = f"{exam_type}_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # セッション開始
            session_id = self.tracker.start_study_session(
                session_name=session_name,
                exam_type=exam_type,
                study_mode=study_mode,
                target_questions=count
            )
            
            # 問題を取得
            if mode == "weak_area":
                questions = self._get_weak_area_questions(exam_type, count)
            else:
                questions = self.db.get_random_questions(exam_type, category, count)
            
            if not questions:
                print(f"❌ 問題が見つかりません。先にデータを取得してください。")
                return False
            
            print(f"🎯 学習セッション開始: {session_name}")
            print(f"📚 問題数: {len(questions)} 問")
            print(f"🎲 モード: {mode}")
            if category:
                print(f"📖 分野: {category}")
            print("=" * 50)
            
            # 問題を出題
            correct_count = 0
            for i, question in enumerate(questions, 1):
                print(f"\n【問題 {i}/{len(questions)}】")
                print(f"分野: {question.get('category', '不明')}")
                print(f"問題: {question['question_text']}")
                print()
                
                # 選択肢を表示
                for j, choice in enumerate(question['choices'], 1):
                    print(f"{j}. {choice}")
                
                # 回答を入力
                while True:
                    try:
                        print()
                        user_input = input("回答を選択してください (1-{}) または 'q' で終了: ".format(len(question['choices'])))
                        
                        if user_input.lower() == 'q':
                            print("学習セッションを終了します。")
                            break
                        
                        user_answer = int(user_input)
                        if 1 <= user_answer <= len(question['choices']):
                            break
                        else:
                            print("無効な選択です。")
                    except ValueError:
                        print("数字を入力してください。")
                
                if user_input.lower() == 'q':
                    break
                
                # 回答を記録
                correct_answer = question.get('correct_answer', 1)
                is_correct = user_answer == correct_answer
                
                if is_correct:
                    correct_count += 1
                    print("✅ 正解！")
                else:
                    print(f"❌ 不正解。正解は {correct_answer} です。")
                
                # 解説があれば表示
                if question.get('explanation'):
                    print(f"💡 解説: {question['explanation']}")
                
                # 記録
                self.tracker.record_answer(
                    question_id=question['id'],
                    user_answer=user_answer,
                    correct_answer=correct_answer
                )
                
                # 次の問題へ
                if i < len(questions):
                    input("\nEnterキーを押して次の問題へ...")
            
            # セッション終了
            summary = self.tracker.end_study_session()
            
            # 結果表示
            print("\n" + "=" * 50)
            print("🎉 学習セッション終了")
            print(f"総問題数: {summary.total_questions}")
            print(f"正解数: {summary.correct_answers}")
            print(f"正答率: {summary.correct_rate:.1f}%")
            print(f"平均回答時間: {summary.average_response_time:.1f}秒")
            
            # 成績評価
            if summary.correct_rate >= 0.8:
                print("🏆 素晴らしい成績です！")
            elif summary.correct_rate >= 0.6:
                print("👍 良い成績です！")
            elif summary.correct_rate >= 0.4:
                print("📚 もう少し頑張りましょう。")
            else:
                print("💪 基礎から復習しましょう。")
            
            # 達成事項
            if summary.achievements:
                print("\n🏅 達成事項:")
                for achievement in summary.achievements:
                    print(f"  • {achievement}")
            
            # 弱点分野
            if summary.weak_areas:
                print("\n⚠️ 改善が必要な分野:")
                for area in summary.weak_areas:
                    print(f"  • {area}")
            
            # レポート生成の提案
            print("\n📊 詳細なレポートを生成しますか？ (y/n)")
            if input().lower() == 'y':
                report_path = self.report_generator.generate_session_report(summary)
                print(f"📄 レポートを生成しました: {report_path}")
                
                # レポートを開く
                print("レポートを開きますか？ (y/n)")
                if input().lower() == 'y':
                    webbrowser.open(f"file://{report_path.absolute()}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"学習セッションエラー: {e}")
            print(f"❌ エラーが発生しました: {e}")
            return False
    
    def _get_weak_area_questions(self, exam_type: str, count: int) -> List[Dict]:
        """弱点分野の問題を取得"""
        weak_areas = self.db.get_weak_areas(exam_type, limit=3)
        if not weak_areas:
            return self.db.get_random_questions(exam_type, None, count)
        
        questions = []
        questions_per_area = count // len(weak_areas)
        
        for area in weak_areas:
            area_questions = self.db.get_random_questions(
                exam_type, area['category'], questions_per_area
            )
            questions.extend(area_questions)
        
        # 不足分を補う
        remaining = count - len(questions)
        if remaining > 0:
            additional = self.db.get_random_questions(exam_type, None, remaining)
            questions.extend(additional)
        
        return questions[:count]
    
    def generate_report(self, exam_type: str = "FE", days: int = 30) -> bool:
        """
        レポートを生成
        
        Args:
            exam_type: 試験種別
            days: 対象日数
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            print(f"📊 レポート生成中... ({exam_type}, {days}日間)")
            
            report_path = self.report_generator.generate_comprehensive_report(
                exam_type=exam_type,
                days=days
            )
            
            print(f"✅ レポートを生成しました: {report_path}")
            
            # レポートを開く
            print("レポートを開きますか？ (y/n)")
            if input().lower() == 'y':
                webbrowser.open(f"file://{report_path.absolute()}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"レポート生成エラー: {e}")
            print(f"❌ レポート生成に失敗しました: {e}")
            return False
    
    def show_statistics(self, exam_type: str = None) -> bool:
        """
        統計情報を表示
        
        Args:
            exam_type: 試験種別
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            print("📈 統計情報")
            print("=" * 50)
            
            # 全体統計
            progress = self.tracker.get_overall_progress(exam_type)
            stats = progress['overall_statistics']
            
            print(f"総問題数: {stats['total_questions']}")
            print(f"正解数: {stats['total_correct']}")
            print(f"全体正答率: {stats['overall_correct_rate']:.1f}%")
            print(f"学習分野数: {stats['categories_studied']}")
            
            # 分野別統計
            if progress['category_statistics']:
                print("\n📚 分野別統計:")
                for stat in progress['category_statistics']:
                    print(f"  {stat['category']}: {stat['correct_rate']:.1f}% ({stat['total_questions']}問)")
            
            # 弱点分野
            if progress['weak_areas']:
                print("\n⚠️ 弱点分野:")
                for area in progress['weak_areas']:
                    print(f"  {area['category']}: {area['correct_rate']:.1f}%")
            
            # 推奨事項
            if progress['recommendations']:
                print("\n💡 推奨事項:")
                for rec in progress['recommendations']:
                    print(f"  • {rec}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"統計表示エラー: {e}")
            print(f"❌ 統計表示に失敗しました: {e}")
            return False
    
    def backup_database(self, backup_path: str = None) -> bool:
        """
        データベースをバックアップ
        
        Args:
            backup_path: バックアップパス
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            if backup_path:
                backup_path = Path(backup_path)
            else:
                backup_path = None
            
            backup_file = self.db.backup_database(backup_path)
            print(f"✅ データベースをバックアップしました: {backup_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"バックアップエラー: {e}")
            print(f"❌ バックアップに失敗しました: {e}")
            return False
    
    def cleanup(self, days: int = 90) -> bool:
        """
        古いデータを削除
        
        Args:
            days: 保持期間（日）
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            # 古い学習記録を削除
            deleted_records = self.db.cleanup_old_records(days)
            
            # 古いレポートを削除
            deleted_reports = self.report_generator.cleanup_old_reports(days)
            
            print(f"✅ クリーンアップ完了:")
            print(f"  学習記録: {deleted_records} 件削除")
            print(f"  レポート: {deleted_reports} 件削除")
            
            # データベース最適化
            self.db.vacuum_database()
            print("  データベースを最適化しました")
            
            return True
            
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")
            print(f"❌ クリーンアップに失敗しました: {e}")
            return False
    
    def show_info(self) -> bool:
        """システム情報を表示"""
        try:
            print("ℹ️ システム情報")
            print("=" * 50)
            
            # データベース情報
            db_info = self.db.get_database_info()
            print(f"データベース:")
            print(f"  問題数: {db_info['questions_count']}")
            print(f"  学習記録: {db_info['learning_records_count']}")
            print(f"  セッション数: {db_info['study_sessions_count']}")
            print(f"  ファイルサイズ: {db_info['file_size'] / 1024 / 1024:.1f} MB")
            print(f"  最終更新: {db_info['last_modified']}")
            
            # 設定情報
            print(f"\n設定:")
            print(f"  プロジェクトルート: {config.PROJECT_ROOT}")
            print(f"  データベース: {config.DATABASE_PATH}")
            print(f"  レポート出力: {config.REPORT_OUTPUT_DIR}")
            print(f"  ログレベル: {config.LOG_LEVEL}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"情報表示エラー: {e}")
            print(f"❌ 情報表示に失敗しました: {e}")
            return False

def create_parser() -> argparse.ArgumentParser:
    """コマンドライン引数パーサーを作成"""
    parser = argparse.ArgumentParser(
        description="情報技術者試験学習システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main.py --fetch-data --exam-type FE --year 2023
  python main.py --study --exam-type FE --mode practice --count 20
  python main.py --report --exam-type FE --days 30
  python main.py --stats --exam-type FE
        """
    )
    
    # 基本オプション
    parser.add_argument('--exam-type', default='FE', 
                       choices=['FE', 'AP', 'IP', 'SG'],
                       help='試験種別 (default: FE)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='詳細ログを出力')
    
    # データ取得
    parser.add_argument('--fetch-data', action='store_true',
                       help='過去問題データを取得')
    parser.add_argument('--year', type=int,
                       help='取得する年度 (未指定の場合は全年度)')
    parser.add_argument('--force-update', action='store_true',
                       help='強制更新')
    
    # 学習
    parser.add_argument('--study', action='store_true',
                       help='学習セッションを開始')
    parser.add_argument('--mode', default='practice',
                       choices=['practice', 'mock_exam', 'review', 'weak_area'],
                       help='学習モード (default: practice)')
    parser.add_argument('--count', type=int, default=20,
                       help='問題数 (default: 20)')
    parser.add_argument('--category', 
                       help='学習分野を指定')
    
    # レポート
    parser.add_argument('--report', action='store_true',
                       help='レポートを生成')
    parser.add_argument('--days', type=int, default=30,
                       help='レポート対象日数 (default: 30)')
    
    # 統計
    parser.add_argument('--stats', action='store_true',
                       help='統計情報を表示')
    
    # 管理
    parser.add_argument('--backup', action='store_true',
                       help='データベースをバックアップ')
    parser.add_argument('--cleanup', action='store_true',
                       help='古いデータを削除')
    parser.add_argument('--info', action='store_true',
                       help='システム情報を表示')
    
    # データベース初期化
    parser.add_argument('--init-db', action='store_true',
                       help='データベースを初期化')
    
    return parser

def main():
    """メイン関数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # ログレベル設定
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    try:
        # 必要なディレクトリを作成
        config.create_directories()
        
        # データベース初期化のみの場合
        if args.init_db:
            print("🔧 データベースを初期化中...")
            db = DatabaseManager()
            print("✅ データベース初期化完了")
            return 0
        
        # システム初期化
        print("🚀 システムを初期化中...")
        system = ITExamStudySystem()
        print("✅ システム初期化完了")
        
        # コマンド実行
        success = True
        
        if args.fetch_data:
            success = system.fetch_data(args.exam_type, args.year, args.force_update)
        
        elif args.study:
            success = system.start_study_session(
                args.exam_type, args.mode, args.count, args.category
            )
        
        elif args.report:
            success = system.generate_report(args.exam_type, args.days)
        
        elif args.stats:
            success = system.show_statistics(args.exam_type)
        
        elif args.backup:
            success = system.backup_database()
        
        elif args.cleanup:
            success = system.cleanup(args.days)
        
        elif args.info:
            success = system.show_info()
        
        else:
            # 対話モード
            print("🎯 情報技術者試験学習システム")
            print("使用方法: python main.py --help")
            print("\n主な機能:")
            print("  --fetch-data : 過去問題データを取得")
            print("  --study      : 学習セッションを開始")
            print("  --report     : レポートを生成")
            print("  --stats      : 統計情報を表示")
            success = True
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n⏹️ 操作がキャンセルされました。")
        return 1
    
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())