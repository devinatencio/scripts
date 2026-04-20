"""Unit tests for log_manager module.

Covers: directory creation, file handler configuration (100 MB max, 1 backup),
format string validation, ES logger suppression, and debug override.
"""

import logging
import logging.handlers
import os
import shutil

import pytest

from server.log_manager import setup_logger


@pytest.fixture(autouse=True)
def clean_loggers():
    """Remove handlers added during tests so loggers start fresh."""
    yield
    # Tear down: remove any handlers we added and reset ES logger
    for name in list(logging.Logger.manager.loggerDict.keys()):
        lgr = logging.getLogger(name)
        lgr.handlers = []
        lgr.setLevel(logging.WARNING)


@pytest.fixture()
def logs_dir():
    """Return the expected logs directory path and clean it up after test."""
    # logs/ is at the project root (one level above the server package)
    module_dir = os.path.dirname(os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'log_manager.py')
    ))
    project_root = os.path.dirname(module_dir)
    d = os.path.join(project_root, 'logs')
    yield d
    # Cleanup created log files (but keep the directory if it existed before)
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.startswith('test-'):
                os.remove(os.path.join(d, f))


class TestSetupLogger(object):
    """Tests for setup_logger."""

    def test_creates_logs_directory(self, logs_dir):
        """Requirement 8.1 - logs/ directory created if missing."""
        # Even if it already exists this should not raise
        logger = setup_logger('test-dir-creation')
        assert os.path.isdir(logs_dir)
        assert isinstance(logger, logging.Logger)

    def test_returns_logger_with_correct_name(self):
        """Logger name matches the utility_name argument."""
        logger = setup_logger('test-name-check')
        assert logger.name == 'test-name-check'

    def test_rotating_file_handler_configured(self):
        """Requirement 8.3, 8.4 - RotatingFileHandler with 100 MB / 1 backup."""
        logger = setup_logger('test-handler-config')
        rfh = None
        for h in logger.handlers:
            if isinstance(h, logging.handlers.RotatingFileHandler):
                rfh = h
                break
        assert rfh is not None, "Expected a RotatingFileHandler"
        assert rfh.maxBytes == 100 * 1024 * 1024
        assert rfh.backupCount == 1

    def test_log_format(self):
        """Requirement 8.5 - consistent format with timestamp, level, message."""
        logger = setup_logger('test-format')
        rfh = logger.handlers[0]
        fmt = rfh.formatter._fmt
        assert '%(asctime)s' in fmt
        assert '%(levelname)s' in fmt
        assert '%(message)s' in fmt

    def test_default_level_is_info(self):
        """Default log level is INFO when debug=False."""
        logger = setup_logger('test-info-level')
        assert logger.level == logging.INFO

    def test_debug_flag_sets_debug_level(self):
        """Requirement 8.7 - debug=True sets DEBUG level."""
        logger = setup_logger('test-debug-level', debug=True)
        assert logger.level == logging.DEBUG
        # Handler should also be DEBUG
        for h in logger.handlers:
            assert h.level == logging.DEBUG

    def test_elasticsearch_logger_suppressed(self):
        """Requirement 8.6 - ES library logger set to WARNING."""
        setup_logger('test-es-suppress')
        es_logger = logging.getLogger('elasticsearch')
        assert es_logger.level >= logging.WARNING

    def test_no_duplicate_handlers_on_repeat_call(self):
        """Calling setup_logger twice for the same name should not add extra handlers."""
        logger1 = setup_logger('test-dup-handlers')
        count1 = len(logger1.handlers)
        logger2 = setup_logger('test-dup-handlers')
        assert logger2 is logger1
        assert len(logger2.handlers) == count1

    def test_log_file_created_on_write(self, logs_dir):
        """Requirement 8.2 - log file named after utility in logs/ directory."""
        logger = setup_logger('test-file-write')
        logger.info('hello')
        # Flush handlers
        for h in logger.handlers:
            h.flush()
        expected = os.path.join(logs_dir, 'test-file-write.log')
        assert os.path.isfile(expected)

    def test_debug_override_updates_existing_handlers(self):
        """When called again with debug=True, existing handler levels update."""
        logger = setup_logger('test-debug-override', debug=False)
        assert logger.level == logging.INFO
        logger = setup_logger('test-debug-override', debug=True)
        assert logger.level == logging.DEBUG
        for h in logger.handlers:
            assert h.level == logging.DEBUG
