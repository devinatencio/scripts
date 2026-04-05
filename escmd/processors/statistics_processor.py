"""
Statistics processing utilities for Elasticsearch command-line tool.

This module provides statistical calculations and data formatting utilities
including byte size conversions and data aggregations.
"""

import re
from typing import Union, Dict, List, Any, Optional


class StatisticsProcessor:
    """
    Handles statistical calculations and data formatting.
    
    Provides methods for size conversions, data aggregations, and statistical
    analysis without being tied to any specific data source.
    """
    
    def __init__(self):
        """Initialize the statistics processor."""
        self.size_units = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
            'TB': 1024 ** 4,
            'PB': 1024 ** 5
        }
    
    def format_bytes(self, size_in_bytes: Union[int, float]) -> str:
        """
        Convert bytes to a human-readable format.
        
        Args:
            size_in_bytes: Size in bytes
            
        Returns:
            Human-readable size string
        """
        if size_in_bytes is None or size_in_bytes == 0:
            return "0B"
        
        size = float(size_in_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        
        # For very large sizes
        return f"{size:.2f} PB"
    
    def size_to_bytes(self, size_str: str) -> int:
        """
        Convert a storage size string to bytes.
        
        Supports B, KB, MB, GB, TB, PB (case insensitive)
        Examples: '24.9mb', '25M', '103.3M', '1.2GB'
        
        Args:
            size_str: Size string to convert
            
        Returns:
            Size in bytes
            
        Raises:
            ValueError: If the input format is invalid
        """
        if size_str is None or size_str == "":
            return 0
        
        # Clean and standardize input
        size_str = str(size_str).strip().upper()
        
        # Handle special cases
        if size_str == "0" or size_str == "0B":
            return 0
        
        # Find the numeric part and unit
        match = re.match(r'^([\d.]+)([A-Z]*)$', size_str)
        if not match:
            raise ValueError(f"Invalid size format: {size_str}")
        
        number_str, unit = match.groups()
        
        # Handle cases where unit might be shortened or missing
        if not unit or unit == '':
            unit = 'B'  # Default to bytes
        elif unit == 'M':
            unit = 'MB'
        elif unit == 'G':
            unit = 'GB'
        elif unit == 'K':
            unit = 'KB'
        elif unit == 'T':
            unit = 'TB'
        elif unit == 'P':
            unit = 'PB'
        
        # Verify unit is valid
        if unit not in self.size_units:
            raise ValueError(f"Invalid unit: {unit}")
        
        try:
            # Convert size to float and multiply by unit multiplier
            return int(float(number_str) * self.size_units[unit])
        except ValueError:
            raise ValueError(f"Invalid number format: {number_str}")
    
    def calculate_percentage(self, part: Union[int, float], total: Union[int, float], 
                           decimal_places: int = 2) -> float:
        """
        Calculate percentage of part from total.
        
        Args:
            part: Part value
            total: Total value
            decimal_places: Number of decimal places to round to
            
        Returns:
            Percentage value
        """
        if total == 0:
            return 0.0
        return round((part / total) * 100, decimal_places)
    
    def aggregate_sizes(self, data: List[Dict[str, Any]], size_field: str) -> Dict[str, Any]:
        """
        Aggregate size information from a list of objects.
        
        Args:
            data: List of objects containing size information
            size_field: Field name containing size data
            
        Returns:
            Dictionary with aggregated size statistics
        """
        total_bytes = 0
        sizes = []
        
        for item in data:
            size_value = item.get(size_field)
            if size_value is not None:
                try:
                    if isinstance(size_value, str):
                        bytes_value = self.size_to_bytes(size_value)
                    else:
                        bytes_value = int(size_value)
                    
                    total_bytes += bytes_value
                    sizes.append(bytes_value)
                except (ValueError, TypeError):
                    continue
        
        if not sizes:
            return {
                'total': 0,
                'total_formatted': '0B',
                'average': 0,
                'average_formatted': '0B',
                'min': 0,
                'min_formatted': '0B',
                'max': 0,
                'max_formatted': '0B',
                'count': 0
            }
        
        average_bytes = total_bytes // len(sizes)
        min_bytes = min(sizes)
        max_bytes = max(sizes)
        
        return {
            'total': total_bytes,
            'total_formatted': self.format_bytes(total_bytes),
            'average': average_bytes,
            'average_formatted': self.format_bytes(average_bytes),
            'min': min_bytes,
            'min_formatted': self.format_bytes(min_bytes),
            'max': max_bytes,
            'max_formatted': self.format_bytes(max_bytes),
            'count': len(sizes)
        }
    
    def calculate_distribution(self, values: List[Union[int, float]]) -> Dict[str, Any]:
        """
        Calculate distribution statistics for a list of values.
        
        Args:
            values: List of numeric values
            
        Returns:
            Dictionary with distribution statistics
        """
        if not values:
            return {
                'count': 0,
                'sum': 0,
                'mean': 0,
                'median': 0,
                'min': 0,
                'max': 0
            }
        
        sorted_values = sorted(values)
        count = len(values)
        total = sum(values)
        mean = total / count
        
        # Calculate median
        if count % 2 == 0:
            median = (sorted_values[count//2 - 1] + sorted_values[count//2]) / 2
        else:
            median = sorted_values[count//2]
        
        return {
            'count': count,
            'sum': total,
            'mean': mean,
            'median': median,
            'min': sorted_values[0],
            'max': sorted_values[-1]
        }
    
    def group_by_field(self, data: List[Dict[str, Any]], field: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group data by a specific field value.
        
        Args:
            data: List of dictionaries to group
            field: Field name to group by
            
        Returns:
            Dictionary mapping field values to lists of items
        """
        grouped = {}
        
        for item in data:
            key = item.get(field, 'unknown')
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(item)
        
        return grouped
    
    def calculate_field_statistics(self, data: List[Dict[str, Any]], field: str) -> Dict[str, Any]:
        """
        Calculate statistics for a numeric field across multiple items.
        
        Args:
            data: List of dictionaries containing the field
            field: Field name to analyze
            
        Returns:
            Dictionary with field statistics
        """
        values = []
        
        for item in data:
            value = item.get(field)
            if value is not None:
                try:
                    if isinstance(value, str):
                        # Try to convert string numbers
                        numeric_value = float(value)
                    else:
                        numeric_value = float(value)
                    values.append(numeric_value)
                except (ValueError, TypeError):
                    continue
        
        return self.calculate_distribution(values)
    
    def format_number(self, number: Union[int, float], decimal_places: int = 2) -> str:
        """
        Format a number with thousands separators.
        
        Args:
            number: Number to format
            decimal_places: Number of decimal places for floats
            
        Returns:
            Formatted number string
        """
        if isinstance(number, float):
            return f"{number:,.{decimal_places}f}"
        else:
            return f"{number:,}"


# Backward compatibility functions
def format_bytes(size_in_bytes: Union[int, float]) -> str:
    """Backward compatibility function for existing code."""
    processor = StatisticsProcessor()
    return processor.format_bytes(size_in_bytes)


def size_to_bytes(size_str: str) -> int:
    """Backward compatibility function for existing code."""
    processor = StatisticsProcessor()
    return processor.size_to_bytes(size_str)
