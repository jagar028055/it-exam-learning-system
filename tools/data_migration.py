#!/usr/bin/env python3
"""
データ移行スクリプト
抽出したJSONファイルの問題データをSQLiteデータベースに統合します。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import sqlite3
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from src.core.database import DatabaseManager
from src.core.config import config

class DataMigration:
    """データ移行クラス"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.migration_log = []
    
    def migrate_extracted_questions(self, json_file_path: Path) -> Dict:
        """抽出した問題データをデータベースに移行"""
        print(f"\n=== データ移行開始: {json_file_path} ===")
        
        if not json_file_path.exists():
            raise FileNotFoundError(f"JSONファイルが見つかりません: {json_file_path}")
        
        # JSONデータの読み込み
        with open(json_file_path, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
        
        print(f"読み込み問題数: {len(questions_data)}")
        
        results = {
            'total_questions': len(questions_data),
            'successful_imports': 0,
            'failed_imports': 0,
            'errors': []
        }
        
        # 既存データの確認
        existing_count = self._count_existing_questions()
        print(f"既存問題数: {existing_count}")
        
        # 各問題をデータベースに追加
        for i, question_data in enumerate(questions_data, 1):
            try:
                # データ形式変換
                db_question_data = self._convert_question_format(question_data)
                
                # データベースに挿入
                question_id = self.db_manager.insert_question(db_question_data)
                
                results['successful_imports'] += 1
                self.migration_log.append(f"問題 {question_data['id']} を追加: DB ID={question_id}")
                
                if i % 10 == 0:
                    print(f"進捗: {i}/{len(questions_data)} 問題処理完了")
                    
            except Exception as e:
                results['failed_imports'] += 1
                error_msg = f"問題 {question_data.get('id', 'unknown')} の追加失敗: {e}"
                results['errors'].append(error_msg)
                self.migration_log.append(error_msg)
                print(f"エラー: {error_msg}")
        
        print(f"\n=== 移行完了 ===")
        print(f"成功: {results['successful_imports']} 問題")
        print(f"失敗: {results['failed_imports']} 問題")
        
        return results
    
    def _convert_question_format(self, question_data: Dict) -> Dict:
        """問題データ形式を変換"""
        # 正解選択肢を数値に変換
        correct_answer_num = None
        if question_data.get('correct_answer'):
            choice_map = {'ア': 1, 'イ': 2, 'ウ': 3, 'エ': 4, 'オ': 5}
            correct_answer_num = choice_map.get(question_data['correct_answer'])
        
        # 科目に基づいて試験区分を決定
        exam_type = 'FE'  # 基本情報技術者試験
        
        # カテゴリを設定（後で分類機能を追加予定）
        category = self._categorize_question(question_data)
        
        # データベース形式に変換
        db_data = {
            'exam_type': exam_type,
            'year': question_data['year'],
            'question_number': question_data['question_number'],
            'question_text': question_data['question_text'],
            'choices': question_data['choices'],
            'correct_answer': correct_answer_num,
            'explanation': question_data.get('explanation'),
            'category': category,
            'subcategory': question_data['subject'],  # A or B
            'difficulty_level': 2,  # デフォルト値
            'source_url': f"IPA公式過去問_{question_data['year']}"
        }
        
        return db_data
    
    def _categorize_question(self, question_data: Dict) -> str:
        """問題をカテゴリ分類（基本的な分類）"""
        question_text = question_data['question_text'].lower()
        
        # キーワードベースの簡易分類
        categories = {
            'プログラミング': ['プログラム', 'アルゴリズム', '配列', '関数', 'コード'],
            'データベース': ['sql', 'データベース', 'テーブル', 'select', 'insert'],
            'ネットワーク': ['tcp', 'ip', 'ネットワーク', 'lan', 'wan', 'プロトコル'],
            'セキュリティ': ['暗号', 'セキュリティ', '認証', 'ssl', 'https'],
            'ハードウェア': ['cpu', 'メモリ', 'ハードディスク', 'ssd'],
            'ソフトウェア': ['os', 'オペレーティングシステム', 'アプリケーション'],
            '数学・統計': ['進数', '確率', '統計', '数学', '計算'],
            'マネジメント': ['プロジェクト', '管理', 'itil', 'pdca'],
            'ストラテジ': ['経営', '戦略', 'ビジネス', 'it戦略']
        }
        
        for category, keywords in categories.items():
            if any(keyword in question_text for keyword in keywords):
                return category
        
        # 科目Bの場合
        if question_data['subject'] == 'B':
            return 'プログラミング'
        
        return '一般'
    
    def _count_existing_questions(self) -> int:
        """既存問題数をカウント"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM questions")
            return cursor.fetchone()[0]
    
    def clear_existing_questions(self, confirm: bool = False) -> int:
        """既存の問題データをクリア（開発用）"""
        if not confirm:
            print("警告: この操作は全ての問題データを削除します")
            response = input("続行しますか？ (yes/no): ")
            if response.lower() != 'yes':
                print("操作をキャンセルしました")
                return 0
        
        with self.db_manager.get_connection() as conn:
            # 関連データも削除
            cursor = conn.execute("DELETE FROM learning_records")
            cursor = conn.execute("DELETE FROM study_sessions")
            cursor = conn.execute("DELETE FROM study_statistics")
            cursor = conn.execute("DELETE FROM questions")
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            print(f"削除した問題数: {deleted_count}")
            return deleted_count
    
    def generate_migration_report(self, results: Dict) -> str:
        """移行レポートを生成"""
        report = f"""
データ移行レポート
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=== 移行結果 ===
総問題数: {results['total_questions']}
成功: {results['successful_imports']}
失敗: {results['failed_imports']}
成功率: {(results['successful_imports'] / results['total_questions'] * 100):.1f}%

=== エラー詳細 ===
"""
        
        if results['errors']:
            for error in results['errors']:
                report += f"- {error}\n"
        else:
            report += "エラーなし\n"
        
        report += "\n=== 移行ログ ===\n"
        for log_entry in self.migration_log[-20:]:  # 最新20件
            report += f"- {log_entry}\n"
        
        return report
    
    def validate_migration(self) -> Dict:
        """移行後のデータ検証"""
        print("\n=== データ検証中 ===")
        
        validation_results = {
            'total_questions': 0,
            'questions_with_answers': 0,
            'questions_with_choices': 0,
            'categories_found': set(),
            'years_found': set(),
            'subjects_found': set()
        }
        
        questions = self.db_manager.get_questions()
        validation_results['total_questions'] = len(questions)
        
        for question in questions:
            if question.get('correct_answer'):
                validation_results['questions_with_answers'] += 1
            
            if question.get('choices') and len(question['choices']) > 0:
                validation_results['questions_with_choices'] += 1
            
            if question.get('category'):
                validation_results['categories_found'].add(question['category'])
            
            if question.get('year'):
                validation_results['years_found'].add(question['year'])
            
            if question.get('subcategory'):
                validation_results['subjects_found'].add(question['subcategory'])
        
        # 集合を リストに変換
        validation_results['categories_found'] = sorted(list(validation_results['categories_found']))
        validation_results['years_found'] = sorted(list(validation_results['years_found']))
        validation_results['subjects_found'] = sorted(list(validation_results['subjects_found']))
        
        print(f"総問題数: {validation_results['total_questions']}")
        print(f"正解付き問題: {validation_results['questions_with_answers']}")
        print(f"選択肢付き問題: {validation_results['questions_with_choices']}")
        print(f"カテゴリ: {validation_results['categories_found']}")
        print(f"年度: {validation_results['years_found']}")
        print(f"科目: {validation_results['subjects_found']}")
        
        return validation_results

def main():
    """メイン関数"""
    migration = DataMigration()
    
    # JSONファイルのパス
    json_file = Path("data/extracted_questions.json")
    
    if not json_file.exists():
        print(f"エラー: JSONファイルが見つかりません: {json_file}")
        return
    
    try:
        # 既存データをクリア（新規データ統合のため）
        print("既存データをクリアして新規データを統合します...")
        migration.clear_existing_questions(confirm=True)
        
        # データ移行実行
        results = migration.migrate_extracted_questions(json_file)
        
        # 移行後の検証
        validation_results = migration.validate_migration()
        
        # レポート生成
        report = migration.generate_migration_report(results)
        
        # レポートをファイルに保存
        report_file = Path("data/migration_report.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n移行レポートを保存: {report_file}")
        
        # 成功時にデータベース最適化
        if results['failed_imports'] == 0:
            print("\nデータベースを最適化中...")
            migration.db_manager.optimize_database()
            print("最適化完了")
        
    except Exception as e:
        print(f"移行エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()