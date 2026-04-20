"""Per-utility logging with file rotation.

Provides a setup_logger function that configures a named logger with
RotatingFileHandler, consistent formatting, and Elasticsearch library
log suppression.
"""

import logging
import logging.handlers
import os

# type: ignore comments for Python 3.6 compat
from typing import Optional  # noqa: F401


def setup_logger(utility_name, debug=False):
    # type: (str, bool) -> logging.Logger
    """Create and configure a logger for a specific utility.

    Creates a logs/ directory at the project root (one level above the
    server package) if it does not already exist.  Configures a
    RotatingFileHandler with 100 MB max file size and 1 backup.
    Suppresses the Elasticsearch library logger below WARNING level.

    Args:
        utility_name: Name used for the log file
            (e.g. 'cold-snapshots' -> logs/cold-snapshots.log).
        debug: If True the log level is set to DEBUG, otherwise INFO.

    Returns:
        A configured logging.Logger instance.
    """
    # Determine logs directory at the project root (one level above this package)
    module_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(module_dir)
    logs_dir = os.path.join(project_root, 'logs')

    if not os.path.isdir(logs_dir):
        os.makedirs(logs_dir)

    log_file = os.path.join(logs_dir, '%s.log' % utility_name)

    logger = logging.getLogger(utility_name)
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    # Avoid adding duplicate handlers when setup_logger is called more
    # than once for the same utility_name (e.g. in tests).
    if not logger.handlers:
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=100 * 1024 * 1024,  # 100 MB
            backupCount=1,
        )
        handler.setLevel(level)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
    else:
        # Update existing handler levels when debug flag changes
        for h in logger.handlers:
            h.setLevel(level)

    # Suppress Elasticsearch library logger below WARNING
    logging.getLogger('elasticsearch').setLevel(logging.WARNING)

    return logger
