"""Metrics collection and reporting module for dev-agent.

This module provides functionality to track, store, and report on
metrics related to the dev-agent's performance, including:
- Patch success rates
- Iteration counts
- LLM backend performance comparisons
- Execution durations

Typical usage:
    from agent_lib.metrics import record_metrics, generate_metrics_report
    from pathlib import Path

    @record_metrics(llm_backend="llama-cpp", model_name="codellama")
    def fix_test_failure(test_name: str) -> bool:
        # ... implementation ...
        return success

    # Later, generate a report
    from agent_lib.metrics import MetricsStorage, generate_metrics_report
    storage = MetricsStorage()
    metrics = storage.load_metrics()
    report = generate_metrics_report(metrics)
    print(report)
"""

import functools
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar


@dataclass
class PatchMetrics:
    """Metrics for a single patch generation attempt."""

    test_name: str
    llm_backend: str  # e.g., "llama-cpp", "ollama"
    model_name: str  # e.g., "codellama", "phi"
    iterations: int
    success: bool
    duration_ms: int


@dataclass
class DevAgentMetrics:
    """Aggregate metrics for multiple patch attempts."""

    patch_results: List[PatchMetrics] = field(default_factory=list)

    @property
    def total_iterations(self) -> int:
        """Get the total number of iterations across all patch attempts."""
        return sum(result.iterations for result in self.patch_results)

    @property
    def successful_patches(self) -> int:
        """Get the number of successful patches."""
        return sum(1 for result in self.patch_results if result.success)

    @property
    def failed_patches(self) -> int:
        """Get the number of failed patches."""
        return sum(1 for result in self.patch_results if not result.success)

    def add_patch_result(self, result: PatchMetrics) -> None:
        """Add a patch result to the metrics collection."""
        self.patch_results.append(result)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the metrics."""
        total_tests = len(self.patch_results)
        if total_tests == 0:
            return {
                "total_tests": 0,
                "successful_patches": 0,
                "failed_patches": 0,
                "success_rate": 0.0,
                "total_iterations": 0,
                "avg_iterations_per_test": 0.0,
                "avg_duration_ms": 0.0,
                "backends": {},
            }

        # Overall statistics
        success_rate = self.successful_patches / total_tests if total_tests > 0 else 0.0
        avg_iterations = self.total_iterations / total_tests if total_tests > 0 else 0.0
        total_duration = sum(result.duration_ms for result in self.patch_results)
        avg_duration = total_duration / total_tests if total_tests > 0 else 0.0

        # Backend-specific statistics
        backends: Dict[str, Dict[str, Any]] = {}
        for result in self.patch_results:
            backend = result.llm_backend
            if backend not in backends:
                backends[backend] = {
                    "tests": 0,
                    "success": 0,
                    "iterations": 0,
                    "duration_ms": 0,
                }

            backends[backend]["tests"] += 1
            backends[backend]["iterations"] += result.iterations
            backends[backend]["duration_ms"] += result.duration_ms
            if result.success:
                backends[backend]["success"] += 1

        # Calculate averages for each backend
        for backend, stats in backends.items():
            tests = stats["tests"]
            if tests > 0:
                stats["success_rate"] = stats["success"] / tests
                stats["avg_iterations"] = stats["iterations"] / tests
                stats["avg_duration_ms"] = stats["duration_ms"] / tests
            else:
                stats["success_rate"] = 0.0
                stats["avg_iterations"] = 0.0
                stats["avg_duration_ms"] = 0.0

        return {
            "total_tests": total_tests,
            "successful_patches": self.successful_patches,
            "failed_patches": self.failed_patches,
            "success_rate": success_rate,
            "total_iterations": self.total_iterations,
            "avg_iterations_per_test": avg_iterations,
            "avg_duration_ms": avg_duration,
            "backends": backends,
        }


class MetricsStorage:
    """Storage backend for metrics data."""

    def __init__(self, metrics_file: Optional[Path] = None) -> None:
        """Initialize metrics storage with an optional file path.

        Args:
            metrics_file: Path to metrics JSON file. If None, uses default location.
        """
        if metrics_file is None:
            # Default location in user's home directory
            home_dir = Path.home()
            metrics_dir = home_dir / ".dev-agent"
            metrics_dir.mkdir(exist_ok=True)
            self.metrics_file = metrics_dir / "metrics.json"
        else:
            self.metrics_file = metrics_file

    def save_metrics(self, metrics: DevAgentMetrics) -> None:
        """Save metrics to storage.

        Args:
            metrics: DevAgentMetrics object to save
        """
        # Convert metrics to serializable format
        metrics_dict = {
            "patch_results": [asdict(result) for result in metrics.patch_results]
        }

        # Create directory if it doesn't exist
        self.metrics_file.parent.mkdir(exist_ok=True, parents=True)

        # Write to file
        with open(self.metrics_file, "w") as f:
            json.dump(metrics_dict, f, indent=2)

    def load_metrics(self) -> DevAgentMetrics:
        """Load metrics from storage.

        Returns:
            DevAgentMetrics object loaded from storage,
            or a new empty DevAgentMetrics if file doesn't exist
        """
        if not self.metrics_file.exists():
            return DevAgentMetrics()

        try:
            with open(self.metrics_file, "r") as f:
                data = json.load(f)

            metrics = DevAgentMetrics()
            for result_dict in data.get("patch_results", []):
                metrics.add_patch_result(PatchMetrics(**result_dict))

            return metrics
        except (json.JSONDecodeError, KeyError):
            # Return empty metrics if file is corrupt
            return DevAgentMetrics()


# Type variable for the decorated function's return type
T = TypeVar("T")


def record_metrics(
    llm_backend: str, model_name: str
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to record metrics for a function.

    Args:
        llm_backend: The LLM backend being used (e.g., "llama-cpp", "ollama")
        model_name: The model name being used (e.g., "codellama", "phi")

    Returns:
        Decorator function that records metrics
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Extract test name more robustly
            # Priority: explicit test_name kwarg > first positional arg > unknown
            test_name = "unknown"
            if "test_name" in kwargs:
                test_name = str(kwargs["test_name"])
            elif args and hasattr(args[0], "test_name"):
                # If first arg is a TestFailure object with test_name attribute
                test_name = str(args[0].test_name)
            elif args:
                # Fallback to first positional argument
                test_name = str(args[0])

            # Load existing metrics
            storage = MetricsStorage()
            metrics = storage.load_metrics()

            # Record start time
            start_time = time.time()

            # Call the function and get its result
            iterations = 0
            result = func(*args, **kwargs)

            # Get iterations from the result if it's a tuple with iterations
            if isinstance(result, tuple) and len(result) > 1:
                success, iterations = result[0], result[1]
            else:
                success = bool(result)
                iterations = 1  # Default to 1 iteration if not specified

            # Record end time and calculate duration
            end_time = time.time()
            duration_ms = int((end_time - start_time) * 1000)

            # Create and add patch metrics
            patch_metrics = PatchMetrics(
                test_name=str(test_name),
                llm_backend=llm_backend,
                model_name=model_name,
                iterations=iterations,
                success=success,
                duration_ms=duration_ms,
            )
            metrics.add_patch_result(patch_metrics)

            # Save updated metrics
            storage.save_metrics(metrics)

            # Return the original result
            return result

        return wrapper

    return decorator


def generate_metrics_report(metrics: DevAgentMetrics) -> str:
    """Generate a human-readable report from metrics.

    Args:
        metrics: DevAgentMetrics object to generate report from

    Returns:
        Formatted string report
    """
    summary = metrics.get_summary()

    # Format success rate as percentage
    success_rate = summary["success_rate"] * 100 if "success_rate" in summary else 0.0

    # Build the report
    report = [
        "=================================================",
        "            Dev Agent Metrics Report              ",
        "=================================================",
        f"Total Tests: {summary['total_tests']}",
        f"Success Rate: {success_rate:.1f}%",
        f"Successful Patches: {summary['successful_patches']}",
        f"Failed Patches: {summary['failed_patches']}",
        f"Total Iterations: {summary['total_iterations']}",
        f"Average Iterations: {summary['avg_iterations_per_test']:.1f}",
        f"Average Duration: {summary['avg_duration_ms']:.1f}ms",
        "",
        "Backend Performance:",
        "-------------------------------------------------",
    ]

    # Add backend-specific metrics
    backends = summary.get("backends", {})
    for backend, stats in backends.items():
        backend_success_rate = (
            stats["success_rate"] * 100 if "success_rate" in stats else 0.0
        )
        report.extend(
            [
                f"  {backend}:",
                f"    Tests: {stats['tests']}",
                f"    Success Rate: {backend_success_rate:.1f}%",
                f"    Average Iterations: {stats['avg_iterations']:.1f}",
                f"    Average Duration: {stats['avg_duration_ms']:.1f}ms",
                "",
            ]
        )

    report.append("=================================================")

    return "\n".join(report)
