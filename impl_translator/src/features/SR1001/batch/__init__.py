"""SR1001: Batch operations for job summary statistics and monitoring."""

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

from impl_translator.src.features.SR1001 import summary


def main() -> int:
    """Main CLI entry point for SR1001 batch operations."""
    parser = argparse.ArgumentParser(
        description="SR1001 job summary and statistics"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")
    
    # Summary command
    summary_parser = subparsers.add_parser(
        "summary", 
        help="Display job summary statistics"
    )
    summary_parser.add_argument(
        "--working-dir",
        type=Path,
        required=True,
        help="Working directory containing jobs",
    )
    summary_parser.add_argument(
        "--job-id",
        required=True,
        help="Job ID to summarize",
    )
    summary_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of human-readable format",
    )
    
    # Page metrics command
    metrics_parser = subparsers.add_parser(
        "metrics",
        help="Display page-by-page metrics",
    )
    metrics_parser.add_argument(
        "--working-dir",
        type=Path,
        required=True,
        help="Working directory containing jobs",
    )
    metrics_parser.add_argument(
        "--job-id",
        required=True,
        help="Job ID to get metrics for",
    )
    metrics_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of human-readable format",
    )
    
    args = parser.parse_args()
    
    if args.command == "summary":
        return _cmd_summary(args)
    elif args.command == "metrics":
        return _cmd_metrics(args)
    elif args.command is None:
        parser.print_help()
        return 1
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


def _cmd_summary(args) -> int:
    """Handle summary command."""
    try:
        state, metrics = summary.load_and_summarize(args.working_dir.resolve(), args.job_id)
        
        if args.json:
            import json
            print(json.dumps(summary.format_summary_json(metrics), indent=2))
        else:
            print(summary.format_summary(metrics))
        
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def _cmd_metrics(args) -> int:
    """Handle metrics command."""
    try:
        state = summary.load_job_state(args.working_dir.resolve(), args.job_id)
        metrics = summary.calculate_page_metrics(state)
        
        if args.json:
            import json
            data = [asdict(m) for m in metrics]
            print(json.dumps(data, indent=2))
        else:
            # Human-readable format
            print(f"Page-by-page metrics for job {args.job_id}:")
            print("-" * 90)
            print(f"{'Page':>4} {'Status':>12} {'Input':>10} {'Output':>10} {'Time (s)':>10}")
            print("-" * 90)
            
            for m in metrics:
                input_str = str(m.input_characters) if m.input_characters is not None else "-"
                output_str = str(m.output_characters) if m.output_characters is not None else "-"
                time_str = f"{m.elapsed_seconds:.2f}" if m.elapsed_seconds is not None else "-"
                
                print(f"{m.page_number:4d} {m.status:>12} {input_str:>10} {output_str:>10} {time_str:>10}")
        
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
