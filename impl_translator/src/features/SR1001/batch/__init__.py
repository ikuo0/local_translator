"""Build SR1001 job reports for the CLI and the Web API."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import yaml

from impl_translator.src.features.SR1001 import summary


def load_report(working_dir: Path, job_id: str) -> dict:
    """Build a report from one read of job.yaml."""
    state, metrics = summary.load_and_summarize(working_dir, job_id)
    data = state["data"]
    pages = data.get("pages", {})
    sf005 = data.get("sf005", {"status": "unknown"})
    export_status = sf005.get("status")
    if export_status == "progress" or metrics.running_pages:
        status = "running"
    elif export_status == "error":
        status = "interrupted" if sf005.get("error") == "Interrupted" else "failed"
    elif metrics.failed_pages or metrics.interrupted_pages:
        status = "failed" if metrics.failed_pages else "interrupted"
    elif metrics.pending_pages or not metrics.total_pages:
        status = "pending"
    elif export_status == "pending":
        status = "awaiting_export"
    elif export_status == "complete":
        status = "completed"
    else:
        status = data.get("status") or "pages_completed"

    return {
        "job_id": job_id,
        "status": status,
        "total_pages": metrics.total_pages,
        "completed": metrics.completed_pages,
        "failed": metrics.failed_pages,
        "interrupted": metrics.interrupted_pages,
        "running": metrics.running_pages,
        "pending": metrics.pending_pages,
        "progress_percent": metrics.progress_percent,
        "created_at": state.get("created_at"),
        "updated_at": state.get("updated_at"),
        "elapsed_seconds": data.get("elapsed_seconds"),
        "log_file": data.get("log_file"),
        "input_pdf": data.get("input_pdf"),
        "selection": data.get("selection"),
        "sf005": sf005,
        "pages": pages,
        "summary": summary.format_summary_json(metrics),
    }


def page_metrics(report: dict) -> list[dict]:
    """Expose individual page rows, preserving legacy metrics fields."""
    pages = report["pages"]
    rows = []
    for metrics in summary.calculate_page_metrics({"data": {"pages": pages}}):
        number = metrics.page_number
        page = pages.get(number, pages.get(str(number), {}))
        rows.append({
            **asdict(metrics),
            "stats": page.get("stats"),
            "error": page.get("error"),
        })
    return rows


def format_status(report: dict) -> str:
    """Format an overview suitable for repeated display with watch."""
    lines = [f"Job {report['job_id']} | {report['status']}"]
    selection = report["selection"]
    if selection:
        lines.append(f"Pages {selection['start_page']}–{selection['end_page']} of {selection['document_page_count']}")
    lines.extend([
        f"Progress: {report['completed']}/{report['total_pages']} ({report['progress_percent']}%)",
        f"Running: {report['running']}  Pending: {report['pending']}  "
        f"Failed: {report['failed']}  Interrupted: {report['interrupted']}",
        f"Updated: {report['updated_at'] or '-'}   Elapsed: {_seconds(report['elapsed_seconds'])}",
    ])
    metrics = report["summary"]
    if metrics["timed_completed_pages"]:
        lines.append(
            f"Page times ({metrics['timed_completed_pages']}): avg {_seconds(metrics['avg_elapsed_seconds'])}"
            f"  min {_seconds(metrics['min_elapsed_seconds'])}  max {_seconds(metrics['max_elapsed_seconds'])}"
            f"  sum {_seconds(metrics['total_elapsed_seconds'])}"
        )
    export = report["sf005"]
    lines.append(f"SF005: {export['status']}  {_seconds(export.get('stats', {}).get('duration_sec'))}")
    if export.get("error"):
        lines.append(f"  Error: {export['error']}")
    for name, path in export.get("outputs", {}).items():
        lines.append(f"  {name}: {path}")
    for number, page in report["pages"].items():
        if page.get("error"):
            lines.append(f"Page {number} ({page['status']}): {page['error']}")
    return "\n".join(lines)


def _seconds(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}s"


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect SR1000 jobs from job.yaml")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("status", "Show job and SF005 status"),
        ("summary", "Show job status and timing summary"),
        ("metrics", "Show page status and phase timings"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--working-dir", type=Path, required=True)
        command.add_argument("--job-id", required=True)
        command.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()
    try:
        report = load_report(args.working_dir.resolve(), args.job_id)
        if args.command == "metrics":
            rows = page_metrics(report)
            if args.json:
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                phases = ("sf001", "sf002", "sf003", "sf004")
                print(f"{'Page':>6} {'Status':>12} {'Total':>9} {'SF001':>9} {'SF002':>9} {'SF003':>9} {'SF004':>9}")
                for row in rows:
                    stats = (row["stats"] or {}).get("phases", {})
                    timings = [_seconds(row["elapsed_seconds"])]
                    timings.extend(_seconds(stats.get(phase, {}).get("duration_sec")) for phase in phases)
                    error = f"  {row['error']}" if row["error"] else ""
                    print(f"{row['page_number']:6d} {row['status']:>12} " + " ".join(f"{t:>9}" for t in timings) + error)
        elif args.json:
            output = report if args.command == "status" else {**report["summary"], "sf005": report["sf005"]}
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(format_status(report))
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0
