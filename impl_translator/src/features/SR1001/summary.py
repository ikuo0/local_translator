"""Job summary statistics and metrics calculation."""

from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, StatisticsError
from typing import Any

from impl_translator.src.libs import job


@dataclass
class PageMetrics:
    """Metrics for a single page."""
    page_number: int
    status: str
    input_characters: int | None
    output_characters: int | None
    elapsed_seconds: float | None


@dataclass
class SummaryMetrics:
    """Summary statistics for completed pages."""
    total_pages: int
    completed_pages: int
    failed_pages: int
    interrupted_pages: int
    running_pages: int
    pending_pages: int
    
    # Timing statistics (for completed pages)
    avg_elapsed_seconds: float | None
    min_elapsed_seconds: float | None
    max_elapsed_seconds: float | None
    total_elapsed_seconds: float | None
    
    # Character statistics (for completed pages with output)
    avg_input_characters: float | None
    min_input_characters: int | None
    max_input_characters: int | None
    total_input_characters: int | None
    
    avg_output_characters: float | None
    min_output_characters: int | None
    max_output_characters: int | None
    total_output_characters: int | None
    
    # Compression ratio
    avg_compression_ratio: float | None
    
    # Overall progress
    progress_percent: float


def _calculate_ratio(output: int | None, input_val: int) -> float | None:
    """Calculate output/input ratio safely."""
    if output is None or input_val == 0:
        return None
    return output / input_val


def calculate_summary(state: dict[str, Any]) -> SummaryMetrics:
    """Calculate summary metrics from job state.
    
    Args:
        state: Job state dictionary loaded from job.yaml
        
    Returns:
        SummaryMetrics containing calculated statistics
    """
    data = state.get("data", {})
    pages = data.get("pages", {})
    total_pages = data.get("page_count", len(pages))
    
    # Count statuses
    completed_pages = []
    failed_pages = 0
    interrupted_pages = 0
    running_pages = 0
    pending_pages = 0
    
    for page_info in pages.values():
        status = page_info.get("status", "pending")
        if status == "completed":
            completed_pages.append(page_info)
        elif status == "failed":
            failed_pages += 1
        elif status == "interrupted":
            interrupted_pages += 1
        elif status == "running":
            running_pages += 1
        elif status == "pending":
            pending_pages += 1
    
    # Timing statistics
    elapsed_times = [p.get("elapsed_seconds") for p in completed_pages 
                     if p.get("elapsed_seconds") is not None]
    avg_elapsed = mean(elapsed_times) if elapsed_times else None
    min_elapsed = min(elapsed_times) if elapsed_times else None
    max_elapsed = max(elapsed_times) if elapsed_times else None
    total_elapsed = sum(elapsed_times) if elapsed_times else None
    
    # Input character statistics
    input_chars = [p.get("input_characters") for p in completed_pages 
                   if p.get("input_characters") is not None]
    avg_input = mean(input_chars) if input_chars else None
    min_input = min(input_chars) if input_chars else None
    max_input = max(input_chars) if input_chars else None
    total_input = sum(input_chars) if input_chars else None
    
    # Output character statistics
    output_chars = [p.get("output_characters") for p in completed_pages 
                    if p.get("output_characters") is not None]
    avg_output = mean(output_chars) if output_chars else None
    min_output = min(output_chars) if output_chars else None
    max_output = max(output_chars) if output_chars else None
    total_output = sum(output_chars) if output_chars else None
    
    # Compression ratio
    compression_ratios = []
    for p in completed_pages:
        output = p.get("output_characters")
        input_val = p.get("input_characters")
        if output is not None and input_val is not None and input_val > 0:
            compression_ratios.append(output / input_val)
    
    avg_compression = mean(compression_ratios) if compression_ratios else None
    
    # Progress percentage
    progress_percent = round(100 * len(completed_pages) / total_pages, 1) if total_pages > 0 else 0
    
    return SummaryMetrics(
        total_pages=total_pages,
        completed_pages=len(completed_pages),
        failed_pages=failed_pages,
        interrupted_pages=interrupted_pages,
        running_pages=running_pages,
        pending_pages=pending_pages,
        avg_elapsed_seconds=avg_elapsed,
        min_elapsed_seconds=min_elapsed,
        max_elapsed_seconds=max_elapsed,
        total_elapsed_seconds=total_elapsed,
        avg_input_characters=avg_input,
        min_input_characters=min_input,
        max_input_characters=max_input,
        total_input_characters=total_input,
        avg_output_characters=avg_output,
        min_output_characters=min_output,
        max_output_characters=max_output,
        total_output_characters=total_output,
        avg_compression_ratio=avg_compression,
        progress_percent=progress_percent,
    )


def calculate_page_metrics(state: dict[str, Any]) -> list[PageMetrics]:
    """Extract page-by-page metrics from job state.
    
    Args:
        state: Job state dictionary loaded from job.yaml
        
    Returns:
        List of PageMetrics ordered by page number
    """
    pages = state.get("data", {}).get("pages", {})
    metrics = []
    
    for page_num_str, page_info in sorted(pages.items(), key=lambda x: int(x[0])):
        metrics.append(PageMetrics(
            page_number=int(page_num_str),
            status=page_info.get("status", "unknown"),
            input_characters=page_info.get("input_characters"),
            output_characters=page_info.get("output_characters"),
            elapsed_seconds=page_info.get("elapsed_seconds"),
        ))
    
    return metrics


def format_summary(summary: SummaryMetrics) -> str:
    """Format summary metrics as human-readable string.
    
    Args:
        summary: SummaryMetrics object
        
    Returns:
        Formatted summary string
    """
    lines = [
        "=" * 70,
        "JOB SUMMARY STATISTICS",
        "=" * 70,
        "",
        f"Progress: {summary.progress_percent}% ({summary.completed_pages}/{summary.total_pages} pages)",
        "",
        "Status Breakdown:",
        f"  Completed:  {summary.completed_pages:4d}",
        f"  Failed:     {summary.failed_pages:4d}",
        f"  Interrupted:{summary.interrupted_pages:4d}",
        f"  Running:    {summary.running_pages:4d}",
        f"  Pending:    {summary.pending_pages:4d}",
        "",
    ]
    
    if summary.completed_pages > 0:
        lines.extend([
            "Timing Statistics (Completed Pages):",
        ])
        if summary.avg_elapsed_seconds is not None:
            lines.extend([
                f"  Average:    {summary.avg_elapsed_seconds:8.2f} sec",
                f"  Min:        {summary.min_elapsed_seconds:8.2f} sec",
                f"  Max:        {summary.max_elapsed_seconds:8.2f} sec",
                f"  Total:      {summary.total_elapsed_seconds:8.2f} sec",
            ])
        
        lines.extend([""])
        
        if summary.avg_input_characters is not None:
            lines.extend([
                "Input Characters (Completed Pages):",
                f"  Average:    {summary.avg_input_characters:8.0f} chars",
                f"  Min:        {summary.min_input_characters:8d} chars",
                f"  Max:        {summary.max_input_characters:8d} chars",
                f"  Total:      {summary.total_input_characters:8d} chars",
                "",
            ])
        
        if summary.avg_output_characters is not None:
            lines.extend([
                "Output Characters (Completed Pages):",
                f"  Average:    {summary.avg_output_characters:8.0f} chars",
                f"  Min:        {summary.min_output_characters:8d} chars",
                f"  Max:        {summary.max_output_characters:8d} chars",
                f"  Total:      {summary.total_output_characters:8d} chars",
                "",
            ])
        
        if summary.avg_compression_ratio is not None:
            lines.extend([
                "Compression Ratio (Output/Input):",
                f"  Average:    {summary.avg_compression_ratio:8.3f}",
                "",
            ])
    
    lines.append("=" * 70)
    return "\n".join(lines)


def format_summary_json(summary: SummaryMetrics) -> dict[str, Any]:
    """Convert summary metrics to JSON-serializable dict.
    
    Args:
        summary: SummaryMetrics object
        
    Returns:
        Dictionary suitable for JSON serialization
    """
    data = asdict(summary)
    # Convert float values to round to 2 decimal places for readability
    for key in list(data.keys()):
        if key.startswith("avg_") or key.startswith("total_") or key == "progress_percent":
            if isinstance(data[key], float):
                data[key] = round(data[key], 2)
        elif key.startswith("min_") or key.startswith("max_"):
            if isinstance(data[key], float):
                data[key] = round(data[key], 2)
    return data


def load_and_summarize(working_dir: Path, job_id: str) -> tuple[dict[str, Any], SummaryMetrics]:
    """Load job state and calculate summary in one call.
    
    Args:
        working_dir: Working directory containing jobs
        job_id: Job ID to load
        
    Returns:
        Tuple of (job_state, summary_metrics)
    """
    state = job.load(working_dir, job_id)
    summary = calculate_summary(state)
    return state, summary
