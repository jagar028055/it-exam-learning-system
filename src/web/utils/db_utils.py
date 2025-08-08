"""
データベース操作ユーティリティ
"""

import logging
from functools import wraps
from typing import Callable, Any, Optional, Dict, List
from contextlib import contextmanager

from ...core.database import DatabaseManager
from .error_handler import DatabaseError

logger = logging.getLogger(__name__)

class DatabaseUtils:
    """データベース操作ユーティリティ"""
    
    @staticmethod
    def with_transaction(db_manager: DatabaseManager):
        """トランザクション管理デコレータ"""
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def wrapper(*args, **kwargs):
                with db_manager.get_connection() as conn:
                    try:
                        result = f(conn, *args, **kwargs)
                        conn.commit()
                        return result
                    except Exception as e:
                        conn.rollback()
                        logger.error(f"トランザクションエラー in {f.__name__}: {e}")
                        raise DatabaseError(f"データベース操作に失敗しました: {e}")
            return wrapper
        return decorator
    
    @staticmethod
    def with_error_handling(f: Callable) -> Callable:
        """データベースエラーハンドリングデコレータ"""
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"データベースエラー in {f.__name__}: {e}")
                raise DatabaseError(f"データベース操作に失敗しました: {e}")
        return wrapper
    
    @staticmethod
    def paginate_results(results: List[Dict], page: int = 1, per_page: int = 20) -> Dict:
        """結果のページネーション"""
        total = len(results)
        start = (page - 1) * per_page
        end = start + per_page
        
        return {
            'items': results[start:end],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total - 1) // per_page + 1,
            'has_prev': page > 1,
            'has_next': end < total,
            'prev_num': page - 1 if page > 1 else None,
            'next_num': page + 1 if end < total else None
        }
    
    @staticmethod
    def validate_exam_type(exam_type: str) -> bool:
        """試験種別の検証"""
        from ...core.config import config
        return exam_type in config.EXAM_CATEGORIES
    
    @staticmethod
    def validate_study_mode(mode: str) -> bool:
        """学習モードの検証"""
        valid_modes = ['practice', 'mock_exam', 'review', 'weak_area']
        return mode in valid_modes
    
    @staticmethod
    def validate_question_count(count: int) -> bool:
        """問題数の検証"""
        return isinstance(count, int) and 1 <= count <= 100
    
    @staticmethod
    def sanitize_input(value: Any) -> str:
        """入力値のサニタイズ"""
        if value is None:
            return ""
        return str(value).strip()

class QueryBuilder:
    """クエリビルダー"""
    
    def __init__(self):
        self.query_parts = []
        self.params = []
    
    def select(self, columns: str) -> 'QueryBuilder':
        """SELECT句"""
        self.query_parts.append(f"SELECT {columns}")
        return self
    
    def from_table(self, table: str) -> 'QueryBuilder':
        """FROM句"""
        self.query_parts.append(f"FROM {table}")
        return self
    
    def where(self, condition: str, *params) -> 'QueryBuilder':
        """WHERE句"""
        self.query_parts.append(f"WHERE {condition}")
        self.params.extend(params)
        return self
    
    def and_where(self, condition: str, *params) -> 'QueryBuilder':
        """AND WHERE句"""
        self.query_parts.append(f"AND {condition}")
        self.params.extend(params)
        return self
    
    def order_by(self, column: str, direction: str = "ASC") -> 'QueryBuilder':
        """ORDER BY句"""
        self.query_parts.append(f"ORDER BY {column} {direction}")
        return self
    
    def limit(self, count: int) -> 'QueryBuilder':
        """LIMIT句"""
        self.query_parts.append(f"LIMIT {count}")
        return self
    
    def build(self) -> tuple:
        """クエリとパラメータを生成"""
        query = " ".join(self.query_parts)
        return query, self.params

class DatabaseCache:
    """シンプルなインメモリキャッシュ"""
    
    def __init__(self, max_size: int = 100):
        self.cache = {}
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[Any]:
        """キャッシュから取得"""
        return self.cache.get(key)
    
    def set(self, key: str, value: Any):
        """キャッシュに保存"""
        if len(self.cache) >= self.max_size:
            # LRU的に古いものを削除
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[key] = value
    
    def clear(self):
        """キャッシュをクリア"""
        self.cache.clear()
    
    def cached_query(self, cache_key: str, query_func: Callable, *args, **kwargs):
        """クエリ結果をキャッシュ"""
        result = self.get(cache_key)
        if result is None:
            result = query_func(*args, **kwargs)
            self.set(cache_key, result)
        return result