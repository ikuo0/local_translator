import argparse
import sys
from pathlib import Path

import yaml

from . import create, load, update


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage file-based jobs")
    parser.add_argument("--working-dir", required=True, type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--create", action="store_true")
    action.add_argument("--update", action="store_true")
    action.add_argument("--get", action="store_true")
    parser.add_argument("--job-id")
    parser.add_argument("--sub-key")
    parser.add_argument("--data", help="YAML value")
    args = parser.parse_args()
    if not args.create and (not args.job_id or not args.sub_key):
        parser.error("--job-id and --sub-key are required for --get and --update")
    if args.update and args.data is None:
        parser.error("--data is required for --update")
    try:
        if args.create:
            print(create(args.working_dir))
        elif args.update:
            update(
                args.working_dir, args.job_id, args.sub_key, yaml.safe_load(args.data)
            )
        else:
            state = load(args.working_dir, args.job_id)
            if args.sub_key not in state["data"]:
                raise KeyError(f"Unknown sub-key: {args.sub_key}")
            print(
                yaml.safe_dump(
                    {
                        "job_id": state["job_id"],
                        "created_at": state["created_at"],
                        "updated_at": state["updated_at"],
                        args.sub_key: state["data"][args.sub_key],
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                end="",
            )
    except (OSError, ValueError, KeyError, RuntimeError, yaml.YAMLError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
