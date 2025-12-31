#!/usr/bin/env python3
"""
Generate additional realistic test traces for batch testing.
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path


def generate_run_id():
    return str(uuid.uuid4())


def ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def save_trace(trace: dict, name: str, output_dir: Path):
    filename = f"{name}_{trace['run_id'][:8]}.json"
    filepath = output_dir / filename
    with open(filepath, "w") as f:
        json.dump(trace, f, indent=2)
    print(f"  Created: {filename}")
    return filepath


# ============================================================================
# SUCCESSFUL TRACES
# ============================================================================

def trace_code_generation():
    """Successful code generation task."""
    run_id = generate_run_id()
    start = datetime.now()
    return {
        "run_id": run_id,
        "start_time": ts(start),
        "end_time": ts(start + timedelta(seconds=12)),
        "duration_ms": 12000,
        "status": "success",
        "goal": "Write a Python function to calculate Fibonacci numbers",
        "events": [
            {"event_id": 0, "ts": ts(start), "type": "llm_call", "name": "claude-3",
             "input": "Write a Python function to calculate Fibonacci numbers",
             "output": "I'll write an efficient Fibonacci function using memoization.",
             "token_count": 200, "latency_ms": 1200},
            {"event_id": 1, "ts": ts(start + timedelta(milliseconds=1300)), "type": "tool_call", "name": "code_writer",
             "input": {"language": "python", "task": "fibonacci function"},
             "output": {"code": "def fib(n, memo={}):\n    if n <= 1: return n\n    if n not in memo:\n        memo[n] = fib(n-1) + fib(n-2)\n    return memo[n]"},
             "latency_ms": 500},
            {"event_id": 2, "ts": ts(start + timedelta(milliseconds=1900)), "type": "tool_call", "name": "code_executor",
             "input": {"code": "print([fib(i) for i in range(10)])"},
             "output": {"result": "[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]", "success": True},
             "latency_ms": 200},
            {"event_id": 3, "ts": ts(start + timedelta(milliseconds=2200)), "type": "llm_call", "name": "claude-3",
             "input": "Code executed successfully: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]",
             "output": "The Fibonacci function works correctly. Here's the implementation with explanation...",
             "token_count": 350, "latency_ms": 1500},
            {"event_id": 4, "ts": ts(start + timedelta(milliseconds=3800)), "type": "message", "name": "assistant",
             "role": "assistant", "output": "Here's an efficient Fibonacci implementation using memoization..."}
        ],
        "metadata": {"scenario": "code_generation_success", "model": "claude-3"}
    }


def trace_data_analysis():
    """Successful data analysis workflow."""
    run_id = generate_run_id()
    start = datetime.now()
    return {
        "run_id": run_id,
        "start_time": ts(start),
        "end_time": ts(start + timedelta(seconds=18)),
        "duration_ms": 18000,
        "status": "success",
        "goal": "Analyze quarterly sales data and identify trends",
        "events": [
            {"event_id": 0, "ts": ts(start), "type": "llm_call", "name": "gpt-4",
             "input": "Analyze quarterly sales data and identify trends",
             "output": "I'll load the data and perform trend analysis.",
             "token_count": 150, "latency_ms": 800},
            {"event_id": 1, "ts": ts(start + timedelta(milliseconds=900)), "type": "tool_call", "name": "data_loader",
             "input": {"source": "sales_q4_2024.csv"},
             "output": {"rows": 1500, "columns": ["date", "product", "revenue", "units"]},
             "latency_ms": 1200},
            {"event_id": 2, "ts": ts(start + timedelta(milliseconds=2200)), "type": "tool_call", "name": "statistics",
             "input": {"operation": "trend_analysis", "column": "revenue"},
             "output": {"trend": "increasing", "growth_rate": 0.15, "r_squared": 0.92},
             "latency_ms": 800},
            {"event_id": 3, "ts": ts(start + timedelta(milliseconds=3100)), "type": "tool_call", "name": "visualizer",
             "input": {"chart_type": "line", "data": "revenue_by_month"},
             "output": {"chart_url": "/charts/revenue_trend.png"},
             "latency_ms": 600},
            {"event_id": 4, "ts": ts(start + timedelta(milliseconds=3800)), "type": "llm_call", "name": "gpt-4",
             "input": "Analysis complete: 15% growth, R²=0.92",
             "output": "The quarterly sales show a strong upward trend with 15% growth...",
             "token_count": 400, "latency_ms": 1200},
            {"event_id": 5, "ts": ts(start + timedelta(milliseconds=5100)), "type": "message", "name": "assistant",
             "role": "assistant", "output": "Sales Analysis Report:\n- Growth: 15% QoQ\n- Trend: Strong positive\n- Top products: Widget Pro, Gadget X"}
        ],
        "metadata": {"scenario": "data_analysis_success"}
    }


def trace_multi_step_research():
    """Successful multi-step research task."""
    run_id = generate_run_id()
    start = datetime.now()
    return {
        "run_id": run_id,
        "start_time": ts(start),
        "end_time": ts(start + timedelta(seconds=25)),
        "duration_ms": 25000,
        "status": "success",
        "goal": "Research competitors and summarize their pricing strategies",
        "events": [
            {"event_id": 0, "ts": ts(start), "type": "llm_call", "name": "gpt-4",
             "input": "Research competitors and summarize pricing strategies",
             "output": "I'll search for information about each competitor.",
             "token_count": 180, "latency_ms": 900},
            {"event_id": 1, "ts": ts(start + timedelta(milliseconds=1000)), "type": "tool_call", "name": "web_search",
             "input": {"query": "CompanyA pricing plans 2024"},
             "output": {"results": [{"title": "CompanyA Pricing", "snippet": "Starting at $29/month..."}]},
             "latency_ms": 1500},
            {"event_id": 2, "ts": ts(start + timedelta(milliseconds=2600)), "type": "tool_call", "name": "web_search",
             "input": {"query": "CompanyB pricing plans 2024"},
             "output": {"results": [{"title": "CompanyB Plans", "snippet": "Free tier available, Pro at $49..."}]},
             "latency_ms": 1400},
            {"event_id": 3, "ts": ts(start + timedelta(milliseconds=4100)), "type": "tool_call", "name": "web_search",
             "input": {"query": "CompanyC enterprise pricing"},
             "output": {"results": [{"title": "CompanyC Enterprise", "snippet": "Custom pricing, contact sales..."}]},
             "latency_ms": 1300},
            {"event_id": 4, "ts": ts(start + timedelta(milliseconds=5500)), "type": "llm_call", "name": "gpt-4",
             "input": "Research results for 3 competitors collected",
             "output": "Based on the research, here's the competitive pricing analysis...",
             "token_count": 600, "latency_ms": 2000},
            {"event_id": 5, "ts": ts(start + timedelta(milliseconds=7600)), "type": "message", "name": "assistant",
             "role": "assistant", "output": "Competitor Pricing Summary:\n1. CompanyA: $29-99/mo\n2. CompanyB: Free-$49/mo\n3. CompanyC: Enterprise only"}
        ],
        "metadata": {"scenario": "multi_step_research_success"}
    }


# ============================================================================
# FAILURE TRACES
# ============================================================================

def trace_api_rate_limit():
    """API rate limit exceeded."""
    run_id = generate_run_id()
    start = datetime.now()
    return {
        "run_id": run_id,
        "start_time": ts(start),
        "end_time": ts(start + timedelta(seconds=5)),
        "duration_ms": 5000,
        "status": "failed",
        "goal": "Fetch latest stock prices",
        "events": [
            {"event_id": 0, "ts": ts(start), "type": "llm_call", "name": "gpt-4",
             "input": "Get current stock prices for AAPL, GOOGL, MSFT",
             "output": "I'll fetch the stock prices.",
             "token_count": 100, "latency_ms": 500},
            {"event_id": 1, "ts": ts(start + timedelta(milliseconds=600)), "type": "tool_call", "name": "stock_api",
             "input": {"symbols": ["AAPL"]}, "output": {"AAPL": 185.50}, "latency_ms": 300},
            {"event_id": 2, "ts": ts(start + timedelta(milliseconds=1000)), "type": "tool_call", "name": "stock_api",
             "input": {"symbols": ["GOOGL"]}, "output": {"GOOGL": 142.30}, "latency_ms": 300},
            {"event_id": 3, "ts": ts(start + timedelta(milliseconds=1400)), "type": "tool_call", "name": "stock_api",
             "input": {"symbols": ["MSFT"]},
             "error": "Rate limit exceeded: 429 Too Many Requests. Retry after 60 seconds.",
             "latency_ms": 100},
            {"event_id": 4, "ts": ts(start + timedelta(milliseconds=1600)), "type": "error", "name": "stock_api",
             "error": "Rate limit exceeded: 429 Too Many Requests",
             "metadata": {"error_type": "RateLimitError", "retry_after": 60}},
            {"event_id": 5, "ts": ts(start + timedelta(milliseconds=1700)), "type": "llm_call", "name": "gpt-4",
             "input": "Rate limit error on MSFT lookup",
             "output": "I was able to get prices for AAPL and GOOGL but hit a rate limit for MSFT.",
             "token_count": 120, "latency_ms": 600}
        ],
        "error_summary": "API rate limit exceeded during stock price fetch",
        "metadata": {"scenario": "api_rate_limit"}
    }


def trace_authentication_failure():
    """Authentication/authorization failure."""
    run_id = generate_run_id()
    start = datetime.now()
    return {
        "run_id": run_id,
        "start_time": ts(start),
        "end_time": ts(start + timedelta(seconds=3)),
        "duration_ms": 3000,
        "status": "failed",
        "goal": "Access user's private repository",
        "events": [
            {"event_id": 0, "ts": ts(start), "type": "llm_call", "name": "gpt-4",
             "input": "Clone and analyze the private repo github.com/user/private-repo",
             "output": "I'll access the repository.",
             "token_count": 80, "latency_ms": 400},
            {"event_id": 1, "ts": ts(start + timedelta(milliseconds=500)), "type": "tool_call", "name": "github_api",
             "input": {"action": "get_repo", "repo": "user/private-repo"},
             "error": "401 Unauthorized: Bad credentials or token expired",
             "latency_ms": 200},
            {"event_id": 2, "ts": ts(start + timedelta(milliseconds=800)), "type": "error", "name": "github_api",
             "error": "Authentication failed: Invalid or expired GitHub token",
             "metadata": {"error_type": "AuthenticationError", "status_code": 401}}
        ],
        "error_summary": "GitHub authentication failed - invalid or expired token",
        "metadata": {"scenario": "authentication_failure"}
    }


def trace_timeout():
    """Operation timeout."""
    run_id = generate_run_id()
    start = datetime.now()
    return {
        "run_id": run_id,
        "start_time": ts(start),
        "end_time": ts(start + timedelta(seconds=35)),
        "duration_ms": 35000,
        "status": "timeout",
        "goal": "Process large PDF document",
        "events": [
            {"event_id": 0, "ts": ts(start), "type": "llm_call", "name": "gpt-4",
             "input": "Extract and summarize content from large_report.pdf (500 pages)",
             "output": "I'll process the PDF document.",
             "token_count": 100, "latency_ms": 500},
            {"event_id": 1, "ts": ts(start + timedelta(milliseconds=600)), "type": "tool_call", "name": "pdf_processor",
             "input": {"file": "large_report.pdf", "operation": "extract_text"},
             "error": "Operation timed out after 30000ms",
             "latency_ms": 30000},
            {"event_id": 2, "ts": ts(start + timedelta(milliseconds=30700)), "type": "error", "name": "pdf_processor",
             "error": "Timeout: PDF processing exceeded 30 second limit",
             "metadata": {"error_type": "TimeoutError", "timeout_ms": 30000, "file_size_mb": 125}}
        ],
        "error_summary": "PDF processing timed out - file too large",
        "metadata": {"scenario": "operation_timeout"}
    }


def trace_invalid_input():
    """Invalid input validation failure."""
    run_id = generate_run_id()
    start = datetime.now()
    return {
        "run_id": run_id,
        "start_time": ts(start),
        "end_time": ts(start + timedelta(seconds=2)),
        "duration_ms": 2000,
        "status": "failed",
        "goal": "Send email to user",
        "events": [
            {"event_id": 0, "ts": ts(start), "type": "llm_call", "name": "gpt-4",
             "input": "Send welcome email to new user john",
             "output": "I'll send the welcome email.",
             "token_count": 80, "latency_ms": 400},
            {"event_id": 1, "ts": ts(start + timedelta(milliseconds=500)), "type": "tool_call", "name": "email_sender",
             "input": {"to": "john", "subject": "Welcome!", "body": "Welcome to our platform..."},
             "error": "Invalid email address format: 'john' is not a valid email",
             "latency_ms": 50},
            {"event_id": 2, "ts": ts(start + timedelta(milliseconds=600)), "type": "error", "name": "email_sender",
             "error": "Validation error: Invalid email address format",
             "metadata": {"error_type": "ValidationError", "field": "to", "value": "john"}}
        ],
        "error_summary": "Invalid email address provided",
        "metadata": {"scenario": "invalid_input_validation"}
    }


def trace_permission_denied():
    """Permission denied for operation."""
    run_id = generate_run_id()
    start = datetime.now()
    return {
        "run_id": run_id,
        "start_time": ts(start),
        "end_time": ts(start + timedelta(seconds=3)),
        "duration_ms": 3000,
        "status": "failed",
        "goal": "Delete old log files",
        "events": [
            {"event_id": 0, "ts": ts(start), "type": "llm_call", "name": "gpt-4",
             "input": "Clean up old log files in /var/log/app/",
             "output": "I'll delete the old log files.",
             "token_count": 90, "latency_ms": 400},
            {"event_id": 1, "ts": ts(start + timedelta(milliseconds=500)), "type": "tool_call", "name": "file_system",
             "input": {"action": "delete", "path": "/var/log/app/*.log", "older_than_days": 30},
             "error": "Permission denied: Cannot delete files in /var/log/app/",
             "latency_ms": 100},
            {"event_id": 2, "ts": ts(start + timedelta(milliseconds=700)), "type": "error", "name": "file_system",
             "error": "PermissionError: Operation not permitted on /var/log/app/",
             "metadata": {"error_type": "PermissionError", "path": "/var/log/app/"}}
        ],
        "error_summary": "Permission denied for file deletion operation",
        "metadata": {"scenario": "permission_denied"}
    }


def trace_resource_not_found():
    """Resource not found error."""
    run_id = generate_run_id()
    start = datetime.now()
    return {
        "run_id": run_id,
        "start_time": ts(start),
        "end_time": ts(start + timedelta(seconds=4)),
        "duration_ms": 4000,
        "status": "failed",
        "goal": "Get user profile details",
        "events": [
            {"event_id": 0, "ts": ts(start), "type": "llm_call", "name": "gpt-4",
             "input": "Fetch profile for user ID 12345",
             "output": "I'll retrieve the user profile.",
             "token_count": 70, "latency_ms": 350},
            {"event_id": 1, "ts": ts(start + timedelta(milliseconds=450)), "type": "tool_call", "name": "database_query",
             "input": {"query": "SELECT * FROM users WHERE id = 12345"},
             "output": {"rows": [], "count": 0},
             "latency_ms": 150},
            {"event_id": 2, "ts": ts(start + timedelta(milliseconds=700)), "type": "llm_call", "name": "gpt-4",
             "input": "Query returned no results",
             "output": "The user with ID 12345 was not found in the database.",
             "token_count": 80, "latency_ms": 400},
            {"event_id": 3, "ts": ts(start + timedelta(milliseconds=1200)), "type": "error", "name": "user_service",
             "error": "User not found: No user exists with ID 12345",
             "metadata": {"error_type": "NotFoundError", "resource": "user", "id": 12345}}
        ],
        "error_summary": "User with ID 12345 not found",
        "metadata": {"scenario": "resource_not_found"}
    }


def trace_retry_storm():
    """Aggressive retry pattern causing storm."""
    run_id = generate_run_id()
    start = datetime.now()
    events = [
        {"event_id": 0, "ts": ts(start), "type": "llm_call", "name": "gpt-4",
         "input": "Check service health",
         "output": "I'll check the service status.",
         "token_count": 60, "latency_ms": 300}
    ]

    # Generate 8 rapid retries
    for i in range(8):
        events.append({
            "event_id": i + 1,
            "ts": ts(start + timedelta(milliseconds=400 + i * 200)),
            "type": "tool_call",
            "name": "health_check",
            "input": {"service": "payment-service", "timeout": 1000},
            "error": "Service unavailable: Connection refused",
            "latency_ms": 150,
            "metadata": {"retry_attempt": i + 1}
        })

    events.append({
        "event_id": 9,
        "ts": ts(start + timedelta(milliseconds=2100)),
        "type": "error",
        "name": "retry_policy",
        "error": "Max retries exceeded (8) for health_check",
        "metadata": {"error_type": "MaxRetriesExceeded", "attempts": 8}
    })

    return {
        "run_id": run_id,
        "start_time": ts(start),
        "end_time": ts(start + timedelta(seconds=3)),
        "duration_ms": 3000,
        "status": "failed",
        "goal": "Check payment service health",
        "events": events,
        "error_summary": "Retry storm: 8 rapid retries without backoff",
        "metadata": {"scenario": "retry_storm"}
    }


def trace_partial_failure():
    """Partial success with some operations failing."""
    run_id = generate_run_id()
    start = datetime.now()
    return {
        "run_id": run_id,
        "start_time": ts(start),
        "end_time": ts(start + timedelta(seconds=15)),
        "duration_ms": 15000,
        "status": "success",
        "goal": "Send notifications to 5 users",
        "events": [
            {"event_id": 0, "ts": ts(start), "type": "llm_call", "name": "gpt-4",
             "input": "Send notification to users: alice, bob, charlie, david, eve",
             "output": "I'll send notifications to each user.",
             "token_count": 120, "latency_ms": 500},
            {"event_id": 1, "ts": ts(start + timedelta(milliseconds=600)), "type": "tool_call", "name": "notify",
             "input": {"user": "alice", "message": "New update available"},
             "output": {"success": True, "delivered": True},
             "latency_ms": 200},
            {"event_id": 2, "ts": ts(start + timedelta(milliseconds=900)), "type": "tool_call", "name": "notify",
             "input": {"user": "bob", "message": "New update available"},
             "error": "User 'bob' has notifications disabled",
             "latency_ms": 100},
            {"event_id": 3, "ts": ts(start + timedelta(milliseconds=1100)), "type": "tool_call", "name": "notify",
             "input": {"user": "charlie", "message": "New update available"},
             "output": {"success": True, "delivered": True},
             "latency_ms": 180},
            {"event_id": 4, "ts": ts(start + timedelta(milliseconds=1400)), "type": "tool_call", "name": "notify",
             "input": {"user": "david", "message": "New update available"},
             "error": "Invalid user ID: david not found",
             "latency_ms": 80},
            {"event_id": 5, "ts": ts(start + timedelta(milliseconds=1600)), "type": "tool_call", "name": "notify",
             "input": {"user": "eve", "message": "New update available"},
             "output": {"success": True, "delivered": True},
             "latency_ms": 190},
            {"event_id": 6, "ts": ts(start + timedelta(milliseconds=1900)), "type": "llm_call", "name": "gpt-4",
             "input": "Notification results: 3 delivered, 2 failed",
             "output": "Notifications sent to 3 out of 5 users. Failed for bob (disabled) and david (not found).",
             "token_count": 150, "latency_ms": 600}
        ],
        "metadata": {"scenario": "partial_failure", "success_rate": 0.6}
    }


def main():
    output_dir = Path("traces")
    output_dir.mkdir(exist_ok=True)

    print("Generating additional test traces...\n")
    print("SUCCESS SCENARIOS:")

    # Success traces
    save_trace(trace_code_generation(), "success_code", output_dir)
    save_trace(trace_data_analysis(), "success_data", output_dir)
    save_trace(trace_multi_step_research(), "success_research", output_dir)

    print("\nFAILURE SCENARIOS:")

    # Failure traces
    save_trace(trace_api_rate_limit(), "fail_ratelimit", output_dir)
    save_trace(trace_authentication_failure(), "fail_auth", output_dir)
    save_trace(trace_timeout(), "fail_timeout", output_dir)
    save_trace(trace_invalid_input(), "fail_validation", output_dir)
    save_trace(trace_permission_denied(), "fail_permission", output_dir)
    save_trace(trace_resource_not_found(), "fail_notfound", output_dir)
    save_trace(trace_retry_storm(), "fail_retrystorm", output_dir)
    save_trace(trace_partial_failure(), "partial_notify", output_dir)

    print(f"\nDone! Total traces in {output_dir}/:")
    print(f"  {len(list(output_dir.glob('*.json')))} files")


if __name__ == "__main__":
    main()
