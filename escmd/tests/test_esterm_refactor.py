#!/usr/bin/env python3
"""
Simple test script to verify the refactored esterm modules work correctly.
Tests basic functionality without requiring an actual Elasticsearch connection.
"""

import sys
import os

# Add parent directory to path to find esterm_modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

def test_imports():
    """Test that all esterm modules can be imported successfully."""
    print("Testing module imports...")

    try:
        from esterm_modules import (
            ClusterManager,
            CommandProcessor,
            TerminalUI,
            HealthMonitor,
            HelpSystem,
            TerminalSession
        )
        print("✓ All esterm modules imported successfully")
        assert True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        assert False, f"Import failed: {e}"

def test_terminal_session_creation():
    """Test that TerminalSession can be created."""
    print("Testing TerminalSession creation...")

    try:
        from esterm_modules import TerminalSession
        session = TerminalSession(version="test", date="test")
        print("✓ TerminalSession created successfully")

        # Test session info
        info = session.get_session_info()
        expected_keys = {'version', 'date', 'connected', 'current_cluster', 'available_clusters', 'running'}
        if expected_keys.issubset(info.keys()):
            print("✓ Session info contains expected keys")
        else:
            missing_keys = expected_keys - info.keys()
            print(f"✗ Session info missing keys: {missing_keys}")
            assert False, f"Session info missing keys: {missing_keys}"

        assert True
    except Exception as e:
        print(f"✗ TerminalSession creation failed: {e}")
        assert False, f"TerminalSession creation failed: {e}"

def test_help_system():
    """Test that HelpSystem works."""
    print("Testing HelpSystem...")

    try:
        from rich.console import Console
        from esterm_modules import HelpSystem

        console = Console()
        help_system = HelpSystem(console)

        # Test loading parser
        parser_loaded = help_system.load_parser()
        if parser_loaded:
            print("✓ Argument parser loaded successfully")
        else:
            print("⚠ Argument parser could not be loaded (expected if cli module not available)")

        # Test getting command list
        commands = help_system.get_command_list()
        print(f"✓ Retrieved {len(commands)} commands from help system")

        assert True
    except Exception as e:
        print(f"✗ HelpSystem test failed: {e}")
        assert False, f"HelpSystem test failed: {e}"

def test_command_processor():
    """Test CommandProcessor functionality."""
    print("Testing CommandProcessor...")

    try:
        from rich.console import Console
        from esterm_modules import CommandProcessor

        console = Console()
        processor = CommandProcessor(console)

        # Test command parsing
        test_cases = [
            ("help", ("help", [])),
            ("status --format json", ("status", ["--format", "json"])),
            ("indices test-*", ("indices", ["test-*"])),
            ("", (None, []))
        ]

        for input_cmd, expected in test_cases:
            result = processor.parse_command(input_cmd)
            if result == expected:
                print(f"✓ Command parsing correct for: '{input_cmd}'")
            else:
                print(f"✗ Command parsing failed for: '{input_cmd}' - got {result}, expected {expected}")
                assert False, f"Command parsing failed for: '{input_cmd}' - got {result}, expected {expected}"

        # Test builtin command detection
        builtin_tests = [
            ("help", True),
            ("exit", True),
            ("indices", False),
            ("status", True)
        ]

        for cmd, expected in builtin_tests:
            result = processor.is_builtin_command(cmd)
            if result == expected:
                print(f"✓ Builtin detection correct for: '{cmd}'")
            else:
                print(f"✗ Builtin detection failed for: '{cmd}' - got {result}, expected {expected}")
                assert False, f"Builtin detection failed for: '{cmd}' - got {result}, expected {expected}"

        assert True
    except Exception as e:
        print(f"✗ CommandProcessor test failed: {e}")
        assert False, f"CommandProcessor test failed: {e}"

def test_cluster_manager():
    """Test ClusterManager functionality."""
    print("Testing ClusterManager...")

    try:
        from rich.console import Console
        from esterm_modules import ClusterManager

        console = Console()
        cluster_manager = ClusterManager(console)

        # Test basic functionality (without actual connections)
        available = cluster_manager.get_available_clusters()
        print(f"✓ Retrieved {len(available)} available clusters")

        connected = cluster_manager.is_connected()
        print(f"✓ Connection status check: {connected}")

        current = cluster_manager.get_current_cluster()
        print(f"✓ Current cluster: {current}")

        print(f"✓ ClusterManager test completed (no active cluster)")
        assert True
    except Exception as e:
        print(f"✗ ClusterManager test failed: {e}")
        assert False, f"ClusterManager test failed: {e}"

def main():
    """Run all tests."""
    print("=" * 50)
    print("ESterm Refactor Test Suite")
    print("=" * 50)

    tests = [
        test_imports,
        test_terminal_session_creation,
        test_help_system,
        test_command_processor,
        test_cluster_manager
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        print()
        try:
            if test():
                passed += 1
                print("✓ Test PASSED")
            else:
                print("✗ Test FAILED")
        except Exception as e:
            print(f"✗ Test ERROR: {e}")

    print()
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    print("=" * 50)

    if passed == total:
        print("🎉 All tests passed! The refactor appears to be working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
