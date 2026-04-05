#!/usr/bin/env python3
"""
Centralized logging configuration for escmd.

This module provides standardized logging setup for the escmd application,
supporting both console and file logging with proper rotation and formatting.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class LoggingConfig:
    """Centralized logging configuration manager."""

    def __init__(self, script_directory: str):
        """
        Initialize logging configuration.

        Args:
            script_directory: The directory where the main script is located
        """
        self.script_directory = script_directory
        self.logs_directory = os.path.join(script_directory, "logs")
        self._ensure_logs_directory()

    def _ensure_logs_directory(self):
        """Ensure the logs directory exists."""
        Path(self.logs_directory).mkdir(parents=True, exist_ok=True)

    def setup_logging(
        self,
        logger_name: str = "escmd",
        log_level: str = "INFO",
        enable_file_logging: bool = True,
        enable_console_logging: bool = True,
        log_filename: Optional[str] = None,
    ) -> logging.Logger:
        """
        Set up logging with both file and console handlers.

        Args:
            logger_name: Name of the logger
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            enable_file_logging: Whether to enable file logging
            enable_console_logging: Whether to enable console logging
            log_filename: Custom log filename (optional)

        Returns:
            Configured logger instance
        """
        # Create logger
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        # Clear existing handlers to avoid duplicates
        logger.handlers.clear()

        # Create formatters
        detailed_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        )

        simple_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )

        # Set up file logging
        if enable_file_logging:
            if not log_filename:
                # Generate default filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d")
                log_filename = f"{logger_name}_{timestamp}.log"

            log_filepath = os.path.join(self.logs_directory, log_filename)

            # Use rotating file handler to manage log file size
            file_handler = logging.handlers.RotatingFileHandler(
                log_filepath,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)  # File gets all messages
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)

        # Set up console logging
        if enable_console_logging:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
            console_handler.setFormatter(simple_formatter)
            logger.addHandler(console_handler)

        return logger

    def setup_command_logging(
        self, command: str, env: Optional[str] = None, log_level: str = "INFO"
    ) -> logging.Logger:
        """
        Set up logging specifically for command execution (like cron jobs).

        Args:
            command: The command being executed (e.g., 'dangling')
            env: Environment name if applicable
            log_level: Logging level

        Returns:
            Configured logger instance
        """
        # Create logger name based on command and environment
        logger_name = f"escmd_{command}"
        if env:
            logger_name += f"_{env}"

        # Create log filename based on command and current date
        timestamp = datetime.now().strftime("%Y%m%d")

        # For dangling command, use single rotating log file regardless of environment
        if command == "dangling":
            log_filename = "dangling.log"
        else:
            log_filename = f"{command}"
            if env:
                log_filename += f"_{env}"
            log_filename += f"_{timestamp}.log"

        # For dangling command, use rotating file handler
        if command == "dangling":
            return self.setup_dangling_logging(logger_name, log_level, log_filename)
        else:
            return self.setup_logging(
                logger_name=logger_name,
                log_level=log_level,
                enable_file_logging=True,
                enable_console_logging=False,  # For cron jobs, typically only file logging
                log_filename=log_filename,
            )

    def setup_metrics_logging(
        self, command: str, env: Optional[str] = None
    ) -> logging.Logger:
        """
        Set up logging specifically for metrics operations.

        Args:
            command: The command being executed
            env: Environment name if applicable

        Returns:
            Configured logger instance
        """
        logger_name = f"escmd_metrics_{command}"
        if env:
            logger_name += f"_{env}"

        timestamp = datetime.now().strftime("%Y%m%d")
        log_filename = f"metrics_{command}"
        if env:
            log_filename += f"_{env}"
        log_filename += f"_{timestamp}.log"

        return self.setup_logging(
            logger_name=logger_name,
            log_level="INFO",
            enable_file_logging=True,
            enable_console_logging=True,  # Metrics might want both
            log_filename=log_filename,
        )

    def get_log_file_path(self, filename: str) -> str:
        """
        Get the full path to a log file.

        Args:
            filename: Log filename

        Returns:
            Full path to the log file
        """
        return os.path.join(self.logs_directory, filename)

    def list_log_files(self) -> list:
        """
        List all log files in the logs directory.

        Returns:
            List of log filenames
        """
        try:
            log_files = [
                f for f in os.listdir(self.logs_directory) if f.endswith(".log")
            ]
            return sorted(log_files)
        except OSError:
            return []

    def cleanup_old_logs(self, days_to_keep: int = 30):
        """
        Clean up log files older than specified days.

        Args:
            days_to_keep: Number of days to keep log files
        """
        import time

        current_time = time.time()
        cutoff_time = current_time - (days_to_keep * 24 * 60 * 60)

        try:
            for filename in os.listdir(self.logs_directory):
                if filename.endswith(".log"):
                    file_path = os.path.join(self.logs_directory, filename)
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        print(f"Removed old log file: {filename}")
        except OSError as e:
            print(f"Error cleaning up logs: {e}")

    def setup_dangling_logging(
        self, logger_name: str, log_level: str, log_filename: str
    ) -> logging.Logger:
        """
        Set up rotating logging specifically for dangling commands.

        Args:
            logger_name: Name of the logger
            log_level: Logging level
            log_filename: Log filename

        Returns:
            Configured logger instance with rotating file handler
        """
        # Create logger
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        # Clear existing handlers to avoid duplicates
        logger.handlers.clear()

        # Create detailed formatter
        detailed_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        )

        # Set up rotating file logging
        log_filepath = os.path.join(self.logs_directory, log_filename)

        # Use rotating file handler with 200MB max size, 1 backup
        file_handler = logging.handlers.RotatingFileHandler(
            log_filepath,
            maxBytes=200 * 1024 * 1024,  # 200MB
            backupCount=1,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

        return logger


# Global instance for easy access
_logging_config = None


def get_logging_config(script_directory: Optional[str] = None) -> LoggingConfig:
    """
    Get or create the global logging configuration instance.

    Args:
        script_directory: Script directory (required for first call)

    Returns:
        LoggingConfig instance
    """
    global _logging_config

    if _logging_config is None:
        if script_directory is None:
            # Try to determine script directory automatically
            import inspect

            frame = inspect.currentframe()
            try:
                # Get the caller's file directory
                caller_file = inspect.getfile(frame.f_back)
                script_directory = os.path.dirname(os.path.abspath(caller_file))
            finally:
                del frame

        _logging_config = LoggingConfig(script_directory)

    return _logging_config


def setup_command_logging(
    command: str, env: Optional[str] = None, script_directory: Optional[str] = None
) -> logging.Logger:
    """
    Convenience function to set up command logging.

    Args:
        command: Command name
        env: Environment name
        script_directory: Script directory

    Returns:
        Configured logger
    """
    config = get_logging_config(script_directory)
    return config.setup_command_logging(command, env)
