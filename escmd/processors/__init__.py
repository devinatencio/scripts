"""
Data processors module for Elasticsearch command-line tool.

This module provides a clean separation of data processing logic from business logic,
making it easier to test, maintain, and extend data transformation capabilities.
"""

# Import modules for availability
from . import index_processor
from . import node_processor
from . import shard_processor
from . import allocation_processor
from . import statistics_processor
from . import replica_processor

# Import classes for direct access
try:
    from .index_processor import IndexProcessor
    from .node_processor import NodeProcessor
    from .shard_processor import ShardProcessor
    from .allocation_processor import AllocationProcessor
    from .statistics_processor import StatisticsProcessor
    from .replica_processor import ReplicaProcessor
    
    __all__ = [
        'IndexProcessor',
        'NodeProcessor',
        'ShardProcessor', 
        'AllocationProcessor',
        'StatisticsProcessor',
        'ReplicaProcessor'
    ]
except ImportError as e:
    # Fallback if there are import issues during development
    __all__ = []
    print(f"Warning: Could not import processor components: {e}")
