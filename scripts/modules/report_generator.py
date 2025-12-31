"""
Module for generating summary reports from analysis results.
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class SummaryReportGenerator:
    """Generate comprehensive summary reports from analysis results."""
    
    def __init__(self, reports_dir: Path = None):
        self.reports_dir = reports_dir or Path("./reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_summary(
        self,
        all_results: list[dict],
        traces_dir: Path = None,
        verbose: bool = True
    ) -> Path:
        """
        Generate a comprehensive summary report.
        
        Args:
            all_results: List of analysis result dicts
            traces_dir: Directory with trace files (for error type extraction)
            verbose: Print progress messages
        
        Returns:
            Path to generated summary report
        """
        traces_dir = traces_dir or Path("./traces")
        
        # Aggregate patterns
        pattern_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        error_types = defaultdict(int)
        analysis_types = defaultdict(int)
        successful_analyses = 0
        failed_analyses = 0
        
        for result in all_results:
            if result["success"]:
                successful_analyses += 1
            else:
                failed_analyses += 1
            
            analysis_type = result.get("analysis_type", "unknown")
            analysis_types[analysis_type] += 1
            
            for pattern in result.get("patterns", []):
                pattern_counts[pattern["type"]] += 1
                severity_counts[pattern["severity"]] += 1
        
        # Extract error types from trace files
        if traces_dir.exists():
            for trace_file in traces_dir.glob("*.json"):
                try:
                    with open(trace_file, "r") as f:
                        trace_data = json.load(f)
                    events = trace_data.get("events", [])
                    for event in events:
                        if event.get("type") == "error":
                            error_type = event.get("metadata", {}).get("error_type", "Unknown")
                            error_types[error_type] += 1
                except:
                    pass
        
        # Generate summary report with improved formatting
        report_lines = [
            "# 🔬 Autopsy Analysis Summary Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## 📊 Overview",
            "",
            f"- **Total Traces Analyzed:** {len(all_results)}",
            f"- **Successful Analyses:** {successful_analyses} ✅",
            f"- **Failed Analyses:** {failed_analyses} ❌",
            f"- **Success Rate:** {(successful_analyses / len(all_results) * 100):.1f}%",
            "",
            "### Analysis Types",
            "",
        ]
        
        for analysis_type, count in sorted(analysis_types.items(), key=lambda x: -x[1]):
            report_lines.append(f"- **{analysis_type}**: {count} trace(s)")
        
        report_lines.extend([
            "",
            "---",
            "",
            "## 🔍 Pattern Detection Summary",
            "",
            "### Patterns Found",
            "",
        ])
        
        if pattern_counts:
            for pattern_type, count in sorted(pattern_counts.items(), key=lambda x: -x[1]):
                percentage = (count / len(all_results) * 100)
                report_lines.append(f"- **{pattern_type}**: {count} occurrence(s) ({percentage:.1f}%)")
        else:
            report_lines.append("- No patterns detected")
        
        report_lines.extend([
            "",
            "### Severity Distribution",
            "",
        ])
        
        if severity_counts:
            for severity, count in sorted(severity_counts.items(), key=lambda x: -x[1]):
                severity_emoji = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(severity, "⚪")
                report_lines.append(f"- {severity_emoji} **{severity}**: {count} occurrence(s)")
        else:
            report_lines.append("- No severity data available")
        
        report_lines.extend([
            "",
            "### Error Types",
            "",
        ])
        
        if error_types:
            total_errors = sum(error_types.values())
            for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
                percentage = (count / total_errors * 100) if total_errors > 0 else 0
                report_lines.append(f"- **{error_type}**: {count} occurrence(s) ({percentage:.1f}%)")
        else:
            report_lines.append("- No error type data available")
        
        report_lines.extend([
            "",
            "---",
            "",
            "## 📋 Individual Trace Results",
            "",
            "| # | Trace File | Status | Analysis Type | Patterns | Report |",
            "|---|------------|--------|---------------|----------|--------|",
        ])
        
        for i, result in enumerate(all_results, 1):
            trace_name = result["trace_file"]
            status = "✅" if result["success"] else "❌"
            analysis_type = result.get("analysis_type", "N/A")
            pattern_count = len(result.get("patterns", []))
            report_name = Path(result["report_path"]).name if result["report_path"] else "N/A"
            
            # Truncate long names
            if len(trace_name) > 40:
                trace_name = trace_name[:37] + "..."
            if len(report_name) > 30:
                report_name = report_name[:27] + "..."
            
            report_lines.append(f"| {i} | `{trace_name}` | {status} | {analysis_type} | {pattern_count} | `{report_name}` |")
        
        report_lines.extend([
            "",
            "---",
            "",
            "## 🔬 Detailed Pattern Analysis",
            "",
        ])
        
        # Group by pattern type
        patterns_by_type = defaultdict(list)
        for result in all_results:
            for pattern in result.get("patterns", []):
                patterns_by_type[pattern["type"]].append({
                    "trace": result["trace_file"],
                    "severity": pattern["severity"],
                    "evidence": pattern["evidence"],
                })
        
        for pattern_type, occurrences in sorted(patterns_by_type.items()):
            report_lines.extend([
                f"### {pattern_type.upper()}",
                "",
                f"**Found in {len(occurrences)} trace(s):**",
                "",
            ])
            
            # Group by severity
            by_severity = defaultdict(list)
            for occ in occurrences:
                by_severity[occ["severity"]].append(occ)
            
            for severity in ["critical", "high", "medium", "low"]:
                if severity in by_severity:
                    severity_emoji = {
                        "critical": "🔴",
                        "high": "🟠",
                        "medium": "🟡",
                        "low": "🟢"
                    }.get(severity, "⚪")
                    
                    report_lines.append(f"**{severity_emoji} {severity.upper()}** ({len(by_severity[severity])} occurrence(s)):")
                    report_lines.append("")
                    
                    for occ in by_severity[severity][:10]:  # Show first 10
                        trace_short = occ["trace"][:50] + "..." if len(occ["trace"]) > 50 else occ["trace"]
                        report_lines.append(f"- `{trace_short}`: {occ['evidence']}")
                    
                    if len(by_severity[severity]) > 10:
                        report_lines.append(f"  *... and {len(by_severity[severity]) - 10} more*")
                    
                    report_lines.append("")
        
        report_lines.extend([
            "",
            "---",
            "",
            "## 📈 Statistics",
            "",
            f"- **Total Patterns Detected:** {sum(len(r.get('patterns', [])) for r in all_results)}",
            f"- **Average Patterns per Trace:** {(sum(len(r.get('patterns', [])) for r in all_results) / len(all_results)):.2f}",
            f"- **Most Common Pattern:** {max(pattern_counts.items(), key=lambda x: x[1])[0] if pattern_counts else 'N/A'}",
            "",
            "---",
            "",
            f"*Report generated by Agent Autopsy at {datetime.now().isoformat()}*",
        ])
        
        # Save summary report
        summary_file = self.reports_dir / "analysis_summary.md"
        with open(summary_file, "w") as f:
            f.write("\n".join(report_lines))
        
        if verbose:
            print(f"✓ Summary report saved: {summary_file}")
        
        return summary_file

