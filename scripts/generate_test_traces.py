#!/usr/bin/env python3
"""
Generate diverse sample traces for testing the GUI.

Creates traces with various patterns:
1. Successful execution
2. Tool error with retry
3. Infinite loop detected
4. Context overflow
5. Hallucinated tool call
6. Error cascade
7. Mixed success with warnings
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path


def generate_run_id():
    return str(uuid.uuid4())


def timestamp_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def save_trace(trace: dict, name: str, output_dir: Path):
    """Save trace to file."""
    filename = f"test_{name}_{trace['run_id'][:8]}.json"
    filepath = output_dir / filename
    with open(filepath, "w") as f:
        json.dump(trace, f, indent=2)
    print(f"Created: {filepath}")
    return filepath


def generate_successful_trace():
    """Generate a trace of successful agent execution."""
    run_id = generate_run_id()
    start = datetime.now()

    return {
        "run_id": run_id,
        "start_time": timestamp_iso(start),
        "end_time": timestamp_iso(start + timedelta(seconds=5)),
        "duration_ms": 5000,
        "status": "success",
        "total_events": 8,
        "events": [
            {
                "event_id": 0,
                "ts": timestamp_iso(start),
                "type": "llm_call",
                "name": "gpt-4",
                "input": "What is the weather in New York?",
                "output": "I'll check the weather for you using the weather tool.",
                "token_count": 150,
                "latency_ms": 800,
                "metadata": {"model": "gpt-4"}
            },
            {
                "event_id": 1,
                "ts": timestamp_iso(start + timedelta(milliseconds=850)),
                "type": "tool_call",
                "name": "get_weather",
                "input": {"city": "New York"},
                "output": {"temperature": 72, "condition": "sunny", "humidity": 45},
                "latency_ms": 200,
                "metadata": {}
            },
            {
                "event_id": 2,
                "ts": timestamp_iso(start + timedelta(milliseconds=1100)),
                "type": "llm_call",
                "name": "gpt-4",
                "input": "Weather data: temperature=72, condition=sunny",
                "output": "The weather in New York is currently sunny with a temperature of 72°F and 45% humidity.",
                "token_count": 180,
                "latency_ms": 600,
                "metadata": {"model": "gpt-4"}
            },
            {
                "event_id": 3,
                "ts": timestamp_iso(start + timedelta(milliseconds=1750)),
                "type": "message",
                "name": "assistant",
                "role": "assistant",
                "output": "The weather in New York is currently sunny with a temperature of 72°F and 45% humidity. It's a beautiful day!",
                "metadata": {}
            }
        ],
        "metadata": {
            "trace_version": "1.0",
            "captured_by": "test_generator",
            "scenario": "successful_execution"
        }
    }


def generate_tool_error_retry_trace():
    """Generate a trace with tool error and successful retry."""
    run_id = generate_run_id()
    start = datetime.now()

    return {
        "run_id": run_id,
        "start_time": timestamp_iso(start),
        "end_time": timestamp_iso(start + timedelta(seconds=8)),
        "duration_ms": 8000,
        "status": "success",
        "total_events": 10,
        "events": [
            {
                "event_id": 0,
                "ts": timestamp_iso(start),
                "type": "llm_call",
                "name": "gpt-4",
                "input": "Search for recent news about AI",
                "output": "I'll search for recent AI news.",
                "token_count": 120,
                "latency_ms": 500,
                "metadata": {}
            },
            {
                "event_id": 1,
                "ts": timestamp_iso(start + timedelta(milliseconds=600)),
                "type": "tool_call",
                "name": "web_search",
                "input": {"query": "recent AI news 2024"},
                "latency_ms": 2000,
                "error": "Connection timeout after 2000ms",
                "metadata": {"retry_count": 0}
            },
            {
                "event_id": 2,
                "ts": timestamp_iso(start + timedelta(milliseconds=2700)),
                "type": "error",
                "name": "web_search",
                "error": "Connection timeout after 2000ms",
                "metadata": {"error_type": "TimeoutError"}
            },
            {
                "event_id": 3,
                "ts": timestamp_iso(start + timedelta(milliseconds=2800)),
                "type": "tool_call",
                "name": "web_search",
                "input": {"query": "recent AI news 2024"},
                "output": [
                    {"title": "GPT-5 announced", "url": "https://example.com/1"},
                    {"title": "AI regulation updates", "url": "https://example.com/2"}
                ],
                "latency_ms": 1500,
                "metadata": {"retry_count": 1}
            },
            {
                "event_id": 4,
                "ts": timestamp_iso(start + timedelta(milliseconds=4400)),
                "type": "llm_call",
                "name": "gpt-4",
                "input": "Search results: GPT-5 announced, AI regulation updates",
                "output": "Here are the recent AI news highlights...",
                "token_count": 250,
                "latency_ms": 700,
                "metadata": {}
            },
            {
                "event_id": 5,
                "ts": timestamp_iso(start + timedelta(milliseconds=5200)),
                "type": "message",
                "name": "assistant",
                "role": "assistant",
                "output": "Here are the latest AI news: 1) GPT-5 has been announced 2) New AI regulations are being discussed",
                "metadata": {}
            }
        ],
        "metadata": {
            "trace_version": "1.0",
            "captured_by": "test_generator",
            "scenario": "tool_error_with_retry"
        }
    }


def generate_infinite_loop_trace():
    """Generate a trace showing infinite loop detection."""
    run_id = generate_run_id()
    start = datetime.now()

    # Generate repeated identical tool calls (loop pattern)
    events = [
        {
            "event_id": 0,
            "ts": timestamp_iso(start),
            "type": "llm_call",
            "name": "gpt-4",
            "input": "Find information about quantum computing",
            "output": "I'll search for quantum computing information.",
            "token_count": 100,
            "latency_ms": 400,
            "metadata": {}
        }
    ]

    # Add 10 identical search calls (loop)
    for i in range(10):
        events.append({
            "event_id": i + 1,
            "ts": timestamp_iso(start + timedelta(milliseconds=500 + i * 300)),
            "type": "tool_call",
            "name": "web_search",
            "input": {"query": "quantum computing basics"},  # Same input every time
            "output": {"results": []},  # Empty results causing retry
            "latency_ms": 250,
            "metadata": {"iteration": i + 1}
        })

    events.append({
        "event_id": 11,
        "ts": timestamp_iso(start + timedelta(milliseconds=3800)),
        "type": "error",
        "name": "loop_detector",
        "error": "Infinite loop detected: tool 'web_search' called 10 times with identical input",
        "metadata": {"loop_count": 10, "tool": "web_search"}
    })

    return {
        "run_id": run_id,
        "start_time": timestamp_iso(start),
        "end_time": timestamp_iso(start + timedelta(seconds=4)),
        "duration_ms": 4000,
        "status": "loop_detected",
        "total_events": len(events),
        "events": events,
        "error_summary": "Infinite loop detected after 10 identical tool calls",
        "metadata": {
            "trace_version": "1.0",
            "captured_by": "test_generator",
            "scenario": "infinite_loop"
        }
    }


def generate_context_overflow_trace():
    """Generate a trace showing context window overflow."""
    run_id = generate_run_id()
    start = datetime.now()

    events = []
    total_tokens = 0

    # Simulate building up context until overflow
    for i in range(15):
        tokens = 8000 + i * 1000  # Increasing token counts
        total_tokens += tokens

        events.append({
            "event_id": i,
            "ts": timestamp_iso(start + timedelta(milliseconds=i * 1000)),
            "type": "llm_call",
            "name": "gpt-4",
            "input": f"Continue processing document part {i+1}...",
            "output": f"Processed part {i+1}. " + "x" * 500,  # Long output
            "token_count": tokens,
            "latency_ms": 1500,
            "metadata": {"cumulative_tokens": total_tokens}
        })

        if total_tokens > 120000:  # Simulate overflow
            events.append({
                "event_id": i + 1,
                "ts": timestamp_iso(start + timedelta(milliseconds=(i + 1) * 1000)),
                "type": "error",
                "name": "context_manager",
                "error": f"Context window overflow: {total_tokens} tokens exceeds limit of 128000",
                "metadata": {"token_count": total_tokens, "limit": 128000}
            })
            break

    return {
        "run_id": run_id,
        "start_time": timestamp_iso(start),
        "end_time": timestamp_iso(start + timedelta(seconds=15)),
        "duration_ms": 15000,
        "status": "failed",
        "total_events": len(events),
        "events": events,
        "error_summary": f"Context overflow at {total_tokens} tokens",
        "metadata": {
            "trace_version": "1.0",
            "captured_by": "test_generator",
            "scenario": "context_overflow"
        }
    }


def generate_hallucinated_tool_trace():
    """Generate a trace with hallucinated (non-existent) tool call."""
    run_id = generate_run_id()
    start = datetime.now()

    return {
        "run_id": run_id,
        "start_time": timestamp_iso(start),
        "end_time": timestamp_iso(start + timedelta(seconds=3)),
        "duration_ms": 3000,
        "status": "failed",
        "total_events": 5,
        "tools": ["web_search", "calculator", "get_weather"],  # Available tools
        "events": [
            {
                "event_id": 0,
                "ts": timestamp_iso(start),
                "type": "llm_call",
                "name": "gpt-4",
                "input": "Book a flight to Paris for tomorrow",
                "output": "I'll book the flight using the flight_booking tool.",
                "token_count": 100,
                "latency_ms": 500,
                "metadata": {}
            },
            {
                "event_id": 1,
                "ts": timestamp_iso(start + timedelta(milliseconds=600)),
                "type": "tool_call",
                "name": "flight_booking",  # This tool doesn't exist!
                "input": {"destination": "Paris", "date": "tomorrow"},
                "latency_ms": 50,
                "error": "Tool 'flight_booking' not found in available tools",
                "metadata": {"available_tools": ["web_search", "calculator", "get_weather"]}
            },
            {
                "event_id": 2,
                "ts": timestamp_iso(start + timedelta(milliseconds=700)),
                "type": "error",
                "name": "tool_executor",
                "error": "Hallucinated tool call: 'flight_booking' does not exist. Available: web_search, calculator, get_weather",
                "metadata": {"error_type": "HallucinatedToolError", "tool_called": "flight_booking"}
            },
            {
                "event_id": 3,
                "ts": timestamp_iso(start + timedelta(milliseconds=800)),
                "type": "llm_call",
                "name": "gpt-4",
                "input": "Error: flight_booking tool not available",
                "output": "I apologize, I don't have access to a flight booking tool. I can only search the web, calculate, or check weather.",
                "token_count": 80,
                "latency_ms": 400,
                "metadata": {}
            }
        ],
        "error_summary": "Attempted to use non-existent tool 'flight_booking'",
        "metadata": {
            "trace_version": "1.0",
            "captured_by": "test_generator",
            "scenario": "hallucinated_tool"
        }
    }


def generate_error_cascade_trace():
    """Generate a trace showing error cascade from initial failure."""
    run_id = generate_run_id()
    start = datetime.now()

    return {
        "run_id": run_id,
        "start_time": timestamp_iso(start),
        "end_time": timestamp_iso(start + timedelta(seconds=6)),
        "duration_ms": 6000,
        "status": "failed",
        "total_events": 8,
        "events": [
            {
                "event_id": 0,
                "ts": timestamp_iso(start),
                "type": "llm_call",
                "name": "gpt-4",
                "input": "Analyze the sales data and create a report",
                "output": "I'll fetch the sales data first.",
                "token_count": 100,
                "latency_ms": 400,
                "metadata": {}
            },
            {
                "event_id": 1,
                "ts": timestamp_iso(start + timedelta(milliseconds=500)),
                "type": "tool_call",
                "name": "database_query",
                "input": {"query": "SELECT * FROM sales WHERE date > '2024-01-01'"},
                "latency_ms": 500,
                "error": "Database connection failed: Connection refused",
                "metadata": {}
            },
            {
                "event_id": 2,
                "ts": timestamp_iso(start + timedelta(milliseconds=1100)),
                "type": "error",
                "name": "database_query",
                "error": "Database connection failed: Connection refused",
                "metadata": {"error_type": "ConnectionError", "host": "db.example.com"}
            },
            {
                "event_id": 3,
                "ts": timestamp_iso(start + timedelta(milliseconds=1200)),
                "type": "llm_call",
                "name": "gpt-4",
                "input": "Database error occurred",
                "output": "Let me try to fetch from the backup cache.",
                "token_count": 80,
                "latency_ms": 300,
                "metadata": {}
            },
            {
                "event_id": 4,
                "ts": timestamp_iso(start + timedelta(milliseconds=1600)),
                "type": "tool_call",
                "name": "cache_fetch",
                "input": {"key": "sales_data_backup"},
                "latency_ms": 200,
                "error": "Cache miss: key 'sales_data_backup' not found",
                "metadata": {}
            },
            {
                "event_id": 5,
                "ts": timestamp_iso(start + timedelta(milliseconds=1900)),
                "type": "error",
                "name": "cache_fetch",
                "error": "Cache miss: key 'sales_data_backup' not found",
                "metadata": {"error_type": "CacheMissError"}
            },
            {
                "event_id": 6,
                "ts": timestamp_iso(start + timedelta(milliseconds=2000)),
                "type": "llm_call",
                "name": "gpt-4",
                "input": "Cache also failed",
                "output": "I cannot complete this task without access to the sales data.",
                "token_count": 60,
                "latency_ms": 250,
                "metadata": {}
            },
            {
                "event_id": 7,
                "ts": timestamp_iso(start + timedelta(milliseconds=2300)),
                "type": "error",
                "name": "agent",
                "error": "Task failed: Unable to access required data after multiple attempts",
                "metadata": {"error_type": "TaskFailure", "cascade_depth": 3}
            }
        ],
        "error_summary": "Error cascade: database failure -> cache miss -> task failure",
        "metadata": {
            "trace_version": "1.0",
            "captured_by": "test_generator",
            "scenario": "error_cascade"
        }
    }


def generate_mixed_success_trace():
    """Generate a trace with partial success and warnings."""
    run_id = generate_run_id()
    start = datetime.now()

    return {
        "run_id": run_id,
        "start_time": timestamp_iso(start),
        "end_time": timestamp_iso(start + timedelta(seconds=10)),
        "duration_ms": 10000,
        "status": "success",
        "total_events": 12,
        "events": [
            {
                "event_id": 0,
                "ts": timestamp_iso(start),
                "type": "llm_call",
                "name": "gpt-4",
                "input": "Compare prices for iPhone 15 across different stores",
                "output": "I'll search multiple stores for iPhone 15 prices.",
                "token_count": 120,
                "latency_ms": 500,
                "metadata": {}
            },
            {
                "event_id": 1,
                "ts": timestamp_iso(start + timedelta(milliseconds=600)),
                "type": "tool_call",
                "name": "web_search",
                "input": {"query": "iPhone 15 price Amazon"},
                "output": {"price": 799, "store": "Amazon", "in_stock": True},
                "latency_ms": 800,
                "metadata": {}
            },
            {
                "event_id": 2,
                "ts": timestamp_iso(start + timedelta(milliseconds=1500)),
                "type": "tool_call",
                "name": "web_search",
                "input": {"query": "iPhone 15 price BestBuy"},
                "output": {"price": 829, "store": "BestBuy", "in_stock": True},
                "latency_ms": 600,
                "metadata": {}
            },
            {
                "event_id": 3,
                "ts": timestamp_iso(start + timedelta(milliseconds=2200)),
                "type": "tool_call",
                "name": "web_search",
                "input": {"query": "iPhone 15 price Walmart"},
                "latency_ms": 3000,
                "error": "Request timeout",
                "metadata": {"warning": True}
            },
            {
                "event_id": 4,
                "ts": timestamp_iso(start + timedelta(milliseconds=5300)),
                "type": "tool_call",
                "name": "web_search",
                "input": {"query": "iPhone 15 price Target"},
                "output": {"price": 799, "store": "Target", "in_stock": False},
                "latency_ms": 700,
                "metadata": {}
            },
            {
                "event_id": 5,
                "ts": timestamp_iso(start + timedelta(milliseconds=6100)),
                "type": "llm_call",
                "name": "gpt-4",
                "input": "Price data: Amazon=$799, BestBuy=$829, Walmart=timeout, Target=$799(out of stock)",
                "output": "Based on the available data, here's the price comparison...",
                "token_count": 200,
                "latency_ms": 600,
                "metadata": {}
            },
            {
                "event_id": 6,
                "ts": timestamp_iso(start + timedelta(milliseconds=6800)),
                "type": "message",
                "name": "assistant",
                "role": "assistant",
                "output": "iPhone 15 Price Comparison:\n- Amazon: $799 (in stock)\n- BestBuy: $829 (in stock)\n- Target: $799 (out of stock)\n- Walmart: Unable to fetch (timeout)\n\nBest deal: Amazon at $799",
                "metadata": {"partial_data": True, "stores_checked": 4, "stores_succeeded": 3}
            }
        ],
        "metadata": {
            "trace_version": "1.0",
            "captured_by": "test_generator",
            "scenario": "mixed_success_with_warnings"
        }
    }


def main():
    output_dir = Path("traces")
    output_dir.mkdir(exist_ok=True)

    print("Generating diverse test traces...\n")

    # Generate all trace types
    traces = [
        (generate_successful_trace(), "success"),
        (generate_tool_error_retry_trace(), "retry"),
        (generate_infinite_loop_trace(), "loop"),
        (generate_context_overflow_trace(), "overflow"),
        (generate_hallucinated_tool_trace(), "hallucination"),
        (generate_error_cascade_trace(), "cascade"),
        (generate_mixed_success_trace(), "mixed"),
    ]

    created_files = []
    for trace, name in traces:
        filepath = save_trace(trace, name, output_dir)
        created_files.append(filepath)

    print(f"\nCreated {len(created_files)} test traces in {output_dir}/")
    print("\nScenarios generated:")
    print("  1. success     - Clean successful execution")
    print("  2. retry       - Tool error with successful retry")
    print("  3. loop        - Infinite loop detection")
    print("  4. overflow    - Context window overflow")
    print("  5. hallucination - Hallucinated tool call")
    print("  6. cascade     - Error cascade from initial failure")
    print("  7. mixed       - Partial success with warnings")


if __name__ == "__main__":
    main()
