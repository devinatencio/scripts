"""
Base help content class for modular help system.

Provides common functionality and structure for individual help content modules.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align


class _UsageRows(list):
    """Simple list subclass with an add_row() method matching Rich Table's API."""
    def add_row(self, label="", value=""):
        self.append((str(label), str(value)))


class BaseHelpContent(ABC):
    """Base class for help content modules."""

    def __init__(self, theme_manager=None):
        self.theme_manager = theme_manager
        self.console = Console()

    def _get_theme_styles(self) -> Tuple[Dict[str, str], str]:
        """Pull styles from the theme, with sensible fallbacks."""
        defaults = {
            'command':        'bold cyan',
            'description':    'white',
            'example':        'cyan',
            'section_header': 'bold yellow',
            'border':         'white',
            'header_style':   'bold white on grey23',
            'zebra':          'on grey7',
            'table_box':      'heavy',
        }
        if self.theme_manager:
            raw = self.theme_manager.get_theme_styles()
            # get_theme_styles() flattens table_styles to top level
            border       = raw.get('border_style', defaults['border'])
            header_style = raw.get('header_style', defaults['header_style'])
            zebra_bg     = raw.get('row_styles', {}).get('zebra', '')
            zebra        = f"on {zebra_bg}" if zebra_bg and not zebra_bg.startswith('on ') else (zebra_bg or defaults['zebra'])
            # help_styles takes priority over panel_styles
            panel        = raw.get('help_styles') or raw.get('panel_styles', {})

            return {
                'command':        panel.get('command',        defaults['command']),
                'description':    panel.get('description',    defaults['description']),
                'example':        panel.get('example') or panel.get('info') or panel.get('secondary') or defaults['example'],
                'section_header': panel.get('section_header') or panel.get('title') or defaults['section_header'],
                'border':         border,
                'header_style':   header_style,
                'zebra':          zebra,
                'table_box':      raw.get('table_box', defaults['table_box']),
            }, border
        return defaults, defaults['border']

    def _s(self, key: str) -> str:
        """Shorthand — return a single theme style string."""
        styles, _ = self._get_theme_styles()
        return styles.get(key, 'white')

    def _create_commands_table(self) -> Table:
        """3-column merged commands+examples table (command | description | example)."""
        from rich import box as rich_box
        styles, _  = self._get_theme_styles()
        cmd_style  = styles['command']
        desc_style = styles['description']
        ex_style   = styles['example']
        hdr_style  = styles['header_style']
        zebra      = styles['zebra']

        box_mapping = {
            'heavy':       rich_box.HEAVY,
            'double':      rich_box.DOUBLE,
            'rounded':     rich_box.ROUNDED,
            'simple':      rich_box.SIMPLE,
            'minimal':     rich_box.MINIMAL,
            'horizontals': rich_box.HORIZONTALS,
            'none':        None,
        }
        table_box = box_mapping.get(styles.get('table_box', 'heavy').lower(), rich_box.HEAVY)

        t = Table(
            expand=True,
            show_header=True,
            header_style=hdr_style,
            border_style=styles['border'],
            box=table_box,
            row_styles=["", zebra],
            show_lines=False,
            pad_edge=True,
            padding=(0, 1),
        )
        t.add_column("Command",     style=cmd_style,           no_wrap=True, min_width=34)
        t.add_column("Description", style=desc_style)
        t.add_column("Example",     style=f"dim {ex_style}",   no_wrap=True)
        return t

    def _create_examples_table(self) -> Table:
        """Kept for backward compat — returns a dummy table that is ignored."""
        t = Table.grid()
        t.add_column()
        t.add_column()
        return t

    def _create_usage_table(self):
        """Returns a UsageRows list. Parsed into scenario panels at render time."""
        return _UsageRows()

    # ── internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _parse_usage_rows(usage_rows) -> List[Tuple[str, List[Tuple[str, str]]]]:
        """
        Parse a list of (label, value) tuples into [(section_title, [(label, value), ...]), ...].
        Section headers: non-indented, end with ':'.
        Blank rows act as separators.
        """
        sections: List[Tuple[str, List]] = []
        current_title = ""
        current_rows: List[Tuple[str, str]] = []

        for label_raw, value in usage_rows:
            label = str(label_raw).strip()
            value = str(value).strip()

            if not label and not value:
                if current_title and current_rows:
                    sections.append((current_title, current_rows))
                    current_title = ""
                    current_rows = []
                continue

            # Section header: ends with ':', not indented (no leading spaces in original)
            if label.endswith(":") and not str(label_raw).startswith(" "):
                if current_title and current_rows:
                    sections.append((current_title, current_rows))
                current_title = label.rstrip(":")
                current_rows = [(value, "")] if value else []
            else:
                current_rows.append((label.lstrip(), value))

        if current_title and current_rows:
            sections.append((current_title, current_rows))

        return sections

    # ── public render method ──────────────────────────────────────────────────

    def _display_help_panels(
        self,
        commands_table: Table,
        examples_table: Table,   # ignored — examples now live in commands_table
        commands_title: str,
        examples_title: str,
        usage_table: Table = None,
        usage_title: str = None,
    ) -> None:
        """Render topic header, merged commands table, and stacked workflow panels."""
        styles, border = self._get_theme_styles()
        cmd_style     = styles['command']
        desc_style    = styles['description']
        ex_style      = styles['example']
        hdr_style     = styles['section_header']

        # ── topic header ──────────────────────────────────────────────────────
        topic = self.get_topic_name()
        desc  = self.get_topic_description()

        header = Text()
        header.append(f" {topic} ", style=f"bold black on {cmd_style.replace('bold ', '')}")
        header.append(f"  {desc}", style=desc_style)
        header.append(f"   ./escmd.py help {topic}", style=f"dim {ex_style}")

        self.console.print()
        self.console.print(Panel(header, border_style=border, padding=(0, 2)))
        self.console.print()

        # ── commands + examples table ─────────────────────────────────────────
        self.console.print(Panel(
            commands_table,
            title=f"[{hdr_style}]{commands_title}[/{hdr_style}]",
            border_style=border,
            padding=(0, 0),
        ))
        self.console.print()

        # ── workflow scenario panels ──────────────────────────────────────────
        if usage_table is not None:
            sections = self._parse_usage_rows(usage_table)
            if sections:
                for section_title, rows in sections:
                    t = Table.grid(padding=(0, 2))
                    t.add_column(style="dim",         no_wrap=True, min_width=18)
                    t.add_column(style=cmd_style,     no_wrap=True)

                    start = 0
                    if rows and rows[0][1] == "":
                        subtitle = rows[0][0]
                        if subtitle:
                            t.add_row(Text(subtitle, style="dim italic"), Text(""))
                            t.add_row(Text(""), Text(""))
                        start = 1

                    for label, value in rows[start:]:
                        t.add_row(Text(label, style="dim"), Text(value, style=cmd_style))

                    self.console.print(Panel(
                        t,
                        title=f"[{hdr_style}]{section_title}[/{hdr_style}]",
                        border_style=border,
                        padding=(0, 2),
                    ))
            else:
                self.console.print(Panel(
                    usage_table,
                    title=f"[{hdr_style}]{usage_title or '🎯 Workflows'}[/{hdr_style}]",
                    border_style=border,
                    padding=(1, 2),
                ))
            self.console.print()

        # ── footer ────────────────────────────────────────────────────────────
        footer = Text(justify="center")
        footer.append("./escmd.py help", style=cmd_style)
        footer.append("  back to topic list  ·  ", style="dim")
        footer.append("-l <cluster>", style=cmd_style)
        footer.append("  target a specific cluster  ·  ", style="dim")
        footer.append("--format json", style=cmd_style)
        footer.append("  machine output", style="dim")
        self.console.print(Panel(Align.center(footer), border_style=border, padding=(0, 1)))
        self.console.print()

    @abstractmethod
    def show_help(self) -> None:
        pass

    @abstractmethod
    def get_topic_name(self) -> str:
        pass

    @abstractmethod
    def get_topic_description(self) -> str:
        pass
