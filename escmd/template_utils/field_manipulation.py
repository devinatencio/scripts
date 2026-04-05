#!/usr/bin/env python3
"""
Field manipulation utilities for escmd template modification.

This module provides functionality to manipulate nested fields in Elasticsearch
templates using dot notation and various operations.
"""

import re
from typing import Any, Dict, List, Union, Tuple
import logging

logger = logging.getLogger(__name__)


class FieldManipulator:
    """Handles field path parsing and value manipulation for template modification."""

    @staticmethod
    def parse_field_path(field_path: str) -> List[str]:
        """
        Parse a dot-notation field path into components.

        Args:
            field_path: Dot-separated field path (e.g., "template.settings.index.routing")

        Returns:
            List of field path components

        Examples:
            >>> FieldManipulator.parse_field_path("template.settings.index")
            ['template', 'settings', 'index']
        """
        if not field_path or not isinstance(field_path, str):
            raise ValueError("Field path must be a non-empty string")

        # Split on dots, but handle escaped dots if needed in the future
        components = field_path.split('.')

        # Remove empty components
        components = [comp.strip() for comp in components if comp.strip()]

        if not components:
            raise ValueError("Field path cannot be empty after parsing")

        return components

    @staticmethod
    def get_nested_value(data: Dict[str, Any], field_path: str) -> Tuple[Any, bool]:
        """
        Get a value from nested dictionary using dot notation.

        Args:
            data: Dictionary to search in
            field_path: Dot-separated field path

        Returns:
            Tuple of (value, found) where found indicates if the path exists
        """
        if not isinstance(data, dict):
            return None, False

        try:
            components = FieldManipulator.parse_field_path(field_path)
            current = data

            for component in components:
                if not isinstance(current, dict) or component not in current:
                    return None, False
                current = current[component]

            return current, True

        except Exception as e:
            logger.error(f"Error getting nested value for path '{field_path}': {str(e)}")
            return None, False

    @staticmethod
    def set_nested_value(data: Dict[str, Any], field_path: str, value: Any) -> Dict[str, Any]:
        """
        Set a value in nested dictionary using dot notation.

        Args:
            data: Dictionary to modify (will be modified in place)
            field_path: Dot-separated field path
            value: Value to set

        Returns:
            Modified dictionary (same object as input)
        """
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")

        try:
            components = FieldManipulator.parse_field_path(field_path)
            current = data

            # Navigate to parent of target field, creating path if needed
            for component in components[:-1]:
                if component not in current:
                    current[component] = {}
                elif not isinstance(current[component], dict):
                    raise ValueError(f"Cannot traverse path: '{component}' is not a dictionary")
                current = current[component]

            # Set the final value
            current[components[-1]] = value

            return data

        except Exception as e:
            logger.error(f"Error setting nested value for path '{field_path}': {str(e)}")
            raise RuntimeError(f"Failed to set nested value: {str(e)}")

    @staticmethod
    def delete_nested_field(data: Dict[str, Any], field_path: str) -> Dict[str, Any]:
        """
        Delete a field from nested dictionary using dot notation.

        Args:
            data: Dictionary to modify (will be modified in place)
            field_path: Dot-separated field path

        Returns:
            Modified dictionary (same object as input)
        """
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")

        try:
            components = FieldManipulator.parse_field_path(field_path)
            current = data

            # Navigate to parent of target field
            for component in components[:-1]:
                if component not in current or not isinstance(current[component], dict):
                    # Path doesn't exist, nothing to delete
                    return data
                current = current[component]

            # Delete the final field if it exists
            final_field = components[-1]
            if final_field in current:
                del current[final_field]

            return data

        except Exception as e:
            logger.error(f"Error deleting nested field for path '{field_path}': {str(e)}")
            raise RuntimeError(f"Failed to delete nested field: {str(e)}")

    @staticmethod
    def field_exists(data: Dict[str, Any], field_path: str) -> bool:
        """
        Check if a field exists in nested dictionary.

        Args:
            data: Dictionary to check
            field_path: Dot-separated field path

        Returns:
            True if field exists, False otherwise
        """
        _, exists = FieldManipulator.get_nested_value(data, field_path)
        return exists


class ListManipulator:
    """Handles manipulation of comma-separated string lists and JSON arrays."""

    @staticmethod
    def parse_comma_list(value: str) -> List[str]:
        """
        Parse a comma-separated string into a list of trimmed values.

        Args:
            value: Comma-separated string

        Returns:
            List of trimmed string values
        """
        if not isinstance(value, str):
            return []

        # Split on commas and trim whitespace
        items = [item.strip() for item in value.split(',') if item.strip()]
        return items

    @staticmethod
    def format_comma_list(items: List[str]) -> str:
        """
        Format a list of strings as a comma-separated string.

        Args:
            items: List of strings

        Returns:
            Comma-separated string
        """
        if not isinstance(items, list):
            return ""

        # Filter out empty items and join with commas
        valid_items = [str(item).strip() for item in items if str(item).strip()]
        return ",".join(valid_items)

    @staticmethod
    def append_to_list(current_value: Any, new_value: str) -> str:
        """
        Append a value to a comma-separated list, avoiding duplicates.

        Args:
            current_value: Current list value (string or list)
            new_value: Value to append

        Returns:
            Updated comma-separated string
        """
        if isinstance(current_value, list):
            current_items = [str(item) for item in current_value]
        elif isinstance(current_value, str):
            current_items = ListManipulator.parse_comma_list(current_value)
        else:
            current_items = []

        new_items = ListManipulator.parse_comma_list(new_value)

        # Append new items that don't already exist
        for item in new_items:
            if item not in current_items:
                current_items.append(item)

        return ListManipulator.format_comma_list(current_items)

    @staticmethod
    def remove_from_list(current_value: Any, remove_value: str) -> str:
        """
        Remove values from a comma-separated list.

        Args:
            current_value: Current list value (string or list)
            remove_value: Values to remove (comma-separated)

        Returns:
            Updated comma-separated string
        """
        if isinstance(current_value, list):
            current_items = [str(item) for item in current_value]
        elif isinstance(current_value, str):
            current_items = ListManipulator.parse_comma_list(current_value)
        else:
            current_items = []

        remove_items = ListManipulator.parse_comma_list(remove_value)

        # Remove specified items
        for item in remove_items:
            while item in current_items:
                current_items.remove(item)

        return ListManipulator.format_comma_list(current_items)

    @staticmethod
    def replace_list(current_value: Any, new_value: str) -> str:
        """
        Replace the entire list with new values.

        Args:
            current_value: Current list value (ignored)
            new_value: New comma-separated values

        Returns:
            New comma-separated string
        """
        new_items = ListManipulator.parse_comma_list(new_value)
        return ListManipulator.format_comma_list(new_items)


class ValueManipulator:
    """Handles different types of value manipulation operations."""

    @staticmethod
    def apply_operation(current_value: Any, operation: str, new_value: str) -> Any:
        """
        Apply an operation to a value based on its type and the operation.

        Args:
            current_value: Current value in the template
            operation: Operation to perform ('set', 'append', 'remove', 'delete')
            new_value: New value to use in the operation

        Returns:
            Modified value
        """
        if operation == 'delete':
            return None  # Indicates field should be deleted

        if operation == 'set':
            return ValueManipulator._convert_value(new_value)

        if operation == 'append':
            if ValueManipulator._is_list_like(current_value):
                return ListManipulator.append_to_list(current_value, new_value)
            else:
                # If current value is not list-like, treat as replacement
                return ValueManipulator._convert_value(new_value)

        if operation == 'remove':
            if ValueManipulator._is_list_like(current_value):
                return ListManipulator.remove_from_list(current_value, new_value)
            else:
                # Can't remove from non-list, return current value
                logger.warning(f"Cannot remove from non-list value: {current_value}")
                return current_value

        raise ValueError(f"Unknown operation: {operation}")

    @staticmethod
    def _is_list_like(value: Any) -> bool:
        """Check if a value should be treated as a list."""
        if isinstance(value, list):
            return True
        if isinstance(value, str) and ',' in value:
            return True
        return False

    @staticmethod
    def _convert_value(value_str: str) -> Any:
        """
        Convert a string value to appropriate type.

        Args:
            value_str: String representation of value

        Returns:
            Converted value (bool, int, float, or string)
        """
        if not isinstance(value_str, str):
            return value_str

        # Try boolean
        if value_str.lower() in ('true', 'false'):
            return value_str.lower() == 'true'

        # Try integer
        try:
            if '.' not in value_str:
                return int(value_str)
        except ValueError:
            pass

        # Try float
        try:
            return float(value_str)
        except ValueError:
            pass

        # Return as string
        return value_str


class TemplateModifier:
    """High-level interface for template modification operations."""

    def __init__(self):
        self.field_manipulator = FieldManipulator()
        self.value_manipulator = ValueManipulator()

    def modify_field(self, template_data: Dict[str, Any], field_path: str,
                    operation: str, value: str) -> Dict[str, Any]:
        """
        Modify a field in template data using specified operation.

        Args:
            template_data: Template data dictionary
            field_path: Dot-notation path to field
            operation: Operation to perform ('set', 'append', 'remove', 'delete')
            value: Value for the operation

        Returns:
            Modified template data
        """
        if operation not in ['set', 'append', 'remove', 'delete']:
            raise ValueError(f"Invalid operation: {operation}. Must be one of: set, append, remove, delete")

        # Get current value
        current_value, field_exists = self.field_manipulator.get_nested_value(template_data, field_path)

        if not field_exists and operation in ['append', 'remove']:
            logger.warning(f"Field '{field_path}' does not exist, treating as 'set' operation")
            operation = 'set'

        # Apply operation
        if operation == 'delete':
            self.field_manipulator.delete_nested_field(template_data, field_path)
        else:
            new_value = self.value_manipulator.apply_operation(current_value, operation, value)
            self.field_manipulator.set_nested_value(template_data, field_path, new_value)

        return template_data

    def get_field_value(self, template_data: Dict[str, Any], field_path: str) -> Tuple[Any, bool]:
        """
        Get the current value of a field.

        Args:
            template_data: Template data dictionary
            field_path: Dot-notation path to field

        Returns:
            Tuple of (value, exists)
        """
        return self.field_manipulator.get_nested_value(template_data, field_path)

    def validate_field_path(self, template_data: Dict[str, Any], field_path: str) -> List[str]:
        """
        Validate a field path and return any issues found.

        Args:
            template_data: Template data dictionary
            field_path: Dot-notation path to field

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        try:
            components = self.field_manipulator.parse_field_path(field_path)
        except ValueError as e:
            issues.append(f"Invalid field path format: {str(e)}")
            return issues

        # Check if path can be traversed
        current = template_data
        for i, component in enumerate(components[:-1]):
            if not isinstance(current, dict):
                path_so_far = ".".join(components[:i])
                issues.append(f"Cannot traverse path beyond '{path_so_far}': not a dictionary")
                break

            if component not in current:
                path_so_far = ".".join(components[:i+1])
                issues.append(f"Path component '{path_so_far}' does not exist")
                break

            current = current[component]

        return issues
