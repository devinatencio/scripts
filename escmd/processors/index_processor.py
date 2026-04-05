"""
Index processing utilities for Elasticsearch command-line tool.

This module provides index-related data processing capabilities including
pattern extraction, filtering, and index name manipulation.
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Pattern


class IndexProcessor:
    """
    Handles index data processing and manipulation.

    Provides methods for filtering, pattern extraction, and index name cleaning
    without being tied to any specific Elasticsearch client implementation.
    """

    def __init__(self):
        """Initialize the index processor."""
        self.date_pattern_regex = re.compile(r"^(.*?)-(\d{4}\.\d{2}\.\d{2})-(\d+)$")
        self.pattern_extraction_regex = re.compile(r"^(.*?)-\d{4}\.\d{2}\.\d{2}-\d+$")

    def extract_unique_patterns(self, data: List[Dict[str, Any]]) -> List[str]:
        """
        Extract unique patterns from index data by removing date and suffix components.

        Args:
            data: List of index objects with 'index' keys

        Returns:
            List of unique base patterns
        """
        unique_patterns = set()

        for entry in data:
            index = entry.get("index", "")
            match = self.pattern_extraction_regex.match(index)
            if match:
                unique_patterns.add(match.group(1))

        return list(unique_patterns)

    def filter_indices(
        self,
        indices: List[Dict[str, Any]],
        pattern: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter indices based on regex pattern or status.

        Args:
            indices: List of index objects to filter
            pattern: Regex pattern or shell-style wildcard pattern to match index names
            status: Status to filter by (health field)

        Returns:
            Filtered list of index objects
        """
        filtered_indices = indices.copy()

        # Apply pattern filter if provided
        if pattern:
            regex = self._compile_pattern_regex(pattern)
            filtered_indices = [
                index
                for index in filtered_indices
                if regex.search(index.get("index", ""))
            ]

        # Apply status filter if provided
        if status:
            filtered_indices = [
                index
                for index in filtered_indices
                if index.get("health") == status.lower()
            ]

        # Sort filtered indices alphabetically by index name
        filtered_indices.sort(key=lambda x: x.get("index", "").lower())
        return filtered_indices

    def filter_indices_by_status(
        self, indices: List[Dict[str, Any]], status: str
    ) -> List[Dict[str, Any]]:
        """
        Filter indices by status/health.

        Args:
            indices: List of index objects
            status: Status to filter by

        Returns:
            Filtered list of indices
        """
        return [index for index in indices if index.get("health") == status.lower()]

    def find_latest_indices(self, data: List[Dict[str, Any]]) -> List[str]:
        """
        Find the latest index for each unique pattern.

        Args:
            data: List of index objects

        Returns:
            List of latest index names for each pattern
        """
        latest_indices = {}

        for entry in data:
            index = entry.get("index", "")
            match = self.date_pattern_regex.match(index)
            if match:
                base_pattern, date_str, suffix = match.groups()
                try:
                    date = datetime.strptime(date_str, "%Y.%m.%d")
                    suffix = int(suffix)

                    if (
                        base_pattern not in latest_indices
                        or date > latest_indices[base_pattern]["date"]
                        or (
                            date == latest_indices[base_pattern]["date"]
                            and suffix > latest_indices[base_pattern]["suffix"]
                        )
                    ):
                        latest_indices[base_pattern] = {
                            "index": index,
                            "date": date,
                            "suffix": suffix,
                        }
                except ValueError:
                    # Skip indices with invalid date formats
                    continue

        return [item["index"] for item in latest_indices.values()]

    def clean_index_name(self, index_name: str) -> str:
        """
        Clean Elasticsearch index names by removing '.ds-' prefix and date-related suffixes.

        Args:
            index_name: The original Elasticsearch index name

        Returns:
            Cleaned index name without '.ds-' prefix and date suffix

        Raises:
            ValueError: If the input string is empty, None, or doesn't match expected pattern
        """
        if not index_name:
            raise ValueError("Index name cannot be empty or None")

        original_name = index_name

        # Remove '.ds-' prefix if it exists
        if index_name.startswith(".ds-"):
            index_name = index_name[4:]

        # Find and remove the date pattern and anything after it
        # Pattern matches: YYYY.MM.DD or YYYY.MM.D or YYYY.M.DD or YYYY.M.D
        pattern = r"-\d{4}\.\d{1,2}\.\d{1,2}.*$"
        cleaned_name = re.sub(pattern, "", index_name)

        # Verify we actually found and removed a date pattern
        if cleaned_name == index_name and not original_name.startswith(".ds-"):
            raise ValueError(
                "Input string doesn't match expected pattern with date suffix"
            )

        return cleaned_name

    def group_indices_by_pattern(
        self, indices: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group indices by their base patterns.

        Args:
            indices: List of index objects

        Returns:
            Dictionary mapping base patterns to lists of matching indices
        """
        grouped = {}

        for index in indices:
            index_name = index.get("index", "")
            try:
                pattern = self._extract_base_pattern(index_name)
                if pattern not in grouped:
                    grouped[pattern] = []
                grouped[pattern].append(index)
            except ValueError:
                # Handle indices that don't match the expected pattern
                if "other" not in grouped:
                    grouped["other"] = []
                grouped["other"].append(index)

        return grouped

    def get_index_statistics(self, indices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistics about the indices.

        Args:
            indices: List of index objects

        Returns:
            Dictionary containing various statistics
        """
        if not indices:
            return {
                "total_count": 0,
                "patterns": [],
                "status_breakdown": {},
                "latest_indices": [],
            }

        stats = {
            "total_count": len(indices),
            "patterns": self.extract_unique_patterns(indices),
            "latest_indices": self.find_latest_indices(indices),
            "status_breakdown": {},
        }

        # Calculate status breakdown
        for index in indices:
            status = index.get("health", "unknown")
            stats["status_breakdown"][status] = (
                stats["status_breakdown"].get(status, 0) + 1
            )

        return stats

    def _compile_pattern_regex(self, pattern: str) -> Pattern:
        """Compile a pattern string into a regex, handling shell-style wildcards and true regex patterns."""
        # First, try to detect if this is already a valid regex pattern
        if self._is_likely_regex_pattern(pattern):
            try:
                # If it compiles as a regex, use it directly
                return re.compile(pattern)
            except re.error:
                # If it fails to compile, fall through to glob handling
                pass

        # Handle shell-style wildcards
        if "*" in pattern or "?" in pattern:
            # Convert shell-style wildcards to regex
            escaped = re.escape(pattern)
            escaped = escaped.replace(r"\*", ".*").replace(r"\?", ".")
            return re.compile(f"^{escaped}$")
        else:
            # Original behavior: substring match
            return re.compile(f".*{re.escape(pattern)}.*")

    def _is_likely_regex_pattern(self, pattern: str) -> bool:
        """
        Detect if a pattern is likely a regex rather than a shell-style glob.

        Args:
            pattern: The pattern string to analyze

        Returns:
            bool: True if pattern appears to be a regex
        """
        # Common regex patterns that indicate regex usage rather than glob
        regex_indicators = [
            r"\.\*",  # .* (very common in regex)
            r"\.\+",  # .+
            r"\[.*\]",  # [character class]
            r"\{.*\}",  # {quantifier}
            r"\|",  # | (alternation)
            r"\^",  # ^ (start anchor)
            r"\$",  # $ (end anchor)
            r"\+",  # + (one or more)
            r"\?",  # ? (zero or one) - but only if not preceded by .
            r"\(",  # ( (grouping start)
            r"\)",  # ) (grouping end)
            r"\\[a-zA-Z]",  # escaped characters like \d, \w, etc.
        ]

        # Check for regex indicators
        for indicator in regex_indicators:
            if re.search(indicator, pattern):
                return True

        # Special case: if pattern ends with .* it's almost certainly regex
        if pattern.endswith(".*"):
            return True

        # Special case: if pattern starts with ^ or ends with $ it's regex
        if pattern.startswith("^") or pattern.endswith("$"):
            return True

        return False

    def _extract_base_pattern(self, index_name: str) -> str:
        """Extract base pattern from an index name."""
        match = self.pattern_extraction_regex.match(index_name)
        if match:
            return match.group(1)
        else:
            # For indices that don't match the date pattern, return the full name
            return index_name

    def find_matching_index(
        self, indices_data: Union[List[Dict[str, Any]], str], indice: str
    ) -> bool:
        """
        Check if a given index exists in the provided indices data.

        Args:
            indices_data: List of dictionaries or JSON string containing index data
            indice: The index name to search for

        Returns:
            bool: True if the index is found, False otherwise
        """
        # Ensure indices_data is a list of dictionaries, not a JSON string
        if isinstance(indices_data, str):
            try:
                import json

                indices_data = json.loads(
                    indices_data
                )  # Convert JSON string to Python object
            except json.JSONDecodeError:
                print("Error: Provided data is not valid JSON.")
                return False

        for data in indices_data:
            if isinstance(data, dict) and data.get("index") == indice:
                return True
        return False  # Return False if no match is found


# Backward compatibility functions
def extract_unique_patterns(data: List[Dict[str, Any]]) -> List[str]:
    """Backward compatibility function for existing code."""
    processor = IndexProcessor()
    return processor.extract_unique_patterns(data)


def filter_indices(
    indices: List[Dict[str, Any]],
    pattern: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Backward compatibility function for existing code."""
    processor = IndexProcessor()
    return processor.filter_indices(indices, pattern, status)


def find_latest_indices(data: List[Dict[str, Any]]) -> List[str]:
    """Backward compatibility function for existing code."""
    processor = IndexProcessor()
    return processor.find_latest_indices(data)


def clean_index_name(index_name: str) -> str:
    """Backward compatibility function for existing code."""
    processor = IndexProcessor()
    return processor.clean_index_name(index_name)
