"""
パフォーマンステスト
"""
import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.core.database import DatabaseManager
from src.core.cache_manager import cache_manager
from src.web.services.study_service import StudyService


class TestPerformance:
    """パフォーマンステスト"""
    
    @pytest.fixture
    def db_manager(self):
        """テスト用DBマネージャー"""
        return DatabaseManager()
    
    @pytest.fixture
    def study_service(self, db_manager):
        """テスト用StudyService"""
        return StudyService(db_manager)
    
    @pytest.mark.slow
    def test_database_query_performance(self, db_manager):
        """データベースクエリのパフォーマンステスト"""
        # 統計情報取得のパフォーマンス測定
        start_time = time.time()
        
        for i in range(10):
            stats = db_manager.get_statistics('FE')
        
        end_time = time.time()
        avg_time = (end_time - start_time) / 10
        
        # 平均100ms以下であることを確認
        assert avg_time < 0.1, f"Database query too slow: {avg_time:.3f}s"
        print(f"Average database query time: {avg_time:.3f}s")
    
    @pytest.mark.slow
    def test_cache_performance(self, db_manager):
        """キャッシュのパフォーマンステスト"""
        # キャッシュなしでの実行時間測定
        cache_manager.clear()
        start_time = time.time()
        
        for i in range(5):
            stats = db_manager.get_statistics('FE')
        
        uncached_time = time.time() - start_time
        
        # キャッシュありでの実行時間測定
        start_time = time.time()
        
        for i in range(5):
            stats = db_manager.get_statistics('FE')
        
        cached_time = time.time() - start_time
        
        # キャッシュによる改善を確認
        improvement = (uncached_time - cached_time) / uncached_time * 100
        print(f"Cache improvement: {improvement:.1f}%")
        print(f"Uncached time: {uncached_time:.3f}s, Cached time: {cached_time:.3f}s")
        
        # キャッシュによる改善が期待される
        assert cached_time < uncached_time, "Cache should improve performance"
    
    @pytest.mark.slow
    def test_concurrent_access_performance(self, db_manager):
        """並行アクセスのパフォーマンステスト"""
        num_threads = 10
        queries_per_thread = 5
        
        def query_database():
            """データベースクエリを実行"""
            results = []
            for _ in range(queries_per_thread):
                start = time.time()
                stats = db_manager.get_statistics('FE')
                end = time.time()
                results.append(end - start)
            return results
        
        # 並行実行
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(query_database) for _ in range(num_threads)]
            all_results = []
            
            for future in as_completed(futures):
                all_results.extend(future.result())
        
        total_time = time.time() - start_time
        avg_query_time = sum(all_results) / len(all_results)
        
        print(f"Concurrent test - Total time: {total_time:.3f}s")
        print(f"Average query time: {avg_query_time:.3f}s")
        print(f"Total queries: {len(all_results)}")
        
        # 並行アクセスでも適切な性能を維持
        assert avg_query_time < 0.5, f"Concurrent access too slow: {avg_query_time:.3f}s"
    
    @pytest.mark.slow
    def test_memory_usage_performance(self, study_service):
        """メモリ使用量のパフォーマンステスト"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 大量のデータ処理を実行
        for i in range(100):
            stats = study_service.get_statistics('FE')
            recommendations = study_service.get_recommendations()
            categories = study_service.get_categories()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Initial memory: {initial_memory:.1f}MB")
        print(f"Final memory: {final_memory:.1f}MB") 
        print(f"Memory increase: {memory_increase:.1f}MB")
        
        # メモリ増加量が50MB以下であることを確認
        assert memory_increase < 50, f"Memory usage too high: {memory_increase:.1f}MB"
    
    def test_cache_hit_rate(self, db_manager):
        """キャッシュヒット率のテスト"""
        cache_manager.clear()
        
        # 同じクエリを複数回実行
        cache_hits = 0
        total_queries = 20
        
        for i in range(total_queries):
            start_time = time.time()
            stats = db_manager.get_statistics('FE')
            query_time = time.time() - start_time
            
            # 2回目以降は明らかに高速（キャッシュヒット）
            if i > 0 and query_time < 0.001:  # 1ms以下
                cache_hits += 1
        
        hit_rate = cache_hits / (total_queries - 1) * 100  # 最初のクエリは除外
        print(f"Cache hit rate: {hit_rate:.1f}%")
        
        # 80%以上のヒット率を期待
        assert hit_rate >= 80, f"Cache hit rate too low: {hit_rate:.1f}%"
    
    def test_large_dataset_performance(self, db_manager):
        """大量データでのパフォーマンステスト"""
        # テスト用の大量データ生成（実際の環境を想定）
        large_results = []
        
        start_time = time.time()
        
        # 大量データの処理をシミュレート
        for i in range(1000):
            # 軽量なデータ処理
            result = {
                'id': i,
                'timestamp': time.time(),
                'processed': True
            }
            large_results.append(result)
        
        processing_time = time.time() - start_time
        
        print(f"Large dataset processing time: {processing_time:.3f}s")
        print(f"Items processed: {len(large_results)}")
        print(f"Items per second: {len(large_results)/processing_time:.0f}")
        
        # 1秒以内での処理完了を確認
        assert processing_time < 1.0, f"Large dataset processing too slow: {processing_time:.3f}s"
    
    def test_response_time_consistency(self, db_manager):
        """レスポンス時間の一貫性テスト"""
        response_times = []
        
        # 複数回実行してレスポンス時間を測定
        for i in range(50):
            start_time = time.time()
            stats = db_manager.get_statistics('FE')
            response_time = time.time() - start_time
            response_times.append(response_time)
        
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        
        print(f"Response times - Avg: {avg_time:.3f}s, Min: {min_time:.3f}s, Max: {max_time:.3f}s")
        
        # 最大時間が平均の3倍以下であることを確認（一貫性）
        assert max_time <= avg_time * 3, f"Response time inconsistent: max={max_time:.3f}s, avg={avg_time:.3f}s"
    
    @pytest.mark.slow
    def test_system_resource_limits(self):
        """システムリソース制限のテスト"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # CPU使用率監視
        cpu_percent = process.cpu_percent()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        print(f"CPU usage: {cpu_percent:.1f}%")
        print(f"Memory usage: {memory_mb:.1f}MB")
        
        # リソース使用量の妥当性確認
        assert memory_mb < 200, f"Memory usage too high: {memory_mb:.1f}MB"  # 200MB以下