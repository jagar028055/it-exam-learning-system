"""
E2Eテスト - 学習フロー
Playwrightを使用したブラウザテスト
"""
import pytest
from playwright.sync_api import Page, expect
import time


class TestStudyFlowE2E:
    """学習フロー全体のE2Eテスト"""
    
    @pytest.fixture(scope="session")
    def base_url(self):
        """ベースURL（開発サーバー想定）"""
        return "http://localhost:5000"
    
    def test_complete_study_session_flow(self, page: Page, base_url: str):
        """完全な学習セッションフローのE2Eテスト"""
        
        # 1. トップページアクセス
        page.goto(base_url)
        expect(page).to_have_title("IT試験学習システム")
        
        # 2. 学習ページへ移動
        page.click("text=学習開始")
        expect(page).to_have_url(f"{base_url}/study")
        
        # 3. 学習設定
        page.select_option('select[name="exam_type"]', "FE")
        page.select_option('select[name="mode"]', "practice")
        page.fill('input[name="count"]', "3")
        
        # 4. 学習セッション開始
        page.click('button:text("開始")')
        
        # 5. 問題ページに遷移
        expect(page).to_have_url(f"{base_url}/question")
        
        # 6. 3問の問題に回答
        for i in range(3):
            # 問題が表示されることを確認
            expect(page.locator(".question-text")).to_be_visible()
            expect(page.locator(".choices")).to_be_visible()
            
            # 最初の選択肢を選択
            page.check('input[name="answer"][value="1"]')
            
            # 回答送信
            page.click('button[type="submit"]:text("回答")')
            
            # 最後の問題でなければ、次の問題ページに遷移
            if i < 2:
                expect(page).to_have_url(f"{base_url}/question")
            else:
                # 最後の問題後は結果ページに遷移
                expect(page).to_have_url(f"{base_url}/result")
        
        # 7. 結果ページの確認
        expect(page.locator(".session-result")).to_be_visible()
        expect(page.locator(".correct-rate")).to_be_visible()
        expect(page.locator(".total-questions")).to_be_visible()
    
    def test_mock_exam_flow(self, page: Page, base_url: str):
        """模擬試験フローのE2Eテスト"""
        
        # 学習ページアクセス
        page.goto(f"{base_url}/study")
        
        # 模擬試験設定
        page.select_option('select[name="exam_type"]', "FE")
        page.select_option('select[name="mode"]', "mock_exam")
        
        # 開始
        page.click('button:text("開始")')
        
        # 問題ページ確認
        expect(page).to_have_url(f"{base_url}/question")
        
        # 模擬試験では80問になることを確認（問題番号表示で確認）
        question_info = page.locator(".question-info")
        expect(question_info).to_contain_text("80")
    
    def test_progress_page_interaction(self, page: Page, base_url: str):
        """進捗ページのE2Eテスト"""
        
        # 進捗ページアクセス
        page.goto(f"{base_url}/progress")
        expect(page).to_have_title("進捗確認")
        
        # 基本要素の確認
        expect(page.locator(".statistics-section")).to_be_visible()
        expect(page.locator(".chart-container")).to_be_visible()
        
        # 試験種別選択
        if page.locator('select[name="exam_type"]').is_visible():
            page.select_option('select[name="exam_type"]', "FE")
            page.click('button:text("更新")')
        
        # チャートが更新されることを確認
        page.wait_for_selector(".chart-container canvas", timeout=5000)
    
    def test_settings_page_interaction(self, page: Page, base_url: str):
        """設定ページのE2Eテスト"""
        
        # 設定ページアクセス
        page.goto(f"{base_url}/settings")
        expect(page).to_have_title("設定")
        
        # 設定変更
        if page.locator('select[name="theme"]').is_visible():
            page.select_option('select[name="theme"]', "dark")
        
        if page.locator('select[name="difficulty_level"]').is_visible():
            page.select_option('select[name="difficulty_level"]', "2")
        
        # 設定保存
        page.click('button:text("保存")')
        
        # 成功メッセージまたはリダイレクト確認
        expect(page.locator(".alert-success")).to_be_visible(timeout=3000)
    
    def test_reports_generation_flow(self, page: Page, base_url: str):
        """レポート生成フローのE2Eテスト"""
        
        # レポートページアクセス
        page.goto(f"{base_url}/reports")
        expect(page).to_have_title("レポート")
        
        # レポート生成設定
        page.select_option('select[name="exam_type"]', "FE")
        page.select_option('select[name="days"]', "30")
        
        # レポート生成実行
        page.click('button:text("生成")')
        
        # 生成中メッセージまたは結果確認
        # （実際の処理時間に応じてタイムアウト調整）
        page.wait_for_selector(".report-result", timeout=10000)
    
    def test_responsive_design(self, page: Page, base_url: str):
        """レスポンシブデザインのE2Eテスト"""
        
        # モバイルサイズに変更
        page.set_viewport_size({"width": 375, "height": 667})
        
        # トップページアクセス
        page.goto(base_url)
        
        # モバイルメニューが適切に表示されることを確認
        if page.locator(".navbar-toggle").is_visible():
            page.click(".navbar-toggle")
            expect(page.locator(".navbar-nav")).to_be_visible()
        
        # 学習ページでのレスポンシブ確認
        page.goto(f"{base_url}/study")
        
        # フォーム要素が適切に表示されることを確認
        expect(page.locator('select[name="exam_type"]')).to_be_visible()
        expect(page.locator('select[name="mode"]')).to_be_visible()
    
    def test_error_handling_scenarios(self, page: Page, base_url: str):
        """エラーハンドリングのE2Eテスト"""
        
        # 存在しないページアクセス
        page.goto(f"{base_url}/nonexistent")
        expect(page.locator(".error-404")).to_be_visible()
        
        # セッション未開始で問題ページアクセス
        page.goto(f"{base_url}/question")
        
        # エラーページまたは学習ページへのリダイレクト確認
        current_url = page.url
        assert "/study" in current_url or "/error" in current_url
    
    def test_accessibility_features(self, page: Page, base_url: str):
        """アクセシビリティ機能のE2Eテスト"""
        
        # トップページアクセス
        page.goto(base_url)
        
        # キーボードナビゲーション確認
        page.press("body", "Tab")
        focused_element = page.evaluate("document.activeElement.tagName")
        assert focused_element in ["A", "BUTTON", "INPUT", "SELECT"]
        
        # 学習ページでのキーボード操作
        page.goto(f"{base_url}/study")
        
        # Tab キーでフォーム要素間の移動確認
        page.press("body", "Tab")
        page.press("body", "Tab")
        page.press("body", "Tab")
        
        # Enter キーでのフォーム送信確認（適切なバリデーション後）
        page.select_option('select[name="exam_type"]', "FE")
        page.select_option('select[name="mode"]', "practice")
        page.fill('input[name="count"]', "1")
        page.press('button:text("開始")', "Enter")
    
    def test_performance_metrics(self, page: Page, base_url: str):
        """パフォーマンス指標のE2Eテスト"""
        
        # ページ読み込み時間測定
        start_time = time.time()
        page.goto(base_url)
        load_time = time.time() - start_time
        
        # 2秒以内の読み込み確認
        assert load_time < 2.0, f"Page load time {load_time:.2f}s exceeds 2s limit"
        
        # 学習ページの応答性確認
        start_time = time.time()
        page.goto(f"{base_url}/study")
        study_load_time = time.time() - start_time
        
        assert study_load_time < 2.0, f"Study page load time {study_load_time:.2f}s exceeds 2s limit"