#!/usr/bin/env python3
"""
問題データ抽出スクリプト
情報技術者試験の過去問PDFから問題データを抽出します。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pdfplumber
import re
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional

@dataclass
class Question:
    """問題データクラス"""
    id: str
    year: int
    subject: str  # A or B
    question_number: int
    question_text: str
    choices: List[str]
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None

class PDFQuestionExtractor:
    """PDF問題抽出クラス"""
    
    def __init__(self):
        self.questions = []
    
    def extract_from_pdf(self, pdf_path: Path) -> List[Question]:
        """PDFファイルから問題を抽出"""
        print(f"\n=== 問題抽出開始: {pdf_path.name} ===")
        
        # ファイル名から年度と科目を抽出
        match = re.search(r'(\d{4})_.*科目([AB])_問題', pdf_path.name)
        if not match:
            print("ファイル名から年度・科目を抽出できません")
            return []
        
        year = int(match.group(1))
        subject = match.group(2)
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                
                if subject == "A":
                    return self._extract_subject_a_questions(full_text, year, subject)
                else:
                    return self._extract_subject_b_questions(full_text, year, subject)
                    
        except Exception as e:
            print(f"エラー: {e}")
            return []
    
    def _extract_subject_a_questions(self, text: str, year: int, subject: str) -> List[Question]:
        """科目A問題の抽出"""
        questions = []
        
        # 問題パターンの検索
        pattern = r'問(\d+)\s+(.*?)(?=問\d+|$)'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for match in matches:
            question_num = int(match[0])
            question_content = match[1].strip()
            
            # 選択肢を抽出
            choices = []
            choice_pattern = r'([ア-エ])\s+([^ア-エ]+?)(?=[ア-エ]|$)'
            choice_matches = re.findall(choice_pattern, question_content)
            
            if choice_matches:
                for choice_label, choice_text in choice_matches:
                    choices.append(f"{choice_label} {choice_text.strip()}")
                
                # 問題文（選択肢より前の部分）
                question_text = re.split(r'[ア-エ]\s+', question_content)[0].strip()
                
                question = Question(
                    id=f"{year}-{subject}-{question_num:02d}",
                    year=year,
                    subject=subject,
                    question_number=question_num,
                    question_text=question_text,
                    choices=choices
                )
                questions.append(question)
                print(f"問{question_num}: 抽出完了 (選択肢: {len(choices)}個)")
            else:
                print(f"問{question_num}: 選択肢が見つかりません")
        
        return questions
    
    def _extract_subject_b_questions(self, text: str, year: int, subject: str) -> List[Question]:
        """科目B問題の抽出（プログラミング問題）"""
        questions = []
        
        # 問題パターンの検索（科目Bは複雑な構造）
        pattern = r'問(\d+)\s+(.*?)(?=問\d+|$)'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for match in matches:
            question_num = int(match[0])
            question_content = match[1].strip()
            
            # 科目Bは小問に分かれることが多い
            # 基本的な問題文として処理
            question = Question(
                id=f"{year}-{subject}-{question_num:02d}",
                year=year,
                subject=subject,
                question_number=question_num,
                question_text=question_content,
                choices=[]  # 科目Bは記述式のため選択肢なし
            )
            questions.append(question)
            print(f"問{question_num}: 抽出完了 (科目B)")
        
        return questions
    
    def load_answers_from_pdf(self, pdf_path: Path) -> dict:
        """解答PDFから正解を抽出"""
        print(f"\n=== 解答抽出開始: {pdf_path.name} ===")
        
        answers = {}
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                
                # 解答パターンの検索
                # 例: "問1 エ", "問 1 エ", "1. エ"
                patterns = [
                    r'問\s*(\d+)\s*([ア-エ])',
                    r'(\d+)\.\s*([ア-エ])',
                    r'(\d+)\s+([ア-エ])'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, full_text)
                    for match in matches:
                        question_num = int(match[0])
                        answer = match[1]
                        answers[question_num] = answer
                        print(f"問{question_num}: {answer}")
                
        except Exception as e:
            print(f"エラー: {e}")
        
        return answers
    
    def save_to_json(self, questions: List[Question], output_path: Path):
        """JSONファイルに保存"""
        data = [asdict(q) for q in questions]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n{len(questions)}問を {output_path} に保存しました")

def main():
    """メイン関数"""
    extractor = PDFQuestionExtractor()
    docs_dir = Path("書類")
    
    if not docs_dir.exists():
        print("書類フォルダが見つかりません")
        return
    
    # 問題PDFファイルを処理
    question_files = list(docs_dir.glob("*問題*.pdf"))
    answer_files = list(docs_dir.glob("*解答*.pdf"))
    
    all_questions = []
    
    for question_file in sorted(question_files):
        questions = extractor.extract_from_pdf(question_file)
        
        # 対応する解答ファイルを検索
        base_name = question_file.name.replace("問題", "解答例")
        answer_file = docs_dir / base_name
        
        if answer_file.exists():
            answers = extractor.load_answers_from_pdf(answer_file)
            # 正解を問題データに追加
            for question in questions:
                if question.question_number in answers:
                    question.correct_answer = answers[question.question_number]
        
        all_questions.extend(questions)
    
    # 結果を保存
    if all_questions:
        output_path = Path("data/extracted_questions.json")
        output_path.parent.mkdir(exist_ok=True)
        extractor.save_to_json(all_questions, output_path)
        
        # 統計情報
        print(f"\n=== 抽出統計 ===")
        years = set(q.year for q in all_questions)
        subjects = set(q.subject for q in all_questions)
        print(f"年度: {sorted(years)}")
        print(f"科目: {sorted(subjects)}")
        print(f"総問題数: {len(all_questions)}")
        
        for year in sorted(years):
            for subject in sorted(subjects):
                count = len([q for q in all_questions if q.year == year and q.subject == subject])
                print(f"{year}年 科目{subject}: {count}問")

if __name__ == "__main__":
    main()