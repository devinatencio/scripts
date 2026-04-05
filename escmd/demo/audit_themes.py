#!/usr/bin/env python3
"""
ESCMD Theme Consistency Auditor

This script analyzes all command files and reports on theme consistency,
identifying areas that need migration to the new semantic styling system.
"""

import os
import re
import ast
from typing import Dict, List, Set, Tuple
from pathlib import Path


class ThemeConsistencyAuditor:
    """Audits ESCMD codebase for theme consistency and migration opportunities."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.hardcoded_colors = {
            'red', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'white', 'black',
            'bright_red', 'bright_green', 'bright_blue', 'bright_yellow', 
            'bright_cyan', 'bright_magenta', 'bright_white', 'bright_black',
            'bold red', 'bold green', 'bold blue', 'bold yellow', 
            'bold cyan', 'bold magenta', 'bold white'
        }
        
        self.semantic_indicators = {
            'success', 'error', 'warning', 'info', 'primary', 'secondary', 
            'neutral', 'muted', 'get_themed_style', 'create_semantic_text',
            'create_status_text', 'style_system'
        }
        
    def audit_file(self, file_path: Path) -> Dict[str, any]:
        """Audit a single Python file for theme consistency."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {'error': str(e)}
        
        # Find hardcoded color usage
        hardcoded_usage = []
        for color in self.hardcoded_colors:
            # Look for string literals containing colors
            pattern = rf'["\'].*{re.escape(color)}.*["\']'
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                hardcoded_usage.append({
                    'color': color,
                    'line': line_num,
                    'context': match.group()
                })
        
        # Find Panel/Table/Text with hardcoded styles
        style_patterns = [
            (r'Panel\([^)]*style=["\'](.*?)["\']', 'Panel style'),
            (r'Table\([^)]*header_style=["\'](.*?)["\']', 'Table header_style'),
            (r'Table\([^)]*border_style=["\'](.*?)["\']', 'Table border_style'), 
            (r'Text\([^)]*style=["\'](.*?)["\']', 'Text style'),
            (r'\.add_column\([^)]*style=["\'](.*?)["\']', 'Column style')
        ]
        
        hardcoded_styles = []
        for pattern, style_type in style_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                style_value = match.group(1)
                if any(color in style_value.lower() for color in self.hardcoded_colors):
                    hardcoded_styles.append({
                        'type': style_type,
                        'line': line_num,
                        'style': style_value,
                        'context': match.group()[:100] + '...' if len(match.group()) > 100 else match.group()
                    })
        
        # Find semantic styling usage (good practices)
        semantic_usage = []
        for indicator in self.semantic_indicators:
            pattern = rf'\b{re.escape(indicator)}\b'
            matches = list(re.finditer(pattern, content))
            if matches:
                semantic_usage.append({
                    'indicator': indicator,
                    'count': len(matches),
                    'lines': [content[:m.start()].count('\n') + 1 for m in matches[:5]]  # First 5 occurrences
                })
        
        # Calculate migration score
        total_issues = len(hardcoded_usage) + len(hardcoded_styles)
        semantic_points = sum(usage['count'] for usage in semantic_usage)
        
        if total_issues == 0 and semantic_points > 0:
            migration_score = 100  # Perfect
        elif total_issues == 0:
            migration_score = 90   # Good (no issues but no semantic usage either)
        else:
            # Score based on ratio of semantic to hardcoded usage
            migration_score = max(0, 100 - (total_issues * 10) + (semantic_points * 5))
            migration_score = min(100, migration_score)
        
        return {
            'file': str(file_path.relative_to(self.base_path)),
            'hardcoded_colors': hardcoded_usage,
            'hardcoded_styles': hardcoded_styles, 
            'semantic_usage': semantic_usage,
            'total_issues': total_issues,
            'migration_score': migration_score
        }
    
    def audit_directory(self, directory: str = "commands") -> List[Dict]:
        """Audit all Python files in a directory."""
        dir_path = self.base_path / directory
        results = []
        
        if not dir_path.exists():
            return results
            
        for py_file in dir_path.glob("*.py"):
            if py_file.name.startswith('__'):
                continue
                
            result = self.audit_file(py_file)
            if 'error' not in result:
                results.append(result)
        
        return results
    
    def generate_report(self) -> str:
        """Generate a comprehensive migration report."""
        # Audit main directories
        commands_results = self.audit_directory("commands")
        handlers_results = self.audit_directory("handlers") 
        display_results = self.audit_directory("display")
        
        all_results = commands_results + handlers_results + display_results
        
        # Sort by migration score (worst first)
        all_results.sort(key=lambda x: x['migration_score'])
        
        report = []
        report.append("# 🎨 ESCMD Theme Consistency Audit Report")
        report.append("=" * 60)
        report.append("")
        
        # Summary
        total_files = len(all_results)
        files_with_issues = len([r for r in all_results if r['total_issues'] > 0])
        avg_score = sum(r['migration_score'] for r in all_results) / total_files if total_files > 0 else 0
        
        report.append("## 📊 Summary")
        report.append(f"- **Total Files Analyzed**: {total_files}")
        report.append(f"- **Files with Issues**: {files_with_issues}")
        report.append(f"- **Files Using Semantic Styling**: {total_files - files_with_issues}")
        report.append(f"- **Average Migration Score**: {avg_score:.1f}/100")
        report.append("")
        
        # Priority Migration List
        needs_migration = [r for r in all_results if r['migration_score'] < 80]
        report.append("## 🚨 Priority Migration List")
        report.append("Files that most urgently need theme migration:")
        report.append("")
        
        for result in needs_migration[:10]:  # Top 10 worst
            report.append(f"### {result['file']} (Score: {result['migration_score']}/100)")
            
            if result['hardcoded_colors']:
                report.append("**Hardcoded Colors:**")
                for usage in result['hardcoded_colors'][:3]:  # First 3
                    report.append(f"- Line {usage['line']}: `{usage['context']}`")
                report.append("")
            
            if result['hardcoded_styles']:
                report.append("**Hardcoded Styles:**")
                for style in result['hardcoded_styles'][:3]:  # First 3  
                    report.append(f"- Line {style['line']} ({style['type']}): `{style['style']}`")
                report.append("")
        
        # Best Practices Examples
        good_examples = [r for r in all_results if r['migration_score'] >= 90 and r['semantic_usage']]
        if good_examples:
            report.append("## ✅ Best Practices Examples")
            report.append("Files that demonstrate good semantic styling:")
            report.append("")
            
            for result in good_examples[:5]:  # Top 5 examples
                report.append(f"### {result['file']} (Score: {result['migration_score']}/100)")
                semantic_indicators = [usage['indicator'] for usage in result['semantic_usage']]
                report.append(f"Uses: {', '.join(semantic_indicators)}")
                report.append("")
        
        # Migration Progress by Directory
        report.append("## 📁 Progress by Directory")
        report.append("")
        
        for directory in ["commands", "handlers", "display"]:
            dir_results = [r for r in all_results if directory in r['file']]
            if dir_results:
                avg_dir_score = sum(r['migration_score'] for r in dir_results) / len(dir_results)
                files_migrated = len([r for r in dir_results if r['migration_score'] >= 80])
                report.append(f"**{directory.title()}**: {files_migrated}/{len(dir_results)} files migrated (avg score: {avg_dir_score:.1f})")
        
        report.append("")
        
        # Quick Fix Suggestions
        report.append("## 🔧 Quick Migration Tips")
        report.append("")
        report.append("1. **Replace hardcoded colors with semantic equivalents:**")
        report.append("   - `'green'` → `style_system.get_semantic_style('success')`")
        report.append("   - `'red'` → `style_system.get_semantic_style('error')`")
        report.append("   - `'yellow'` → `style_system.get_semantic_style('warning')`")
        report.append("")
        report.append("2. **Use standard component creation:**")
        report.append("   - `Panel(...)` → `style_system.create_info_panel(...)`")
        report.append("   - `Table(...)` → `style_system.create_standard_table(...)`")
        report.append("")
        report.append("3. **Import StyleSystem in command files:**")
        report.append("   ```python")
        report.append("   from display.style_system import StyleSystem")
        report.append("   # Available as self.style_system in BaseCommand subclasses")
        report.append("   ```")
        
        return "\n".join(report)


def main():
    """Run the theme consistency audit."""
    auditor = ThemeConsistencyAuditor()
    report = auditor.generate_report()
    
    # Save report
    with open("THEME_AUDIT_REPORT.md", "w") as f:
        f.write(report)
    
    print("🎨 Theme Consistency Audit Complete!")
    print("📄 Report saved to: THEME_AUDIT_REPORT.md")
    print("")
    print("Quick Summary:")
    print(report.split("## 📊 Summary")[1].split("##")[0])


if __name__ == "__main__":
    main()
