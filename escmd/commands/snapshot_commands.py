"""
Snapshot command processors extracted from ElasticsearchClient.

This module handles snapshot-related operations including:
- Snapshot creation and management
- Repository management
- Snapshot restoration
- Snapshot status monitoring
"""

from typing import Dict, Any, Optional, List, Callable
from .base_command import BaseCommand
from display.progress_display import ProgressDisplay


class SnapshotCommands(BaseCommand):
    """
    Command processor for snapshot-related operations.

    This class extracts snapshot management methods from the main ElasticsearchClient,
    providing a focused interface for backup and restore operations.
    """

    def __init__(self, es_client, theme_manager=None):
        """Initialize with ES client reference."""
        super().__init__(es_client)
        self.last_error = None
        self.theme_manager = theme_manager
        self.progress_display = (
            ProgressDisplay(theme_manager=theme_manager) if theme_manager else None
        )

    def get_command_group(self) -> str:
        """Get the command group identifier."""
        return "snapshots"

    def get_snapshot_timeout(self) -> int:
        """
        Get the snapshot operation timeout value from configuration.

        Returns:
            int: Timeout in seconds, defaults to 120 if not configured
        """
        if (
            hasattr(self.es_client, "configuration_manager")
            and self.es_client.configuration_manager
        ):
            # Try to get snapshot-specific timeout
            config = self.es_client.configuration_manager.main_config or {}
            settings = config.get("settings", {})

            # First check for snapshot-specific timeout
            if "snapshot_timeout" in settings:
                return int(settings["snapshot_timeout"])

            # Fall back to general read_timeout
            if "read_timeout" in settings:
                return int(settings["read_timeout"])

            # As a last resort, try the timeout from the ES client
            if hasattr(self.es_client, "timeout"):
                return int(self.es_client.timeout)

        # Default timeout if not configured
        return 120

    def get_snapshots(
        self,
        repository: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Get snapshots from all repositories or a specific repository.

        Args:
            repository: Specific repository name (optional)
            progress_callback: Optional callback function to update progress display

        Returns:
            dict: Snapshot information
        """
        try:
            # Get the configured timeout
            timeout = self.get_snapshot_timeout()

            if repository:
                try:
                    # Set a configurable timeout for repository operations
                    snapshots = self.es_client.es.snapshot.get(
                        repository=repository,
                        snapshot="*",
                        request_timeout=timeout,  # Use configurable timeout
                    )

                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback(100)  # Complete

                except Exception as repo_error:
                    self._handle_snapshot_error(repo_error, repository)
                    return {"error": self.last_error}
            else:
                # Get from all repositories
                repositories = self.get_repositories()
                all_snapshots = {}

                # Calculate progress increment per repository
                total_repos = len(repositories.keys())
                progress_increment = 100 / total_repos if total_repos > 0 else 100
                current_progress = 0

                for repo_name in repositories.keys():
                    try:
                        # Update progress if callback provided
                        if progress_callback:
                            progress_callback(current_progress)

                        repo_snapshots = self.es_client.es.snapshot.get(
                            repository=repo_name, snapshot="*", request_timeout=timeout
                        )

                        # Handle response format differences
                        if hasattr(repo_snapshots, "body"):
                            snapshots_data = repo_snapshots.body
                        elif hasattr(repo_snapshots, "get"):
                            snapshots_data = dict(repo_snapshots)
                        else:
                            snapshots_data = repo_snapshots

                        all_snapshots[repo_name] = snapshots_data

                        # Increment progress
                        current_progress += progress_increment
                        if progress_callback:
                            progress_callback(
                                min(current_progress, 99)
                            )  # Ensure we don't exceed 100%

                    except Exception as e:
                        all_snapshots[repo_name] = {"error": str(e)}

                # Final progress update
                if progress_callback:
                    progress_callback(100)

                return all_snapshots

            # Handle response format differences for single repository
            if hasattr(snapshots, "body"):
                return snapshots.body
            elif hasattr(snapshots, "get"):
                return dict(snapshots)
            else:
                return snapshots

        except Exception as e:
            return {"error": f"Failed to get snapshots: {str(e)}"}

    def _handle_snapshot_error(self, error, repository):
        """
        Handle and format snapshot operation errors.

        Args:
            error: The exception object
            repository: The repository name being accessed
        """
        error_type = type(error).__name__
        error_msg = str(error)

        # Customize error message based on error type
        if "repository_missing_exception" in error_msg.lower():
            self.last_error = (
                f"Repository '{repository}' not found on Elasticsearch server"
            )
        elif (
            "ConnectionTimeout" in error_type
            or "timeout" in error_msg.lower()
            or "timed out" in error_msg.lower()
            or "ReadTimeoutError" in error_msg
        ):
            timeout = self.get_snapshot_timeout()
            self.last_error = (
                f"Connection timeout ({timeout}s) accessing repository '{repository}'. "
                f"The repository may contain many snapshots or be on a slow storage system. "
                f"Try increasing 'snapshot_timeout' in escmd.yml to a larger value like 240 seconds."
            )
        elif (
            "access_denied" in error_msg.lower() or "unauthorized" in error_msg.lower()
        ):
            self.last_error = f"Access denied to repository '{repository}'. Check user permissions on the Elasticsearch server."
        else:
            self.last_error = f"Error accessing repository '{repository}': {error_msg}"

    def list_snapshots_formatted(
        self, repository_name: str, progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        List snapshots in a repository, returns formatted list for display.

        Args:
            repository_name: Repository name to list snapshots from
            progress_callback: Optional callback function to update progress display

        Returns:
            list: Formatted snapshot information for display
        """
        # Reset last error
        self.last_error = None

        # Get snapshots with progress updates
        snapshots_dict = self.get_snapshots(repository_name, progress_callback)

        # Handle error case
        if "error" in snapshots_dict:
            # Error is already set in self.last_error in get_snapshots
            return []

        # Extract snapshots list from the response
        if "snapshots" in snapshots_dict:
            snapshots_raw = snapshots_dict["snapshots"]
        else:
            return []

        # Format snapshots into expected list format
        snapshots = []

        # Calculate progress increment per snapshot for formatting phase
        total_snapshots = len(snapshots_raw)
        progress_increment = (
            50 / total_snapshots if total_snapshots > 0 else 50
        )  # Use 50% for this phase
        current_progress = 50  # Start at 50% since fetching was first half

        for idx, snapshot in enumerate(snapshots_raw):
            # Update progress if callback provided
            if (
                progress_callback and idx % max(1, int(total_snapshots / 10)) == 0
            ):  # Update progress every ~10% of snapshots
                progress_callback(current_progress)
                current_progress += progress_increment * max(
                    1, int(total_snapshots / 10)
                )

            snapshot_info = {
                "repository": repository_name,
                "snapshot": snapshot.get("snapshot", "Unknown"),
                "state": snapshot.get("state", "Unknown"),
                "start_time": snapshot.get("start_time", "N/A"),
                "end_time": snapshot.get("end_time", "N/A"),
                "duration_in_millis": snapshot.get("duration_in_millis", 0),
                "indices": snapshot.get("indices", []),
                "include_global_state": snapshot.get("include_global_state", False),
                "failures": snapshot.get("failures", []),
            }

            # Calculate duration in human readable format
            if snapshot_info["duration_in_millis"] > 0:
                duration_seconds = snapshot_info["duration_in_millis"] / 1000
                if duration_seconds >= 3600:
                    snapshot_info["duration"] = f"{duration_seconds / 3600:.1f}h"
                elif duration_seconds >= 60:
                    snapshot_info["duration"] = f"{duration_seconds / 60:.1f}m"
                else:
                    snapshot_info["duration"] = f"{duration_seconds:.1f}s"
            else:
                # Fallback: try to calculate duration from start and end times
                try:
                    import datetime

                    start_time = snapshot_info.get("start_time")
                    end_time = snapshot_info.get("end_time")

                    if (
                        start_time
                        and end_time
                        and start_time != "N/A"
                        and end_time != "N/A"
                    ):
                        start_dt = datetime.datetime.fromisoformat(
                            start_time.replace("Z", "+00:00")
                        )
                        end_dt = datetime.datetime.fromisoformat(
                            end_time.replace("Z", "+00:00")
                        )
                        duration_seconds = (end_dt - start_dt).total_seconds()

                        if duration_seconds >= 3600:
                            snapshot_info["duration"] = (
                                f"{duration_seconds / 3600:.1f}h"
                            )
                        elif duration_seconds >= 60:
                            snapshot_info["duration"] = f"{duration_seconds / 60:.1f}m"
                        elif duration_seconds >= 1:
                            snapshot_info["duration"] = f"{duration_seconds:.1f}s"
                        else:
                            # Very fast snapshot (< 1 second)
                            millis = duration_seconds * 1000
                            if millis >= 1:
                                snapshot_info["duration"] = f"{millis:.0f}ms"
                            else:
                                snapshot_info["duration"] = "<1ms"
                    else:
                        snapshot_info["duration"] = "N/A"
                except:
                    snapshot_info["duration"] = "N/A"

            # Format timestamps for display
            import datetime

            def format_timestamp(ts_str):
                if not ts_str or ts_str == "N/A":
                    return "N/A"
                try:
                    # Parse ISO format timestamp
                    dt = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    return ts_str

            snapshot_info["start_time_formatted"] = format_timestamp(
                snapshot_info["start_time"]
            )
            snapshot_info["end_time_formatted"] = format_timestamp(
                snapshot_info["end_time"]
            )

            # Add indices count for easier access
            snapshot_info["indices_count"] = len(snapshot_info["indices"])

            snapshots.append(snapshot_info)

        return snapshots

    def list_snapshots_fast(
        self, repository_name: str, progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        List snapshots in a repository using fast mode (minimal metadata), returns formatted list for display.

        Args:
            repository_name: Repository name to list snapshots from
            progress_callback: Optional callback function to update progress display

        Returns:
            list: Formatted snapshot information for display (minimal metadata)
        """
        # Reset last error
        self.last_error = None

        try:
            # Get the configured timeout
            timeout = self.get_snapshot_timeout()

            # Call progress callback if provided (start)
            if progress_callback:
                progress_callback(10)

            # Use the fast API with minimal metadata
            snapshots_response = self.es_client.es.snapshot.get(
                repository=repository_name,
                snapshot="_all",
                verbose=False,  # Reduce response size
                ignore_unavailable=True,
                request_timeout=timeout,
            )

            # Call progress callback if provided (fetched)
            if progress_callback:
                progress_callback(70)

        except Exception as repo_error:
            self._handle_snapshot_error(repo_error, repository_name)
            return []

        # Handle response format differences
        if hasattr(snapshots_response, "body"):
            snapshots_dict = snapshots_response.body
        elif hasattr(snapshots_response, "get"):
            snapshots_dict = dict(snapshots_response)
        else:
            snapshots_dict = snapshots_response

        # Handle error case
        if "error" in snapshots_dict:
            return []

        # Extract snapshots list from the response
        if "snapshots" in snapshots_dict:
            snapshots_raw = snapshots_dict["snapshots"]
        else:
            return []

        # Format snapshots into expected list format (minimal processing for speed)
        snapshots = []

        # Calculate progress increment per snapshot for formatting phase
        total_snapshots = len(snapshots_raw)
        progress_increment = (
            25 / total_snapshots if total_snapshots > 0 else 25
        )  # Use remaining 25% for this phase
        current_progress = 75  # Start at 75% since fetching was first 70%

        for idx, snapshot in enumerate(snapshots_raw):
            # Update progress if callback provided (less frequently for speed)
            if (
                progress_callback and idx % max(1, int(total_snapshots / 5)) == 0
            ):  # Update progress every ~20% of snapshots
                progress_callback(current_progress)
                current_progress += progress_increment * max(
                    1, int(total_snapshots / 5)
                )

            snapshot_info = {
                "repository": repository_name,
                "snapshot": snapshot.get("snapshot", "Unknown"),
                "state": snapshot.get("state", "Unknown"),
                "start_time": snapshot.get("start_time", "N/A"),
                "end_time": snapshot.get("end_time", "N/A"),
                "duration_in_millis": snapshot.get("duration_in_millis", 0),
                "indices": snapshot.get("indices", []),
                "include_global_state": snapshot.get("include_global_state", False),
                "failures": snapshot.get("failures", []),
            }

            # Fast duration calculation (simplified)
            if snapshot_info["duration_in_millis"] > 0:
                duration_seconds = snapshot_info["duration_in_millis"] / 1000
                if duration_seconds >= 3600:
                    snapshot_info["duration"] = f"{duration_seconds / 3600:.1f}h"
                elif duration_seconds >= 60:
                    snapshot_info["duration"] = f"{duration_seconds / 60:.1f}m"
                else:
                    snapshot_info["duration"] = f"{duration_seconds:.1f}s"
            else:
                snapshot_info["duration"] = "N/A"

            # Fast timestamp formatting (simplified)
            def format_timestamp_fast(ts_str):
                if not ts_str or ts_str == "N/A":
                    return "N/A"
                try:
                    # Simple format for speed - just take first part if ISO format
                    if "T" in ts_str:
                        date_part, time_part = ts_str.split("T", 1)
                        time_part = time_part.split(".")[0]  # Remove milliseconds
                        return f"{date_part} {time_part}"
                    return ts_str
                except:
                    return ts_str

            snapshot_info["start_time_formatted"] = format_timestamp_fast(
                snapshot_info["start_time"]
            )
            snapshot_info["end_time_formatted"] = format_timestamp_fast(
                snapshot_info["end_time"]
            )

            # Add indices count for easier access
            snapshot_info["indices_count"] = len(snapshot_info["indices"])

            snapshots.append(snapshot_info)

        # Final progress update
        if progress_callback:
            progress_callback(100)

        return snapshots

    def get_repositories(self) -> Dict[str, Any]:
        """
        Get all snapshot repositories.

        Returns:
            dict: Repository information
        """
        try:
            repositories = self.es_client.es.snapshot.get_repository()

            # Handle response format differences
            if hasattr(repositories, "body"):
                return repositories.body
            elif hasattr(repositories, "get"):
                return dict(repositories)
            else:
                return repositories

        except Exception as e:
            return {"error": f"Failed to get repositories: {str(e)}"}

    def create_snapshot(
        self,
        repository: Optional[str] = None,
        snapshot_name: str = None,
        indices: Optional[str] = None,
        datastreams: Optional[str] = None,
        wait_for_completion: bool = False,
        default_repository: str = "s3-repo",
    ) -> Dict[str, Any]:
        """
        Create a new snapshot with enhanced parameter handling.

        Args:
            repository: Repository name (optional, uses default if not provided)
            snapshot_name: Name for the new snapshot
            indices: Comma-separated list of indices or list of indices (required - will not default to all)
            datastreams: Comma-separated list of datastreams or list of datastreams (optional)
            wait_for_completion: Whether to wait for completion
            default_repository: Default repository to use if repository is None

        Returns:
            dict: Operation result
        """
        try:
            # Handle default repository
            if repository is None:
                repository = default_repository

            # Convert indices/datastreams to the format expected by Elasticsearch
            target_indices = None
            if indices:
                if isinstance(indices, list):
                    target_indices = ",".join(indices)
                else:
                    target_indices = indices
            elif datastreams:
                # For datastreams, handle them as indices in the current implementation
                if isinstance(datastreams, list):
                    target_indices = ",".join(datastreams)
                else:
                    target_indices = datastreams

            # Require explicit specification of what to snapshot - don't default to all indices
            if not target_indices:
                return {
                    "error": "No indices or datastreams specified for snapshot. Please specify what to backup to avoid accidentally snapshotting all cluster data.",
                    "repository": repository,
                    "snapshot": snapshot_name,
                }

            body = {
                "indices": target_indices,
                "include_global_state": False,  # Exclude global state to avoid including system indices
            }

            snapshot = self.es_client.es.snapshot.create(
                repository=repository,
                snapshot=snapshot_name,
                body=body,
                wait_for_completion=wait_for_completion,
            )

            # Handle response format differences
            if hasattr(snapshot, "body"):
                return snapshot.body
            elif hasattr(snapshot, "get"):
                return dict(snapshot)
            else:
                return snapshot

        except Exception as e:
            return {
                "error": f"Failed to create snapshot: {str(e)}",
                "repository": repository,
                "snapshot": snapshot_name,
            }

    def delete_snapshot(self, repository: str, snapshot_name: str) -> Dict[str, Any]:
        """
        Delete a snapshot.

        Args:
            repository: Repository name
            snapshot_name: Snapshot name to delete

        Returns:
            dict: Operation result
        """
        try:
            result = self.es_client.es.snapshot.delete(
                repository=repository, snapshot=snapshot_name
            )

            # Handle response format differences
            if hasattr(result, "body"):
                return result.body
            elif hasattr(result, "get"):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to delete snapshot: {str(e)}",
                "repository": repository,
                "snapshot": snapshot_name,
            }

    def get_snapshot_status(
        self, repository: Optional[str] = None, snapshot: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get status of snapshots.

        Args:
            repository: Repository name (optional)
            snapshot: Snapshot name (optional)

        Returns:
            dict: Snapshot status information
        """
        try:
            params = {}
            if repository:
                params["repository"] = repository
            if snapshot:
                params["snapshot"] = snapshot

            if params:
                status = self.es_client.es.snapshot.status(**params)
            else:
                status = self.es_client.es.snapshot.status()

            # Handle response format differences
            if hasattr(status, "body"):
                return status.body
            elif hasattr(status, "get"):
                return dict(status)
            else:
                return status

        except Exception as e:
            return {"error": f"Failed to get snapshot status: {str(e)}"}

    def restore_snapshot(
        self,
        repository: str,
        snapshot_name: str,
        indices: Optional[str] = None,
        wait_for_completion: bool = False,
    ) -> Dict[str, Any]:
        """
        Restore a snapshot.

        Args:
            repository: Repository name
            snapshot_name: Snapshot name to restore
            indices: Comma-separated list of indices to restore (optional)
            wait_for_completion: Whether to wait for completion

        Returns:
            dict: Operation result
        """
        try:
            body = {}
            if indices:
                body["indices"] = indices

            restore = self.es_client.es.snapshot.restore(
                repository=repository,
                snapshot=snapshot_name,
                body=body,
                wait_for_completion=wait_for_completion,
            )

            # Handle response format differences
            if hasattr(restore, "body"):
                return restore.body
            elif hasattr(restore, "get"):
                return dict(restore)
            else:
                return restore

        except Exception as e:
            return {
                "error": f"Failed to restore snapshot: {str(e)}",
                "repository": repository,
                "snapshot": snapshot_name,
            }

    def create_repository(
        self, repository_name: str, repo_type: str, settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a snapshot repository.

        Args:
            repository_name: Name for the repository
            repo_type: Repository type (fs, s3, etc.)
            settings: Repository-specific settings

        Returns:
            dict: Operation result
        """
        try:
            repository = self.es_client.es.snapshot.create_repository(
                repository=repository_name,
                body={"type": repo_type, "settings": settings},
            )

            # Handle response format differences
            if hasattr(repository, "body"):
                return repository.body
            elif hasattr(repository, "get"):
                return dict(repository)
            else:
                return repository

        except Exception as e:
            return {
                "error": f"Failed to create repository: {str(e)}",
                "repository": repository_name,
                "type": repo_type,
            }

    def delete_repository(self, repository_name: str) -> Dict[str, Any]:
        """
        Delete a snapshot repository.

        Args:
            repository_name: Repository name to delete

        Returns:
            dict: Operation result
        """
        try:
            result = self.es_client.es.snapshot.delete_repository(
                repository=repository_name
            )

            # Handle response format differences
            if hasattr(result, "body"):
                return result.body
            elif hasattr(result, "get"):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to delete repository: {str(e)}",
                "repository": repository_name,
            }

    def verify_repository(self, repository_name: str) -> Dict[str, Any]:
        """
        Verify a snapshot repository.

        Args:
            repository_name: Repository name to verify

        Returns:
            dict: Verification result
        """
        try:
            result = self.es_client.es.snapshot.verify_repository(
                repository=repository_name
            )

            # Handle response format differences
            if hasattr(result, "body"):
                return result.body
            elif hasattr(result, "get"):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to verify repository: {str(e)}",
                "repository": repository_name,
            }

    def get_snapshot_info_comprehensive(
        self, repository_name: str, snapshot_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive snapshot information with formatted timestamps and details.

        Args:
            repository_name: Repository containing the snapshot
            snapshot_name: Name of the snapshot

        Returns:
            dict: Comprehensive snapshot information with formatted data, or None if not found
        """
        # Get snapshot data
        snapshots_dict = self.get_snapshots(repository_name)

        # Handle error case
        if "error" in snapshots_dict:
            return None

        # Extract snapshots list from the response
        if "snapshots" not in snapshots_dict:
            return None

        # Get repository information
        try:
            repositories = self.get_repositories()
            repo_info = repositories.get(repository_name, {})
            repo_settings = repo_info.get("settings", {})
            repo_type = repo_info.get("type", "unknown")
        except:
            repo_settings = {}
            repo_type = "unknown"

        # Find the specific snapshot
        for snapshot in snapshots_dict["snapshots"]:
            if snapshot.get("snapshot") == snapshot_name:
                # Build comprehensive snapshot info
                info = {
                    "snapshot_name": snapshot.get("snapshot"),
                    "repository_name": repository_name,
                    "repository_type": repo_type,
                    "repository_settings": repo_settings,
                    "uuid": snapshot.get("uuid"),
                    "version_id": snapshot.get("version_id"),
                    "version": snapshot.get("version"),
                    "state": snapshot.get("state", "UNKNOWN").upper(),
                    "start_time": snapshot.get("start_time"),
                    "end_time": snapshot.get("end_time"),
                    "duration_in_millis": snapshot.get("duration_in_millis", 0),
                    "indices": snapshot.get("indices", []),
                    "data_streams": snapshot.get("data_streams", []),
                    "include_global_state": snapshot.get("include_global_state", False),
                    "failures": snapshot.get("failures", []),
                    "metadata": snapshot.get("metadata", {}),
                    "successful_shards": snapshot.get("shards", {}).get(
                        "successful", 0
                    ),
                    "failed_shards": snapshot.get("shards", {}).get("failed", 0),
                    "total_shards": snapshot.get("shards", {}).get("total", 0),
                    "indices_count": len(snapshot.get("indices", [])),
                    "data_streams_count": len(snapshot.get("data_streams", [])),
                    "failures_count": len(snapshot.get("failures", [])),
                }

                # Format timestamps
                if info["start_time"] and info["start_time"] != "N/A":
                    try:
                        from datetime import datetime

                        start_dt = datetime.fromisoformat(
                            info["start_time"].replace("Z", "+00:00")
                        )
                        info["start_time_formatted"] = start_dt.strftime(
                            "%Y-%m-%d %H:%M:%S UTC"
                        )
                    except:
                        info["start_time_formatted"] = info["start_time"]
                else:
                    info["start_time_formatted"] = "N/A"

                if info["end_time"] and info["end_time"] != "N/A":
                    try:
                        from datetime import datetime

                        end_dt = datetime.fromisoformat(
                            info["end_time"].replace("Z", "+00:00")
                        )
                        info["end_time_formatted"] = end_dt.strftime(
                            "%Y-%m-%d %H:%M:%S UTC"
                        )
                    except:
                        info["end_time_formatted"] = info["end_time"]
                else:
                    info["end_time_formatted"] = "N/A"

                # Format duration
                if info["duration_in_millis"] > 0:
                    duration_seconds = info["duration_in_millis"] / 1000
                    if duration_seconds >= 3600:
                        info["duration"] = f"{duration_seconds / 3600:.1f}h"
                    elif duration_seconds >= 60:
                        info["duration"] = f"{duration_seconds / 60:.1f}m"
                    else:
                        info["duration"] = f"{duration_seconds:.1f}s"
                else:
                    info["duration"] = "N/A"

                return info

        return None

    def get_snapshot_status_enhanced(
        self, repository_name: Optional[str] = None, snapshot_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get enhanced snapshot status information combining status and info.

        Args:
            repository_name: Repository name (optional)
            snapshot_name: Snapshot name (optional)

        Returns:
            dict: Enhanced snapshot status information, or None if not found
        """
        # Get raw status from snapshot commands
        status_data = self.get_snapshot_status(repository_name, snapshot_name)

        if "error" in status_data:
            return None

        # Extract snapshots from status response
        snapshots = status_data.get("snapshots", [])
        if not snapshots:
            return None

        # Find the specific snapshot in the status
        target_snapshot = None
        for snapshot_status in snapshots:
            if snapshot_name and snapshot_status.get("snapshot") == snapshot_name:
                target_snapshot = snapshot_status
                break

        if not target_snapshot and snapshots:
            # If no specific snapshot found but we have snapshots, take the first one
            target_snapshot = snapshots[0]

        if not target_snapshot:
            return None

        # Get additional snapshot info for more complete data
        snapshot_info = self.get_snapshot_info_comprehensive(
            repository_name, target_snapshot.get("snapshot")
        )

        # If we have info, use it as base and enhance with status data
        if snapshot_info:
            # Update with live status information
            status_specific_data = target_snapshot.get("stats", {})
            if "incremental" in status_specific_data:
                incremental = status_specific_data["incremental"]
                snapshot_info.update(
                    {
                        "total_size_in_bytes": incremental.get("size_in_bytes", 0),
                        "files_processed": incremental.get("file_count", 0),
                        "bytes_processed": incremental.get("size_in_bytes", 0),
                    }
                )

            # Update state from status if available
            if "state" in target_snapshot:
                snapshot_info["state"] = target_snapshot["state"].upper()

            return snapshot_info
        else:
            # Fallback: build from status data only
            shards_stats = target_snapshot.get("shards_stats", {})
            indices = target_snapshot.get("indices", {})

            return {
                "snapshot_name": target_snapshot.get("snapshot"),
                "repository_name": repository_name or "default",
                "repository_type": "unknown",
                "repository_settings": {},
                "uuid": target_snapshot.get("uuid"),
                "state": target_snapshot.get("state", "UNKNOWN").upper(),
                "start_time_formatted": "N/A",
                "end_time_formatted": "N/A",
                "duration": "N/A",
                "indices_count": len(indices) if indices else 0,
                "data_streams_count": 0,
                "include_global_state": False,
                "total_shards": shards_stats.get("total", 0),
                "successful_shards": shards_stats.get("done", 0),
                "failed_shards": shards_stats.get("failed", 0),
                "failures_count": 0,
                "version": "N/A",
            }

    def list_restored_snapshots(
        self, index_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all restored snapshots/indices tracked in the system.

        Args:
            index_name: Name of the index containing restored snapshot tracking data.
                       If None, uses configured default from settings.

        Returns:
            List[Dict[str, Any]]: List of restored snapshot records

        Raises:
            Exception: If there's an error accessing the tracking index
        """
        try:
            # Get index name from config if not provided
            if index_name is None:
                if (
                    hasattr(self.es_client, "configuration_manager")
                    and self.es_client.configuration_manager
                ):
                    config = self.es_client.configuration_manager.main_config or {}
                    settings = config.get("settings", {})
                    index_name = settings.get(
                        "restored_snapshots_index", "rc_snapshots"
                    )
                else:
                    index_name = "rc_snapshots"  # Default fallback

            # Define the search query to get all documents
            query = {"query": {"match_all": {}}}

            # Perform the search using the ES client
            result = self.es_client.es.search(index=index_name, body=query)

            # Extract the documents from the search result
            hits = result.get("hits", {}).get("hits", [])

            # Extract and return the source data from each hit
            restored_records = []
            for hit in hits:
                source_data = hit.get("_source", {})
                # Add document ID for reference if needed
                source_data["_id"] = hit.get("_id")
                restored_records.append(source_data)

            return restored_records

        except Exception as e:
            error_msg = f"Error retrieving restored snapshots from index '{index_name}': {str(e)}"
            self.last_error = error_msg
            raise Exception(error_msg) from e

    def get_staged_count(self, index_name: Optional[str] = None) -> int:
        """
        Get the count of staged snapshots (in INIT status) that would be cleared.

        Args:
            index_name: Name of the index containing restored snapshot tracking data.
                       If None, uses configured default from settings.

        Returns:
            int: Number of staged snapshots found

        Raises:
            Exception: If there's an error accessing the tracking index
        """
        try:
            # Get index name from config if not provided
            if index_name is None:
                if (
                    hasattr(self.es_client, "configuration_manager")
                    and self.es_client.configuration_manager
                ):
                    config = self.es_client.configuration_manager.main_config or {}
                    settings = config.get("settings", {})
                    index_name = settings.get(
                        "restored_snapshots_index", "rc_snapshots"
                    )
                else:
                    index_name = "rc_snapshots"  # Default fallback

            # Define the search query to find documents with status 'init'
            query = {"query": {"match": {"status": "init"}}}

            # Perform the count using the ES client
            result = self.es_client.es.count(index=index_name, body=query)
            return result.get("count", 0)

        except Exception as e:
            error_msg = (
                f"Error counting staged snapshots from index '{index_name}': {str(e)}"
            )
            self.last_error = error_msg
            raise Exception(error_msg) from e

    def clear_staged_snapshots(self, index_name: Optional[str] = None) -> int:
        """
        Clear all staged snapshots (in INIT status) from the tracking system.

        Args:
            index_name: Name of the index containing restored snapshot tracking data.
                       If None, uses configured default from settings.

        Returns:
            int: Number of documents cleared

        Raises:
            Exception: If there's an error accessing the tracking index
        """
        try:
            # Get index name from config if not provided
            if index_name is None:
                if (
                    hasattr(self.es_client, "configuration_manager")
                    and self.es_client.configuration_manager
                ):
                    config = self.es_client.configuration_manager.main_config or {}
                    settings = config.get("settings", {})
                    index_name = settings.get(
                        "restored_snapshots_index", "rc_snapshots"
                    )
                else:
                    index_name = "rc_snapshots"  # Default fallback

            # First, search for documents with the specified status to get their IDs
            search_query = {"query": {"match": {"status": "init"}}}

            # Perform the search using the ES client
            result = self.es_client.es.search(index=index_name, body=search_query)
            hits = result.get("hits", {}).get("hits", [])

            # Delete the matching documents
            cleared_count = 0
            for hit in hits:
                document_id = hit.get("_id")
                if document_id:
                    try:
                        self.es_client.es.delete(index=index_name, id=document_id)
                        cleared_count += 1
                    except Exception as delete_error:
                        # Log individual delete errors but continue with others
                        error_msg = f"Failed to delete document {document_id}: {str(delete_error)}"
                        if hasattr(self.es_client, "logger"):
                            self.es_client.logger.warning(error_msg)
                        # Continue processing other documents

            return cleared_count

        except Exception as e:
            error_msg = (
                f"Error clearing staged snapshots from index '{index_name}': {str(e)}"
            )
            self.last_error = error_msg
            raise Exception(error_msg) from e


# Backward compatibility functions
def get_snapshots(es_client, repository: Optional[str] = None) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    snapshot_cmd = SnapshotCommands(es_client)
    return snapshot_cmd.get_snapshots(repository)


def get_repositories(es_client) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    snapshot_cmd = SnapshotCommands(es_client)
    return snapshot_cmd.get_repositories()


def create_snapshot(
    es_client,
    repository: str,
    snapshot_name: str,
    indices: Optional[str] = None,
    wait_for_completion: bool = False,
) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    snapshot_cmd = SnapshotCommands(es_client)
    return snapshot_cmd.create_snapshot(
        repository, snapshot_name, indices, wait_for_completion
    )


def delete_snapshot(es_client, repository: str, snapshot_name: str) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    snapshot_cmd = SnapshotCommands(es_client)
    return snapshot_cmd.delete_snapshot(repository, snapshot_name)
