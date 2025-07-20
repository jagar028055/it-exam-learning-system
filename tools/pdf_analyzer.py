#!/usr/bin/env python3
"""
PDF構造分析スクリプト
情報技術者試験の過去問PDFファイルを分析して、問題データの構造を把握します。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pdfplumber
import PyPDF2
from pathlib import Path
import re

def analyze_pdf_structure(pdf_path):
    """PDFファイルの構造を分析"""
    print(f"\n=== PDF構造分析: {pdf_path} ===")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"総ページ数: {len(pdf.pages)}")
            
            # 最初の数ページを分析
            for i, page in enumerate(pdf.pages[:3]):
                print(f"\n--- Page {i+1} ---")
                text = page.extract_text()
                if text:
                    lines = text.split('\n')
                    print(f"行数: {len(lines)}")
                    print("最初の10行:")
                    for j, line in enumerate(lines[:10]):
                        print(f"  {j+1}: {line.strip()}")
                    
                    # 問題番号のパターンを探す
                    question_patterns = [
                        r'問\s*\d+',
                        r'Q\s*\d+',
                        r'\d+\.',
                        r'第\s*\d+\s*問'
                    ]
                    
                    for pattern in question_patterns:
                        matches = re.findall(pattern, text)
                        if matches:
                            print(f"問題番号パターン '{pattern}' 検出: {matches[:5]}")
                else:
                    print("テキスト抽出失敗")
                    
    except Exception as e:
        print(f"エラー: {e}")

def main():
    """メイン関数"""
    docs_dir = Path("書類")
    
    if not docs_dir.exists():
        print("書類フォルダが見つかりません")
        return
    
    # 問題PDFファイルを優先的に分析
    pdf_files = list(docs_dir.glob("*問題*.pdf"))
    
    if not pdf_files:
        print("問題PDFファイルが見つかりません")
        return
    
    # 最新年度の科目Aから分析開始
    for pdf_file in sorted(pdf_files, reverse=True)[:2]:
        analyze_pdf_structure(pdf_file)

if __name__ == "__main__":
    main()