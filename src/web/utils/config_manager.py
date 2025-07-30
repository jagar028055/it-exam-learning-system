"""
Web設定管理ユーティリティ
"""

import os
from typing import Dict, Any

class WebConfigManager:
    """Web設定管理クラス"""
    
    @staticmethod
    def get_flask_config() -> Dict[str, Any]:
        """Flask設定を取得"""
        return {
            'SECRET_KEY': WebConfigManager._get_secret_key(),
            'SESSION_TYPE': 'filesystem',
            'SESSION_PERMANENT': False,
            'SESSION_USE_SIGNER': True,
            'SESSION_FILE_DIR': WebConfigManager._get_session_dir(),
            'SEND_FILE_MAX_AGE_DEFAULT': WebConfigManager._get_cache_max_age(),
        }
    
    @staticmethod
    def get_security_config() -> Dict[str, Any]:
        """セキュリティ設定を取得"""
        if not WebConfigManager.is_production():
            return {}
        
        return {
            'CSP': {
                'default-src': "'self'",
                'script-src': "'self' 'unsafe-inline'",
                'style-src': "'self' 'unsafe-inline'",
                'img-src': "'self' data:",
                'font-src': "'self'",
                'connect-src': "'self'", 
                'frame-src': "'none'"
            },
            'FORCE_HTTPS': True,
            'STRICT_TRANSPORT_SECURITY': True
        }
    
    @staticmethod
    def get_logging_config() -> Dict[str, Any]:
        """ログ設定を取得"""
        level = 'DEBUG' if WebConfigManager.is_development() else 'INFO'
        
        return {
            'level': level,
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'handlers': ['file', 'console']
        }
    
    @staticmethod
    def is_production() -> bool:
        """本番環境かどうか"""
        return os.environ.get('FLASK_ENV') == 'production'
    
    @staticmethod
    def is_development() -> bool:
        """開発環境かどうか"""
        return not WebConfigManager.is_production()
    
    @staticmethod
    def _get_secret_key() -> str:
        """シークレットキーを取得"""
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key:
            if WebConfigManager.is_production():
                raise ValueError("SECRET_KEY environment variable is required in production")
            # 開発環境では警告を出して固定値を使用
            import secrets
            secret_key = secrets.token_hex(16)
            print(f"WARNING: Using generated SECRET_KEY: {secret_key}")
        return secret_key
    
    @staticmethod
    def _get_session_dir() -> str:
        """セッションディレクトリを取得"""
        default_dir = '/tmp/flask_session' if WebConfigManager.is_production() else './flask_session'
        return os.environ.get('SESSION_FILE_DIR', default_dir)
    
    @staticmethod
    def _get_cache_max_age() -> int:
        """キャッシュ最大期間を取得"""
        return 31536000 if WebConfigManager.is_production() else 0  # 本番: 1年, 開発: キャッシュなし