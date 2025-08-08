"""
統一エラーハンドリングユーティリティ
"""

import logging
from functools import wraps
from typing import Any, Callable, Tuple

from flask import flash, redirect, url_for, jsonify, render_template

logger = logging.getLogger(__name__)

class ErrorHandler:
    """統一エラーハンドリングクラス"""
    
    @staticmethod
    def handle_route_error(fallback_route: str = 'main.index'):
        """ルートエラーハンドリングデコレータ"""
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def wrapper(*args, **kwargs):
                try:
                    return f(*args, **kwargs)
                except ValidationError as e:
                    logger.warning(f"バリデーションエラー in {f.__name__}: {e}")
                    flash(f"入力値エラー: {e}", 'error')
                    return redirect(url_for(fallback_route))
                except DatabaseError as e:
                    logger.error(f"データベースエラー in {f.__name__}: {e}")
                    flash(f"データベースエラーが発生しました", 'error')
                    return redirect(url_for(fallback_route))
                except ServiceError as e:
                    logger.error(f"サービスエラー in {f.__name__}: {e}")
                    flash(f"サービスエラー: {e}", 'error')
                    return redirect(url_for(fallback_route))
                except Exception as e:
                    logger.error(f"予期しないエラー in {f.__name__}: {e}")
                    flash(f"予期しないエラーが発生しました", 'error')
                    return redirect(url_for(fallback_route))
            return wrapper
        return decorator
    
    @staticmethod
    def handle_api_error(f: Callable) -> Callable:
        """APIエラーハンドリングデコレータ"""
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except ValidationError as e:
                logger.warning(f"バリデーションエラー in {f.__name__}: {e}")
                return jsonify({'error': str(e), 'type': 'validation'}), 400
            except DatabaseError as e:
                logger.error(f"データベースエラー in {f.__name__}: {e}")
                return jsonify({'error': 'データベースエラー', 'type': 'database'}), 500
            except ServiceError as e:
                logger.error(f"サービスエラー in {f.__name__}: {e}")
                return jsonify({'error': str(e), 'type': 'service'}), 500
            except Exception as e:
                logger.error(f"予期しないエラー in {f.__name__}: {e}")
                return jsonify({'error': '内部サーバーエラー', 'type': 'internal'}), 500
        return wrapper
    
    @staticmethod
    def handle_service_error(logger_name: str = None):
        """サービス層エラーハンドリングデコレータ"""
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def wrapper(*args, **kwargs):
                service_logger = logging.getLogger(logger_name or f.__module__)
                try:
                    return f(*args, **kwargs)
                except DatabaseError as e:
                    service_logger.error(f"データベースエラー in {f.__name__}: {e}")
                    raise ServiceError(f"データ操作に失敗しました: {e}")
                except ValidationError as e:
                    service_logger.warning(f"バリデーションエラー in {f.__name__}: {e}")
                    raise  # ValidationErrorはそのまま再発生
                except Exception as e:
                    service_logger.error(f"予期しないエラー in {f.__name__}: {e}")
                    raise ServiceError(f"サービス処理に失敗しました: {e}")
            return wrapper
        return decorator

class ValidationError(Exception):
    """バリデーションエラー"""
    pass

class DatabaseError(Exception):
    """データベースエラー"""
    pass

class ServiceError(Exception):
    """サービス層エラー"""
    pass

class ErrorTemplateRenderer:
    """エラー画面レンダリング"""
    
    @staticmethod
    def render_error(error_code: int, error_message: str, details: str = None) -> Tuple[str, int]:
        """エラー画面をレンダリング"""
        return render_template('error.html',
                             error_code=error_code,
                             error_message=error_message,
                             details=details), error_code
    
    @staticmethod
    def render_404(error):
        """404エラー画面"""
        return ErrorTemplateRenderer.render_error(
            404, 
            "ページが見つかりません",
            "指定されたページは存在しません"
        )
    
    @staticmethod
    def render_500(error):
        """500エラー画面"""
        return ErrorTemplateRenderer.render_error(
            500,
            "内部サーバーエラー",
            "サーバー内部でエラーが発生しました"
        )
    
    @staticmethod
    def render_400(error):
        """400エラー画面"""
        return ErrorTemplateRenderer.render_error(
            400,
            "不正なリクエスト", 
            "リクエストの形式が正しくありません"
        )
    
    @staticmethod
    def render_403(error):
        """403エラー画面"""
        return ErrorTemplateRenderer.render_error(
            403,
            "アクセス拒否",
            "このリソースへのアクセス権限がありません"
        )