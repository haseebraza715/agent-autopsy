"""
Module for verifying and validating traces.
"""

import json
from collections import defaultdict
from pathlib import Path


class TraceVerifier:
    """Verify traces and check for failures."""
    
    def __init__(self, traces_dir: Path = None):
        self.traces_dir = traces_dir or Path("./traces")
    
    def analyze_trace(self, trace_file: Path) -> dict:
        """Analyze a trace file and return detailed information."""
        try:
            with open(trace_file, "r") as f:
                trace_data = json.load(f)
            
            events = trace_data.get("events", [])
            
            # Count event types
            event_types = defaultdict(int)
            errors = []
            error_count = 0
            
            for event in events:
                event_type = event.get("type", "unknown")
                event_types[event_type] += 1
                
                if event_type == "error":
                    error_count += 1
                    errors.append({
                        "event_id": event.get("event_id"),
                        "name": event.get("name", "unknown"),
                        "error": event.get("error", "Unknown error"),
                        "metadata": event.get("metadata", {}).get("error_type", "Unknown")
                    })
            
            return {
                "file": trace_file.name,
                "run_id": trace_data.get("run_id", "unknown"),
                "total_events": len(events),
                "event_types": dict(event_types),
                "error_count": error_count,
                "has_failure": error_count > 0,
                "errors": errors,
                "duration_ms": trace_data.get("duration_ms", 0),
                "start_time": trace_data.get("start_time", "unknown"),
            }
        except Exception as e:
            return {
                "file": trace_file.name,
                "error": str(e),
                "has_failure": False,
            }
    
    def verify_all(self, verbose: bool = True) -> dict:
        """
        Verify all traces in the traces directory.
        
        Returns:
            dict with verification results
        """
        if not self.traces_dir.exists():
            if verbose:
                print("No traces directory found!")
            return {}
        
        trace_files = sorted(self.traces_dir.glob("*.json"))
        
        if not trace_files:
            if verbose:
                print("No trace files found!")
            return {}
        
        if verbose:
            print("=" * 80)
            print("TRACE VERIFICATION REPORT")
            print("=" * 80)
            print()
        
        # Analyze all traces
        all_results = []
        failed_traces = []
        successful_traces = []
        
        for trace_file in trace_files:
            result = self.analyze_trace(trace_file)
            all_results.append(result)
            
            if result.get("has_failure"):
                failed_traces.append(result)
            else:
                successful_traces.append(result)
        
        # Aggregate statistics
        error_types = defaultdict(int)
        for result in failed_traces:
            for err in result.get("errors", []):
                error_type = err.get("metadata", "Unknown")
                error_types[error_type] += 1
        
        verification_result = {
            "total_traces": len(all_results),
            "failed_traces": len(failed_traces),
            "successful_traces": len(successful_traces),
            "failed_trace_files": [r["file"] for r in failed_traces],
            "error_types": dict(error_types),
            "all_results": all_results,
        }
        
        if verbose:
            print(f"Total traces analyzed: {len(all_results)}")
            print(f"Traces with failures: {len(failed_traces)}")
            print(f"Traces without failures: {len(successful_traces)}")
            print()
            
            if failed_traces:
                print("=" * 80)
                print("FAILED TRACES (Verified)")
                print("=" * 80)
                print()
                
                for i, trace in enumerate(failed_traces[:10], 1):  # Show first 10
                    print(f"{i}. {trace['file']}")
                    print(f"   Run ID: {trace.get('run_id', 'unknown')}")
                    print(f"   Total Events: {trace.get('total_events', 0)}")
                    print(f"   Error Count: {trace.get('error_count', 0)}")
                    
                    if trace.get('errors'):
                        for err in trace['errors'][:2]:  # Show first 2 errors
                            print(f"     - Event {err['event_id']}: {err['name']}")
                            print(f"       Error: {err['error'][:80]}...")
                    print()
                
                if len(failed_traces) > 10:
                    print(f"... and {len(failed_traces) - 10} more failed traces")
                    print()
            
            if error_types:
                print("=" * 80)
                print("ERROR STATISTICS")
                print("=" * 80)
                print()
                for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
                    print(f"  - {error_type}: {count} occurrence(s)")
                print()
        
        return verification_result

