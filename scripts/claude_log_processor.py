#!/usr/bin/env python3
"""
Claude Pro連携用ログ処理スクリプト

使用方法:
1. render logs -f $SERVICE_ID > latest.log
2. python scripts/claude_log_processor.py latest.log
3. 出力されたファイルをClaude Proにアップロード
"""

import re
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
import subprocess

class LogProcessor:
    def __init__(self, log_file_path):
        self.log_file_path = Path(log_file_path)
        self.errors_found = []
        self.error_patterns = {
            '500_errors': r'.*\s500\s.*',
            'python_exceptions': r'.*Exception.*|.*Error.*|.*Traceback.*',
            'database_errors': r'.*database.*error.*|.*connection.*failed.*',
            'timeout_errors': r'.*timeout.*|.*timed out.*',
            'memory_errors': r'.*OutOfMemory.*|.*MemoryError.*'
        }
    
    def extract_errors(self):
        """ログからエラーを抽出"""
        if not self.log_file_path.exists():
            raise FileNotFoundError(f"Log file not found: {self.log_file_path}")
        
        with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            for error_type, pattern in self.error_patterns.items():
                if re.search(pattern, line, re.IGNORECASE):
                    context_lines = self._get_context_lines(lines, i, context=3)
                    self.errors_found.append({
                        'type': error_type,
                        'line_number': i + 1,
                        'content': line.strip(),
                        'context': context_lines,
                        'timestamp': self._extract_timestamp(line)
                    })
    
    def _get_context_lines(self, lines, index, context=3):
        """エラー行の前後の文脈を取得"""
        start = max(0, index - context)
        end = min(len(lines), index + context + 1)
        return [line.strip() for line in lines[start:end]]
    
    def _extract_timestamp(self, line):
        """ログ行からタイムスタンプを抽出"""
        timestamp_patterns = [
            r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})',
            r'(\d{2}/\d{2}/\d{4}\s\d{2}:\d{2}:\d{2})',
            r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})'
        ]
        
        for pattern in timestamp_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)
        return 'Unknown'
    
    def generate_claude_prompt(self):
        """Claude Pro用のプロンプトを生成"""
        if not self.errors_found:
            return "ログにエラーは見つかりませんでした。"
        
        # エラーを種類別に集計
        error_summary = {}
        for error in self.errors_found:
            error_type = error['type']
            if error_type not in error_summary:
                error_summary[error_type] = []
            error_summary[error_type].append(error)
        
        prompt = f"""# 500エラー解析とパッチ生成依頼

## ログ解析結果 ({datetime.now().isoformat()})

### エラーサマリー
"""
        
        for error_type, errors in error_summary.items():
            prompt += f"- **{error_type}**: {len(errors)}件\n"
        
        prompt += "\n### 詳細なエラー情報\n\n"
        
        # 各エラーの詳細を追加
        for error_type, errors in error_summary.items():
            prompt += f"#### {error_type.replace('_', ' ').title()}\n\n"
            
            # 最新の3件のエラーを詳細表示
            for error in errors[:3]:
                prompt += f"**タイムスタンプ**: {error['timestamp']}\n"
                prompt += f"**行番号**: {error['line_number']}\n"
                prompt += f"**エラー内容**:\n```\n{error['content']}\n```\n\n"
                prompt += f"**前後の文脈**:\n```\n"
                for ctx_line in error['context']:
                    prompt += f"{ctx_line}\n"
                prompt += "```\n\n"
        
        prompt += """
## 依頼内容

上記のエラーログを分析し、以下を生成してください：

1. **根本原因の特定**
   - エラーの原因となっている関数・ファイルを特定
   - 発生頻度とパターンの分析

2. **最小再現テストコード**
   - Jest または Python unittest でのテストケース
   - エラーを再現できる最小限のコード

3. **修正パッチ (patch.diff)**
   - `git apply` で適用可能な形式
   - 修正理由とコメント付き
   - 副作用を最小限に抑えた修正

4. **デプロイ手順**
   - パッチ適用からデプロイまでの具体的な手順
   - ロールバック方法

## ファイル構造
プロジェクトはFlask製のIT試験学習システムです。
主要なファイル:
- `src/web/app.py` - メインアプリケーション
- `src/web/routes/` - ルート定義
- `src/core/database.py` - データベース処理
- `render.yaml` - Render設定

よろしくお願いします！
"""
        
        return prompt
    
    def save_output_files(self):
        """出力ファイルを保存"""
        output_dir = Path('claude_analysis')
        output_dir.mkdir(exist_ok=True)
        
        # プロンプトファイルを保存
        prompt = self.generate_claude_prompt()
        with open(output_dir / 'claude_prompt.md', 'w', encoding='utf-8') as f:
            f.write(prompt)
        
        # エラー詳細をJSONで保存
        with open(output_dir / 'errors_detail.json', 'w', encoding='utf-8') as f:
            json.dump(self.errors_found, f, indent=2, ensure_ascii=False)
        
        # 対象ソースファイルのリストを生成
        source_files = self._identify_source_files()
        with open(output_dir / 'relevant_files.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(source_files))
        
        return output_dir
    
    def _identify_source_files(self):
        """エラーに関連するソースファイルを特定"""
        source_files = []
        
        # 基本的なファイルは常に含める
        base_files = [
            'src/web/app.py',
            'src/web/routes/main_routes.py', 
            'src/core/database.py',
            'src/core/config.py'
        ]
        
        # エラーログから関連ファイルを抽出
        for error in self.errors_found:
            content = error['content']
            # ファイルパスらしき文字列を抽出
            file_patterns = re.findall(r'src/[\w/]+\.py', content)
            source_files.extend(file_patterns)
        
        # 重複を除去してソート
        all_files = list(set(base_files + source_files))
        return sorted(all_files)

def main():
    parser = argparse.ArgumentParser(description='Process logs for Claude Pro analysis')
    parser.add_argument('log_file', help='Path to the log file')
    parser.add_argument('--output-dir', default='claude_analysis', help='Output directory')
    
    args = parser.parse_args()
    
    try:
        processor = LogProcessor(args.log_file)
        processor.extract_errors()
        
        if not processor.errors_found:
            print("✅ ログにエラーは見つかりませんでした")
            return 0
        
        output_dir = processor.save_output_files()
        
        print(f"📊 解析完了: {len(processor.errors_found)}件のエラーを検出")
        print(f"📁 出力ディレクトリ: {output_dir}")
        print(f"📝 Claude用プロンプト: {output_dir}/claude_prompt.md")
        print(f"🔍 エラー詳細: {output_dir}/errors_detail.json")
        print(f"📋 関連ファイル: {output_dir}/relevant_files.txt")
        
        print("\n次の手順:")
        print("1. claude_prompt.md をClaude Proにアップロード")
        print("2. relevant_files.txt の各ファイルもアップロード")
        print("3. Claude からの回答でパッチを取得")
        print("4. scripts/apply_patch.sh でパッチを適用")
        
        return 0
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())