"""
Snapshot processor for escmd snapshot utility operations.

This module handles snapshot-related utility functions and data processing
that don't involve direct Elasticsearch API calls.
"""

from typing import Dict, Any, Optional


class SnapshotProcessor:
    """
    Processor for snapshot-related utility operations.
    
    This class handles snapshot data processing, statistics calculation,
    and formatting operations.
    """
    
    def __init__(self, es_client):
        """Initialize the SnapshotProcessor with ES client reference."""
        self.es_client = es_client
    
    def get_snapshot_stats_fast(self, repository_name: str) -> Dict[str, int]:
        """
        Get basic snapshot statistics (fast version for dashboard).
        
        Args:
            repository_name: Name of the snapshot repository
            
        Returns:
            dict: Statistics with counts for total, successful, failed, in_progress, partial snapshots
        """
        try:
            # Skip repository existence check for speed - let the snapshot call handle it
            # Get snapshots with minimal information
            response = self.es_client.es.snapshot.get(
                repository=repository_name, 
                snapshot="_all",
                verbose=False,  # Reduce response size
                ignore_unavailable=True
            )

            if 'snapshots' not in response:
                return {'total': 0, 'successful': 0, 'failed': 0, 'in_progress': 0, 'partial': 0}

            # Fast counting - only look at state field
            stats = {'total': 0, 'successful': 0, 'failed': 0, 'in_progress': 0, 'partial': 0}
            
            for snapshot in response['snapshots']:
                stats['total'] += 1
                state = snapshot.get('state', '').upper()
                if state == 'SUCCESS':
                    stats['successful'] += 1
                elif state == 'FAILED':
                    stats['failed'] += 1
                elif state == 'IN_PROGRESS':
                    stats['in_progress'] += 1
                elif state == 'PARTIAL':
                    stats['partial'] += 1

            return stats

        except Exception:
            # Silently return empty stats on any error for dashboard speed
            return {'total': 0, 'successful': 0, 'failed': 0, 'in_progress': 0, 'partial': 0}


# Backward compatibility function
def get_snapshot_stats_fast(es_client, repository_name: str) -> Dict[str, int]:
    """Backward compatibility function for getting snapshot stats fast."""
    processor = SnapshotProcessor(es_client)
    return processor.get_snapshot_stats_fast(repository_name)
