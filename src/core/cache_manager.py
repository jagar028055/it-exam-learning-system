"""
Redisキャッシュマネージャー
"""
import json
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Union
import logging

logger = logging.getLogger(__name__)

# Redis の遅延インポート
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    logger.warning("Redis not available, using fallback cache")


class CacheManager:
    """統一キャッシュ管理クラス"""
    
    def __init__(self, redis_url: str = None, default_ttl: int = 3600):
        self.default_ttl = default_ttl  # 1時間
        self._memory_cache: Dict[str, tuple] = {}  # (value, expires_at)
        
        # Redis接続の試行
        self.redis_client = None
        if HAS_REDIS and redis_url:
            try:
                self.redis_client = redis.from_url(
                    redis_url,
                    decode_responses=False,  # バイナリデータ対応
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                # 接続テスト
                self.redis_client.ping()
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Redis connection failed, using memory cache: {e}")
                self.redis_client = None
    
    def get(self, key: str, default: Any = None) -> Any:
        """キャッシュから値を取得"""
        try:
            # Redis から取得試行
            if self.redis_client:
                value = self.redis_client.get(self._format_key(key))
                if value is not None:
                    return pickle.loads(value)
            
            # メモリキャッシュから取得
            if key in self._memory_cache:
                value, expires_at = self._memory_cache[key]
                if datetime.now() < expires_at:
                    return value
                else:
                    del self._memory_cache[key]
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
        
        return default
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """値をキャッシュに保存"""
        if ttl is None:
            ttl = self.default_ttl
        
        try:
            # Redis に保存
            if self.redis_client:
                serialized = pickle.dumps(value)
                success = self.redis_client.setex(
                    self._format_key(key), 
                    ttl, 
                    serialized
                )
                if success:
                    return True
            
            # メモリキャッシュに保存
            expires_at = datetime.now() + timedelta(seconds=ttl)
            self._memory_cache[key] = (value, expires_at)
            
            # メモリキャッシュのサイズ制限（1000アイテム）
            if len(self._memory_cache) > 1000:
                self._cleanup_memory_cache()
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """キーを削除"""
        try:
            deleted = False
            
            # Redis から削除
            if self.redis_client:
                result = self.redis_client.delete(self._format_key(key))
                deleted = result > 0
            
            # メモリキャッシュから削除
            if key in self._memory_cache:
                del self._memory_cache[key]
                deleted = True
            
            return deleted
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """キーの存在確認"""
        try:
            # Redis で確認
            if self.redis_client:
                return bool(self.redis_client.exists(self._format_key(key)))
            
            # メモリキャッシュで確認
            if key in self._memory_cache:
                _, expires_at = self._memory_cache[key]
                if datetime.now() < expires_at:
                    return True
                else:
                    del self._memory_cache[key]
            
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
        
        return False
    
    def clear(self, pattern: str = None) -> int:
        """キャッシュクリア"""
        cleared = 0
        
        try:
            if self.redis_client:
                if pattern:
                    # パターンマッチングでキー取得
                    keys = self.redis_client.keys(f"{self._get_prefix()}:{pattern}")
                    if keys:
                        cleared = self.redis_client.delete(*keys)
                else:
                    # 全キー削除
                    keys = self.redis_client.keys(f"{self._get_prefix()}:*")
                    if keys:
                        cleared = self.redis_client.delete(*keys)
            
            # メモリキャッシュクリア
            if pattern:
                memory_keys = [k for k in self._memory_cache.keys() if pattern in k]
                for k in memory_keys:
                    del self._memory_cache[k]
                cleared += len(memory_keys)
            else:
                cleared += len(self._memory_cache)
                self._memory_cache.clear()
                
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
        
        return cleared
    
    def get_stats(self) -> Dict:
        """キャッシュ統計情報"""
        stats = {
            'memory_cache_size': len(self._memory_cache),
            'redis_available': self.redis_client is not None,
            'redis_connected': False,
            'redis_info': {}
        }
        
        if self.redis_client:
            try:
                self.redis_client.ping()
                stats['redis_connected'] = True
                info = self.redis_client.info()
                stats['redis_info'] = {
                    'used_memory': info.get('used_memory_human', 'N/A'),
                    'connected_clients': info.get('connected_clients', 0),
                    'total_commands_processed': info.get('total_commands_processed', 0)
                }
            except Exception as e:
                stats['redis_error'] = str(e)
        
        return stats
    
    def _format_key(self, key: str) -> str:
        """キーをフォーマット"""
        return f"{self._get_prefix()}:{key}"
    
    def _get_prefix(self) -> str:
        """キャッシュプレフィックス"""
        return "itexam"
    
    def _cleanup_memory_cache(self):
        """期限切れキャッシュの削除"""
        now = datetime.now()
        expired_keys = [
            k for k, (_, expires_at) in self._memory_cache.items()
            if now >= expires_at
        ]
        
        for key in expired_keys:
            del self._memory_cache[key]
        
        # まだサイズが大きい場合は古いものから削除
        if len(self._memory_cache) > 1000:
            sorted_items = sorted(
                self._memory_cache.items(),
                key=lambda x: x[1][1]  # expires_at でソート
            )
            
            # 半分まで削減
            keep_count = 500
            for key, _ in sorted_items[keep_count:]:
                del self._memory_cache[key]


class CachedDataService:
    """データサービス用キャッシュデコレータ"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
    
    def cached_method(self, ttl: int = 3600, key_prefix: str = None):
        """メソッド結果をキャッシュするデコレータ"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # キャッシュキー生成
                cache_key = self._generate_cache_key(
                    func.__name__, args, kwargs, key_prefix
                )
                
                # キャッシュから取得試行
                result = self.cache.get(cache_key)
                if result is not None:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result
                
                # 関数実行
                logger.debug(f"Cache miss for {func.__name__}, executing...")
                result = func(*args, **kwargs)
                
                # 結果をキャッシュ
                if result is not None:
                    self.cache.set(cache_key, result, ttl)
                
                return result
            return wrapper
        return decorator
    
    def cached_property(self, ttl: int = 3600):
        """プロパティ結果をキャッシュするデコレータ"""
        def decorator(func):
            def wrapper(self_instance):
                cache_key = f"{self_instance.__class__.__name__}.{func.__name__}"
                
                result = self.cache.get(cache_key)
                if result is not None:
                    return result
                
                result = func(self_instance)
                if result is not None:
                    self.cache.set(cache_key, result, ttl)
                
                return result
            return property(wrapper)
        return decorator
    
    def invalidate_cache(self, pattern: str):
        """キャッシュ無効化"""
        return self.cache.clear(pattern)
    
    def _generate_cache_key(self, func_name: str, args: tuple, kwargs: dict, prefix: str = None) -> str:
        """キャッシュキーを生成"""
        # 引数をシリアライズ可能な形式に変換
        serializable_args = []
        for arg in args[1:]:  # self は除外
            if hasattr(arg, '__dict__'):
                serializable_args.append(str(arg))
            else:
                serializable_args.append(arg)
        
        key_data = {
            'func': func_name,
            'args': serializable_args,
            'kwargs': sorted(kwargs.items())
        }
        
        # ハッシュ化
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()[:12]
        
        if prefix:
            return f"{prefix}:{func_name}:{key_hash}"
        else:
            return f"{func_name}:{key_hash}"


# グローバルインスタンス
cache_manager = CacheManager()
cached_service = CachedDataService(cache_manager)