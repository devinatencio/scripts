#!/usr/bin/env python3
"""
Template backup and restore utilities for escmd.

This module provides functionality to backup and restore Elasticsearch templates
before making modifications, ensuring safe template management.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class TemplateBackup:
    """Handles backup and restore operations for Elasticsearch templates."""

    def __init__(self, backup_dir: Optional[str] = None):
        """
        Initialize the template backup manager.

        Args:
            backup_dir: Custom backup directory path. If None, uses default.
        """
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            # Default backup directory in user's escmd config area
            home_dir = Path.home()
            self.backup_dir = home_dir / '.escmd' / 'template_backups'

        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, template_name: str, template_type: str,
                     template_data: Dict[str, Any], cluster_name: Optional[str] = None) -> str:
        """
        Create a backup of a template.

        Args:
            template_name: Name of the template
            template_type: Type of template ('legacy', 'composable', 'component')
            template_data: Template data to backup
            cluster_name: Elasticsearch cluster name (optional)

        Returns:
            str: Path to the created backup file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Create backup filename
        cluster_suffix = f"_{cluster_name}" if cluster_name else ""
        backup_filename = f"{template_name}_{template_type}{cluster_suffix}_{timestamp}.json"
        backup_path = self.backup_dir / backup_filename

        # Prepare backup metadata
        backup_data = {
            'metadata': {
                'template_name': template_name,
                'template_type': template_type,
                'cluster_name': cluster_name,
                'backup_timestamp': datetime.now().isoformat(),
                'escmd_version': '3.0.3',  # Should be passed in or retrieved dynamically
                'backup_format_version': '1.0'
            },
            'template_data': template_data
        }

        try:
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Template backup created: {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Failed to create backup for template {template_name}: {str(e)}")
            raise RuntimeError(f"Backup creation failed: {str(e)}")

    def restore_template(self, backup_file: str) -> Dict[str, Any]:
        """
        Restore template data from a backup file.

        Args:
            backup_file: Path to the backup file

        Returns:
            Dict containing the restored template data and metadata
        """
        backup_path = Path(backup_file)

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")

        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            # Validate backup format
            if 'metadata' not in backup_data or 'template_data' not in backup_data:
                raise ValueError("Invalid backup file format")

            logger.info(f"Template backup restored from: {backup_path}")
            return backup_data

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in backup file {backup_file}: {str(e)}")
            raise ValueError(f"Invalid backup file format: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to restore from backup {backup_file}: {str(e)}")
            raise RuntimeError(f"Backup restoration failed: {str(e)}")

    def list_backups(self, template_name: Optional[str] = None, template_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available backups, optionally filtered by template name and type.

        Args:
            template_name: Filter by template name (optional)
            template_type: Filter by template type (optional)

        Returns:
            List of backup information dictionaries
        """
        backups = []

        try:
            for backup_file in self.backup_dir.glob('*.json'):
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        backup_data = json.load(f)

                    metadata = backup_data.get('metadata', {})

                    # Apply filters
                    if template_name and metadata.get('template_name') != template_name:
                        continue
                    if template_type and metadata.get('template_type') != template_type:
                        continue

                    backup_info = {
                        'file_path': str(backup_file),
                        'file_name': backup_file.name,
                        'template_name': metadata.get('template_name'),
                        'template_type': metadata.get('template_type'),
                        'cluster_name': metadata.get('cluster_name'),
                        'backup_timestamp': metadata.get('backup_timestamp'),
                        'file_size': backup_file.stat().st_size,
                        'created_date': datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
                    }

                    backups.append(backup_info)

                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Skipping invalid backup file {backup_file}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error listing backups: {str(e)}")
            raise RuntimeError(f"Failed to list backups: {str(e)}")

        # Sort by backup timestamp (newest first)
        backups.sort(key=lambda x: x.get('backup_timestamp', ''), reverse=True)

        return backups

    def cleanup_old_backups(self, template_name: Optional[str] = None, keep_count: int = 10) -> List[str]:
        """
        Clean up old backup files, keeping only the most recent ones.

        Args:
            template_name: Only cleanup backups for this template (optional)
            keep_count: Number of backups to keep per template

        Returns:
            List of deleted backup file paths
        """
        deleted_files = []

        try:
            # Group backups by template name
            backups_by_template = {}

            for backup_file in self.backup_dir.glob('*.json'):
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        backup_data = json.load(f)

                    metadata = backup_data.get('metadata', {})
                    tpl_name = metadata.get('template_name', 'unknown')

                    # Apply template name filter
                    if template_name and tpl_name != template_name:
                        continue

                    if tpl_name not in backups_by_template:
                        backups_by_template[tpl_name] = []

                    backups_by_template[tpl_name].append({
                        'path': backup_file,
                        'timestamp': metadata.get('backup_timestamp', ''),
                        'mtime': backup_file.stat().st_mtime
                    })

                except (json.JSONDecodeError, KeyError, OSError) as e:
                    logger.warning(f"Skipping file during cleanup {backup_file}: {str(e)}")
                    continue

            # Clean up old backups for each template
            for tpl_name, template_backups in backups_by_template.items():
                # Sort by modification time (newest first)
                template_backups.sort(key=lambda x: x['mtime'], reverse=True)

                # Delete old backups beyond keep_count
                for backup_info in template_backups[keep_count:]:
                    try:
                        backup_info['path'].unlink()
                        deleted_files.append(str(backup_info['path']))
                        logger.info(f"Deleted old backup: {backup_info['path']}")
                    except OSError as e:
                        logger.error(f"Failed to delete backup {backup_info['path']}: {str(e)}")

        except Exception as e:
            logger.error(f"Error during backup cleanup: {str(e)}")
            raise RuntimeError(f"Backup cleanup failed: {str(e)}")

        return deleted_files

    def get_backup_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the backup directory.

        Returns:
            Dictionary with backup statistics
        """
        stats = {
            'backup_directory': str(self.backup_dir),
            'total_backups': 0,
            'total_size_bytes': 0,
            'templates': {},
            'oldest_backup': None,
            'newest_backup': None
        }

        try:
            oldest_time = float('inf')
            newest_time = 0

            for backup_file in self.backup_dir.glob('*.json'):
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        backup_data = json.load(f)

                    stats['total_backups'] += 1
                    stats['total_size_bytes'] += backup_file.stat().st_size

                    metadata = backup_data.get('metadata', {})
                    tpl_name = metadata.get('template_name', 'unknown')
                    tpl_type = metadata.get('template_type', 'unknown')

                    if tpl_name not in stats['templates']:
                        stats['templates'][tpl_name] = {
                            'count': 0,
                            'types': set(),
                            'latest_backup': None
                        }

                    stats['templates'][tpl_name]['count'] += 1
                    stats['templates'][tpl_name]['types'].add(tpl_type)

                    # Track oldest and newest
                    mtime = backup_file.stat().st_mtime
                    if mtime < oldest_time:
                        oldest_time = mtime
                        stats['oldest_backup'] = str(backup_file)
                    if mtime > newest_time:
                        newest_time = mtime
                        stats['newest_backup'] = str(backup_file)
                        stats['templates'][tpl_name]['latest_backup'] = str(backup_file)

                except (json.JSONDecodeError, KeyError, OSError) as e:
                    logger.warning(f"Skipping file during stats collection {backup_file}: {str(e)}")
                    continue

            # Convert sets to lists for JSON serialization
            for tpl_info in stats['templates'].values():
                tpl_info['types'] = list(tpl_info['types'])

        except Exception as e:
            logger.error(f"Error collecting backup stats: {str(e)}")
            raise RuntimeError(f"Failed to collect backup statistics: {str(e)}")

        return stats
