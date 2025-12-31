"""
Module for generating traces by running the analysis agent.
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ingestion import parse_trace_file, TraceNormalizer
from src.analysis import run_analysis
from src.analysis.agent import run_analysis_without_llm
from src.utils.config import get_config


class TraceGenerator:
    """Generate traces by running the analysis agent on sample traces."""
    
    def __init__(self, traces_dir: Path = None, config=None):
        self.traces_dir = traces_dir or Path("./traces")
        self.config = config or get_config()
        self.traces_dir.mkdir(parents=True, exist_ok=True)
    
    def check_trace_for_failure(self, trace_file: Path) -> tuple[bool, int]:
        """Check if a trace file contains failures."""
        try:
            with open(trace_file, "r") as f:
                trace_data = json.load(f)
            
            events = trace_data.get("events", [])
            error_count = sum(1 for e in events if e.get("type") == "error")
            
            return error_count > 0, error_count
        except Exception:
            return False, 0
    
    def generate_traces(
        self,
        sample_traces: list[str],
        min_runs: int = 20,
        stop_on_failure: bool = True,
        verbose: bool = True
    ) -> dict:
        """
        Generate traces by running analysis agent multiple times.
        
        Args:
            sample_traces: List of sample trace file paths
            min_runs: Minimum number of runs before stopping
            stop_on_failure: Stop after finding a failure (if min_runs reached)
            verbose: Print progress messages
        
        Returns:
            dict with statistics and generated trace files
        """
        all_traces = []
        failed_traces = []
        run_count = 0
        failure_found = False
        initial_count = len(list(self.traces_dir.glob("*.json"))) if self.traces_dir.exists() else 0
        trace_index = 0
        
        if verbose:
            print("=" * 60)
            print("Generating traces by running analysis agent")
            print(f"Will run until failure detected or {min_runs}+ runs completed")
            print("=" * 60)
            print()
        
        while run_count < min_runs or (not failure_found and stop_on_failure):
            # Select trace to use (cycle through)
            trace_file = sample_traces[trace_index % len(sample_traces)]
            trace_path = Path(trace_file)
            
            if not trace_path.exists():
                if verbose:
                    print(f"Warning: {trace_file} not found, skipping...")
                trace_index += 1
                continue
            
            # Parse the trace
            try:
                trace = parse_trace_file(trace_path)
                trace = TraceNormalizer.normalize(trace)
            except Exception as e:
                if verbose:
                    print(f"Error parsing {trace_file}: {e}")
                trace_index += 1
                continue
            
            run_count += 1
            if verbose:
                print(f"\n{'='*60}")
                print(f"Run {run_count}: Processing {Path(trace_file).name}")
                print(f"{'='*60}")
            
            try:
                # Use LLM if API key is available
                if self.config.openrouter_api_key:
                    result = run_analysis(trace, verbose=False, enable_tracing=True)
                    if verbose:
                        print(f"  ✓ Analysis complete (with LLM)")
                else:
                    # Use deterministic analysis with synthetic trace events
                    # Since no LLM callbacks fire, we manually create trace events
                    from src.tracing import TraceSaver, get_trace_config
                    from src.preanalysis import RootCauseBuilder
                    import json
                    from datetime import datetime

                    trace_handler = TraceSaver(config=get_trace_config())

                    # Add synthetic event for analysis mode decision
                    trace_handler._add_event(
                        event_type="decision",
                        name="analysis_mode",
                        input_data={"mode": "deterministic", "reason": "No API key configured"},
                        output_data={"selected": "deterministic_analysis"},
                    )

                    # Run pre-analysis and add events for each pattern found
                    preanalysis = RootCauseBuilder(trace).build()

                    for signal in preanalysis.signals:
                        trace_handler._add_event(
                            event_type="message",
                            name="pattern_detected",
                            input_data={"pattern": signal.name, "severity": signal.severity},
                            output_data={"description": signal.description},
                        )

                    # Run the analysis
                    result = run_analysis_without_llm(trace)

                    # Add event for final result
                    trace_handler._add_event(
                        event_type="message",
                        name="analysis_complete",
                        input_data={"hypotheses_count": len(preanalysis.hypotheses)},
                        output_data={"success": result.success},
                    )

                    # Save the trace
                    saved_path = trace_handler.save()

                    if verbose:
                        print(f"  ✓ Analysis complete (deterministic)")

                    if saved_path:
                        all_traces.append(saved_path)
                        has_failure, error_count = self.check_trace_for_failure(saved_path)
                        if has_failure:
                            failed_traces.append((saved_path, error_count))
                            failure_found = True
                            if verbose:
                                print(f"  ⚠ FAILURE DETECTED! ({error_count} error(s))")
                                print(f"  → Trace: {saved_path}")
                
                # Check latest trace file for failures
                if self.traces_dir.exists():
                    trace_files = sorted(self.traces_dir.glob("*.json"))
                    if trace_files:
                        latest_trace = trace_files[-1]
                        if latest_trace not in [t[0] if isinstance(t, tuple) else t for t in all_traces]:
                            all_traces.append(latest_trace)
                            has_failure, error_count = self.check_trace_for_failure(latest_trace)
                            if has_failure:
                                failed_traces.append((latest_trace, error_count))
                                failure_found = True
                                if verbose:
                                    print(f"  ⚠ FAILURE DETECTED! ({error_count} error(s))")
                                    print(f"  → Trace: {latest_trace}")
                            
            except Exception as e:
                if verbose:
                    print(f"  ✗ Error during analysis: {e}")
                # Still check if a trace was saved
                if self.traces_dir.exists():
                    trace_files = sorted(self.traces_dir.glob("*.json"))
                    if trace_files:
                        latest_trace = trace_files[-1]
                        if latest_trace not in [t[0] if isinstance(t, tuple) else t for t in all_traces]:
                            all_traces.append(latest_trace)
                            has_failure, error_count = self.check_trace_for_failure(latest_trace)
                            if has_failure:
                                failed_traces.append((latest_trace, error_count))
                                failure_found = True
                                if verbose:
                                    print(f"  ⚠ FAILURE DETECTED in error trace! ({error_count} error(s))")
            
            trace_index += 1
            
            # Stop if we found a failure and have at least min_runs
            if failure_found and run_count >= min_runs and stop_on_failure:
                if verbose:
                    print(f"\n  → Stopping: Failure found and minimum runs ({min_runs}) completed")
                break
        
        # Count new traces
        final_trace_files = list(self.traces_dir.glob("*.json"))
        new_traces = len(final_trace_files) - initial_count
        
        result = {
            "total_runs": run_count,
            "new_traces": new_traces,
            "failed_traces": len(failed_traces),
            "failed_trace_files": [t[0] for t in failed_traces],
            "all_traces": all_traces,
        }
        
        if verbose:
            print("\n" + "=" * 60)
            print("Trace generation complete!")
            print("=" * 60)
            print(f"\nTotal runs: {run_count}")
            print(f"New traces generated: {new_traces}")
            print(f"Traces with failures: {len(failed_traces)}")
            
            if failed_traces:
                print(f"\n⚠ Failed Traces:")
                for trace_file, error_count in failed_traces:
                    print(f"  - {trace_file.name} ({error_count} error(s))")
            
            print(f"\nAll new traces saved in: {self.traces_dir}")
            print(f"Ready for analysis!")
        
        return result

