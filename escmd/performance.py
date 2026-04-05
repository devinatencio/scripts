"""
Performance enhancements for the esclient refactored architecture.

This module provides caching and performance optimization utilities
to improve the efficiency of the modular esclient system.
"""

import functools
import time
from typing import Any, Dict, Optional, Union
import json
import hashlib


class MethodCache:
    """
    Simple caching system for expensive Elasticsearch operations.

    This class provides caching functionality for methods that make
    expensive API calls to Elasticsearch, reducing redundant requests.
    """

    def __init__(self, default_ttl: int = 300):
        """
        Initialize the method cache.

        Args:
            default_ttl: Default time-to-live in seconds for cached items
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl

    def _generate_key(self, method_name: str, args: tuple, kwargs: dict, client_context: str = None) -> str:
        """
        Generate a cache key from method name and parameters.

        Args:
            method_name: Name of the method being cached
            args: Method positional arguments
            kwargs: Method keyword arguments
            client_context: Client-specific context to include in key

        Returns:
            str: Cache key
        """
        # Create a stable hash from the method name and parameters
        key_data = {
            'method': method_name,
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else {},
            'client_context': client_context
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """
        Get a cached value by key.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key in self.cache:
            item = self.cache[key]
            if time.time() < item['expires']:
                return item['value']
            else:
                # Remove expired item
                del self.cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        if ttl is None:
            ttl = self.default_ttl

        self.cache[key] = {
            'value': value,
            'expires': time.time() + ttl,
            'created': time.time()
        }

    def invalidate(self, pattern: Optional[str] = None) -> int:
        """
        Invalidate cache entries.

        Args:
            pattern: Pattern to match keys for invalidation (None = all)

        Returns:
            int: Number of items invalidated
        """
        if pattern is None:
            count = len(self.cache)
            self.cache.clear()
            return count

        keys_to_remove = [
            key for key in self.cache.keys()
            if pattern in key
        ]

        for key in keys_to_remove:
            del self.cache[key]

        return len(keys_to_remove)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            dict: Cache statistics
        """
        now = time.time()
        expired_count = sum(
            1 for item in self.cache.values()
            if now >= item['expires']
        )

        return {
            'total_items': len(self.cache),
            'expired_items': expired_count,
            'active_items': len(self.cache) - expired_count
        }


def cached_method(ttl: int = 300, cache_instance: Optional[MethodCache] = None):
    """
    Decorator to cache method results.

    Args:
        ttl: Time-to-live in seconds for cached results
        cache_instance: Specific cache instance to use

    Returns:
        Decorated method with caching
    """
    def decorator(func):
        # Use a default cache instance if none provided
        cache = cache_instance or MethodCache(ttl)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key with client context
            method_name = f"{func.__qualname__}"

            # Extract client context from self (args[0])
            client_context = None
            if len(args) > 0 and hasattr(args[0], 'es_client'):
                # For command classes, get client connection info
                es_client = args[0].es_client

                # Try multiple ways to get connection info (in order of preference)
                if hasattr(es_client, 'elastic_host') and hasattr(es_client, 'elastic_port'):
                    # Use the client's stored connection parameters
                    client_context = f"{es_client.elastic_host}:{es_client.elastic_port}"
                elif hasattr(es_client, 'host1') and hasattr(es_client, 'port'):
                    # Fallback to host1/port attributes
                    client_context = f"{es_client.host1}:{es_client.port}"
                elif hasattr(es_client, 'transport') and hasattr(es_client.transport, 'hosts'):
                    # Use transport hosts info
                    hosts = es_client.transport.hosts
                    if hosts and len(hosts) > 0:
                        host_info = hosts[0]
                        client_context = f"{host_info.get('host', 'unknown')}:{host_info.get('port', 9200)}"
                elif hasattr(es_client, 'transport') and hasattr(es_client.transport, 'connection_pool'):
                    # Use connection pool info as last resort
                    try:
                        connections = es_client.transport.connection_pool.connections
                        if connections and len(connections) > 0:
                            conn = connections[0]
                            if hasattr(conn, 'hostname') and hasattr(conn, 'port'):
                                client_context = f"{conn.hostname}:{conn.port}"
                    except:
                        pass

            cache_key = cache._generate_key(method_name, args[1:], kwargs, client_context)  # Skip 'self'

            # Try to get from cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Call the actual method
            result = func(*args, **kwargs)

            # Cache the result
            cache.set(cache_key, result, ttl)

            return result

        # Attach cache management methods
        wrapper.cache = cache
        wrapper.invalidate_cache = lambda pattern=None: cache.invalidate(pattern)
        wrapper.cache_stats = lambda: cache.get_stats()

        return wrapper

    return decorator


class PerformanceMonitor:
    """
    Monitor method execution performance.

    This class helps identify performance bottlenecks in the refactored
    architecture by tracking method execution times.
    """

    def __init__(self):
        self.metrics: Dict[str, Dict[str, Any]] = {}

    def record_execution(self, method_name: str, execution_time: float) -> None:
        """
        Record method execution time.

        Args:
            method_name: Name of the method
            execution_time: Execution time in seconds
        """
        if method_name not in self.metrics:
            self.metrics[method_name] = {
                'count': 0,
                'total_time': 0.0,
                'min_time': float('inf'),
                'max_time': 0.0,
                'avg_time': 0.0
            }

        metric = self.metrics[method_name]
        metric['count'] += 1
        metric['total_time'] += execution_time
        metric['min_time'] = min(metric['min_time'], execution_time)
        metric['max_time'] = max(metric['max_time'], execution_time)
        metric['avg_time'] = metric['total_time'] / metric['count']

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get performance report for all monitored methods.

        Returns:
            dict: Performance metrics
        """
        return {
            'methods': self.metrics.copy(),
            'total_methods': len(self.metrics),
            'total_calls': sum(m['count'] for m in self.metrics.values())
        }

    def get_slowest_methods(self, limit: int = 10) -> list:
        """
        Get the slowest methods by average execution time.

        Args:
            limit: Number of methods to return

        Returns:
            list: Sorted list of slowest methods
        """
        sorted_methods = sorted(
            self.metrics.items(),
            key=lambda x: x[1]['avg_time'],
            reverse=True
        )
        return sorted_methods[:limit]


def performance_monitor(monitor_instance: Optional[PerformanceMonitor] = None):
    """
    Decorator to monitor method performance.

    Args:
        monitor_instance: Specific monitor instance to use

    Returns:
        Decorated method with performance monitoring
    """
    def decorator(func):
        monitor = monitor_instance or PerformanceMonitor()

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                method_name = f"{func.__qualname__}"
                monitor.record_execution(method_name, execution_time)

        # Attach monitoring methods
        wrapper.performance_monitor = monitor
        wrapper.get_performance_report = monitor.get_performance_report
        wrapper.get_slowest_methods = monitor.get_slowest_methods

        return wrapper

    return decorator


# Global instances for convenience
default_cache = MethodCache(default_ttl=300)  # 5-minute default TTL
default_monitor = PerformanceMonitor()

# Convenience decorators using global instances
cache_5min = cached_method(ttl=300, cache_instance=default_cache)
cache_1min = cached_method(ttl=60, cache_instance=default_cache)
cache_30sec = cached_method(ttl=30, cache_instance=default_cache)
monitor_performance = performance_monitor(default_monitor)
