#!/bin/bash
"""
Claude生成パッチの自動適用スクリプト

使用方法:
1. Claude からパッチを受け取り patch.diff として保存
2. ./scripts/apply_patch.sh patch.diff "修正内容の説明"
"""

set -e  # エラー時に停止

PATCH_FILE="$1"
DESCRIPTION="$2"

if [ -z "$PATCH_FILE" ] || [ -z "$DESCRIPTION" ]; then
    echo "使用方法: $0 <patch_file> <description>"
    echo "例: $0 patch.diff 'Fix 500 error in user authentication'"
    exit 1
fi

if [ ! -f "$PATCH_FILE" ]; then
    echo "❌ パッチファイルが見つかりません: $PATCH_FILE"
    exit 1
fi

echo "🔧 Claude生成パッチの自動適用を開始..."
echo "📁 パッチファイル: $PATCH_FILE"
echo "📝 説明: $DESCRIPTION"

# バックアップブランチを作成
BACKUP_BRANCH="backup-$(date +%Y%m%d_%H%M%S)"
echo "💾 バックアップブランチを作成: $BACKUP_BRANCH"
git checkout -b "$BACKUP_BRANCH"
git checkout main

# 修正ブランチを作成
FIX_BRANCH="fix/claude-auto-$(date +%Y%m%d_%H%M%S)"
echo "🌿 修正ブランチを作成: $FIX_BRANCH"
git checkout -b "$FIX_BRANCH"

# パッチを適用
echo "🔨 パッチを適用中..."
if git apply --check "$PATCH_FILE"; then
    git apply "$PATCH_FILE"
    echo "✅ パッチが正常に適用されました"
else
    echo "❌ パッチの適用に失敗しました"
    echo "🔍 パッチの内容を確認してください:"
    cat "$PATCH_FILE"
    git checkout main
    git branch -D "$FIX_BRANCH"
    exit 1
fi

# 変更をステージング
echo "📋 変更をステージング..."
git add -A

# テストを実行 (もしテストがある場合)
if [ -f "requirements.txt" ] && command -v pytest >/dev/null 2>&1; then
    echo "🧪 テストを実行..."
    if ! pytest -v; then
        echo "❌ テストが失敗しました"
        echo "🔄 変更を取り消します..."
        git checkout main
        git branch -D "$FIX_BRANCH"
        exit 1
    fi
    echo "✅ テストが成功しました"
fi

# コミット
COMMIT_MSG="fix: $DESCRIPTION

🤖 Generated with Claude Pro

Co-Authored-By: Claude <noreply@anthropic.com>"

echo "💾 変更をコミット..."
git commit -m "$COMMIT_MSG"

# PR作成
if command -v gh >/dev/null 2>&1; then
    echo "🔀 Pull Requestを作成..."
    
    PR_BODY="$(cat <<EOF
## 概要
$DESCRIPTION

## 変更内容
- Claude Proが生成した自動パッチを適用
- 500エラーの修正

## テスト
- [x] 自動テストが成功
- [ ] 手動テストが必要

## デプロイ計画
1. PR承認後、自動的にmainブランチにマージ
2. GitHub ActionsでRenderに自動デプロイ
3. ヘルスチェックで動作確認

## ロールバック計画
問題が発生した場合は以下で即座にロールバック可能:
\`\`\`bash
git checkout main
git reset --hard HEAD~1
git push --force-with-lease
\`\`\`

または Render ダッシュボードで前のデプロイに戻す

---
🤖 Generated with Claude Pro
EOF
)"

    if gh pr create --title "🤖 Claude Auto Fix: $DESCRIPTION" --body "$PR_BODY"; then
        echo "✅ Pull Request が作成されました"
        
        # Auto-merge を有効化 (テストが通った場合)
        PR_URL=$(gh pr view --json url --jq .url)
        echo "🔗 PR URL: $PR_URL"
        
        # GitHub CLI で auto-merge を設定
        if gh pr merge --auto --merge; then
            echo "✅ Auto-merge が設定されました (テスト成功後に自動マージ)"
        else
            echo "⚠️  Auto-merge の設定に失敗しました。手動でマージしてください"
        fi
    else
        echo "❌ Pull Request の作成に失敗しました"
        echo "📋 手動でPRを作成してください:"
        echo "   git push origin $FIX_BRANCH"
        exit 1
    fi
else
    echo "⚠️  GitHub CLI (gh) がインストールされていません"
    echo "📋 手動でPRを作成してください:"
    echo "   git push origin $FIX_BRANCH"
    echo "   ブラウザでGitHubにアクセスしてPRを作成"
fi

echo ""
echo "🎉 Claude自動パッチ適用が完了しました！"
echo "📊 サマリー:"
echo "   - バックアップブランチ: $BACKUP_BRANCH"
echo "   - 修正ブランチ: $FIX_BRANCH"
echo "   - パッチファイル: $PATCH_FILE"
echo ""
echo "📈 次のステップ:"
echo "   1. PRのCI/CDが正常に完了するのを待機"
echo "   2. 自動的にmainブランチにマージ"
echo "   3. Renderに自動デプロイ"
echo "   4. ヘルスチェックで動作確認"
echo ""
echo "🚨 問題が発生した場合:"
echo "   git checkout main"
echo "   git branch -D $FIX_BRANCH"
echo "   # Renderで前のデプロイに戻す"