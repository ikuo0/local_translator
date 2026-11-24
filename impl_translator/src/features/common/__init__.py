"""Common data structures and functions shared across SR99xx features."""

from dataclasses import dataclass
from typing import Any


@dataclass
class JobStatus:
    """Shared job status representation."""
    
    job_id: str
    status: str  # created, running, completed, interrupted, error, completed_with_errors
    total_pages: int
    completed: int
    failed: int
    interrupted: int
    running: int
    progress_percent: float
    created_at: str
    updated_at: str
    elapsed_seconds: float
    
    @property
    def is_active(self) -> bool:
        """Check if job is still running."""
        return self.status in ("created", "running")
    
    @property
    def is_complete(self) -> bool:
        """Check if job has finished."""
        return self.status in ("completed", "completed_with_errors", "interrupted", "error")


@dataclass
class PageStatus:
    """Shared page status representation."""
    
    page: int
    status: str  # running, completed, failed, interrupted
    started_at: str
    finished_at: str
    elapsed_seconds: float
    input_characters: int
    output_characters: int
    llm_status: str  # completed, not_required, error_or_unavailable
    model: str
    ollama_host: str
    error: str | None = None


def calculate_progress(pages: dict[str, Any]) -> dict[str, int]:
    """Calculate progress statistics from pages dict."""
    completed = sum(1 for p in pages.values() if p.get("status") == "completed")
    failed = sum(1 for p in pages.values() if p.get("status") == "failed")
    interrupted = sum(1 for p in pages.values() if p.get("status") == "interrupted")
    running = sum(1 for p in pages.values() if p.get("status") == "running")
    
    return {
        "completed": completed,
        "failed": failed,
        "interrupted": interrupted,
        "running": running,
    }
