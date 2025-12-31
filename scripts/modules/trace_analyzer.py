"""
Module for analyzing traces and generating reports.
"""

import json
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ingestion import parse_trace_file, TraceNormalizer
from src.preanalysis import RootCauseBuilder
from src.analysis import run_analysis
from src.analysis.agent import run_analysis_without_llm
from src.output import ReportGenerator
from src.utils.config import get_config


class TraceAnalyzer:
    """Analyze traces and generate reports."""
    
    def __init__(self, reports_dir: Path = None, config=None):
        self.reports_dir = reports_dir or Path("./reports")
        self.config = config or get_config()
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def analyze_trace(self, trace_file: Path, use_full_analysis: bool = True) -> dict:
        """
        Analyze a single trace file.
        
        Args:
            trace_file: Path to trace file
            use_full_analysis: Try full analysis first, fallback to basic if fails
        
        Returns:
            dict with analysis results and metadata
        """
        result_info = {
            "trace_file": trace_file.name,
            "success": False,
            "report_path": None,
            "error": None,
            "patterns": [],
            "signals": [],
            "preanalysis": None,
            "analysis_type": None,
        }
        
        try:
            # Try to parse and normalize the trace
            if use_full_analysis:
                try:
                    trace = parse_trace_file(trace_file)
                    trace = TraceNormalizer.normalize(trace)
                    use_full = True
                except Exception as parse_error:
                    use_full = False
                    result_info["error"] = f"Parse error: {str(parse_error)[:100]}"
            else:
                use_full = False
            
            if use_full:
                # Run pre-analysis for pattern detection
                preanalysis = RootCauseBuilder(trace).build()
                result_info["preanalysis"] = {
                    "summary": preanalysis.summary,
                    "signals_count": len(preanalysis.signals),
                    "hypotheses_count": len(preanalysis.hypotheses),
                }
                
                # Extract patterns from signals
                for signal in preanalysis.signals:
                    result_info["patterns"].append({
                        "type": signal.type,
                        "severity": signal.severity,
                        "evidence": signal.evidence,
                        "event_ids": signal.event_ids,
                    })
                    result_info["signals"].append(signal.type)
                
                # Run analysis (with or without LLM)
                if self.config.openrouter_api_key:
                    try:
                        result = run_analysis(trace, verbose=False, enable_tracing=False)
                        result_info["analysis_type"] = "llm"
                    except Exception as e:
                        result = run_analysis_without_llm(trace)
                        result_info["analysis_type"] = "deterministic"
                        result_info["error"] = f"LLM failed: {str(e)[:100]}"
                else:
                    result = run_analysis_without_llm(trace)
                    result_info["analysis_type"] = "deterministic"
                
                # Generate report
                report_generator = ReportGenerator(trace, result)
                report_file = self.reports_dir / f"full_analysis_{trace_file.stem}.md"
                saved_path = report_generator.save(report_file, format="markdown")
                
                result_info["success"] = True
                result_info["report_path"] = str(saved_path)
                result_info["analysis_success"] = result.success
                
            else:
                # Use autopsy-run for basic analysis
                result_info["analysis_type"] = "basic"
                report_file = self.reports_dir / f"basic_analysis_{trace_file.stem}.md"
                
                proc_result = subprocess.run(
                    ["python", "-m", "src.cli", "autopsy-run", str(trace_file), "-o", str(report_file)],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent.parent.parent
                )
                
                if proc_result.returncode == 0:
                    result_info["success"] = True
                    result_info["report_path"] = str(report_file)
                    
                    # Extract basic info from the trace JSON
                    try:
                        with open(trace_file, "r") as f:
                            trace_data = json.load(f)
                        events = trace_data.get("events", [])
                        
                        # Count errors
                        error_count = sum(1 for e in events if e.get("type") == "error")
                        if error_count > 0:
                            result_info["patterns"].append({
                                "type": "error",
                                "severity": "high",
                                "evidence": f"{error_count} error(s) found",
                                "event_ids": [e.get("event_id") for e in events if e.get("type") == "error"],
                            })
                    except:
                        pass
                else:
                    result_info["error"] = proc_result.stderr[:200] if proc_result.stderr else "Unknown error"
                    
        except Exception as e:
            result_info["error"] = str(e)
        
        return result_info
    
    def analyze_all_traces(
        self,
        traces_dir: Path,
        verbose: bool = True
    ) -> list[dict]:
        """
        Analyze all traces in a directory.
        
        Args:
            traces_dir: Directory containing trace files
            verbose: Print progress messages
        
        Returns:
            List of analysis result dicts
        """
        if not traces_dir.exists():
            if verbose:
                print("No traces directory found!")
            return []
        
        trace_files = sorted(traces_dir.glob("*.json"))
        
        if not trace_files:
            if verbose:
                print("No trace files found!")
            return []
        
        if verbose:
            print("=" * 80)
            print("FULL AUTOPSY ANALYSIS - Pattern Detection & Report Generation")
            print("=" * 80)
            print()
            print(f"Analyzing {len(trace_files)} trace files...")
            print()
        
        all_results = []
        
        for i, trace_file in enumerate(trace_files, 1):
            if verbose:
                print(f"[{i}/{len(trace_files)}] Analyzing: {trace_file.name}")
            
            result_info = self.analyze_trace(trace_file)
            all_results.append(result_info)
            
            if verbose:
                if result_info["success"]:
                    print(f"    ✓ Analysis complete ({result_info['analysis_type']})")
                    if result_info.get("patterns"):
                        print(f"    ✓ Patterns detected: {len(result_info['patterns'])}")
                    if result_info["report_path"]:
                        print(f"    ✓ Report: {Path(result_info['report_path']).name}")
                else:
                    print(f"    ✗ Analysis failed: {result_info.get('error', 'Unknown error')}")
                print()
        
        if verbose:
            successful = sum(1 for r in all_results if r["success"])
            total_patterns = sum(len(r.get("patterns", [])) for r in all_results)
            
            print("=" * 80)
            print("ANALYSIS COMPLETE")
            print("=" * 80)
            print()
            print(f"Total traces analyzed: {len(all_results)}")
            print(f"Successful analyses: {successful}")
            print(f"Total patterns detected: {total_patterns}")
            print(f"Reports saved to: {self.reports_dir}")
            print()
        
        return all_results

