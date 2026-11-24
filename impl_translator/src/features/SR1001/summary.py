"""Job summary statistics and metrics calculation."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
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
    timed_completed_pages: int = 0
    job_elapsed_seconds: float | None = None


CURRENT_PAGE_STATUS = {
    "complete": "completed",
    "error": "failed",
    "progress": "running",
}
PHASES = ("SF001_to_html", "SF002_preproc", "SF003_translate", "SF004_restore")


def elapsed_between(start: str | None, end: str | None) -> float | None:
    if not start or not end:
        return None
    try:
        seconds = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
    except (TypeError, ValueError):
        return None
    return seconds if seconds >= 0 else None


def page_status(page_info: dict[str, Any]) -> str:
    status = page_info.get("status", "pending")
    if status == "error" and page_info.get("error") == "Interrupted":
        return "interrupted"
    return CURRENT_PAGE_STATUS.get(status, status)


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        # SR1000 can be writing the file while the dashboard polls.
        return {}


def load_job_state(
    working_dir: Path, job_id: str, *, include_timings: bool = True,
) -> dict[str, Any]:
    """Read current SR1000 output and expose the legacy metrics fields."""
    state = job.load(working_dir, job_id)
    data = state["data"]
    selection = data.get("selection")
    if selection is None:
        return state

    data["page_count"] = selection["selected_page_count"]
    directory = job.job_directory(working_dir, job_id)
    data.setdefault("log_file", str(directory / "log.txt"))
    data["elapsed_seconds"] = elapsed_between(state.get("created_at"), state.get("updated_at"))
    metadata = None
    for number, page in data["pages"].items():
        page["status"] = page_status(page)
        if not include_timings or page["status"] != "completed":
            continue
        page_id = f"page_{int(number):06d}"
        saved = read_json(directory / "states" / f"{page_id}.json")
        steps = saved.get("steps", {})
        elapsed = elapsed_between(
            steps.get("sf001", {}).get("stats", {}).get("started_at"),
            steps.get("sf004", {}).get("stats", {}).get("finished_at"),
        )
        if elapsed is None:
            if metadata is None:
                metadata = read_json(directory / "metadata.json")
            phases = metadata.get(page_id, {}).get("phases", {})
            durations = [phases.get(phase, {}).get("duration_sec") for phase in PHASES]
            if all(isinstance(duration, (int, float)) for duration in durations):
                elapsed = sum(durations)
        page["elapsed_seconds"] = elapsed
    return state


def calculate_summary(state: dict[str, Any]) -> SummaryMetrics:
    """Calculate summary metrics from job state.
    
    Args:
        state: Job state dictionary loaded from job.yaml
        
    Returns:
        SummaryMetrics containing calculated statistics
    """
    data = state.get("data", {})
    pages = data.get("pages", {})
    total_pages = data.get("selection", {}).get("selected_page_count", data.get("page_count", len(pages)))
    
    # Count statuses
    completed_pages = []
    failed_pages = 0
    interrupted_pages = 0
    running_pages = 0
    pending_pages = 0
    
    for page_info in pages.values():
        status = page_status(page_info)
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
        timed_completed_pages=len(elapsed_times),
        job_elapsed_seconds=data.get("elapsed_seconds"),
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
            status=page_status(page_info),
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
    
    if summary.job_elapsed_seconds is not None:
        lines.extend([f"Job elapsed: {summary.job_elapsed_seconds:.2f} sec", ""])

    if summary.completed_pages > 0:
        lines.extend([
            f"Timing Statistics (Completed Pages, {summary.timed_completed_pages} timed):",
        ])
        if summary.avg_elapsed_seconds is not None:
            lines.extend([
                f"  Average:    {summary.avg_elapsed_seconds:8.2f} sec",
                f"  Min:        {summary.min_elapsed_seconds:8.2f} sec",
                f"  Max:        {summary.max_elapsed_seconds:8.2f} sec",
                f"  Page time sum: {summary.total_elapsed_seconds:8.2f} sec",
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
        if key.startswith("avg_") or key.startswith("total_") or key in {"progress_percent", "job_elapsed_seconds"}:
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
    state = load_job_state(working_dir, job_id)
    summary = calculate_summary(state)
    return state, summary
