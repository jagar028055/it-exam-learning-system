#!/usr/bin/env python3
"""
情報技術者試験学習システム - メインエントリーポイント
統一されたアプリケーション起動スクリプト
"""

import os
import sys
import argparse
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def start_web_server(host='0.0.0.0', port=5001, debug=True):
    """Webサーバーを起動"""
    from src.web.app import app
    from src.core.config import config
    
    # 必要なディレクトリを作成
    config.create_directories()
    
    # セッション用ディレクトリを作成
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    
    print(f"🚀 情報技術者試験学習システム起動")
    print(f"📱 アクセス URL: http://localhost:{port}")
    print(f"⏹️  停止するには Ctrl+C を押してください")
    
    # 開発サーバーを起動
    app.run(debug=debug, host=host, port=port)

def start_cli_interface():
    """CLIインターフェースを起動"""
    from main import main as cli_main
    return cli_main()

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="情報技術者試験学習システム",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--mode', choices=['web', 'cli'], default='web',
                       help='起動モード (default: web)')
    parser.add_argument('--host', default='0.0.0.0',
                       help='Webサーバーのホスト (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5001,
                       help='Webサーバーのポート (default: 5001)')
    parser.add_argument('--no-debug', action='store_true',
                       help='デバッグモードを無効にする')
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'web':
            start_web_server(
                host=args.host, 
                port=args.port, 
                debug=not args.no_debug
            )
        else:
            return start_cli_interface()
            
    except KeyboardInterrupt:
        print("\n\n⏹️ アプリケーションを終了しました。")
        return 0
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        return 1

# Gunicorn用のアプリケーションオブジェクト
from src.web.app import app

if __name__ == '__main__':
    # 開発サーバー用
    sys.exit(main())