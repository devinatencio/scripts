"""
Universal Style System for ESCMD

This module provides standardized styling patterns and utilities to ensure
consistent visual presentation across all commands and displays.
"""

from typing import Dict, Any, Optional, Union, List, Tuple
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich import box


class StyleSystem:
    """
    Central style system providing standardized styling patterns.

    This class works with ThemeManager to provide consistent styling
    utilities that all commands and renderers can use.
    """

    def __init__(self, theme_manager=None):
        """Initialize with theme manager instance."""
        self.theme_manager = theme_manager

    # ====================================================================
    # SEMANTIC COLOR SYSTEM
    # ====================================================================

    def get_semantic_style(self, semantic_type: str) -> str:
        """
        Get semantic color style based on meaning, not hardcoded colors.

        Prefers the dedicated ``semantic_styles`` section in themes.yml so that
        every theme can define its own palette in one place.  Falls back to
        ``panel_styles`` for backward compatibility, then to safe defaults.

        Args:
            semantic_type: One of success, warning, error, info, primary,
                           secondary, neutral, muted

        Returns:
            str: Rich style string
        """
        # Defaults used when neither semantic_styles nor panel_styles has a value
        defaults = {
            "success":   "green",
            "warning":   "yellow",
            "error":     "red",
            "info":      "blue",
            "primary":   "cyan",
            "secondary": "magenta",
            "neutral":   "white",
            "muted":     "dim white",
        }

        # 1. Try the dedicated semantic_styles block (preferred)
        semantic_val = self._get_style("semantic_styles", semantic_type, "")
        if semantic_val:
            return semantic_val

        # 2. Fall back to panel_styles / row_styles (legacy mapping)
        legacy_map = {
            "success":   ("panel_styles", "success"),
            "warning":   ("panel_styles", "warning"),
            "error":     ("panel_styles", "error"),
            "info":      ("panel_styles", "info"),
            "primary":   ("panel_styles", "title"),
            "secondary": ("panel_styles", "secondary"),
            "neutral":   ("row_styles",   "normal"),
            "muted":     ("panel_styles", "subtitle"),
        }
        if semantic_type in legacy_map:
            cat, key = legacy_map[semantic_type]
            legacy_val = self._get_style(cat, key, "")
            if legacy_val:
                return legacy_val

        return defaults.get(semantic_type, "white")

    def create_semantic_text(self, text: str, semantic_type: str, **kwargs) -> Text:
        """Create a Text object with semantic styling."""
        style = self.get_semantic_style(semantic_type)
        return Text(text, style=style, **kwargs)

    # ====================================================================
    # STATUS INDICATORS
    # ====================================================================

    def get_status_icon_and_style(self, status: str) -> Tuple[str, str]:
        """
        Get appropriate icon and style for various status types.

        Args:
            status: Status value (health status, connection status, etc.)

        Returns:
            tuple: (icon, style) pair
        """
        status_lower = status.lower()

        # Health statuses
        if status_lower in [
            "green",
            "healthy",
            "active",
            "running",
            "connected",
            "success",
        ]:
            return "✅", self.get_semantic_style("success")
        elif status_lower in ["yellow", "warning", "degraded", "partial"]:
            return "🔶", self.get_semantic_style("warning")
        elif status_lower in ["red", "critical", "failed", "error", "disconnected"]:
            return "❌", self.get_semantic_style("error")
        elif status_lower in ["blue", "info", "unknown"]:
            return "🔵", self.get_semantic_style("info")
        else:
            return "⭕", self.get_semantic_style("neutral")

    def create_status_text(self, status: str, show_icon: bool = True) -> Text:
        """Create a styled status text with optional icon."""
        icon, style = self.get_status_icon_and_style(status)
        text = f"{icon} {status}" if show_icon else status
        return Text(text, style=style)

    # ====================================================================
    # STANDARDIZED TABLE STYLES
    # ====================================================================

    def create_standard_table(
        self,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        style_variant: str = "default",
    ) -> Table:
        """
        Create a standardized table with consistent styling.

        Args:
            title: Table title
            subtitle: Table subtitle
            style_variant: Variant (default, compact, detailed, dashboard)

        Returns:
            Table: Styled Rich table
        """
        # Use themed table box instead of hardcoded variants
        table_box = self.get_table_box()

        # Apply title styling if provided
        if title:
            title_style = self._get_style("panel_styles", "info", "bright_cyan")
            title = f"[{title_style}]{title}[/{title_style}]"

        return Table(
            title=title,
            box=table_box,  # Use themed box style
            expand=True,
            show_header=True,
            header_style=self._get_style("table_styles", "header_style", "bold white"),
        )

    def add_themed_column(
        self, table: Table, header: str, column_type: str = "default", **kwargs
    ) -> None:
        """
        Add a column with appropriate theming based on data type.

        Args:
            table: Table to add column to
            header: Column header text
            column_type: Type hint (name, status, count, size, date, etc.)
            **kwargs: Additional column arguments
        """
        # Column type styling using semantic styles
        type_styles = {
            "name": self.get_semantic_style("primary"),
            "status": self.get_semantic_style("neutral"),
            "count": self.get_semantic_style("secondary"),
            "size": self.get_semantic_style("success"),
            "date": self.get_semantic_style("info"),
            "percentage": self.get_semantic_style("warning"),
            "error": self.get_semantic_style("error"),
            "warning": self.get_semantic_style("warning"),
            "success": self.get_semantic_style("success"),
            "default": self.get_semantic_style("neutral"),
        }

        style = type_styles.get(column_type, self.get_semantic_style("neutral"))
        table.add_column(header, style=style, **kwargs)

    # ====================================================================
    # STANDARDIZED PANELS
    # ====================================================================

    def create_info_panel(self, content: Any, title: str, icon: str = "🔵") -> Panel:
        """Create a standardized info panel."""
        return self._create_semantic_panel(content, title, icon, "info")

    def create_success_panel(self, content: Any, title: str, icon: str = "✅") -> Panel:
        """Create a standardized success panel."""
        return self._create_semantic_panel(content, title, icon, "success")

    def create_warning_panel(self, content: Any, title: str, icon: str = "🔶") -> Panel:
        """Create a standardized warning panel."""
        return self._create_semantic_panel(content, title, icon, "warning")

    def create_error_panel(self, content: Any, title: str, icon: str = "❌") -> Panel:
        """Create a standardized error panel."""
        return self._create_semantic_panel(content, title, icon, "error")

    def create_dashboard_panel(
        self, content: Any, title: str, icon: str = "📊"
    ) -> Panel:
        """Create a standardized dashboard panel."""
        return self._create_semantic_panel(content, title, icon, "primary")

    def _create_semantic_panel(
        self, content: Any, title: str, icon: str, semantic_type: str
    ) -> Panel:
        """Create a panel with semantic styling."""
        title_style = self.get_semantic_style(semantic_type)
        border_style = self._get_style("table_styles", "border_style", "white")

        styled_title = f"[{title_style}]{icon} {title}[/{title_style}]"

        return Panel(
            content, title=styled_title, border_style=border_style, padding=(1, 2)
        )

    # ====================================================================
    # UTILITY METHODS
    # ====================================================================

    def _get_style(self, category: str, style_type: str, default: str) -> str:
        """Get style from theme manager with fallback."""
        if self.theme_manager:
            return self.theme_manager.get_themed_style(category, style_type, default)
        return default

    def get_zebra_style(self, row_index: int) -> Optional[str]:
        """
        Return a background-only alternate row style for zebra striping.

        Returns None for even rows (use default column style) and a subtle
        background highlight for odd rows. Text colors are preserved.

        Args:
            row_index: Zero-based row index

        Returns:
            str background style for odd rows, None for even rows
        """
        if row_index % 2 == 0:
            return None
        zebra_color = self._get_style("table_styles", "row_styles.zebra", "grey23")
        return f"on {zebra_color}"

    def get_table_box(self) -> Optional[box.Box]:
        """Get table box style from theme configuration."""
        box_style = self._get_style("table_styles", "table_box", "heavy")

        # Debug output
        # print(f"DEBUG: table_box style from theme: '{box_style}'")

        # Map string values to Rich box types
        box_mapping = {
            "heavy": box.HEAVY,
            "double": box.DOUBLE,
            "rounded": box.ROUNDED,
            "simple": box.SIMPLE,
            "minimal": box.MINIMAL,
            "horizontals": box.HORIZONTALS,
            "none": None,
            None: None,
        }

        # Handle case-insensitive lookup
        lookup_key = box_style.lower() if box_style else None
        result = box_mapping.get(lookup_key, box.HEAVY)
        # print(f"DEBUG: returning box style: {result}")
        return result

    def format_size(self, size_bytes: int, semantic: bool = True) -> Text:
        """Format bytes with semantic coloring based on size."""
        if size_bytes is None:
            return Text("N/A", style=self.get_semantic_style("muted"))

        # Convert to human readable
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                size_str = f"{size_bytes:.1f} {unit}"
                break
            size_bytes /= 1024.0
        else:
            size_str = f"{size_bytes:.1f} PB"

        if not semantic:
            return Text(size_str)

        # Semantic coloring based on size
        if "GB" in size_str or "TB" in size_str or "PB" in size_str:
            style = self.get_semantic_style("warning")  # Large sizes
        elif "MB" in size_str:
            style = self.get_semantic_style("info")  # Medium sizes
        else:
            style = self.get_semantic_style("success")  # Small sizes

        return Text(size_str, style=style)

    def format_percentage(self, percentage: float, show_icon: bool = True) -> Text:
        """Format percentage with semantic coloring."""
        if percentage is None:
            return Text("N/A", style=self.get_semantic_style("muted"))

        percentage_str = f"{percentage:.1f}%"

        # Semantic coloring and icons based on percentage
        if percentage >= 95:
            style = self.get_semantic_style("success")
            icon = "🟢" if show_icon else ""
        elif percentage >= 80:
            style = self.get_semantic_style("warning")
            icon = "🟡" if show_icon else ""
        else:
            style = self.get_semantic_style("error")
            icon = "🔴" if show_icon else ""

        text = f"{icon} {percentage_str}" if show_icon else percentage_str
        return Text(text, style=style)

    def create_progress_bar(self, percentage: float, width: int = 12) -> Text:
        """Create a visual progress bar with semantic coloring."""
        if percentage is None or percentage < 0:
            percentage = 0
        elif percentage > 100:
            percentage = 100

        filled = int((percentage / 100) * width)
        empty = width - filled

        # Choose color based on percentage
        if percentage >= 95:
            fill_char, fill_style = "█", self.get_semantic_style("success")
        elif percentage >= 80:
            fill_char, fill_style = "█", self.get_semantic_style("warning")
        else:
            fill_char, fill_style = "█", self.get_semantic_style("error")

        bar = Text()
        bar.append("█" * filled, style=fill_style)
        bar.append("░" * empty, style="dim white")
        bar.append(f" {percentage:.1f}%", style=fill_style)

        return bar
