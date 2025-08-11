"""
パフォーマンス最適化ユーティリティ
"""
import os
import gzip
import hashlib
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta


class StaticFileOptimizer:
    """静的ファイルの最適化クラス"""
    
    def __init__(self, static_dir: Path):
        self.static_dir = static_dir
        self.cache_dir = static_dir / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        self._file_hashes: Dict[str, str] = {}
    
    def get_optimized_path(self, file_path: str) -> str:
        """最適化されたファイルパスを取得"""
        file_path_obj = Path(file_path)
        
        # ハッシュ値を含むファイル名を生成
        file_hash = self._get_file_hash(file_path_obj)
        optimized_name = f"{file_path_obj.stem}.{file_hash[:8]}{file_path_obj.suffix}"
        
        return f"/static/cache/{optimized_name}"
    
    def minify_css(self, css_content: str) -> str:
        """CSS最小化"""
        # 基本的なCSS最小化
        # コメント削除
        import re
        css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
        
        # 不要な空白削除
        css_content = re.sub(r'\s+', ' ', css_content)
        css_content = re.sub(r';\s*}', '}', css_content)
        css_content = re.sub(r'{\s*', '{', css_content)
        css_content = re.sub(r'}\s*', '}', css_content)
        css_content = re.sub(r':\s*', ':', css_content)
        css_content = re.sub(r';\s*', ';', css_content)
        
        return css_content.strip()
    
    def minify_js(self, js_content: str) -> str:
        """JavaScript基本最小化"""
        # 基本的なJS最小化（コメント削除と改行削除）
        import re
        
        # 単行コメント削除
        js_content = re.sub(r'//.*$', '', js_content, flags=re.MULTILINE)
        
        # 複数行コメント削除
        js_content = re.sub(r'/\*.*?\*/', '', js_content, flags=re.DOTALL)
        
        # 不要な空白と改行削除
        js_content = re.sub(r'\s+', ' ', js_content)
        js_content = re.sub(r';\s*', ';', js_content)
        
        return js_content.strip()
    
    def compress_file(self, file_path: Path, content: str) -> Path:
        """ファイルをgzip圧縮"""
        compressed_path = self.cache_dir / f"{file_path.name}.gz"
        
        with gzip.open(compressed_path, 'wt', encoding='utf-8') as f:
            f.write(content)
        
        return compressed_path
    
    def _get_file_hash(self, file_path: Path) -> str:
        """ファイルのハッシュ値を取得"""
        if str(file_path) in self._file_hashes:
            return self._file_hashes[str(file_path)]
        
        if not file_path.exists():
            return "0" * 32
        
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read(), usedforsecurity=False).hexdigest()
            self._file_hashes[str(file_path)] = file_hash
            return file_hash


class MemoryOptimizer:
    """メモリ使用量最適化クラス"""
    
    @staticmethod
    def lazy_import_plotly():
        """Plotly遅延インポート"""
        try:
            import plotly.graph_objects as go
            import plotly.express as px
            return go, px, True
        except ImportError:
            return None, None, False
    
    @staticmethod
    def lazy_import_pandas():
        """Pandas遅延インポート"""
        try:
            import pandas as pd
            return pd, True
        except ImportError:
            return None, False
    
    @staticmethod
    def create_lightweight_chart(data: Dict, chart_type: str = "bar") -> str:
        """軽量チャート生成（Chart.js使用）"""
        chart_id = f"chart_{hashlib.md5(str(data).encode(), usedforsecurity=False).hexdigest()[:8]}"
        
        if chart_type == "bar":
            return f"""
            <canvas id="{chart_id}" width="400" height="200"></canvas>
            <script>
            const ctx_{chart_id} = document.getElementById('{chart_id}').getContext('2d');
            new Chart(ctx_{chart_id}, {{
                type: 'bar',
                data: {str(data).replace("'", '"')},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{ display: false }}
                    }},
                    scales: {{
                        y: {{ beginAtZero: true }}
                    }}
                }}
            }});
            </script>
            """
        
        return f"<div>Chart type '{chart_type}' not supported in lightweight mode</div>"


class CacheManager:
    """キャッシュ管理クラス"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        self._memory_cache: Dict[str, tuple] = {}  # (value, timestamp)
        self.cache_ttl = timedelta(minutes=15)  # 15分TTL
    
    def get(self, key: str) -> Optional[any]:
        """キャッシュから値を取得"""
        # メモリキャッシュから確認
        if key in self._memory_cache:
            value, timestamp = self._memory_cache[key]
            if datetime.now() - timestamp < self.cache_ttl:
                return value
            else:
                del self._memory_cache[key]
        
        # ファイルキャッシュから確認
        cache_file = self.cache_dir / f"{self._hash_key(key)}.cache"
        if cache_file.exists():
            try:
                stat = cache_file.stat()
                cache_time = datetime.fromtimestamp(stat.st_mtime)
                
                if datetime.now() - cache_time < self.cache_ttl:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        import json
                        value = json.load(f)
                        # メモリキャッシュにも保存
                        self._memory_cache[key] = (value, datetime.now())
                        return value
                else:
                    cache_file.unlink()  # 期限切れファイル削除
            except (IOError, ValueError):
                pass
        
        return None
    
    def set(self, key: str, value: any) -> None:
        """値をキャッシュに保存"""
        # メモリキャッシュに保存
        self._memory_cache[key] = (value, datetime.now())
        
        # ファイルキャッシュにも保存
        cache_file = self.cache_dir / f"{self._hash_key(key)}.cache"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(value, f, ensure_ascii=False, default=str)
        except (IOError, TypeError):
            pass  # キャッシュ失敗は致命的でない
    
    def clear(self) -> None:
        """キャッシュをクリア"""
        self._memory_cache.clear()
        
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                cache_file.unlink()
            except OSError:
                pass
    
    def cleanup_expired(self) -> None:
        """期限切れキャッシュを削除"""
        now = datetime.now()
        
        # メモリキャッシュクリーンアップ
        expired_keys = [
            key for key, (_, timestamp) in self._memory_cache.items()
            if now - timestamp >= self.cache_ttl
        ]
        for key in expired_keys:
            del self._memory_cache[key]
        
        # ファイルキャッシュクリーンアップ
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                stat = cache_file.stat()
                cache_time = datetime.fromtimestamp(stat.st_mtime)
                if now - cache_time >= self.cache_ttl:
                    cache_file.unlink()
            except OSError:
                pass
    
    def _hash_key(self, key: str) -> str:
        """キーをハッシュ化"""
        return hashlib.md5(key.encode('utf-8'), usedforsecurity=False).hexdigest()


# グローバルインスタンス
cache_manager = CacheManager()


def cached_function(ttl_minutes: int = 15):
    """関数結果をキャッシュするデコレータ"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # キャッシュキーを生成
            cache_key = f"{func.__name__}_{hash((args, tuple(sorted(kwargs.items()))))}"
            
            # キャッシュから取得試行
            result = cache_manager.get(cache_key)
            if result is not None:
                return result
            
            # 関数実行してキャッシュに保存
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result)
            return result
        
        return wrapper
    return decorator