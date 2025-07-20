#!/usr/bin/env python3
"""
情報技術者試験学習システム - メインエントリーポイント
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.web.app import app
from src.core.config import config

if __name__ == '__main__':
    # 必要なディレクトリを作成
    config.create_directories()
    
    # セッション用ディレクトリを作成
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    
    # 開発サーバーを起動
    app.run(debug=True, host='0.0.0.0', port=5001)